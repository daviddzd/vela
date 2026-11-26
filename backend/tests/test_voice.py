"""ORACLE-Voz: consent first, rules before the classifier (never lowered), fallbacks, scopes, the physician's
inbox and the report filter. The classifier, Whisper and the LLM are replaced by fakes (no external services)."""
import json

import pytest
from sqlalchemy import text

from app.services import llm_report, oracle
from tests.conftest import login, session_on

EMERGENCY_TEXT = "mi papá no puede respirar y tiene los labios morados"
ROUTINE_TEXT = "buenos días, quería confirmar la visita de mañana"


@pytest.fixture(autouse=True)
def no_background_llm(monkeypatch):
    calls = []
    monkeypatch.setattr(oracle, "write_report", lambda rid, inst: calls.append(rid))
    return calls


def fake_classifier(monkeypatch, label: str | None):
    monkeypatch.setattr(oracle, "classify", lambda t: None if label is None else
                        {"label": label, "probs": {"routine": 0.1, "urgent": 0.1, "emergency": 0.8}, "ms": 3})


def send(client, pid: str, text_: str) -> dict:
    """POST a typed note; on any error show the status and body (not just a KeyError)."""
    r = client.post("/api/voice/text", json={"patient_id": pid, "text": text_})
    assert r.status_code == 200, f"{r.status_code} {r.text}"
    return r.json()


def family_patient(db_conn) -> str:
    with session_on(db_conn, "INS-A") as s:
        return s.scalar(text("SELECT patient_id FROM family_members WHERE family_member_id = 'FAM-0001'"))


def test_without_voice_consent_nothing_is_processed(tx_client, db_conn, monkeypatch):
    fake_classifier(monkeypatch, "routine")
    pid = family_patient(db_conn)
    count = text("SELECT count(*) FROM voice_reports WHERE patient_id = :p")
    with session_on(db_conn, "INS-A") as s:
        before = s.scalar(count, {"p": pid})
        s.execute(text("UPDATE consents SET granted = false WHERE patient_id = :p AND type = 'voice_assistant'"), {"p": pid})
        s.commit()
    login(tx_client, "fam-0001@ejemplo.test")
    r = tx_client.post("/api/voice/text", json={"patient_id": pid, "text": EMERGENCY_TEXT})
    assert r.status_code == 403 and "autorización" in r.json()["detail"]
    with session_on(db_conn, "INS-A") as s:
        assert s.scalar(count, {"p": pid}) == before                        # nothing was stored


def test_rule_hit_is_emergency_even_if_the_classifier_says_routine(tx_client, db_conn, monkeypatch):
    fake_classifier(monkeypatch, "routine")
    pid = family_patient(db_conn)
    login(tx_client, "fam-0001@ejemplo.test")
    r = send(tx_client, pid, EMERGENCY_TEXT)
    assert r["level"] == "emergency" and "severe_breathing" in r["rule_hits"] and r["classifier"] == "routine"
    with session_on(db_conn, "INS-A") as s:
        # created_at = now() = start of THIS test's transaction: ignores live alerts committed meanwhile
        alert = s.scalar(text("SELECT level FROM alerts WHERE type = 'emergency' AND patient_id = :p AND created_at = now()"),
                         {"p": pid})
    assert alert == "critical"


def test_classifier_can_raise_a_level(tx_client, db_conn, monkeypatch):
    fake_classifier(monkeypatch, "emergency")
    pid = family_patient(db_conn)
    login(tx_client, "fam-0001@ejemplo.test")
    r = send(tx_client, pid, "está muy raro, no sé qué le pasa")
    assert r["rule_hits"] == [] and r["level"] == "emergency"


def test_without_classifier_rules_only_and_human_review(tx_client, db_conn, monkeypatch):
    fake_classifier(monkeypatch, None)
    pid = family_patient(db_conn)
    login(tx_client, "fam-0001@ejemplo.test")
    r = send(tx_client, pid, ROUTINE_TEXT)
    assert r["level"] == "urgent" and r["needs_human_review"] is True      # never "routine" without the classifier
    r = send(tx_client, pid, EMERGENCY_TEXT)
    assert r["level"] == "emergency"                                        # rules still work


def test_voice_service_down_asks_to_type(tx_client, db_conn, monkeypatch):
    def down(audio, filename):
        raise oracle.VoiceUnavailable("connection refused")
    monkeypatch.setattr(oracle, "transcribe", down)
    pid = family_patient(db_conn)
    login(tx_client, "fam-0001@ejemplo.test")
    r = tx_client.post("/api/voice/notes", data={"patient_id": pid}, files={"audio": ("nota.webm", b"\x1a\x45", "audio/webm")})
    assert r.status_code == 503 and "Escribe" in r.json()["detail"]


