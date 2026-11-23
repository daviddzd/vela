"""Relays: a service longer than any legal shift (SRV-04 / SRV-07, 12 h) covered by two consecutive people.

Rule in app/services/dispatcher.py (relay_options, same function in the operation and SIRAG-D).
- assignments.leg: 1 = first person (from the start until the end of their shift), 2 = the relay (from that moment
  until the end of the service). One ACTIVE assignment per request and leg.
- assignment_proposals: the relay person of each proposal (NULL = one person covers it all).
- v_service_requests: one row per request (leg 1); planned_end / finished_at are those of the whole service and
  relay_* describe the second person.
- alerts.type 'coverage': "Cobertura de la semana" (app/services/coverage.py), skills with nobody on shift.

Revision ID: 0011
Revises: 0010
"""
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE assignments ADD COLUMN leg smallint NOT NULL DEFAULT 1 CHECK (leg IN (1, 2))")
    op.execute("DROP INDEX assignments_one_active_per_request")
    op.execute("CREATE UNIQUE INDEX assignments_one_active_per_request_leg ON assignments (request_id, leg) "
               "WHERE status = 'active'")
    op.execute("""
        ALTER TABLE assignment_proposals
          ADD COLUMN relay_caregiver_id  text REFERENCES caregivers,
          ADD COLUMN relay_travel_min    numeric(6,1),
          ADD COLUMN relay_planned_start timestamptz,
          ADD COLUMN relay_planned_end   timestamptz,
          ADD CONSTRAINT relay_complete CHECK ((relay_caregiver_id IS NULL) = (relay_planned_start IS NULL)
                                               AND (relay_caregiver_id IS NULL) = (relay_planned_end IS NULL))
    """)
    op.execute("DROP VIEW v_service_requests")
    op.execute("""
        CREATE VIEW v_service_requests WITH (security_invoker = true) AS
        SELECT r.*, a.assignment_id, a.caregiver_id, a.approval, a.assigned_at, a.arrived_at,
               CASE WHEN b.assignment_id IS NULL THEN a.finished_at ELSE b.finished_at END AS finished_at,
               a.family_confirmed, a.planned_start, coalesce(b.planned_end, a.planned_end) AS planned_end,
               round(extract(epoch FROM (a.assigned_at - r.created_at)) / 60)::int   AS minutes_to_assign,
               round(extract(epoch FROM (a.arrived_at - r.scheduled_for)) / 60)::int AS minutes_late,
               round(extract(epoch FROM (CASE WHEN b.assignment_id IS NULL THEN a.finished_at ELSE b.finished_at END
                                         - a.arrived_at)) / 60)::int               AS minutes_on_site,
               b.assignment_id AS relay_assignment_id, b.caregiver_id AS relay_caregiver_id,
               CASE WHEN b.assignment_id IS NOT NULL THEN a.planned_end END AS relay_at
        FROM service_requests r
        LEFT JOIN assignments a ON a.request_id = r.request_id AND a.status = 'active' AND a.leg = 1
        LEFT JOIN assignments b ON b.request_id = r.request_id AND b.status = 'active' AND b.leg = 2
    """)
    op.execute("GRANT SELECT ON v_service_requests TO vela_api")
    op.execute("ALTER TABLE alerts DROP CONSTRAINT alerts_type_check")
    op.execute("""ALTER TABLE alerts ADD CONSTRAINT alerts_type_check CHECK (type IN
                  ('emergency','risk','contingency','anomaly','queue_delay','call_back','consent','care_plan','labor',
                   'coverage'))""")


def downgrade() -> None:
    raise NotImplementedError("Rebuild from scratch: docker compose down -v && docker compose up -d")
