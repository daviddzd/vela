-- Enlaza (internal name: vela) · database schema (PostgreSQL 16)
-- Run order: 001_schema.sql -> 002_load_seed.sql -> 003_views.sql -> 004_row_level_security.sql -> 005_postgis.sql (optional)

BEGIN;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- Reference data ---------------------------------------------------------------------------------

CREATE TABLE districts (                                   -- CDMX alcaldías
    district_id              char(5)      PRIMARY KEY,     -- INEGI geostatistical key (09 + municipality)
    name                     text         NOT NULL UNIQUE,
    population_60_plus_2020  integer      NOT NULL CHECK (population_60_plus_2020 >= 0),
    lat                      numeric(8,5) NOT NULL,
    lon                      numeric(8,5) NOT NULL,
    indigenous_language_pct  numeric(4,2)
);

CREATE TABLE subscription_plans (
    plan_id            text    PRIMARY KEY,
    name               text    NOT NULL,                   -- user-facing (Spanish)
    patient_limit      integer CHECK (patient_limit > 0),  -- NULL = unlimited
    monthly_price_mxn  integer NOT NULL CHECK (monthly_price_mxn >= 0)
);

CREATE TABLE services (
    service_id           text    PRIMARY KEY,
    name                 text    NOT NULL,                 -- user-facing (Spanish)
    required_skill       text    NOT NULL CHECK (required_skill IN ('physician','nursing','therapy','caregiving')),
    duration_min         integer NOT NULL CHECK (duration_min > 0),
    reference_price_mxn  integer CHECK (reference_price_mxn >= 0),
    min_price_mxn        integer CHECK (min_price_mxn >= 0),
    max_price_mxn        integer CHECK (max_price_mxn >= min_price_mxn)
);

CREATE TABLE air_quality_stations (
    station_id       text         PRIMARY KEY,
    name             text         NOT NULL,
    district_id      char(5)      NOT NULL REFERENCES districts,
    lat              numeric(8,5) NOT NULL,
    lon              numeric(8,5) NOT NULL,
    o3_factor        numeric(4,2) NOT NULL DEFAULT 1,
    pm25_factor      numeric(4,2) NOT NULL DEFAULT 1,
    location_source  text         NOT NULL CHECK (location_source IN ('approximate','official'))
);

CREATE TABLE air_quality_readings (
    station_id   text        NOT NULL REFERENCES air_quality_stations,
    measured_at  timestamptz NOT NULL,
    o3_ppb       numeric(6,1),
    pm25_ugm3    numeric(6,1),
    source       text        NOT NULL CHECK (source IN ('synthetic_calibrated','simat','scenario')),
    PRIMARY KEY (station_id, measured_at)
);
CREATE INDEX ON air_quality_readings (measured_at);

CREATE TABLE traffic_hourly_profile (
    day_type             text         NOT NULL CHECK (day_type IN ('weekday','weekend')),
    hour                 smallint     NOT NULL CHECK (hour BETWEEN 0 AND 23),
    congestion_pct       numeric(5,1) NOT NULL,
    avg_speed_kmh        numeric(4,1) NOT NULL,
    travel_time_factor   numeric(5,3) NOT NULL,
    free_flow_speed_kmh  numeric(4,1) NOT NULL,
    PRIMARY KEY (day_type, hour)
);

-- Institutions (tenants) -------------------------------------------------------------------------

CREATE TABLE institutions (
    institution_id  text    PRIMARY KEY,
    name            text    NOT NULL UNIQUE,
    type            text    NOT NULL CHECK (type IN ('clinic','residence','day_center','home_care_network')),
    district_id     char(5) NOT NULL REFERENCES districts,
    schedule        text    NOT NULL CHECK (schedule IN ('day','24h')),
    plan_id         text    NOT NULL REFERENCES subscription_plans,
    contract_date   date    NOT NULL,
    active          boolean NOT NULL DEFAULT true
);

CREATE TABLE institution_services (
    institution_id  text    NOT NULL REFERENCES institutions,
    service_id      text    NOT NULL REFERENCES services,
    duration_min    integer NOT NULL CHECK (duration_min > 0),   -- editable by the institution
    price_mxn       integer CHECK (price_mxn >= 0),              -- NULL = price pending
    active          boolean NOT NULL DEFAULT true,
    PRIMARY KEY (institution_id, service_id)
);

