"""/api/voice — ORACLE-Voz for families and caregivers, the physician's inbox, and the demo sample button."""
from __future__ import annotations

import random

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.deps import CurrentUser, require_role, tenant_db
from app.core.events import publish
from app.core.guards import deny, family_patient_id, not_found_or_cross_tenant
from app.core.roles import CAREGIVER, FAMILY, OWNER, PHYSICIAN
from app.services import operations as ops
from app.services import oracle

router = APIRouter(prefix="/api", tags=["voice"])
SPEAKERS = (FAMILY, CAREGIVER, PHYSICIAN)
NO_CONSENT = "Falta autorización para usar el asistente de voz con esta persona. Pide a la coordinación que la registre."
VOICE_DOWN = "El servicio de voz no responde. Escribe tu mensaje."
LANG = {"nahuatl": "náhuatl", "mixtec": "mixteco", "otomi": "otomí", "mazatec": "mazateco", "zapotec": "zapoteco",
        "mazahua": "mazahua", "totonac": "totonaco", "other": "otra lengua indígena"}


def allowed_patient(db: Session, user: CurrentUser, patient_id: str) -> None:
    """Family: their patient. Caregiver / physician: a patient they visit (had or have an assignment)."""
    if db.scalar(text("SELECT 1 FROM patients WHERE patient_id = :p"), {"p": patient_id}) is None:
        raise not_found_or_cross_tenant(db, user, "patient", patient_id)
    ok = (family_patient_id(db, user) == patient_id) if user.role == FAMILY else bool(db.scalar(text("""
        SELECT EXISTS (SELECT 1 FROM assignments a JOIN service_requests r USING (request_id)
                       WHERE a.caregiver_id = :c AND r.patient_id = :p)"""), {"c": user.caregiver_id, "p": patient_id}))
    if not ok:
        raise deny(user, "blocked_out_of_scope", "patient", patient_id, "Esta persona no está a tu cargo. El intento quedó registrado.")


@router.get("/voice/patients")
def voice_patients(user: CurrentUser = Depends(require_role(*SPEAKERS)), db: Session = Depends(tenant_db)) -> list[dict]:
    where = "pa.patient_id = :fp" if user.role == FAMILY else """pa.patient_id IN (
        SELECT r.patient_id FROM assignments a JOIN service_requests r USING (request_id) WHERE a.caregiver_id = :c)"""
    rows = db.execute(text(f"""
        SELECT pa.patient_id, pe.first_name || ' ' || pe.paternal_surname AS name, pe.indigenous_language,
               coalesce((SELECT is_valid FROM v_consents c WHERE c.patient_id = pa.patient_id AND c.type = 'voice_assistant'), false) AS voice_consent
        FROM patients pa JOIN persons pe USING (person_id) WHERE pa.active AND {where}
        ORDER BY name LIMIT 40"""), {"fp": family_patient_id(db, user) if user.role == FAMILY else None,
                                     "c": user.caregiver_id}).mappings().all()
    return [{**dict(r), "language": LANG.get(r["indigenous_language"])} for r in rows]


def _respond(result: dict, user: CurrentUser, background: BackgroundTasks) -> dict:
    background.add_task(oracle.write_report, result["report_id"], user.institution_id)
    return result


@router.post("/voice/notes")
async def voice_note(background: BackgroundTasks, patient_id: str = Form(...), audio: UploadFile = File(...),
                     user: CurrentUser = Depends(require_role(*SPEAKERS)), db: Session = Depends(tenant_db)) -> dict:
    allowed_patient(db, user, patient_id)
    data = await audio.read()
    if len(data) > 8_000_000:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "La nota es demasiado larga (máximo 60 s).")
    try:
        result = oracle.process(db, user_id=user.user_id, institution_id=user.institution_id, patient_id=patient_id,
                                input_mode="audio", audio=data, filename=audio.filename or "nota.webm")
    except oracle.NoConsent:
        db.commit()   # keep the audit row of the blocked attempt
        raise HTTPException(status.HTTP_403_FORBIDDEN, NO_CONSENT)
    except oracle.VoiceUnavailable:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, VOICE_DOWN)
    return _respond(result, user, background)


class TextNoteIn(BaseModel):
    patient_id: str
    text: str = Field(min_length=1, max_length=2000)


@router.post("/voice/text")
def voice_text(body: TextNoteIn, background: BackgroundTasks, user: CurrentUser = Depends(require_role(*SPEAKERS)),
               db: Session = Depends(tenant_db)) -> dict:
    """Typed message (microphone denied / not available, or the voice service is down)."""
    allowed_patient(db, user, body.patient_id)
    try:
        result = oracle.process(db, user_id=user.user_id, institution_id=user.institution_id, patient_id=body.patient_id,
                                input_mode="text", text_=body.text)
    except oracle.NoConsent:
        db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, NO_CONSENT)
    return _respond(result, user, background)


class CallMeIn(BaseModel):
    patient_id: str


