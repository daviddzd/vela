"""Check that the database loaded correctly. Run on the laptop after `docker compose up -d db`.

python scripts/verify_db.py         (uses docker compose exec, so no Python DB driver is needed)
"""
import subprocess
import sys

EXPECTED = {
    "districts": 16, "subscription_plans": 3, "institutions": 5, "services": 9, "institution_services": 30,
    "persons": 20000, "patients": 400, "family_members": 400, "consents": 1200, "caregivers": 44,
    "caregiver_skills": 49, "care_plans": 927, "users": 31, "service_requests": 2864, "assignments": 2597,
    "air_quality_stations": 17, "air_quality_readings": 12240, "traffic_hourly_profile": 48,
}

# Real arrival/finish times never overlap (seed and operation alike). Planned windows of new
# assignments are protected by the EXCLUDE constraint no_caregiver_overlap (migration 0002).
OVERLAPS = """SELECT count(*) FROM assignments a JOIN assignments b
  ON a.caregiver_id = b.caregiver_id AND a.assignment_id < b.assignment_id
 AND a.arrived_at < b.finished_at AND b.arrived_at < a.finished_at"""


def sql(query: str, api_role: bool = False) -> str:
    """Run a query inside the db container. api_role=True connects as vela_api (subject to RLS)."""
    login = 'PGPASSWORD="$VELA_API_DB_PASSWORD" psql -U vela_api' if api_role else 'psql -U "$POSTGRES_USER"'
    cmd = ["docker", "compose", "exec", "-T", "db", "sh", "-c",
           f'{login} -h localhost -At -d "$POSTGRES_DB" -c "{query}"']
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"Error: {out.stderr.strip()}")
    return out.stdout.strip().splitlines()[-1]


# Operational tables keep growing while the app runs (requests from care plans, families, ...).
# For them we check the SEED rows exactly (their ids come before the sequences of migration 0002)
# and report the rows created in operation separately.
SEED_ONLY = {"service_requests": "request_id <= 'REQ-02864'", "assignments": "assignment_id <= 'ASG-02597'",
             # the seed has 30 days of hourly readings; the worker adds live ones after them (rebase-safe window)
             "air_quality_readings": "measured_at < (SELECT min(measured_at) FROM air_quality_readings) + interval '30 days'"}


def main() -> None:
    ok = True
    for table, n in EXPECTED.items():
        where = f" WHERE {SEED_ONLY[table]}" if table in SEED_ONLY else ""
        got = int(sql(f"SELECT count(*) FROM {table}{where}"))
        flag = "ok" if got == n else "FALLA"
        ok &= got == n
        extra = ""
        if table in SEED_ONLY:
            live = int(sql(f"SELECT count(*) FROM {table} WHERE NOT ({SEED_ONLY[table]})"))
            extra = f"  + {live} creadas en operación" if table != "air_quality_readings" else f"  + {live} lecturas en vivo"
        print(f"{flag:5} {table:24} {got:>6} (esperado {n}){extra}")
    overlaps = int(sql(OVERLAPS))
    print(f"{'ok' if overlaps == 0 else 'FALLA':5} traslapes de cuidadores: {overlaps}")
    ok &= overlaps == 0
    # vela_api is subject to row-level security: without a tenant setting it must see nothing.
    hidden = int(sql("SELECT count(*) FROM patients", api_role=True))
    one = int(sql("SET app.institution_id = 'INS-A'; SELECT count(*) FROM patients", api_role=True))
    rls_ok = hidden == 0 and 0 < one < EXPECTED["patients"]
    print(f"{'ok' if rls_ok else 'FALLA':5} aislamiento: sin institución {hidden} pacientes, INS-A {one}")
    ok &= rls_ok
    print("\nTodo correcto." if ok else "\nHay diferencias: revisa los mensajes de arriba.")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
