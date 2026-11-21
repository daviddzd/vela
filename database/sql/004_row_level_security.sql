-- Tenant isolation: each session only sees rows of its institution.
-- The API runs, per request:   SET app.institution_id = 'INS-A';    owner role uses '*'.
-- Without the setting, queries return no rows (fail closed). Applies to roles that do not own the tables
-- (create a dedicated role for the API, e.g. vela_api).
SET client_min_messages = warning;

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['institutions','institution_services','patients','family_members','consents','caregivers',
                           'care_plans','service_requests','assignments','voice_reports','contingency_decisions','invoices']
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS tenant_isolation ON %I', t);
    EXECUTE format($p$CREATE POLICY tenant_isolation ON %I
                     USING (current_setting('app.institution_id', true) = '*'
                            OR institution_id = current_setting('app.institution_id', true))$p$, t);
  END LOOP;
  -- alerts: platform-wide alerts (institution_id NULL) are visible to everyone
  ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
  DROP POLICY IF EXISTS tenant_isolation ON alerts;
  CREATE POLICY tenant_isolation ON alerts
    USING (current_setting('app.institution_id', true) = '*' OR institution_id IS NULL
           OR institution_id = current_setting('app.institution_id', true));
END $$;
