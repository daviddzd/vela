"""Privacy (docs/spec/11): consents registered / revoked by coordination, and ARCO rights requests.

- consents: who recorded it and when, and the revocation (revoked_at/by/reason). A revoked consent has
  granted = false, so v_consents.is_valid is false at once and every API check blocks the function.
  The row stays (UNIQUE patient+type): registering it again updates it; the history is in audit_log.
- arco_requests: access / rectification / cancellation / opposition requests with a folio, the date received
  and the legal due date (LFPDPPP art. 31: 20 business days to answer). Tenant-isolated (RLS).
- alerts.type gains 'consent' (coordination is told what a revocation changed).

Revision ID: 0008
Revises: 0007
"""
from alembic import op

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

TENANT = """USING (current_setting('app.institution_id', true) = '*'
                   OR institution_id = current_setting('app.institution_id', true))"""


def upgrade() -> None:
    op.execute("""
        ALTER TABLE consents
          ADD COLUMN recorded_by   text        REFERENCES users,
          ADD COLUMN recorded_at   timestamptz,
          ADD COLUMN revoked_at    timestamptz,
          ADD COLUMN revoked_by    text        REFERENCES users,
          ADD COLUMN revoke_reason text,
          ADD CONSTRAINT consents_revoked_is_not_granted CHECK (revoked_at IS NULL OR NOT granted)""")
    op.execute("ALTER TABLE alerts DROP CONSTRAINT alerts_type_check")
    op.execute("""ALTER TABLE alerts ADD CONSTRAINT alerts_type_check CHECK (type IN
                  ('emergency','risk','contingency','anomaly','queue_delay','call_back','consent'))""")
    op.execute("CREATE SEQUENCE arco_number_seq")
    op.execute("""
        CREATE TABLE arco_requests (
            arco_id         text        PRIMARY KEY DEFAULT 'ARCO-' || lpad(nextval('arco_number_seq')::text, 5, '0'),
            institution_id  text        NOT NULL REFERENCES institutions,
            patient_id      text        REFERENCES patients,             -- whose data (NULL = the user's own account)
            requested_by    text        NOT NULL REFERENCES users,
            right_type      text        NOT NULL CHECK (right_type IN ('access','rectification','cancellation','opposition')),
            description     text        NOT NULL CHECK (length(description) BETWEEN 10 AND 2000),
            contact         text        NOT NULL CHECK (length(contact) BETWEEN 3 AND 200),
            received_at     timestamptz NOT NULL DEFAULT now(),
            due_on          date        NOT NULL,                        -- 20 business days (art. 31)
            status          text        NOT NULL DEFAULT 'received' CHECK (status IN ('received','in_review','answered'))
        )""")
    op.execute("ALTER TABLE arco_requests ENABLE ROW LEVEL SECURITY")
    op.execute(f"CREATE POLICY tenant_isolation ON arco_requests {TENANT}")
    op.execute("GRANT SELECT, INSERT, UPDATE ON arco_requests, consents TO vela_api")
    op.execute("GRANT USAGE ON SEQUENCE arco_number_seq TO vela_api")
    # entity_institution(): consents too, so a revocation of another institution's consent is told apart
    # from "does not exist" (403 + audit vs 404)
    op.execute("""
        CREATE OR REPLACE FUNCTION public.entity_institution(p_entity text, p_id text)
        RETURNS text LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp
        AS $$
            SELECT CASE p_entity
                     WHEN 'patient'         THEN (SELECT institution_id FROM public.patients WHERE patient_id = p_id)
                     WHEN 'service_request' THEN (SELECT institution_id FROM public.service_requests WHERE request_id = p_id)
                     WHEN 'assignment'      THEN (SELECT institution_id FROM public.assignments WHERE assignment_id = p_id)
                     WHEN 'consent'         THEN (SELECT institution_id FROM public.consents WHERE consent_id = p_id)
                   END
        $$
    """)


def downgrade() -> None:
    raise NotImplementedError("Rebuild from scratch: docker compose down -v && docker compose up -d")
