"""Leave the live operation clean for the defense, with the seed intact.

    python scripts/reset_demo.py --dry-run   # shows what it would delete, changes nothing
    python scripts/reset_demo.py             # applies it (one transaction)
    python scripts/verify_db.py              # must still say "Todo correcto"

What it deletes (all of it is created while the app runs; none of it comes from database/seed/):
  - ORACLE-Voz reports (voice_reports) and every alert (alerts)
  - family notices (family_notices) and ARCO requests (arco_requests)
  - consents changed during a rehearsal (revoked or registered in /privacidad) go back to their seed values
  - weekly rest days changed in /personal during a rehearsal go back to the rotation (app/services/labor.py)
  - care plans changed by a physician in a rehearsal: the seed plans come back as they were and the plans created
    in the rehearsal are deactivated (not deleted: visits that already happened still point to them)
  - demo scenarios: scenario_runs and everything hanging from them (simulated air quality, traffic,
    caregivers out of service, contingency events / proposals / decisions, priority changes)
  - open or past assignment proposals (assignment_proposals)
  - every live service request (not in the seed) created by a PERSON or by the demo panel, finished or not, with its
    assignments: origins family, coordinator, voice_assistant, demo_scenario and contingency (team decision,
    23 Nov 2026: rehearsal visits such as REQ-09008, already closed, must not stay in the agenda);
  - care-plan visits (origin 'care_plan', created by the worker) that have NOT started yet: the worker creates them
    again on its next round, assigned automatically, which also undoes what the demo panel did to them (someone
    out of service, contingency changes).
What it never touches: the seed (it is all past history), care-plan visits that already started or finished (the
real work of the automatic process; one nobody closed is marked "No cerrada" by the worker, see
app/services/alerts_followup.py), and audit_log (the audit trail is append-only).
The reset itself is recorded in audit_log (action 'demo_reset').
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

COUNT_TABLES = ["voice_reports", "alerts", "family_notices", "arco_requests", "scenario_runs", "contingency_events",
                "contingency_proposals", "contingency_decisions", "priority_overrides", "traffic_conditions",
                "caregiver_unavailability", "air_quality_scenario", "assignment_proposals"]

# Live requests to remove: not in the seed, and (created by a person or the demo panel, or a care-plan visit not started).
TARGET_REQUESTS = """
CREATE TEMP TABLE seed_requests (request_id text PRIMARY KEY);
{seed_rows}
CREATE TEMP TABLE seed_consents (consent_id text PRIMARY KEY, granted boolean, granted_by text, family_member_id text,
                                 patient_assent text, signed_on date, expires_on date);
{consent_rows}
CREATE TEMP TABLE target_requests AS
  SELECT r.request_id FROM service_requests r
  WHERE r.request_id NOT IN (SELECT request_id FROM seed_requests)
    AND (r.origin IN ('family', 'coordinator', 'voice_assistant', 'demo_scenario', 'contingency')
         OR NOT EXISTS (SELECT 1 FROM assignments a WHERE a.request_id = r.request_id AND a.arrived_at IS NOT NULL));
"""

DELETE = """
DELETE FROM voice_reports;
DELETE FROM arco_requests;
DELETE FROM family_notices;
DELETE FROM contingency_decisions;
DELETE FROM contingency_proposals;
DELETE FROM priority_overrides;
DELETE FROM alerts;
DELETE FROM contingency_events;
DELETE FROM traffic_conditions;
DELETE FROM caregiver_unavailability;
DELETE FROM air_quality_scenario;
DELETE FROM scenario_runs;
DELETE FROM assignment_proposals;
DELETE FROM assignments WHERE request_id IN (SELECT request_id FROM target_requests);
UPDATE service_requests SET duplicate_of = NULL
  WHERE duplicate_of IN (SELECT request_id FROM target_requests);
DELETE FROM service_requests WHERE request_id IN (SELECT request_id FROM target_requests);
UPDATE consents c SET granted = s.granted, granted_by = s.granted_by, family_member_id = s.family_member_id,
       patient_assent = s.patient_assent, signed_on = s.signed_on, expires_on = s.expires_on,
       recorded_by = NULL, recorded_at = NULL, revoked_at = NULL, revoked_by = NULL, revoke_reason = NULL
  FROM seed_consents s WHERE s.consent_id = c.consent_id;
