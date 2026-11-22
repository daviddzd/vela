"""Care plans adjusted by the physician (docs/spec/04): who created / ended each plan and which plan replaced it.

A change never edits a plan in place: the old plan is ended (active = false, ended_at/by) and a new one is created
(replaces), so the history stays and the worker uses the new plan from its next generation.
alerts.type gains 'care_plan': assigned future visits of a changed plan are reported to coordination.

Revision ID: 0009
Revises: 0008
"""
from alembic import op

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        ALTER TABLE care_plans
          ADD COLUMN created_by  text        REFERENCES users,
          ADD COLUMN created_at  timestamptz,
          ADD COLUMN ended_by    text        REFERENCES users,
          ADD COLUMN ended_at    timestamptz,
          ADD COLUMN replaces    text        REFERENCES care_plans""")
    op.execute("ALTER TABLE alerts DROP CONSTRAINT alerts_type_check")
    op.execute("""ALTER TABLE alerts ADD CONSTRAINT alerts_type_check CHECK (type IN
                  ('emergency','risk','contingency','anomaly','queue_delay','call_back','consent','care_plan'))""")
    op.execute("GRANT SELECT, INSERT, UPDATE ON care_plans, caregiver_unavailability TO vela_api")
    # entity_institution(): caregivers too (403 + audit for another institution's caregiver, 404 if none)
    op.execute("""
        CREATE OR REPLACE FUNCTION public.entity_institution(p_entity text, p_id text)
        RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
            SELECT CASE p_entity
                     WHEN 'patient'         THEN (SELECT institution_id FROM public.patients WHERE patient_id = p_id)
                     WHEN 'service_request' THEN (SELECT institution_id FROM public.service_requests WHERE request_id = p_id)
                     WHEN 'assignment'      THEN (SELECT institution_id FROM public.assignments WHERE assignment_id = p_id)
                     WHEN 'consent'         THEN (SELECT institution_id FROM public.consents WHERE consent_id = p_id)
                     WHEN 'caregiver'       THEN (SELECT institution_id FROM public.caregivers WHERE caregiver_id = p_id)
                   END
        $$
    """)


def downgrade() -> None:
    raise NotImplementedError("Rebuild from scratch: docker compose down -v && docker compose up -d")
