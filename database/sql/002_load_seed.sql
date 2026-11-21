-- Run from the repository root:  psql -d vela -f database/sql/002_load_seed.sql
BEGIN;
\copy districts              FROM 'database/seed/districts.csv'              WITH (FORMAT csv, HEADER true)
\copy subscription_plans     FROM 'database/seed/subscription_plans.csv'     WITH (FORMAT csv, HEADER true)
\copy services               FROM 'database/seed/services.csv'               WITH (FORMAT csv, HEADER true)
\copy institutions           FROM 'database/seed/institutions.csv'           WITH (FORMAT csv, HEADER true)
\copy institution_services   FROM 'database/seed/institution_services.csv'   WITH (FORMAT csv, HEADER true)
\copy persons                FROM 'database/seed/persons.csv'                WITH (FORMAT csv, HEADER true)
\copy patients               FROM 'database/seed/patients.csv'               WITH (FORMAT csv, HEADER true)
\copy family_members         FROM 'database/seed/family_members.csv'         WITH (FORMAT csv, HEADER true)
\copy consents               FROM 'database/seed/consents.csv'               WITH (FORMAT csv, HEADER true)
\copy caregivers             FROM 'database/seed/caregivers.csv'             WITH (FORMAT csv, HEADER true)
\copy caregiver_skills       FROM 'database/seed/caregiver_skills.csv'       WITH (FORMAT csv, HEADER true)
\copy users                  FROM 'database/seed/users.csv'                  WITH (FORMAT csv, HEADER true)
\copy care_plans             FROM 'database/seed/care_plans.csv'             WITH (FORMAT csv, HEADER true)
\copy service_requests (request_id, institution_id, patient_id, service_id, origin, priority, scheduled_for, created_at, status, status_reason) FROM 'database/seed/service_requests.csv' WITH (FORMAT csv, HEADER true)
\copy assignments            FROM 'database/seed/assignments.csv'            WITH (FORMAT csv, HEADER true)
\copy air_quality_stations   FROM 'data/reference/air_quality_stations.csv'  WITH (FORMAT csv, HEADER true)
\copy air_quality_readings   FROM 'data/reference/air_quality_hourly.csv'    WITH (FORMAT csv, HEADER true)
\copy traffic_hourly_profile FROM 'data/reference/traffic_hourly_profile.csv' WITH (FORMAT csv, HEADER true)
COMMIT;
ANALYZE;
