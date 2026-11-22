"""Move the synthetic history so it ends close to YESTERDAY, keeping each day's weekday.

The seed has 30 days of history (requests, assignments, air-quality readings) that end on
20 Nov 2026. On the day of the defense the board, Panorama-AM and the simulation should show a
history that ends "yesterday". Run (from the repo root, with the db container up):

    python scripts/rebase_dates.py              # apply
    python scripts/rebase_dates.py --dry-run    # do everything inside a transaction, show, roll back
    python scripts/rebase_dates.py --today 2026-12-01 --dry-run    # rehearse the defense day

What moves (only HISTORY = visits scheduled before today 00:00 Mexico City time):
  service_requests.scheduled_for / created_at / plan_date, their assignments (assigned, arrived,
  finished, planned window) and proposals, all consents (signed_on / expires_on), and air-quality
  readings measured before today. Everything moves by the SAME number of days, a multiple of 7,
  so weekdays are kept (a Monday stays a Monday: traffic and visit patterns depend on it).
  Because it is a whole number of weeks, the history ends between 0 and 6 days before yesterday.
What never moves: audit_log (the audit trail is real chronology), alerts, today's and future visits.

It can be run again at any time: it computes the shift from the data as they are now (if the history
already ends in the last 7 days, it does nothing). Uses `docker compose exec` like verify_db.py.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

TZ = "America/Mexico_City"
WEEKDAYS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]


def psql(sql: str) -> str:
    """Run SQL as the table owner inside the db container (one transaction, stop on first error)."""
    cmd = ["docker", "compose", "exec", "-T", "db", "sh", "-c",
           'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -At -q']
    out = subprocess.run(cmd, input=sql, capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"Error en la base de datos:\n{out.stderr.strip()}")
    return out.stdout.strip()


def history_end(today: date) -> date | None:
    """Last day of history (requests or air readings) before `today`."""
    value = psql(f"""
        SELECT greatest(
          (SELECT max((scheduled_for AT TIME ZONE '{TZ}')::date) FROM service_requests
            WHERE (scheduled_for AT TIME ZONE '{TZ}')::date < '{today}'),
          (SELECT max((measured_at AT TIME ZONE '{TZ}')::date) FROM air_quality_readings
            WHERE (measured_at AT TIME ZONE '{TZ}')::date < '{today}'));""")
    return date.fromisoformat(value) if value else None


def shift_sql(days: int, today: date, commit: bool) -> str:
    """All updates in ONE transaction. Rows that have uniqueness or no-overlap rules (reading primary
    key, one request per plan and day, EXCLUDE on planned windows) are moved in two steps: first far
    into the future (+1000 years), then to their final place, so they never collide mid-update."""
    shift, far = f"interval '{days} days'", "interval '1000 years'"
    cutoff = f"('{today}'::date::timestamp AT TIME ZONE '{TZ}')"   # today 00:00 in Mexico City
    return f"""
BEGIN;
CREATE TEMP TABLE moved ON COMMIT DROP AS
  SELECT request_id FROM service_requests WHERE scheduled_for < {cutoff};

-- requests (plan_date in two steps: unique per care plan and day)
UPDATE service_requests SET plan_date = plan_date + 365000 WHERE request_id IN (SELECT request_id FROM moved) AND plan_date IS NOT NULL;
UPDATE service_requests SET scheduled_for = scheduled_for + {shift}, created_at = created_at + {shift},
       plan_date = plan_date - 365000 + {days}
 WHERE request_id IN (SELECT request_id FROM moved);

-- assignments (planned window in two steps: EXCLUDE no_caregiver_overlap)
UPDATE assignments SET planned_start = planned_start + {far}, planned_end = planned_end + {far}
 WHERE request_id IN (SELECT request_id FROM moved) AND planned_start IS NOT NULL;
UPDATE assignments SET assigned_at = assigned_at + {shift}, arrived_at = arrived_at + {shift},
       finished_at = finished_at + {shift},
       planned_start = planned_start - {far} + {shift}, planned_end = planned_end - {far} + {shift}
 WHERE request_id IN (SELECT request_id FROM moved);
UPDATE assignment_proposals SET planned_start = planned_start + {shift}, planned_end = planned_end + {shift},
       created_at = created_at + {shift}
 WHERE request_id IN (SELECT request_id FROM moved);

-- consents keep their validity relative to the history
UPDATE consents SET signed_on = signed_on + {days}, expires_on = expires_on + {days};

-- air-quality readings (primary key station + time: two steps)
UPDATE air_quality_readings SET measured_at = measured_at + {far} WHERE measured_at < {cutoff};
UPDATE air_quality_readings SET measured_at = measured_at - {far} + {shift} WHERE measured_at > now() + interval '500 years';

SELECT 'Solicitudes movidas: ' || count(*) FROM moved;
SELECT 'Historial de solicitudes: ' || min((scheduled_for AT TIME ZONE '{TZ}')::date) || ' a ' ||
       max((scheduled_for AT TIME ZONE '{TZ}')::date) FROM service_requests WHERE request_id IN (SELECT request_id FROM moved);
SELECT 'Lecturas de aire: ' || min((measured_at AT TIME ZONE '{TZ}')::date) || ' a ' ||
       max((measured_at AT TIME ZONE '{TZ}')::date) FROM air_quality_readings WHERE measured_at < {cutoff};
SELECT 'Consentimientos vigentes: ' || count(*) FILTER (WHERE is_valid) || ' de ' || count(*) FROM v_consents;
{"COMMIT;" if commit else "ROLLBACK;"}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Mueve el historial sintético para que termine cerca de ayer.")
    parser.add_argument("--today", type=date.fromisoformat, default=datetime.now(ZoneInfo(TZ)).date(),
                        help="fecha de 'hoy' (AAAA-MM-DD); por omisión, hoy en la Ciudad de México")
    parser.add_argument("--dry-run", action="store_true", help="hacer todo y deshacerlo al final (solo mostrar)")
    args = parser.parse_args()

    yesterday = args.today - timedelta(days=1)
    end = history_end(args.today)
    if end is None:
        print("No hay historial anterior a hoy. Nada que mover.")
        return 0
    weeks = (yesterday - end).days // 7
    print(f"Hoy: {args.today} · el historial termina el {end} ({WEEKDAYS[end.weekday()]}) · ayer fue {yesterday}.")
    if weeks <= 0:
        print("El historial ya termina en los últimos 7 días. Nada que mover.")
        return 0
    days = weeks * 7
    print(f"Se moverá {weeks} semana(s) = {days} días; el historial terminará el {end + timedelta(days=days)} "
          f"({WEEKDAYS[(end + timedelta(days=days)).weekday()]}, mismo día de la semana).")
    print(psql(shift_sql(days, args.today, commit=not args.dry_run)))
    print("\nSimulación: no se guardó ningún cambio." if args.dry_run else
          "\nListo. Comprueba con: python scripts/verify_db.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
