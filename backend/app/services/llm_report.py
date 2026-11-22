"""Report for the physician, written by the local LLM (Ollama). It NEVER diagnoses, never recommends a
treatment and never tells anyone that something is not an emergency (CLAUDE.md rule 6).

Defences, in order:
1. System instruction in Spanish: summarize what was said, do not infer diseases, do not recommend.
2. Ollama `format` = the JSON schema below, thinking disabled (`think: false`), temperature 0.2.
3. Pydantic validation. If it fails, only the transcript and the triage level are kept.
4. A text filter on the generated fields (not on the verbatim quotes): diagnosis, treatment advice or
   "no es emergencia" -> the report is discarded and the reason is stored.
The triage level is the SYSTEM's (rules + classifier); the LLM cannot change it.
"""
from __future__ import annotations

import json
import os
import re
import time
from typing import Literal

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.services.triage_rules import normalize

SYSTEM_PROMPT = (
    "Eres un asistente que resume notas de voz de familiares o cuidadores de personas mayores para un médico. "
    "Reglas obligatorias: 1) Resume solo lo que la persona dijo, con sus palabras cuando sea posible. "
    "2) No infieras enfermedades ni des diagnósticos. 3) No recomiendes tratamientos, medicamentos ni dosis. "
    "4) Nunca digas que algo no es una emergencia ni que no es grave. 5) Si algo no se entendió, anótalo en "
    "'limitaciones'. 6) Responde solo con el JSON pedido, en español de México. "
    "Cómo llenar los campos: 'resumen' en una o dos frases en tercera persona; 'sintomas_mencionados' con cada "
    "molestia que la persona describió, con sus palabras (por ejemplo «se agarró el pecho», «suda mucho»); "
    "'signos_de_alarma' con lo dicho que suene grave (falta de aire, dolor en el pecho, no responde, sangrado, "
    "caída, confusión de repente), también con sus palabras y sin nombrar enfermedades; 'inicio' con cuándo "
    "empezó según la persona (o vacío); 'medicamentos_mencionados' solo si los nombró; 'frases_textuales' con "
    "hasta tres frases copiadas tal cual."
)


class Report(BaseModel):
    resumen: str = Field(max_length=600)
    sintomas_mencionados: list[str] = Field(default_factory=list, max_length=12)
    inicio: str = ""
    signos_de_alarma: list[str] = Field(default_factory=list, max_length=12)
    medicamentos_mencionados: list[str] = Field(default_factory=list, max_length=12)
    nivel_triaje: Literal["emergency", "urgent", "routine"]
    frases_textuales: list[str] = Field(default_factory=list, max_length=6)
    limitaciones: str = "Transcripción automática; no es diagnóstico."


# Phrases that must never appear in the generated text (normalized: lowercase, no accents)
FORBIDDEN = [
    r"\bdiagnostico (es|de|probable|presuntivo|seria)", r"\bse diagnostica", r"\bdiagnosticad", r"probablemente (tiene|tenga|sea|es|padece)", r"podria (tener|ser|estar padeciendo)",
    r"se trata de (un|una)", r"(sugiere|indica|compatible con) (un|una)", r"(le|te|les) recomiendo", r"se recomienda",
    r"(debe|deberia|tiene que|tienen que) (tomar|administrar|darle|aplicar)", r"\b(tome|tomar|darle) \d",
    r"no es (una )?emergencia", r"no es grave", r"no hay (de que|por que) preocupar",
]
_forbidden = [re.compile(p) for p in FORBIDDEN]


def forbidden_in(report: Report) -> str | None:
    """First forbidden pattern found in the generated fields (verbatim quotes are the person's own words)."""
    generated = [report.resumen, report.inicio, report.limitaciones, *report.sintomas_mencionados,
                 *report.signos_de_alarma, *report.medicamentos_mencionados]
    # the standard disclaimer ("no es diagnóstico") is ours, not a diagnosis: leave it out of the check
    text = normalize(" ".join(generated)).replace("no es diagnostico", "")
    for rx in _forbidden:
        if rx.search(text):
            return rx.pattern
    return None


def generate(transcript: str, level: str, timeout: float = 240.0) -> tuple[dict | None, str, str | None, int]:
    """Returns (report or None, status, problem, milliseconds). status: ready | invalid | failed."""
    started = time.perf_counter()
    body = {
        "model": os.environ.get("OLLAMA_MODEL", "qwen3:8b"), "stream": False, "think": False,
        "format": Report.model_json_schema(), "options": {"temperature": 0.2},
        "messages": [{"role": "system", "content": SYSTEM_PROMPT},
                     {"role": "user", "content": f"Nivel de triaje asignado por el sistema: {level}.\nNota transcrita:\n\"\"\"{transcript}\"\"\""}],
    }
    try:
        r = httpx.post(f"{os.environ.get('OLLAMA_URL', 'http://host.docker.internal:11434')}/api/chat", json=body, timeout=timeout)
        r.raise_for_status()
        content = r.json()["message"]["content"]
    except Exception as exc:  # noqa: BLE001 - LLM down or slow: keep transcript + level
        return None, "failed", f"llm_unavailable: {type(exc).__name__}", int((time.perf_counter() - started) * 1000)
    ms = int((time.perf_counter() - started) * 1000)
    try:
        report = Report.model_validate(json.loads(content))
    except (ValidationError, json.JSONDecodeError) as exc:
        return None, "invalid", f"json_invalid: {str(exc)[:200]}", ms
    report.nivel_triaje = level                       # the LLM never decides the level
    bad = forbidden_in(report)                        # check what the LLM wrote...
    if bad:
        return None, "invalid", f"forbidden_phrase: {bad}", ms
    if "no es diagnostico" not in normalize(report.limitaciones):   # ...then add the disclaimer, always
        report.limitaciones = (report.limitaciones.strip() + " " if report.limitaciones.strip() else "") + \
            "Transcripción automática; no es diagnóstico."
    return report.model_dump(), "ready", None, ms
