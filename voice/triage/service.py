"""ORACLE-Voz internal service (http://voice:8001), called only by the API.

POST /transcribe  audio (WebM/Opus or WAV) -> text, confidence, no_speech_prob, duration, ms
POST /classify    {"text"} -> label + probabilities (503 while the classifier is not ready)
GET  /health      readiness of each part

Confidence (documented in voice/README.md): segment-duration-weighted exp(avg_logprob) of Whisper;
no_speech_prob = the highest segment value. The API asks to repeat when confidence < 0.6 or the text has
fewer than 3 words, or when no_speech_prob > 0.6 (probably silence).
If voice/models/ is empty (fresh clone), the classifier is trained at start-up in the background.
"""
from __future__ import annotations

import math
import os
import tempfile
import threading
import time

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel

from voice.triage import classifier

app = FastAPI(title="ORACLE-Voz internal")
state: dict = {"whisper": None, "classifier": None, "classifier_status": "loading"}
lock = threading.Lock()


def _load_classifier() -> None:
    try:
        if not classifier.MODEL_PATH.exists():
            state["classifier_status"] = "training"          # fresh clone: train so the demo does not break
            classifier.build_and_train()
        state["classifier"] = classifier.load()
        state["classifier_status"] = "ready"
    except Exception as exc:  # noqa: BLE001
        state["classifier_status"] = f"error: {exc}"


@app.on_event("startup")
def startup() -> None:
    threading.Thread(target=_load_classifier, daemon=True).start()


def whisper():
    with lock:
        if state["whisper"] is None:
            from faster_whisper import WhisperModel
            state["whisper"] = WhisperModel(os.environ.get("WHISPER_MODEL", "small"), device="cpu", compute_type="int8",
                                            cpu_threads=int(os.environ.get("WHISPER_THREADS", "8")))
        return state["whisper"]


@app.get("/health")
def health() -> dict:
    return {"classifier": state["classifier_status"], "whisper": "loaded" if state["whisper"] else "lazy"}


@app.post("/transcribe")
async def transcribe(audio: UploadFile = File(...)) -> dict:
    started = time.perf_counter()
    data = await audio.read()
    if len(data) > 8_000_000:
        raise HTTPException(413, "audio too large")
    with tempfile.NamedTemporaryFile(suffix=os.path.splitext(audio.filename or "a.webm")[1] or ".webm") as f:
        f.write(data)
        f.flush()
        segments, info = whisper().transcribe(f.name, language="es", beam_size=5, vad_filter=True)
        segments = list(segments)
    total = sum(s.end - s.start for s in segments) or 1.0
    confidence = sum(math.exp(s.avg_logprob) * (s.end - s.start) for s in segments) / total if segments else 0.0
    return {"text": " ".join(s.text.strip() for s in segments).strip(), "confidence": round(confidence, 3),
            "no_speech_prob": round(max((s.no_speech_prob for s in segments), default=1.0), 3),
            "duration_s": round(info.duration, 1), "ms": int((time.perf_counter() - started) * 1000)}


class TextIn(BaseModel):
    text: str


@app.post("/classify")
def classify(body: TextIn) -> dict:
    if state["classifier"] is None:
        raise HTTPException(503, state["classifier_status"])
    started = time.perf_counter()
    out = classifier.predict(state["classifier"], [body.text])[0]
    return {**out, "ms": int((time.perf_counter() - started) * 1000)}
