"""Allow approval = 'timeout': an URGENT high-priority assignment applied automatically after N minutes
without the coordinator's answer ("aprobada por tiempo"). See docs/dev/sirag_d_modelo.md, section 8.

Revision ID: 0005
Revises: 0004
"""
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE assignments DROP CONSTRAINT assignments_approval_check")
    op.execute("ALTER TABLE assignments ADD CONSTRAINT assignments_approval_check "
               "CHECK (approval IN ('auto','coordinator','timeout'))")


def downgrade() -> None:
    op.execute("ALTER TABLE assignments DROP CONSTRAINT assignments_approval_check")
    op.execute("ALTER TABLE assignments ADD CONSTRAINT assignments_approval_check "
               "CHECK (approval IN ('auto','coordinator'))")
