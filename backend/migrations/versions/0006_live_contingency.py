"""Live contingency (docs/spec/06 "Contingencia en la operación real") and the /demo panel inputs.

- Demo scenarios never overwrite the calibrated history: their readings live in air_quality_scenario and the
  view v_air_quality_live puts them in front ONLY while their scenario run is active.
- contingency_events stays platform-wide and holds no personal data; each institution's proposal lives in
  contingency_proposals (RLS). Real (detected) and demo events are separate records (run_id).
- priority_overrides: temporary priority raise; the patient's base_priority is never modified.
- family_notices, traffic_conditions, caregiver_unavailability: applied changes / inputs.

Revision ID: 0006
Revises: 0005
"""
from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

TENANT = """USING (current_setting('app.institution_id', true) = '*'
                   OR institution_id = current_setting('app.institution_id', true))"""


def tenant_table(name: str) -> None:
    op.execute(f"ALTER TABLE {name} ENABLE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY tenant_isolation ON {name} {TENANT}")


def upgrade() -> None:
    op.execute("ALTER TABLE service_requests DROP CONSTRAINT service_requests_origin_check")
    op.execute("""ALTER TABLE service_requests ADD CONSTRAINT service_requests_origin_check CHECK (origin IN
                  ('care_plan','family','coordinator','voice_assistant','simulator','contingency','demo_scenario'))""")

    # ---- demo scenario runs and their readings (kept apart from the calibrated history) ----------------
    op.execute("""
        CREATE TABLE scenario_runs (
            run_id      text        PRIMARY KEY DEFAULT 'SC-' || substr(gen_random_uuid()::text, 1, 8),
            scenario    text        NOT NULL,
            origin      text        NOT NULL DEFAULT 'demo_scenario' CHECK (origin = 'demo_scenario'),
            started_by  text        REFERENCES users,
            started_at  timestamptz NOT NULL DEFAULT now(),
            ended_at    timestamptz,
            active      boolean     NOT NULL DEFAULT true
        )""")
    op.execute("CREATE UNIQUE INDEX scenario_runs_one_active ON scenario_runs (active) WHERE active")
    op.execute("""
        CREATE TABLE air_quality_scenario (
            run_id      text        NOT NULL REFERENCES scenario_runs,
            station_id  text        NOT NULL REFERENCES air_quality_stations,
            measured_at timestamptz NOT NULL,
            o3_ppb      numeric(6,1),
            pm25_ugm3   numeric(6,1),
            PRIMARY KEY (run_id, station_id, measured_at)
        )""")
    op.execute("""
        CREATE VIEW v_air_quality_live WITH (security_invoker = true) AS
        SELECT r.station_id, r.measured_at,
               coalesce(s.o3_ppb, r.o3_ppb)       AS o3_ppb,
               coalesce(s.pm25_ugm3, r.pm25_ugm3) AS pm25_ugm3,
               CASE WHEN s.run_id IS NULL THEN r.source ELSE 'scenario' END AS source,
               s.run_id
        FROM air_quality_readings r
        LEFT JOIN (SELECT a.* FROM air_quality_scenario a JOIN scenario_runs sr ON sr.run_id = a.run_id AND sr.active) s
               ON s.station_id = r.station_id AND s.measured_at = r.measured_at""")

    op.execute("""
        CREATE TABLE traffic_conditions (
            condition_id      text        PRIMARY KEY DEFAULT 'TR-' || substr(gen_random_uuid()::text, 1, 8),
            extra_factor      numeric(4,2) NOT NULL DEFAULT 1,
            blocked_districts text[]      NOT NULL DEFAULT '{}',
            extra_minutes     integer     NOT NULL DEFAULT 0,
            origin            text        NOT NULL CHECK (origin IN ('detected','demo_scenario')),
            run_id            text        REFERENCES scenario_runs,
            active            boolean     NOT NULL DEFAULT true,
            started_at        timestamptz NOT NULL DEFAULT now(),
            ended_at          timestamptz
        )""")

    # ---- events: platform-wide, no personal data; real and demo never share a record -----------------
    op.execute("""
        ALTER TABLE contingency_events
          ADD COLUMN run_id        text REFERENCES scenario_runs,
          ADD COLUMN districts     text[] NOT NULL DEFAULT '{}',
          ADD COLUMN stations      jsonb  NOT NULL DEFAULT '[]',
          ADD COLUMN below_streak  integer NOT NULL DEFAULT 0,
          ADD COLUMN last_checked_hour timestamptz""")
    op.execute("CREATE UNIQUE INDEX contingency_one_open_real ON contingency_events ((true)) "
               "WHERE ended_at IS NULL AND run_id IS NULL")
    op.execute("CREATE UNIQUE INDEX contingency_one_open_per_run ON contingency_events (run_id) "
               "WHERE ended_at IS NULL AND run_id IS NOT NULL")

    # ---- per-institution proposal, decision effects -----------------------------------------------------
    op.execute("""
        CREATE TABLE contingency_proposals (
            proposal_id     bigserial   PRIMARY KEY,
            event_id        text        NOT NULL REFERENCES contingency_events,
            institution_id  text        NOT NULL REFERENCES institutions,
            kind            text        NOT NULL CHECK (kind IN ('raise_priority','advance_oxygen','notify_family','recalculate_routes')),
            patient_id      text        REFERENCES patients,
            request_id      text        REFERENCES service_requests,
            assignment_id   text        REFERENCES assignments,
            reason          text        NOT NULL,          -- user-facing (Spanish)
            payload         jsonb       NOT NULL DEFAULT '{}',
            status          text        NOT NULL DEFAULT 'proposed'
                                        CHECK (status IN ('proposed','approved','rejected','applied','reverted')),
            created_at      timestamptz NOT NULL DEFAULT now(),
            decided_by      text        REFERENCES users,
            decided_at      timestamptz
        )""")
    op.execute("CREATE INDEX ON contingency_proposals (event_id, institution_id)")
    tenant_table("contingency_proposals")
    op.execute("""
        CREATE TABLE priority_overrides (
            override_id     bigserial   PRIMARY KEY,
            patient_id      text        NOT NULL REFERENCES patients,
            institution_id  text        NOT NULL REFERENCES institutions,
            event_id        text        NOT NULL REFERENCES contingency_events,
            priority        text        NOT NULL CHECK (priority IN ('high','medium','low')),
            active          boolean     NOT NULL DEFAULT true,
            created_at      timestamptz NOT NULL DEFAULT now(),
            ended_at        timestamptz
        )""")
    op.execute("CREATE INDEX ON priority_overrides (patient_id) WHERE active")
    tenant_table("priority_overrides")
    op.execute("""
        CREATE TABLE family_notices (
            notice_id       bigserial   PRIMARY KEY,
            institution_id  text        NOT NULL REFERENCES institutions,
            patient_id      text        NOT NULL REFERENCES patients,
            event_id        text        REFERENCES contingency_events,
            message         text        NOT NULL,          -- user-facing (Spanish)
            created_at      timestamptz NOT NULL DEFAULT now()
        )""")
    tenant_table("family_notices")
    op.execute("""
        CREATE TABLE caregiver_unavailability (
            unavailability_id bigserial  PRIMARY KEY,
            caregiver_id    text        NOT NULL REFERENCES caregivers,
            institution_id  text        NOT NULL REFERENCES institutions,
            reason          text        NOT NULL,
            origin          text        NOT NULL CHECK (origin IN ('coordinator','demo_scenario')),
            run_id          text        REFERENCES scenario_runs,
            starts_at       timestamptz NOT NULL DEFAULT now(),
            ends_at         timestamptz,
            active          boolean     NOT NULL DEFAULT true
        )""")
    tenant_table("caregiver_unavailability")
    # Only the new tables (never "ALL TABLES": that would give back UPDATE on the append-only audit_log).
    op.execute("""GRANT SELECT, INSERT, UPDATE ON scenario_runs, air_quality_scenario, traffic_conditions,
                  contingency_proposals, priority_overrides, family_notices, caregiver_unavailability TO vela_api""")
    op.execute("GRANT SELECT ON v_air_quality_live TO vela_api")
    op.execute("GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO vela_api")


def downgrade() -> None:
    raise NotImplementedError("Rebuild from scratch: docker compose down -v && docker compose up -d")
