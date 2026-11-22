"""Link care-plan requests to their plan and day, so the worker never creates the same visit twice.

Revision ID: 0003
Revises: 0002
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE service_requests ADD COLUMN care_plan_id text REFERENCES care_plans, "
               "ADD COLUMN plan_date date")
    # One request per care plan per day, whatever the worker restarts.
    op.execute("CREATE UNIQUE INDEX service_requests_one_per_plan_day ON service_requests (care_plan_id, plan_date) "
               "WHERE care_plan_id IS NOT NULL")


def downgrade() -> None:
    op.execute("DROP INDEX service_requests_one_per_plan_day")
    op.execute("ALTER TABLE service_requests DROP COLUMN plan_date, DROP COLUMN care_plan_id")
