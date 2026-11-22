"""Add entity_institution(): tells the API which institution owns an id, nothing else.

Why: with row-level security a patient of another institution is simply invisible to vela_api,
so the API could only answer 404. To answer 403 and record the attempt in audit_log, the API needs
to know that the id exists elsewhere. See docs/dev/decisiones_paso_1_2.md.

Safety:
- SECURITY DEFINER runs with the owner's rights (bypasses RLS) but returns ONLY institution_id.
- SET search_path = public, pg_temp: nobody can plant a fake `patients` table in another schema
  (pg_temp goes last so temporary objects can never shadow ours).
- Fixed list of entities via CASE: any other entity name returns NULL, never an error and never
  dynamic SQL.
- REVOKE ALL FROM PUBLIC, then GRANT EXECUTE only to vela_api.

Revision ID: 0001
Revises: (baseline = database/sql/001-005)
"""
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE OR REPLACE FUNCTION public.entity_institution(p_entity text, p_id text)
        RETURNS text
        LANGUAGE sql
        STABLE
        SECURITY DEFINER
        SET search_path = public, pg_temp
        AS $$
            SELECT CASE p_entity
                     WHEN 'patient' THEN (SELECT p.institution_id FROM public.patients p
                                          WHERE p.patient_id = p_id)
                     -- add new entities here, one WHEN per table
                   END
        $$
    """)
    op.execute("REVOKE ALL ON FUNCTION public.entity_institution(text, text) FROM PUBLIC")
    op.execute("GRANT EXECUTE ON FUNCTION public.entity_institution(text, text) TO vela_api")


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS public.entity_institution(text, text)")
