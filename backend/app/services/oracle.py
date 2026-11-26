"""ORACLE-Voz pipeline (docs/spec/05), run by the API:

  consent voice_assistant? --no--> NoConsent (nothing is recorded or processed)
  audio -> voice service /transcribe (or typed text)          -> VoiceUnavailable: the UI offers typing
  rules (config/emergency_rules.yaml)  -> a hit is ALWAYS emergency
  classifier (voice service /classify) -> may RAISE the level, never lower a rule hit
                                          unavailable -> rules only + needs_human_review
  save voice_report (transcript only; the audio is never stored)
  emergency -> critical alert to coordination at once (before the LLM)
  background: LLM report for the physician (app/services/llm_report.py)
"""
from __future__ import annotations

import os
import time

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.audit import audit
from app.core.db import tenant_session
from app.core.events import publish
from app.services import alerts_followup, llm_report
from app.services.triage_rules import LEVELS, rule_hits, rules

MIN_CONFIDENCE = 0.6        # exp(avg_logprob), duration-weighted (voice/README.md)
MAX_NO_SPEECH = 0.6
MIN_WORDS = 3


class NoConsent(Exception):
    """No voice: no valid voice_assistant consent ("no_consent"), or the person did not assent ("no_assent")."""
    def __init__(self, reason: str = "no_consent"):
        super().__init__(reason)
        self.reason = reason


class VoiceUnavailable(Exception):
    pass


def voice_url() -> str:
    return os.environ.get("VOICE_URL", "http://voice:8001")


def transcribe(audio: bytes, filename: str) -> dict:
    try:
        r = httpx.post(f"{voice_url()}/transcribe", files={"audio": (filename, audio)}, timeout=180)
        r.raise_for_status()
        return r.json()
    except Exception as exc:  # noqa: BLE001
        raise VoiceUnavailable(str(exc)) from exc