-- People and patients (CRM) ----------------------------------------------------------------------

CREATE TABLE persons (
    person_id               text         PRIMARY KEY,
    first_name              text         NOT NULL,
    paternal_surname        text         NOT NULL,
    maternal_surname        text         NOT NULL,
    sex                     char(1)      NOT NULL CHECK (sex IN ('F','M')),
    birth_date              date         NOT NULL,
    district_id             char(5)      NOT NULL REFERENCES districts,
    lat                     numeric(8,5) NOT NULL,
    lon                     numeric(8,5) NOT NULL,
    marital_status          text         NOT NULL CHECK (marital_status IN ('married_union','widowed','single','divorced_separated')),
    health_insurance        text         NOT NULL CHECK (health_insurance IN ('imss','issste','imss_bienestar','private_other','pemex_defense_navy','none')),
    indigenous_language     text         CHECK (indigenous_language IN ('nahuatl','mixtec','otomi','mazatec','zapotec','mazahua','totonac','other')),
    diabetes                boolean NOT NULL,
    hypertension            boolean NOT NULL,
    high_cholesterol        boolean NOT NULL,
    heart_disease           boolean NOT NULL,
    stroke                  boolean NOT NULL,
    kidney_disease          boolean NOT NULL,
    chronic_lung_disease    boolean NOT NULL,
    arthritis               boolean NOT NULL,
    cancer                  boolean NOT NULL,
    obesity                 boolean NOT NULL,
    anemia                  boolean NOT NULL,
    depressive_symptoms     boolean NOT NULL,
    fall_last_12m           boolean NOT NULL,
    frailty                 boolean NOT NULL,
    visual_impairment       boolean NOT NULL,
    hearing_impairment      boolean NOT NULL,
    selfcare_difficulty     boolean NOT NULL,
    iadl_difficulty         boolean NOT NULL,
    disability_limitation   boolean NOT NULL,
    cognitive_status        text NOT NULL CHECK (cognitive_status IN ('none','mild_impairment','dementia')),
    dependency_level        text NOT NULL CHECK (dependency_level IN ('independent','mild','moderate','severe'))
);
CREATE INDEX ON persons (district_id);

CREATE TABLE patients (
    patient_id      text    PRIMARY KEY,
    person_id       text    NOT NULL UNIQUE REFERENCES persons,   -- master patient index: one person = one patient
    institution_id  text    NOT NULL REFERENCES institutions,
    admission_date  date    NOT NULL,
    base_priority   text    NOT NULL CHECK (base_priority IN ('high','medium','low')),
    active          boolean NOT NULL DEFAULT true
);
CREATE INDEX ON patients (institution_id);

CREATE TABLE family_members (
    family_member_id         text    PRIMARY KEY,
    patient_id               text    NOT NULL REFERENCES patients,
    institution_id           text    NOT NULL REFERENCES institutions,
    first_name               text    NOT NULL,
    paternal_surname         text    NOT NULL,
    maternal_surname         text    NOT NULL,
    relationship             text    NOT NULL CHECK (relationship IN ('daughter','son','spouse','grandchild','nephew_niece','other')),
    is_legal_representative  boolean NOT NULL,
    can_request_services     boolean NOT NULL,
    email                    text    NOT NULL UNIQUE
);
CREATE INDEX ON family_members (patient_id);

CREATE TABLE consents (
    consent_id        text    PRIMARY KEY,
    patient_id        text    NOT NULL REFERENCES patients,
    institution_id    text    NOT NULL REFERENCES institutions,
    type              text    NOT NULL CHECK (type IN ('health_data','home_care','voice_assistant')),
    granted           boolean NOT NULL,
    granted_by        text    NOT NULL CHECK (granted_by IN ('patient','legal_representative')),
    family_member_id  text    REFERENCES family_members,
    patient_assent    text    NOT NULL CHECK (patient_assent IN ('yes','no','unable_to_express','not_applicable')),
    signed_on         date    NOT NULL,
    expires_on        date    NOT NULL CHECK (expires_on > signed_on),
    CHECK (granted_by = 'patient' OR family_member_id IS NOT NULL),
    UNIQUE (patient_id, type)
);

