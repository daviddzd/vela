"""Measures the three models of Enlaza Voz on this laptop and prints JSON (run INSIDE the api container).

    docker compose exec -T api python - < docs/biblia/build/measure_models.py
    (bash docs/biblia/build/measure_models.sh does that and writes docs/biblia/datos/modelos_medidos.yaml)

- qwen3:8b through Ollama with the SAME request as backend/app/services/llm_report.py (JSON schema, think false,
  temperature 0.2): once on the integrated GPU (Ollama's default here, Vulkan) and once forced to CPU (num_gpu 0).
  First call of each mode = load + answer; then 3 warm calls. Memory from Ollama's /api/ps (size, size_vram).
- Keras classifier through the voice service (/classify): 20 calls, median.
Nothing is written to the database.
"""
import json
import os
import statistics
import time

import httpx

from app.services import llm_report

OLLAMA = os.environ.get("OLLAMA_URL", "http://host.docker.internal:11434")
MODEL = os.environ.get("OLLAMA_MODEL", "qwen3:8b")
NOTE = ("Mi papá amaneció de buen humor, desayunó completo y ya se tomó sus pastillas. Anoche tosió un poco, "
        "pero hoy ya no, y quiere salir a caminar en la tarde.")


def chat(options: dict) -> dict:
    body = {"model": MODEL, "stream": False, "think": False, "format": llm_report.Report.model_json_schema(),
            "options": {"temperature": 0.2, **options},
            "messages": [{"role": "system", "content": llm_report.SYSTEM_PROMPT},
                         {"role": "user", "content": f"Nivel de triaje asignado por el sistema: routine.\nNota transcrita:\n\"\"\"{NOTE}\"\"\""}]}
    t0 = time.perf_counter()
    r = httpx.post(f"{OLLAMA}/api/chat", json=body, timeout=900).json()
    total = time.perf_counter() - t0
    llm_report.Report.model_validate(json.loads(r["message"]["content"]))   # the answer is valid JSON for the schema
    return {"total_s": total, "load_s": r.get("load_duration", 0) / 1e9,
            "tok_s": r["eval_count"] / (r["eval_duration"] / 1e9), "tokens": r["eval_count"]}


def loaded() -> dict:
    for m in httpx.get(f"{OLLAMA}/api/ps", timeout=30).json().get("models", []):
        if m["name"].startswith(MODEL.split(":")[0]):
            return {"size_gb": m["size"] / 1e9, "vram_gb": m.get("size_vram", 0) / 1e9}
    return {}


def mode(options: dict) -> dict:
    httpx.post(f"{OLLAMA}/api/generate", json={"model": MODEL, "keep_alive": 0}, timeout=60)   # unload: next call loads
    time.sleep(3)
    cold = chat(options)
    warm = [chat(options) for _ in range(3)]
    return {"cold_total_s": cold["total_s"], "load_s": cold["load_s"],
            "warm_total_s": statistics.median(w["total_s"] for w in warm),
            "tok_s": statistics.median(w["tok_s"] for w in warm),
            "tokens": statistics.median(w["tokens"] for w in warm), **loaded()}


def classifier() -> dict:
    times = []
    for _ in range(20):
        t0 = time.perf_counter()
        httpx.post(f"{os.environ.get('VOICE_URL', 'http://voice:8001')}/classify", json={"text": NOTE}, timeout=30).raise_for_status()
        times.append(time.perf_counter() - t0)
    return {"median_ms": statistics.median(times) * 1000}


tags = {m["name"]: m for m in httpx.get(f"{OLLAMA}/api/tags", timeout=30).json()["models"]}
out = {"model": MODEL, "file_gb": tags[MODEL]["size"] / 1e9, "details": tags[MODEL].get("details", {}),
       "cpu": mode({"num_gpu": 0}), "gpu": mode({}), "classifier": classifier()}
print(json.dumps(out))