def classify(text_: str) -> dict | None:
    try:
        r = httpx.post(f"{voice_url()}/classify", json={"text": text_}, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception:  # noqa: BLE001 - classifier missing/training: rules only
        return None


# Why the voice assistant cannot be used for a patient, or NULL if it can. A representative may sign, but if the
# person did NOT assent (patient_assent = 'no') the voice is blocked like without consent (team decision 25 Nov 2026;
# docs/legal/formato_consentimiento.md: "No estuvo de acuerdo (en ese caso no se usa el asistente de voz)").
VOICE_BLOCK_SQL = """
    SELECT CASE WHEN NOT coalesce(c.is_valid, false) THEN 'no_consent'
                WHEN c.patient_assent = 'no' THEN 'no_assent' END
    FROM (SELECT 1) one LEFT JOIN v_consents c ON c.patient_id = :p AND c.type = 'voice_assistant'"""


def voice_block_reason(db: Session, patient_id: str) -> str | None:
    return db.scalar(text(VOICE_BLOCK_SQL), {"p": patient_id})


def has_voice_consent(db: Session, patient_id: str) -> bool:
    return voice_block_reason(db, patient_id) is None


def process(db: Session, *, user_id: str, institution_id: str, patient_id: str, input_mode: str,
            text_: str | None = None, audio: bytes | None = None, filename: str = "nota.webm") -> dict:
    reason = voice_block_reason(db, patient_id)
    if reason is not None:
        audit(db, user_id=user_id, institution_id=institution_id, action=f"voice_blocked_{reason}",
              entity="patient", entity_id=patient_id, allowed=False)
        raise NoConsent(reason)
    timings: dict = {}
    confidence, no_speech = None, None
    if audio is not None:
        t = transcribe(audio, filename)
        text_, confidence, no_speech = t["text"], t["confidence"], t["no_speech_prob"]
        timings.update(transcribe_ms=t["ms"], audio_s=t["duration_s"])
    text_ = (text_ or "").strip()

    started = time.perf_counter()
    hits = rule_hits(text_)
    timings["rules_ms"] = int((time.perf_counter() - started) * 1000)
    cls = classify(text_) if text_ else None
    if cls:
        timings["classify_ms"] = cls["ms"]
    level = "emergency" if hits else (cls["label"] if cls else "urgent")   # classifier never lowers a rule hit
    needs_review = (cls is None or len(text_.split()) < MIN_WORDS
                    or (confidence is not None and confidence < MIN_CONFIDENCE)
                    or (no_speech is not None and no_speech > MAX_NO_SPEECH))
    report_id = db.scalar(text("""
        INSERT INTO voice_reports (institution_id, patient_id, submitted_by, transcript, transcript_confidence,
                                   triage_label, rule_hits, needs_human_review, model_used, input_mode,
                                   classifier_label, classifier_probs, no_speech_prob, timings)
        VALUES (:i, :p, :u, :t, :c, :l, :h, :r, :m, :mode, :cl, CAST(:cp AS jsonb), :ns, CAST(:tm AS jsonb))
        RETURNING report_id"""),
        {"i": institution_id, "p": patient_id, "u": user_id, "t": text_, "c": confidence, "l": level, "h": hits,
         "r": needs_review, "m": f"whisper-{os.environ.get('WHISPER_MODEL', 'small')}+keras+{os.environ.get('OLLAMA_MODEL', 'qwen3:8b')}",
         "mode": input_mode, "cl": cls["label"] if cls else None, "cp": _json(cls["probs"]) if cls else None,
         "ns": no_speech, "tm": _json(timings)})
    # Two ways to be an emergency (team decision 23 Nov 2026, CLAUDE.md rule 6): a RULE fired -> red 911 screen;
    # ONLY the classifier -> amber notice with 911 + critical review alert for coordination. Same stored level.
    source = ("rule" if hits else "classifier") if level == "emergency" else None
    audit(db, user_id=user_id, institution_id=institution_id, action="voice_note", entity="voice_report",
          entity_id=report_id, detail={"level": level, "rule_hits": hits, "input_mode": input_mode,
                                       **({"emergency_source": source} if source else {})})
    if source == "classifier":
        name = db.scalar(text("""SELECT pe.first_name || ' ' || pe.paternal_surname FROM patients pa
                                 JOIN persons pe USING (person_id) WHERE pa.patient_id = :p"""), {"p": patient_id})
        alerts_followup.open_review(db, institution_id=institution_id, patient_id=patient_id, patient_name=name,
                                    report_id=report_id)
    elif source == "rule":
        cats = rules()["categories"]
        reason = ", ".join(cats[h]["label_es"] for h in hits)
        name = db.scalar(text("""SELECT pe.first_name || ' ' || pe.paternal_surname FROM patients pa
                                 JOIN persons pe USING (person_id) WHERE pa.patient_id = :p"""), {"p": patient_id})
        alert_id = db.scalar(text("""INSERT INTO alerts (institution_id, type, level, patient_id, message, code)
                                     VALUES (:i, 'emergency', 'critical', :p, :m, :c) RETURNING alert_id"""),
                             {"i": institution_id, "p": patient_id, "c": f"voice-rule:{report_id}",
                              "m": f"Posible emergencia en nota de voz de {name} ({reason}). Se indicó llamar al 911."})
        publish(db, "alert.created", institution_id, alert_id=alert_id, request_id=None)
    support = next((rules().get("support_lines", {})[h] for h in hits if h in rules().get("support_lines", {})), None)
    return {"report_id": report_id, "level": level, "emergency_source": source, "rule_hits": hits, "support_line": support,
            "needs_human_review": needs_review,
            "classifier": cls["label"] if cls else None, "transcript": text_, "confidence": confidence,
            "ask_repeat": bool(audio is not None and needs_review and cls is not None and level != "emergency")}


def write_report(report_id: str, institution_id: str) -> None:
    """Background task (after the response was sent): LLM report, validated; failures keep transcript + level."""
    with tenant_session(institution_id) as db:
        row = db.execute(text("SELECT transcript, triage_label, timings FROM voice_reports WHERE report_id = :r"),
                         {"r": report_id}).one()
    report, status, problem, ms = llm_report.generate(row.transcript, row.triage_label)
    with tenant_session(institution_id) as db:
        db.execute(text("""UPDATE voice_reports SET report = CAST(:rep AS jsonb), report_status = :s, report_problem = :p,
                           timings = timings || CAST(:tm AS jsonb) WHERE report_id = :r"""),
                   {"rep": _json(report) if report else None, "s": status, "p": problem, "tm": _json({"llm_ms": ms}),
                    "r": report_id})
        publish(db, "voice.report_ready", institution_id, report_id=report_id, status=status)


def _json(v) -> str:
    import json
    return json.dumps(v, ensure_ascii=False)


assert LEVELS == ["routine", "urgent", "emergency"]
