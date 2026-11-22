"""Real-time worker loop (one tick per minute, wall-clock time in Mexico City).

For now it only checks the database and prints a heartbeat. Later steps add: air-quality checks,
contingency detection, queue retries, risk updates and care-plan requests (docs/spec/02).
Run with:  python -m app.worker
"""
import time
from datetime import datetime

from sqlalchemy import text

from app.core.config import MEXICO_CITY
from app.core.db import engine

TICK_SECONDS = 60


def tick() -> None:
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print(f"worker tick {datetime.now(MEXICO_CITY):%Y-%m-%d %H:%M:%S %Z}", flush=True)


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