-- Staff (ERP) -------------------------------------------------------------------------------------

CREATE TABLE caregivers (
    caregiver_id      text         PRIMARY KEY,
    institution_id    text         NOT NULL REFERENCES institutions,
    first_name        text         NOT NULL,
    paternal_surname  text         NOT NULL,
    maternal_surname  text         NOT NULL,
    type              text         NOT NULL CHECK (type IN ('physician','nurse','therapist','caregiver')),
    shift             text         NOT NULL CHECK (shift IN ('day','mixed','evening','night')),
    shift_start       time         NOT NULL,
    shift_end         time         NOT NULL,                      -- shift_end < shift_start => ends next day
    base_lat          numeric(8,5) NOT NULL,
    base_lon          numeric(8,5) NOT NULL,
    active            boolean      NOT NULL DEFAULT true
);
CREATE INDEX ON caregivers (institution_id);

CREATE TABLE caregiver_skills (
    caregiver_id  text NOT NULL REFERENCES caregivers,
    skill         text NOT NULL CHECK (skill IN ('physician','nursing','therapy','caregiving')),
    PRIMARY KEY (caregiver_id, skill)
);

-- Users -------------------------------------------------------------------------------------------

CREATE TABLE users (
    user_id           text    PRIMARY KEY,
    role              text    NOT NULL CHECK (role IN ('owner','coordinator','physician','caregiver','family')),
    institution_id    text    REFERENCES institutions,
    caregiver_id      text    REFERENCES caregivers,
    family_member_id  text    REFERENCES family_members,
    display_name      text    NOT NULL,
    email             text    NOT NULL UNIQUE,
    password_hash     text    NOT NULL,                             -- bcrypt
    active            boolean NOT NULL DEFAULT true,
    CHECK ((role = 'owner') = (institution_id IS NULL)),
    CHECK (role NOT IN ('physician','caregiver') OR caregiver_id IS NOT NULL),
    CHECK (role <> 'family' OR family_member_id IS NOT NULL)
);

-- Operations (TPS) --------------------------------------------------------------------------------

CREATE TABLE care_plans (
    care_plan_id    text         PRIMARY KEY,
    patient_id      text         NOT NULL REFERENCES patients,
    institution_id  text         NOT NULL REFERENCES institutions,
    service_id      text         NOT NULL REFERENCES services,
    times_per_week  numeric(5,3) NOT NULL CHECK (times_per_week > 0),
    reason          text         NOT NULL,                          -- user-facing (Spanish)
    active          boolean      NOT NULL DEFAULT true,
    FOREIGN KEY (institution_id, service_id) REFERENCES institution_services
);

CREATE TABLE service_requests (
    request_id      text        PRIMARY KEY,
    institution_id  text        NOT NULL REFERENCES institutions,
    patient_id      text        NOT NULL REFERENCES patients,
    service_id      text        NOT NULL REFERENCES services,
    origin          text        NOT NULL CHECK (origin IN ('care_plan','family','coordinator','voice_assistant','simulator')),
    priority        text        NOT NULL CHECK (priority IN ('high','medium','low')),
    scheduled_for   timestamptz NOT NULL,
    created_at      timestamptz NOT NULL,
    status          text        NOT NULL CHECK (status IN ('registered','validated','queued','assigned','in_progress','completed','closed','rejected','cancelled','unattended')),
    status_reason   text,
    duplicate_of    text        REFERENCES service_requests,           -- set when a duplicate submission is merged
    FOREIGN KEY (institution_id, service_id) REFERENCES institution_services
);
CREATE INDEX ON service_requests (institution_id, status);
CREATE INDEX ON service_requests (patient_id);
CREATE INDEX ON service_requests (scheduled_for);

CREATE TABLE assignments (
    assignment_id     text        PRIMARY KEY,
    request_id        text        NOT NULL UNIQUE REFERENCES service_requests,
    institution_id    text        NOT NULL REFERENCES institutions,
    caregiver_id      text        NOT NULL REFERENCES caregivers,
    assigned_by       text        NOT NULL REFERENCES users,
    approval          text        NOT NULL CHECK (approval IN ('auto','coordinator')),
    assigned_at       timestamptz NOT NULL,
    arrived_at        timestamptz,
    finished_at       timestamptz,
    family_confirmed  boolean     NOT NULL DEFAULT false,
    CHECK (finished_at IS NULL OR finished_at > arrived_at)
);
CREATE INDEX ON assignments (caregiver_id, arrived_at);