@router.post("/voice/call-me")
def call_me(body: CallMeIn, user: CurrentUser = Depends(require_role(*SPEAKERS)), db: Session = Depends(tenant_db)) -> dict:
    """'No hablo español / Pedir que alguien me llame' (docs/spec/05): request to coordination with the language."""
    allowed_patient(db, user, body.patient_id)
    p = db.execute(text("""SELECT pe.first_name || ' ' || pe.paternal_surname AS name, pe.indigenous_language
                           FROM patients pa JOIN persons pe USING (person_id) WHERE pa.patient_id = :p"""),
                   {"p": body.patient_id}).one()
    lang = LANG.get(p.indigenous_language, "lengua no registrada")
    alert_id = db.scalar(text("""INSERT INTO alerts (institution_id, type, level, patient_id, message)
                                 VALUES (:i, 'call_back', 'high', :p, :m) RETURNING alert_id"""),
                         {"i": user.institution_id, "p": body.patient_id,
                          "m": f"Pedir que alguien llame: {p.name}. Lengua registrada: {lang}."})
    publish(db, "alert.created", user.institution_id, alert_id=alert_id)
    audit(db, user_id=user.user_id, institution_id=user.institution_id, action="voice_call_back", entity="patient",
          entity_id=body.patient_id, detail={"language": p.indigenous_language})
    return {"alert_id": alert_id, "language": lang}


# ---- physician inbox ----------------------------------------------------------------------------------

@router.get("/voice/reports")
def reports(user: CurrentUser = Depends(require_role(PHYSICIAN)), db: Session = Depends(tenant_db)) -> list[dict]:
    """Only the physician's patients; health content only with a valid health_data consent (CLAUDE.md rule 5)."""
    rows = db.execute(text("""
        SELECT v.report_id, v.patient_id, pe.first_name || ' ' || pe.paternal_surname AS patient_name, v.created_at,
               v.transcript, v.transcript_confidence::float AS confidence, v.triage_label, v.rule_hits, v.report,
               v.report_status, v.report_problem, v.needs_human_review, v.input_mode, v.classifier_label,
               v.reviewed_at, v.timings,
               coalesce((SELECT is_valid FROM v_consents c WHERE c.patient_id = v.patient_id AND c.type = 'health_data'), false) AS health_consent
        FROM voice_reports v JOIN patients pa ON pa.patient_id = v.patient_id JOIN persons pe ON pe.person_id = pa.person_id
        WHERE EXISTS (SELECT 1 FROM assignments a JOIN service_requests r USING (request_id)
                      WHERE a.caregiver_id = :c AND r.patient_id = v.patient_id)
        ORDER BY v.reviewed_at IS NOT NULL,                                          -- unreviewed first
                 CASE v.triage_label WHEN 'emergency' THEN 0 WHEN 'urgent' THEN 1 ELSE 2 END,  -- then most serious
                 v.created_at DESC LIMIT 60"""), {"c": user.caregiver_id}).mappings().all()
    out = []
    for r in rows:
        r = dict(r)
        cats = oracle.rules()["categories"]
        r["rule_labels"] = [cats[h]["label_es"] for h in (r["rule_hits"] or []) if h in cats]   # Spanish names
        if not r["health_consent"]:   # no health data without consent
            r.update(transcript=None, report=None, rule_hits=[], rule_labels=[], health_notice="Falta consentimiento")
        out.append(r)
    audit(db, user_id=user.user_id, institution_id=user.institution_id, action="read_voice_reports", entity="voice_report",
          entity_id=None, detail={"count": len(out)})
    return out


@router.post("/voice/reports/{report_id}/review")
def review(report_id: str, user: CurrentUser = Depends(require_role(PHYSICIAN)), db: Session = Depends(tenant_db)) -> dict:
    patient = db.scalar(text("SELECT patient_id FROM voice_reports WHERE report_id = :r"), {"r": report_id})
    if patient is None:
        raise not_found_or_cross_tenant(db, user, "voice_report", report_id)
    allowed_patient(db, user, patient)
    db.execute(text("UPDATE voice_reports SET reviewed_by = :u, reviewed_at = now() WHERE report_id = :r"),
               {"u": user.user_id, "r": report_id})
    audit(db, user_id=user.user_id, institution_id=user.institution_id, action="voice_report_reviewed",
          entity="voice_report", entity_id=report_id)
    return {"report_id": report_id, "reviewed": True}


# ---- demo panel: example phrase as TEXT (no microphone, no Whisper) ---------------------------------------

class DemoVoiceIn(BaseModel):
    institution_id: str
    kind: str          # routine | urgent | emergency


@router.post("/demo/voice-sample")
def demo_voice(body: DemoVoiceIn, background: BackgroundTasks, user: CurrentUser = Depends(require_role(OWNER)),
               db: Session = Depends(tenant_db)) -> dict:
    import csv
    from pathlib import Path
    if body.kind not in ("routine", "urgent", "emergency"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Tipo de frase desconocido.")
    path = Path(ops.config_dir()).parent / "data" / "voice" / "triage_phrases.csv"
    if not path.exists():
        path = Path("/data/voice/triage_phrases.csv")
    with open(path, encoding="utf-8") as f:
        phrases = [r for r in csv.DictReader(f) if r["split"] == "test" and r["label"] == body.kind and r["hard_case"] == "False"]
    phrase = random.Random().choice(phrases)
    patient = db.scalar(text("""SELECT pa.patient_id FROM patients pa JOIN v_consents c USING (patient_id)
                                WHERE pa.institution_id = :i AND pa.active AND c.type = 'voice_assistant' AND c.is_valid
                                ORDER BY pa.patient_id LIMIT 1"""), {"i": body.institution_id})
    if patient is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Esa institución no tiene pacientes con autorización de voz.")
    result = oracle.process(db, user_id=user.user_id, institution_id=body.institution_id, patient_id=patient,
                            input_mode="demo_text", text_=phrase["text"])
    background.add_task(oracle.write_report, result["report_id"], body.institution_id)
    return {**result, "phrase_id": phrase["phrase_id"], "patient_id": patient}