def test_family_cannot_send_a_note_about_another_patient(tx_client, monkeypatch):
    fake_classifier(monkeypatch, "routine")
    login(tx_client, "fam-0001@ejemplo.test")
    assert tx_client.post("/api/voice/text", json={"patient_id": "PAC-0002", "text": ROUTINE_TEXT}).status_code == 403
    assert tx_client.post("/api/voice/text", json={"patient_id": "PAC-0151", "text": ROUTINE_TEXT}).status_code == 403


def test_call_me_creates_a_request_with_the_language(tx_client, db_conn):
    pid = family_patient(db_conn)
    login(tx_client, "fam-0001@ejemplo.test")
    r = tx_client.post("/api/voice/call-me", json={"patient_id": pid}).json()
    with session_on(db_conn, "INS-A") as s:
        msg = s.scalar(text("SELECT message FROM alerts WHERE alert_id = :a AND type = 'call_back'"), {"a": r["alert_id"]})
    assert "Lengua: " in msg


def test_physician_inbox_scope_consent_and_review(tx_client, db_conn, monkeypatch):
    fake_classifier(monkeypatch, "urgent")
    with session_on(db_conn, "INS-A") as s:
        mine = s.scalar(text("""SELECT r.patient_id FROM assignments a JOIN service_requests r USING (request_id)
                                JOIN v_consents c ON c.patient_id = r.patient_id AND c.type = 'voice_assistant' AND c.is_valid
                                WHERE a.caregiver_id = 'CUI-001' LIMIT 1"""))
        rid = s.scalar(text("""INSERT INTO voice_reports (institution_id, patient_id, submitted_by, transcript, triage_label,
                               model_used, report_status) VALUES ('INS-A', :p, 'USR-003', 'le duele la cabeza', 'urgent',
                               'test', 'ready') RETURNING report_id"""), {"p": mine})
        other = s.scalar(text("""SELECT patient_id FROM patients pa WHERE institution_id = 'INS-A' AND NOT EXISTS (
                                 SELECT 1 FROM assignments a JOIN service_requests r USING (request_id)
                                 WHERE a.caregiver_id = 'CUI-001' AND r.patient_id = pa.patient_id) LIMIT 1"""))
        rid_other = s.scalar(text("""INSERT INTO voice_reports (institution_id, patient_id, submitted_by, transcript, triage_label,
                                     model_used) VALUES ('INS-A', :p, 'USR-002', 'x', 'routine', 'test') RETURNING report_id"""), {"p": other})
        s.commit()
    login(tx_client, "cui-001@ejemplo.test")
    ids = {r["report_id"]: r for r in tx_client.get("/api/voice/reports").json()}
    assert rid in ids and rid_other not in ids
    assert tx_client.post(f"/api/voice/reports/{rid}/review").status_code == 200
    assert tx_client.post(f"/api/voice/reports/{rid_other}/review").status_code == 403
    with session_on(db_conn, "INS-A") as s:                      # without health_data consent: content hidden
        s.execute(text("UPDATE consents SET granted = false WHERE patient_id = :p AND type = 'health_data'"), {"p": mine})
        s.commit()
    hidden = next(r for r in tx_client.get("/api/voice/reports").json() if r["report_id"] == rid)
    assert hidden["transcript"] is None and hidden["health_notice"] == "Falta consentimiento"


# ---- the report filter -----------------------------------------------------------------------------

def _fake_ollama(monkeypatch, content: dict):
    class R:
        def raise_for_status(self): ...
        def json(self): return {"message": {"content": json.dumps(content)}}
    monkeypatch.setattr(llm_report.httpx, "post", lambda *a, **k: R())


GOOD = {"resumen": "La hija cuenta que su papá tose desde ayer.", "sintomas_mencionados": ["tose"], "inicio": "ayer",
        "signos_de_alarma": [], "medicamentos_mencionados": [], "nivel_triaje": "routine", "frases_textuales": ["tose mucho"],
        "limitaciones": ""}


def test_valid_report_keeps_the_system_level_and_adds_the_disclaimer(monkeypatch):
    _fake_ollama(monkeypatch, GOOD)
    report, status, problem, _ = llm_report.generate("tose mucho desde ayer", "urgent")
    assert status == "ready" and report["nivel_triaje"] == "urgent"          # the LLM never sets the level
    assert "no es diagnóstico" in report["limitaciones"]


@pytest.mark.parametrize("field, text_", [
    ("resumen", "Probablemente tiene una neumonía."),
    ("resumen", "Le recomiendo que tome paracetamol."),
    ("limitaciones", "No es una emergencia."),
    ("signos_de_alarma", ["no es grave"]),
])
def test_diagnosis_advice_or_reassurance_is_discarded(monkeypatch, field, text_):
    _fake_ollama(monkeypatch, {**GOOD, field: text_})
    report, status, problem, _ = llm_report.generate("tose mucho desde ayer", "urgent")
    assert report is None and status == "invalid" and problem.startswith("forbidden_phrase")