-- Tables filled while the system runs (empty in the seed) -----------------------------------------

CREATE TABLE voice_reports (
    report_id             text        PRIMARY KEY DEFAULT 'VR-' || substr(gen_random_uuid()::text, 1, 8),
    institution_id        text        NOT NULL REFERENCES institutions,
    patient_id            text        NOT NULL REFERENCES patients,
    submitted_by          text        NOT NULL REFERENCES users,
    created_at            timestamptz NOT NULL DEFAULT now(),
    transcript            text        NOT NULL,
    transcript_confidence numeric(4,3),
    triage_label          text        NOT NULL CHECK (triage_label IN ('emergency','urgent','routine')),
    rule_hits             text[]      NOT NULL DEFAULT '{}',
    report                jsonb,                                      -- structured report for the physician (no diagnosis)
    needs_human_review    boolean     NOT NULL DEFAULT false,
    model_used            text        NOT NULL,
    reviewed_by           text        REFERENCES users,
    reviewed_at           timestamptz
);

CREATE TABLE alerts (
    alert_id        text        PRIMARY KEY DEFAULT 'AL-' || substr(gen_random_uuid()::text, 1, 8),
    institution_id  text        REFERENCES institutions,             -- NULL = platform-wide (e.g. contingency)
    type            text        NOT NULL CHECK (type IN ('emergency','risk','contingency','anomaly','queue_delay')),
    level           text        NOT NULL CHECK (level IN ('info','watch','high','critical')),
    patient_id      text        REFERENCES patients,
    district_id     char(5)     REFERENCES districts,
    message         text        NOT NULL,                            -- user-facing (Spanish)
    created_at      timestamptz NOT NULL DEFAULT now(),
    status          text        NOT NULL DEFAULT 'open' CHECK (status IN ('open','acknowledged','resolved')),
    handled_by      text        REFERENCES users
);

CREATE TABLE contingency_events (
    event_id         text        PRIMARY KEY DEFAULT 'CT-' || substr(gen_random_uuid()::text, 1, 8),
    pollutant        text        NOT NULL CHECK (pollutant IN ('o3','pm25')),
    phase            text        NOT NULL CHECK (phase IN ('watch','phase1','phase2')),
    origin           text        NOT NULL CHECK (origin IN ('detected','demo_scenario')),
    scenario         text,
    started_at       timestamptz NOT NULL DEFAULT now(),
    ended_at         timestamptz,
    proposed_changes jsonb       NOT NULL DEFAULT '{}'
);

CREATE TABLE contingency_decisions (
    event_id        text        NOT NULL REFERENCES contingency_events,
    institution_id  text        NOT NULL REFERENCES institutions,
    decision        text        NOT NULL CHECK (decision IN ('approved','partially_approved','rejected')),
    decided_by      text        NOT NULL REFERENCES users,
    decided_at      timestamptz NOT NULL DEFAULT now(),
    notes           text,
    PRIMARY KEY (event_id, institution_id)
);

CREATE TABLE invoices (
    invoice_id          text    PRIMARY KEY,
    institution_id      text    NOT NULL REFERENCES institutions,
    period              date    NOT NULL,                             -- first day of the billed month
    plan_id             text    NOT NULL REFERENCES subscription_plans,
    services_coordinated integer NOT NULL DEFAULT 0,
    amount_mxn          integer NOT NULL,
    status              text    NOT NULL CHECK (status IN ('open','paid')),
    UNIQUE (institution_id, period)
);

CREATE TABLE audit_log (
    audit_id       bigserial   PRIMARY KEY,
    occurred_at    timestamptz NOT NULL DEFAULT now(),
    user_id        text        REFERENCES users,
    institution_id text,
    action         text        NOT NULL,                              -- e.g. read_patient, update_request, blocked_cross_tenant
    entity         text        NOT NULL,
    entity_id      text,
    allowed        boolean     NOT NULL,
    detail         jsonb
);
CREATE INDEX ON audit_log (occurred_at);

COMMIT;
