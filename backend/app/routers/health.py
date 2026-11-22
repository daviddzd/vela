"""Health check used by Docker, Caddy and the Cloudflare rehearsal."""
from datetime import datetime

from fastapi import APIRouter
from sqlalchemy import text

from app.core.config import MEXICO_CITY
from app.core.db import engine

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health")
def health() -> dict:
    """Answer 200 if the API is up; report whether the database answers too."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        db = "ok"
    except Exception:  # noqa: BLE001 - health must never crash
        db = "error"
    return {"status": "ok", "db": db, "time": datetime.now(MEXICO_CITY).isoformat()}
