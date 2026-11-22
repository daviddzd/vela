"""Real-time worker loop (one tick per minute, wall-clock time in Mexico City).

Each tick: retry the request queue, create delay alerts, mark unattended requests. Later steps add
air-quality checks, contingency detection, risk updates and care-plan requests (docs/spec/02).
The worker is a platform process: it scopes its transaction with '*' (all institutions).
Run with:  python -m app.worker
"""
import time
from datetime import datetime

from app.core.config import MEXICO_CITY
from app.core.db import ALL_INSTITUTIONS, tenant_session
from app.services import queue

TICK_SECONDS = 60


def tick() -> None:
    with tenant_session(ALL_INSTITUTIONS) as db:
        retried = queue.process_queue(db)
        queue.create_alerts(db)
        unattended = queue.mark_unattended(db)
    print(f"worker tick {datetime.now(MEXICO_CITY):%Y-%m-%d %H:%M:%S %Z} "
          f"queue={retried} unattended={unattended}", flush=True)


def main() -> None:
    while True:
        try:
            tick()
        except Exception as exc:  # noqa: BLE001 - keep looping; the next tick retries
            print(f"worker error: {exc}", flush=True)
        # Sleep until the start of the next minute so ticks line up with the real clock.
        time.sleep(TICK_SECONDS - datetime.now(MEXICO_CITY).second)


if __name__ == "__main__":
    main()
