"""Leave the live operation clean for the defense, with the seed intact.

    python scripts/reset_demo.py --dry-run   # shows what it would delete, changes nothing
    python scripts/reset_demo.py             # applies it (one transaction)
    python scripts/verify_db.py              # must still say "Todo correcto"

What it deletes (all of it is created while the app runs; none of it comes from database/seed/):
  - ORACLE-Voz reports (voice_reports) and every alert (alerts)
  - family notices (family_notices)
  - demo scenarios: scenario_runs and everything hanging from them (simulated air quality, traffic,
    caregivers out of service, contingency events / proposals / decisions, priority changes)
  - open or past assignment proposals (assignment_proposals)
  - live service requests (not in the seed) that are still PENDING (visit not started), with their
    assignments, and every request created by the demo panel (origin 'demo_scenario').
    The worker creates today's care-plan visits again on its next round, assigned automatically.
What it never touches: the seed (it is all past history; the demo panel only changes pending visits),
visits that already started or finished today, and audit_log (the audit trail is append-only).
The reset itself is recorded in audit_log (action 'demo_reset').
"""
from __future__ import annotations

import argparse
import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

COUNT_TABLES = ["voice_reports", "alerts", "family_notices", "scenario_runs", "contingency_events",
                "contingency_proposals", "contingency_decisions", "priority_overrides", "traffic_conditions",
                "caregiver_unavailability", "air_quality_scenario", "assignment_proposals"]

# Live requests to remove: not in the seed, and (created by the demo panel, or visit not started yet).
TARGET_REQUESTS = """
CREATE TEMP TABLE seed_requests (request_id text PRIMARY KEY);
{seed_rows}
CREATE TEMP TABLE target_requests AS
  SELECT r.request_id FROM service_requests r
  WHERE r.request_id NOT IN (SELECT request_id FROM seed_requests)
    AND (r.origin = 'demo_scenario'
         OR NOT EXISTS (SELECT 1 FROM assignments a WHERE a.request_id = r.request_id AND a.arrived_at IS NOT NULL));
"""

DELETE = """
DELETE FROM voice_reports;
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
    counts = " UNION ALL ".join(f"SELECT '{t}', count(*) FROM {t}" for t in COUNT_TABLES)
    report = f"""SELECT 'service_requests (en vivo)', count(*) FROM target_requests UNION ALL
                 SELECT 'assignments (en vivo)', count(*) FROM assignments WHERE request_id IN (SELECT request_id FROM target_requests)
                 UNION ALL {counts};"""
    sql = ("BEGIN;\n" + TARGET_REQUESTS.format(seed_rows=seed_rows) + report + DELETE
           + ("ROLLBACK;" if args.dry_run else "COMMIT;"))
    print("Simulación (no se guarda nada):" if args.dry_run else "Borrado:")
    for line in psql(sql).strip().splitlines():
        table, n = line.split("|")
        print(f"  {table:32} {int(n):>6}")
    print("Hecho. La semilla no se tocó." if not args.dry_run else "Para aplicarlo: python scripts/reset_demo.py")


if __name__ == "__main__":
    main()
