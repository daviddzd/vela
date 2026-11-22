"""Baseline flag for the seed history and broad multimorbidity in the district view.

- service_requests.is_baseline: TRUE for the 2,864 seed requests (the 30-day history "before Vela").
  Everything created by the running system is FALSE ("con Vela"). Panorama-AM compares both.
- v_district_population gains multimorbidity_broad_pct: 2+ of the 9 chronic diseases + obesity +
  depressive symptoms (the generator's "amplia" definition). Still aggregated, no names, cells >= 10.

Revision ID: 0004
Revises: 0003
"""
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None

CHRONIC = ("p.diabetes::int + p.hypertension::int + p.high_cholesterol::int + p.heart_disease::int + p.stroke::int"
           " + p.kidney_disease::int + p.arthritis::int + p.chronic_lung_disease::int + p.cancer::int")


def upgrade() -> None:
    op.execute("ALTER TABLE service_requests ADD COLUMN is_baseline boolean NOT NULL DEFAULT false")
    # Seed ids end at REQ-02864; the sequences of migration 0002 continue after them.
    op.execute("UPDATE service_requests SET is_baseline = true WHERE request_id <= 'REQ-02864'")

    op.execute(f"""
        CREATE OR REPLACE VIEW v_district_population AS
        SELECT d.district_id, d.name AS district_name, d.population_60_plus_2020,
               count(*)                                                        AS persons_60_plus,
               round(100.0 * avg((vp.multimorbidity)::int), 1)                 AS multimorbidity_pct,
               round(100.0 * avg((vp.dependency_level IN ('moderate','severe'))::int), 1)
                                                                               AS dependency_moderate_severe_pct,
               round(100.0 * avg((vp.pollution_sensitive)::int), 1)            AS pollution_sensitive_pct,
               round(100.0 * avg((vp.age_group = '80+')::int), 1)              AS age_80_plus_pct,
               round(avg(vp.chronic_disease_count), 2)                         AS avg_chronic_diseases,
               round(100.0 * avg((vp.chronic_disease_count + vp.obesity::int + vp.depressive_symptoms::int >= 2)::int), 1)
                                                                               AS multimorbidity_broad_pct
        FROM districts d
        JOIN (SELECT p.*, ({CHRONIC}) AS chronic_disease_count, ({CHRONIC}) >= 2 AS multimorbidity,
                     (p.chronic_lung_disease OR p.heart_disease OR p.stroke) AS pollution_sensitive,
                     CASE WHEN age(current_date, p.birth_date) >= interval '80 years' THEN '80+' END AS age_group
              FROM persons p) vp ON vp.district_id = d.district_id
        GROUP BY d.district_id, d.name, d.population_60_plus_2020
        HAVING count(*) >= 10
    """)


def downgrade() -> None:
    raise NotImplementedError("Rebuild from scratch: docker compose down -v && docker compose up -d")
