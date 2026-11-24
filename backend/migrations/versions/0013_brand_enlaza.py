"""Brand: "Vela" becomes "Enlaza · cuidado coordinado" (team decision, 23 Nov 2026). Only data people read:
the owner's display name. Internal names (roles, database, folders, images) stay "vela" (docs/brand.md).

Revision ID: 0013
Revises: 0012
"""
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE users SET display_name = 'Dirección Enlaza' WHERE display_name = 'Dirección Vela'")


def downgrade() -> None:
    op.execute("UPDATE users SET display_name = 'Dirección Vela' WHERE display_name = 'Dirección Enlaza'")
