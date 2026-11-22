"""Worker jobs for the request queue (run every minute by app/worker.py).

1. Retry waiting requests, in the order the active policy decides (default risk_plus_live_traffic:
   priority → patient risk → minutes waiting). low/medium get assigned; high get 3 proposals.
2. Alerts for coordination: high priority not approved after 10 min; any request queued without a
   free caregiver after 30 min. Each alert is created once (unique per request and code).
3. Requests whose time already passed without anyone going become `unattended`.
"""
from datetime import timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core import messages_es as msg
from app.core.events import publish
from app.services import operations as ops

APPROVAL_ALERT_AFTER = timedelta(minutes=10)
QUEUE_ALERT_AFTER = timedelta(minutes=30)


def process_queue(db: Session) -> int:
    """Retry dispatch for waiting requests. Returns how many were considered."""
    rows = db.execute(text("""
        SELECT r.institution_id, r.request_id FROM service_requests r
        WHERE r.status = 'queued' AND r.scheduled_for > now()
          AND NOT EXISTS (SELECT 1 FROM assignment_proposals p
                          WHERE p.request_id = r.request_id AND p.status = 'open')""")).all()
    by_institution: dict[str, list[str]] = {}
    for r in rows:
        by_institution.setdefault(r.institution_id, []).append(r.request_id)
    for institution_id, ids in by_institution.items():
        ops.dispatch_requests(db, institution_id, ids)   # dispatcher orders them by policy
    return len(rows)


def create_alerts(db: Session) -> None:
    now = ops.now()
    pending = db.execute(text("""
        SELECT request_id, institution_id, patient_id, created_at, status_reason FROM service_requests
        WHERE status = 'queued'""")).all()
    for r in pending:
        waited = now - r.created_at
        if r.status_reason == "awaiting_approval" and waited >= APPROVAL_ALERT_AFTER:
            _alert(db, r, "approval_pending", msg.ALERT_APPROVAL_PENDING, waited)
        elif r.status_reason == "no_caregiver_available" and waited >= QUEUE_ALERT_AFTER:
            _alert(db, r, "queue_wait", msg.ALERT_QUEUE_WAIT, waited)


def mark_unattended(db: Session) -> int:
    """Waiting requests whose visit window is already over."""
    rows = db.execute(text("""
        UPDATE service_requests r SET status = 'unattended', status_reason = 'time_passed'
        FROM institution_services ins
        WHERE r.status = 'queued' AND ins.institution_id = r.institution_id AND ins.service_id = r.service_id
          AND r.scheduled_for + ins.duration_min * interval '1 minute' < now()
        RETURNING r.request_id, r.institution_id""")).all()
    for r in rows:
        publish(db, "request.updated", r.institution_id, request_id=r.request_id, status="unattended")
    return len(rows)


def _alert(db: Session, r, code: str, template: str, waited: timedelta) -> None:
    alert_id = db.execute(text("""
        INSERT INTO alerts (institution_id, type, level, patient_id, message, request_id, code)
        VALUES (:i, 'queue_delay', 'high', :p, :m, :r, :c)
        ON CONFLICT (request_id, code) WHERE request_id IS NOT NULL DO NOTHING
        RETURNING alert_id"""),
        {"i": r.institution_id, "p": r.patient_id, "r": r.request_id, "c": code,
         "m": template.format(request_id=r.request_id, minutes=int(waited.total_seconds() // 60))}).scalar()
    if alert_id:   # only a NEW alert produces an event
        publish(db, "alert.created", r.institution_id, alert_id=alert_id, request_id=r.request_id)
