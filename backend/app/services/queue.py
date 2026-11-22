"""Worker jobs for the request queue (run every minute by app/worker.py).

1. Retry waiting requests, in the order the active policy decides (default risk_plus_live_traffic:
   priority → patient risk → minutes waiting). low/medium get assigned; high get 3 proposals.
   A visit can still be assigned up to the late tolerance after its requested time (YAML, 60 min).
1b. URGENT high-priority requests (visit due within 60 min) that waited 3 min without approval get the
   proposed candidate applied ("aprobada por tiempo"); coordination is alerted and can change it.
2. Alerts for coordination: high priority not approved after 10 min; any request queued without a
   free caregiver after 30 min. Each alert is created once (unique per request and code).
3. Requests whose late tolerance already passed without anyone going become `unattended`.
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
        WHERE r.status = 'queued' AND r.scheduled_for + :tol > now()
          AND NOT EXISTS (SELECT 1 FROM assignment_proposals p
                          WHERE p.request_id = r.request_id AND p.status = 'open')"""), {"tol": ops.late_tolerance()}).all()
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
        WHERE r.status = 'queued' AND r.scheduled_for + :tol < now()
        RETURNING r.request_id, r.institution_id"""), {"tol": ops.late_tolerance()}).all()
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


def auto_apply_urgent(db: Session) -> list[str]:
    """Time-limited approval (product decision from SIRAG-D, docs/dev/sirag_d_modelo.md section 8).

    Only URGENT high-priority requests: the visit is due within `urgent_within_minutes` and the proposals
    have waited `auto_apply_after_minutes` without an answer. Scheduled high-priority visits with time to
    spare keep waiting for a person (CLAUDE.md rule 3). The proposed candidate is applied with
    approval='timeout'; coordination gets an alert and can reassign it."""
    cfg = ops.settings_yaml()["approval"]
    after, urgent = cfg["auto_apply_after_minutes"], cfg["urgent_within_minutes"]
    rows = db.execute(text("""
        SELECT r.request_id, r.institution_id, r.patient_id, min(p.created_at) AS proposed_at
        FROM service_requests r JOIN assignment_proposals p ON p.request_id = r.request_id AND p.status = 'open'
        WHERE r.status = 'queued' AND r.priority = 'high'
          AND r.scheduled_for <= now() + :urgent * interval '1 minute'
        GROUP BY r.request_id, r.institution_id, r.patient_id
        HAVING min(p.created_at) <= now() - :after * interval '1 minute'"""), {"urgent": urgent, "after": after}).all()
    applied = []
    for r in rows:
        options = ops.options_for(db, r.request_id)        # re-check: the proposal may no longer be free
        aid = ops.save_assignment(db, r.institution_id, r.request_id, options, approval="timeout",
                                  assigned_by=ops.duty_coordinator(db, r.institution_id)) if options else None
        if aid is None:
            continue
        caregiver = db.scalar(text("""SELECT c.first_name || ' ' || c.paternal_surname FROM assignments a
                                      JOIN caregivers c USING (caregiver_id) WHERE a.assignment_id = :a"""), {"a": aid})
        alert_id = db.execute(text("""
            INSERT INTO alerts (institution_id, type, level, patient_id, message, request_id, code)
            VALUES (:i, 'queue_delay', 'high', :p, :m, :r, 'approved_by_timeout')
            ON CONFLICT (request_id, code) WHERE request_id IS NOT NULL DO NOTHING RETURNING alert_id"""),
            {"i": r.institution_id, "p": r.patient_id, "r": r.request_id,
             "m": msg.ALERT_APPROVED_BY_TIMEOUT.format(request_id=r.request_id, caregiver=caregiver, minutes=after)}).scalar()
        if alert_id:
            publish(db, "alert.created", r.institution_id, alert_id=alert_id, request_id=r.request_id)
        applied.append(r.request_id)
    return applied
