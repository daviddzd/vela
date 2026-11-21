-- Derived fields (age, multimorbidity, consent validity, timings).

CREATE OR REPLACE VIEW v_persons AS
SELECT p.*,
       date_part('year', age(current_date, p.birth_date))::int AS age,
       CASE WHEN age(current_date, p.birth_date) >= interval '80 years' THEN '80+'
            WHEN age(current_date, p.birth_date) >= interval '70 years' THEN '70-79'
            ELSE '60-69' END AS age_group,
       (p.diabetes::int + p.hypertension::int + p.high_cholesterol::int + p.heart_disease::int + p.stroke::int
        + p.kidney_disease::int + p.arthritis::int + p.chronic_lung_disease::int + p.cancer::int) AS chronic_disease_count,
       (p.diabetes::int + p.hypertension::int + p.high_cholesterol::int + p.heart_disease::int + p.stroke::int
        + p.kidney_disease::int + p.arthritis::int + p.chronic_lung_disease::int + p.cancer::int) >= 2 AS multimorbidity,
       (p.chronic_lung_disease OR p.heart_disease OR p.stroke) AS pollution_sensitive
FROM persons p;

CREATE OR REPLACE VIEW v_patients AS
SELECT pa.patient_id, pa.institution_id, pa.admission_date, pa.base_priority, pa.active, vp.*
FROM patients pa JOIN v_persons vp USING (person_id);

CREATE OR REPLACE VIEW v_consents AS
SELECT c.*, (c.granted AND c.expires_on >= current_date) AS is_valid
FROM consents c;

CREATE OR REPLACE VIEW v_service_requests AS
SELECT r.*, a.assignment_id, a.caregiver_id, a.approval, a.assigned_at, a.arrived_at, a.finished_at, a.family_confirmed,
       round(extract(epoch FROM (a.assigned_at - r.created_at)) / 60)::int     AS minutes_to_assign,
       round(extract(epoch FROM (a.arrived_at - r.scheduled_for)) / 60)::int   AS minutes_late,
       round(extract(epoch FROM (a.finished_at - a.arrived_at)) / 60)::int     AS minutes_on_site
FROM service_requests r LEFT JOIN assignments a USING (request_id);

CREATE OR REPLACE VIEW v_air_quality_24h AS
SELECT station_id, measured_at, o3_ppb, pm25_ugm3,
       avg(pm25_ugm3) OVER (PARTITION BY station_id ORDER BY measured_at
                            RANGE BETWEEN interval '23 hours' PRECEDING AND CURRENT ROW) AS pm25_24h_avg
FROM air_quality_readings;
