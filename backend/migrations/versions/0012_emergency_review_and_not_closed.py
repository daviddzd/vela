"""Two levels of voice emergency, and visits nobody closed.

- alerts.type 'emergency_review': a voice note that ONLY the classifier rated as emergency (no rule fired). The
  person saw the amber notice with 911; coordination must contact the family and say what it was. If nobody
  answers within `classifier_only.escalate_after_minutes` (config/emergency_rules.yaml) it escalates to Dirección.
  New columns: escalate_at (deadline), escalated_at, resolved_at, resolution ('emergency' | 'not_emergency').
- alerts.type 'visit_not_closed' and service_requests.status 'not_closed': a visit in progress whose planned end
  passed more than `dispatch.not_closed_after_minutes` ago (someone forgot "Terminé"); the worker marks it and alerts.

Revision ID: 0012
Revises: 0011
"""
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None

TYPES = ("'emergency','risk','contingency','anomaly','queue_delay','call_back','consent','care_plan','labor',"
         "'coverage'")
STATUSES = ("'registered','validated','queued','assigned','in_progress','completed','closed','rejected','cancelled',"
            "'unattended'")


def upgrade() -> None:
    op.execute("ALTER TABLE alerts DROP CONSTRAINT alerts_type_check")
    op.execute(f"ALTER TABLE alerts ADD CONSTRAINT alerts_type_check CHECK (type IN ({TYPES},'emergency_review','visit_not_closed'))")
    op.execute("""
        ALTER TABLE alerts
          ADD COLUMN escalate_at  timestamptz,
          ADD COLUMN escalated_at timestamptz,
          ADD COLUMN resolved_at  timestamptz,
          ADD COLUMN resolution   text CHECK (resolution IN ('emergency', 'not_emergency'))""")
    op.execute("ALTER TABLE service_requests DROP CONSTRAINT service_requests_status_check")
    op.execute(f"ALTER TABLE service_requests ADD CONSTRAINT service_requests_status_check CHECK (status IN ({STATUSES},'not_closed'))")


def downgrade() -> None:
    op.execute("UPDATE service_requests SET status = 'in_progress' WHERE status = 'not_closed'")
    op.execute("ALTER TABLE service_requests DROP CONSTRAINT service_requests_status_check")
    op.execute(f"ALTER TABLE service_requests ADD CONSTRAINT service_requests_status_check CHECK (status IN ({STATUSES}))")
    op.execute("DELETE FROM alerts WHERE type IN ('emergency_review', 'visit_not_closed')")
    op.execute("ALTER TABLE alerts DROP COLUMN escalate_at, DROP COLUMN escalated_at, DROP COLUMN resolved_at, DROP COLUMN resolution")
    op.execute("ALTER TABLE alerts DROP CONSTRAINT alerts_type_check")
    op.execute(f"ALTER TABLE alerts ADD CONSTRAINT alerts_type_check CHECK (type IN ({TYPES}))")
