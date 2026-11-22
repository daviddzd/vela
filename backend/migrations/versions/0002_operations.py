"""Operations (step 3): privacy fixes, aggregated population views, assignment windows that can
never overlap, high-priority proposals, id sequences and alert codes.

See docs/dev/decisiones_paso_3.md for the reasoning behind each block.

Revision ID: 0002
Revises: 0001
"""
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None

TENANT_POLICY = """USING (current_setting('app.institution_id', true) = '*'
                          OR institution_id = current_setting('app.institution_id', true))"""


def upgrade() -> None:
    # 1. Privacy: persons under RLS. A person is visible only if they are a patient of the session's
    #    institution ('*' = owner, sees the whole synthetic population).
    op.execute("ALTER TABLE persons ENABLE ROW LEVEL SECURITY")
    op.execute("""
        CREATE POLICY tenant_isolation ON persons
        USING (current_setting('app.institution_id', true) = '*'
               OR EXISTS (SELECT 1 FROM patients pa
                          WHERE pa.person_id = persons.person_id
                            AND pa.institution_id = current_setting('app.institution_id', true)))
    """)

    # 2. Privacy leak fix: views ran with their OWNER's rights and skipped RLS. With security_invoker
    #    they apply the RLS of whoever queries them (vela_api).
    for view in ("v_persons", "v_patients", "v_consents", "v_air_quality_24h"):
        op.execute(f"ALTER VIEW {view} SET (security_invoker = true)")

    # 3. Aggregated population views for Panorama-AM (step 5). NO names, NO ids: only counts and
    #    percentages per district. They intentionally run with owner rights (they must read the whole
    #    synthetic population) and hide any district with fewer than 10 people (small-cell rule).
    op.execute("""
        CREATE VIEW v_district_population AS
        SELECT d.district_id, d.name AS district_name, d.population_60_plus_2020,
               count(*)                                                        AS persons_60_plus,
               round(100.0 * avg((vp.multimorbidity)::int), 1)                 AS multimorbidity_pct,
               round(100.0 * avg((vp.dependency_level IN ('moderate','severe'))::int), 1)
                                                                               AS dependency_moderate_severe_pct,
               round(100.0 * avg((vp.pollution_sensitive)::int), 1)            AS pollution_sensitive_pct,
               round(100.0 * avg((vp.age_group = '80+')::int), 1)              AS age_80_plus_pct,
               round(avg(vp.chronic_disease_count), 2)                         AS avg_chronic_diseases
        FROM districts d
        JOIN (SELECT p.*,
                     (p.diabetes::int + p.hypertension::int + p.high_cholesterol::int + p.heart_disease::int
                      + p.stroke::int + p.kidney_disease::int + p.arthritis::int
                      + p.chronic_lung_disease::int + p.cancer::int) AS chronic_disease_count,
                     (p.diabetes::int + p.hypertension::int + p.high_cholesterol::int + p.heart_disease::int
                      + p.stroke::int + p.kidney_disease::int + p.arthritis::int
                      + p.chronic_lung_disease::int + p.cancer::int) >= 2 AS multimorbidity,
                     (p.chronic_lung_disease OR p.heart_disease OR p.stroke) AS pollution_sensitive,
                     CASE WHEN age(current_date, p.birth_date) >= interval '80 years' THEN '80+' END AS age_group
              FROM persons p) vp ON vp.district_id = d.district_id
        GROUP BY d.district_id, d.name, d.population_60_plus_2020
        HAVING count(*) >= 10
    """)
    op.execute("""
        CREATE VIEW v_population_conditions AS
        SELECT c.condition, round(100.0 * avg(c.present::int), 1) AS prevalence_pct, count(*) AS persons
        FROM persons p
        CROSS JOIN LATERAL (VALUES
            ('diabetes', p.diabetes), ('hypertension', p.hypertension),
            ('high_cholesterol', p.high_cholesterol), ('heart_disease', p.heart_disease),
            ('stroke', p.stroke), ('kidney_disease', p.kidney_disease),
            ('chronic_lung_disease', p.chronic_lung_disease), ('arthritis', p.arthritis),
            ('cancer', p.cancer), ('obesity', p.obesity), ('depressive_symptoms', p.depressive_symptoms),
            ('fall_last_12m', p.fall_last_12m), ('frailty', p.frailty)) AS c(condition, present)
        GROUP BY c.condition
        HAVING count(*) >= 10
    """)
    op.execute("GRANT SELECT ON v_district_population, v_population_conditions TO vela_api")

    # 4. Assignments: planned window + status. Seed history keeps planned_* NULL (it only has real
    #    arrival/finish times). New assignments always fill them.
    op.execute("""
        ALTER TABLE assignments
          ADD COLUMN planned_start timestamptz,
          ADD COLUMN planned_end   timestamptz,
          ADD COLUMN travel_min    numeric(6,1),
          ADD COLUMN status        text NOT NULL DEFAULT 'active'
                                   CHECK (status IN ('active','cancelled','reassigned')),
          ADD CONSTRAINT planned_window_complete
              CHECK ((planned_start IS NULL) = (planned_end IS NULL) AND
                     (planned_start IS NULL OR planned_end > planned_start))
    """)
    # One ACTIVE assignment per request (reassignments keep the old row as 'reassigned').
    op.execute("ALTER TABLE assignments DROP CONSTRAINT assignments_request_id_key")
    op.execute("CREATE UNIQUE INDEX assignments_one_active_per_request ON assignments (request_id) "
               "WHERE status = 'active'")
    # The database itself forbids two active planned windows of the same caregiver from overlapping,
    # even if two requests are dispatched at the same instant. Partial: seed rows (planned NULL) and
    # cancelled/reassigned rows do not count.
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")
    op.execute("""
        ALTER TABLE assignments ADD CONSTRAINT no_caregiver_overlap
        EXCLUDE USING gist (caregiver_id WITH =, tstzrange(planned_start, planned_end) WITH &&)
        WHERE (planned_start IS NOT NULL AND status = 'active')
    """)
    # v_service_requests must only join the active assignment now that history rows exist.
    op.execute("DROP VIEW v_service_requests")
    op.execute("""
        CREATE VIEW v_service_requests WITH (security_invoker = true) AS
        SELECT r.*, a.assignment_id, a.caregiver_id, a.approval, a.assigned_at, a.arrived_at, a.finished_at,
               a.family_confirmed, a.planned_start, a.planned_end,
               round(extract(epoch FROM (a.assigned_at - r.created_at)) / 60)::int   AS minutes_to_assign,
               round(extract(epoch FROM (a.arrived_at - r.scheduled_for)) / 60)::int AS minutes_late,
               round(extract(epoch FROM (a.finished_at - a.arrived_at)) / 60)::int   AS minutes_on_site
        FROM service_requests r
        LEFT JOIN assignments a ON a.request_id = r.request_id AND a.status = 'active'
    """)

    # 5. Proposals for high-priority requests: proposed candidate (rank 1) + 2 alternatives.
    op.execute("""
        CREATE TABLE assignment_proposals (
            proposal_id     bigserial   PRIMARY KEY,
            request_id      text        NOT NULL REFERENCES service_requests,
            institution_id  text        NOT NULL REFERENCES institutions,
            rank            smallint    NOT NULL CHECK (rank BETWEEN 1 AND 3),
            caregiver_id    text        NOT NULL REFERENCES caregivers,
            travel_min      numeric(6,1) NOT NULL,
            planned_start   timestamptz NOT NULL,
            planned_end     timestamptz NOT NULL,
            policy          text        NOT NULL,
            status          text        NOT NULL DEFAULT 'open'
                                        CHECK (status IN ('open','approved','superseded')),
            created_at      timestamptz NOT NULL DEFAULT now()
        )
    """)
    op.execute("CREATE INDEX ON assignment_proposals (request_id) WHERE status = 'open'")
    op.execute("ALTER TABLE assignment_proposals ENABLE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY tenant_isolation ON assignment_proposals {TENANT_POLICY}")

    # 6. Alerts: link to the request and a code, so the worker never creates the same alert twice.
    op.execute("ALTER TABLE alerts ADD COLUMN request_id text REFERENCES service_requests, "
               "ADD COLUMN code text")
    op.execute("CREATE UNIQUE INDEX alerts_one_per_request_code ON alerts (request_id, code) "
               "WHERE request_id IS NOT NULL")

    # 7. Id sequences continuing the seed numbering (REQ-02864 → REQ-02865 ...).
    for table, column, prefix, seq in (("service_requests", "request_id", "REQ-", "request_number_seq"),
                                       ("assignments", "assignment_id", "ASG-", "assignment_number_seq")):
        op.execute(f"CREATE SEQUENCE {seq}")
        op.execute(f"SELECT setval('{seq}', (SELECT coalesce(max(substr({column}, 5)::int), 0) + 1 "
                   f"FROM {table}), false)")
        op.execute(f"ALTER TABLE {table} ALTER COLUMN {column} "
                   f"SET DEFAULT '{prefix}' || lpad(nextval('{seq}')::text, 5, '0')")
    op.execute("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO vela_api")
    op.execute("GRANT SELECT, INSERT, UPDATE ON assignment_proposals TO vela_api")

    # 8. entity_institution(): two more entities in the fixed list.
    op.execute("""
        CREATE OR REPLACE FUNCTION public.entity_institution(p_entity text, p_id text)
        RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
            SELECT CASE p_entity
                     WHEN 'patient'         THEN (SELECT institution_id FROM public.patients WHERE patient_id = p_id)
                     WHEN 'service_request' THEN (SELECT institution_id FROM public.service_requests WHERE request_id = p_id)
                     WHEN 'assignment'      THEN (SELECT institution_id FROM public.assignments WHERE assignment_id = p_id)
                   END
        $$
    """)


def downgrade() -> None:
    raise NotImplementedError("Rebuild from scratch: docker compose down -v && docker compose up -d")