def test_invalid_json_keeps_only_transcript_and_level(monkeypatch):
    _fake_ollama(monkeypatch, {"resumen": "x"})                       # missing required fields
    report, status, problem, _ = llm_report.generate("tose", "routine")
    assert report is None and status == "invalid" and problem.startswith("json_invalid")


def test_demo_voice_sample_uses_text_without_whisper(tx_client, monkeypatch):
    fake_classifier(monkeypatch, "routine")
    def never(*a, **k):
        raise AssertionError("Whisper must not be called by the demo button")
    monkeypatch.setattr(oracle, "transcribe", never)
    login(tx_client, "owner@ejemplo.test")
    r = tx_client.post("/api/demo/voice-sample", json={"institution_id": "INS-A", "kind": "emergency"}).json()
    assert r["level"] == "emergency" and r["phrase_id"].startswith("PHR-")


# ---- 21 Nov 2026: new rules, Línea de la Vida, inbox order --------------------------------------------

def test_ext025_seizure_is_caught_by_the_rules():
    from app.services.triage_rules import rule_hits
    assert "seizure" in rule_hits("esta temblando todo el cuerpo bien fuerte y echa espuma por la boca")


def test_self_harm_shows_the_linea_de_la_vida(tx_client, db_conn, monkeypatch):
    fake_classifier(monkeypatch, "routine")
    pid = family_patient(db_conn)
    login(tx_client, "fam-0001@ejemplo.test")
    r = send(tx_client, pid, "mi papá dice que ya no quiere vivir, que se quiere matar")
    assert r["level"] == "emergency" and "self_harm" in r["rule_hits"]
    assert r["support_line"]["phone"] == "800 911 2000" and "gob.mx" in r["support_line"]["source"]
    r = send(tx_client, pid, "mi mamá no puede respirar y tiene los labios morados")
    assert r["support_line"] is None                          # only for self_harm


def test_inbox_unreviewed_first_then_most_serious(tx_client, db_conn):
    with session_on(db_conn, "INS-A") as s:
        pid = s.scalar(text("""SELECT r.patient_id FROM assignments a JOIN service_requests r USING (request_id)
                               WHERE a.caregiver_id = 'CUI-001' LIMIT 1"""))
        made = {}
        for label, reviewed in (("routine", False), ("emergency", True), ("urgent", False), ("emergency", False)):
            made[(label, reviewed)] = s.scalar(text(f"""INSERT INTO voice_reports (institution_id, patient_id, submitted_by,
                transcript, triage_label, model_used, reviewed_at) VALUES ('INS-A', :p, 'USR-003', 'x', :l, 'test',
                {'now()' if reviewed else 'NULL'}) RETURNING report_id"""), {"p": pid, "l": label})
        s.commit()
    login(tx_client, "cui-001@ejemplo.test")
    order = [r["report_id"] for r in tx_client.get("/api/voice/reports").json() if r["report_id"] in made.values()]
    assert order == [made[("emergency", False)], made[("urgent", False)], made[("routine", False)], made[("emergency", True)]]


def test_person_who_did_not_assent_gets_no_voice(tx_client, db_conn, monkeypatch):
    """A representative signed, but the person did not agree (assent = 'no'): blocked like without consent
    (team decision 25 Nov 2026; docs/legal/formato_consentimiento.md)."""
    fake_classifier(monkeypatch, "routine")
    pid = family_patient(db_conn)
    count = text("SELECT count(*) FROM voice_reports WHERE patient_id = :p")
    with session_on(db_conn, "INS-A") as s:
        before = s.scalar(count, {"p": pid})
        s.execute(text("""UPDATE consents SET granted = true, granted_by = 'legal_representative', patient_assent = 'no'
                          WHERE patient_id = :p AND type = 'voice_assistant'"""), {"p": pid})
        assert s.scalar(text("SELECT is_valid FROM v_consents WHERE patient_id = :p AND type = 'voice_assistant'"),
                        {"p": pid})                                    # the signature itself is still valid
        s.commit()
    login(tx_client, "fam-0001@ejemplo.test")
    [p] = [x for x in tx_client.get("/api/voice/patients").json() if x["patient_id"] == pid]
    assert p["voice_consent"] is False and p["voice_block"] == "no_assent"
    r = tx_client.post("/api/voice/text", json={"patient_id": pid, "text": EMERGENCY_TEXT})
    assert r.status_code == 403 and "no estuvo de acuerdo" in r.json()["detail"]
    with session_on(db_conn, "INS-A") as s:
        assert s.scalar(count, {"p": pid}) == before                    # nothing was stored
    # any other assent keeps the voice working
    with session_on(db_conn, "INS-A") as s:
        s.execute(text("UPDATE consents SET patient_assent = 'unable_to_express' WHERE patient_id = :p AND type = 'voice_assistant'"),
                  {"p": pid})
        s.commit()
    assert send(tx_client, pid, "Hoy desayunó bien y salió a caminar un rato.")["level"] in ("routine", "urgent", "emergency")