DELETE FROM consents WHERE consent_id NOT IN (SELECT consent_id FROM seed_consents);
UPDATE care_plans SET active = false WHERE created_at IS NOT NULL AND active;
UPDATE care_plans SET active = true, ended_at = NULL, ended_by = NULL
  WHERE created_at IS NULL AND ended_at IS NOT NULL;
INSERT INTO audit_log (user_id, institution_id, action, entity, entity_id, allowed, detail)
  VALUES (NULL, NULL, 'demo_reset', 'platform', NULL, true, '{"script": "scripts/reset_demo.py"}');
"""


def psql(sql: str) -> str:
    """Run SQL as the table owner inside the db container (stop on first error)."""
    cmd = ["docker", "compose", "exec", "-T", "db", "sh", "-c",
           'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -At -q -F "|"']
    out = subprocess.run(cmd, input=sql, capture_output=True, text=True, cwd=ROOT)
    if out.returncode:
        sys.exit(f"Error en la base de datos:\n{out.stderr.strip()}")
    return out.stdout


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="muestra qué borraría, sin guardar")
    args = ap.parse_args()

    with open(ROOT / "database" / "seed" / "service_requests.csv", encoding="utf-8") as f:
        ids = [r["request_id"] for r in csv.DictReader(f)]
    seed_rows = "INSERT INTO seed_requests VALUES " + ",".join(f"('{i}')" for i in ids) + ";"
    with open(ROOT / "database" / "seed" / "consents.csv", encoding="utf-8") as f:
        cons = list(csv.DictReader(f))
    q = lambda v: "NULL" if v == "" else "'" + v.replace("'", "''") + "'"   # noqa: E731
    consent_rows = "INSERT INTO seed_consents VALUES " + ",".join(
        f"({q(c['consent_id'])},{c['granted']},{q(c['granted_by'])},{q(c['family_member_id'])},{q(c['patient_assent'])},"
        f"{q(c['signed_on'])},{q(c['expires_on'])})" for c in cons) + ";"
    changed = """SELECT 'consents (cambiados en vivo)', count(*) FROM consents c LEFT JOIN seed_consents s USING (consent_id)
                 WHERE s.consent_id IS NULL OR c.revoked_at IS NOT NULL OR c.recorded_at IS NOT NULL OR c.granted <> s.granted
                 UNION ALL """
    counts = " UNION ALL ".join(f"SELECT '{t}', count(*) FROM {t}" for t in COUNT_TABLES)
    report = changed + f"""SELECT 'service_requests (en vivo)', count(*) FROM target_requests UNION ALL
                 SELECT 'assignments (en vivo)', count(*) FROM assignments WHERE request_id IN (SELECT request_id FROM target_requests)
                 UNION ALL {counts};"""
    # Rest days back to the rotation (the same function the migration and SIRAG-D use)
    sys.path.insert(0, str(ROOT / "backend"))
    from datetime import time as _time
    from app.services import labor
    rows = [line.split("|") for line in psql(
        "SELECT c.caregiver_id, c.institution_id, c.shift_start, c.shift_end, string_agg(k.skill, ',') "
        "FROM caregivers c JOIN caregiver_skills k USING (caregiver_id) GROUP BY c.caregiver_id;").strip().splitlines()]
    days = labor.assign_rest_days([{"caregiver_id": r[0], "institution_id": r[1], "shift_start": _time.fromisoformat(r[2]),
                                    "shift_end": _time.fromisoformat(r[3]), "skill": labor.main_skill(r[4].split(","))}
                                   for r in rows])
    rest_sql = "".join(f"UPDATE caregivers SET rest_day = {d} WHERE caregiver_id = '{c}';\n" for c, d in days.items())
    sql = ("BEGIN;\n" + TARGET_REQUESTS.format(seed_rows=seed_rows, consent_rows=consent_rows) + report + DELETE + rest_sql
           + ("ROLLBACK;" if args.dry_run else "COMMIT;"))
    print("Simulación (no se guarda nada):" if args.dry_run else "Borrado:")
    for line in psql(sql).strip().splitlines():
        table, n = line.split("|")
        print(f"  {table:32} {int(n):>6}")
    print("Hecho. La semilla no se tocó." if not args.dry_run else "Para aplicarlo: python scripts/reset_demo.py")


if __name__ == "__main__":
    main()
