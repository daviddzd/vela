#!/usr/bin/env bash
# Measure the three models of Enlaza Voz on this laptop -> docs/biblia/datos/modelos_medidos.yaml (versioned, dated).
# Run by hand when the models or the laptop change (takes ~5 min: qwen3:8b on CPU is slow on purpose):
#   bash docs/biblia/build/measure_models.sh
# Needs `docker compose up -d` and Ollama running on Windows. Writes nothing to the database.
set -euo pipefail
cd "$(dirname "$0")/../../.."
OUTFILE=docs/biblia/datos/modelos_medidos.yaml

echo "Midiendo qwen3:8b (CPU y GPU integrada) y el clasificador…"
LLM=$(docker compose exec -T api python - < docs/biblia/build/measure_models.py)
echo "Tamaño y parámetros del clasificador de Keras y de Whisper small…"
VOICE=$(docker compose exec -T voice python -c '
import json, os, subprocess
import keras
m = keras.models.load_model("/repo/voice/models/triage_classifier.keras")
import glob   # only Whisper small (the cache also keeps models of earlier experiments)
w = subprocess.run(["du", "-sbL", *glob.glob("/root/.cache/huggingface/hub/models--Systran--faster-whisper-small/snapshots/*")],
                   capture_output=True, text=True).stdout.split()[0]
print(json.dumps({"keras_params": m.count_params(), "keras_mb": os.path.getsize("/repo/voice/models/triage_classifier.keras") / 1e6,
                  "whisper_cache_mb": int(w) / 1e6}))' 2>/dev/null | tail -1)
echo "Datos de la laptop (Windows)…"
HW=$(powershell.exe -NoProfile -Command '
$cs = Get-CimInstance Win32_ComputerSystem; $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
$gpu = Get-CimInstance Win32_VideoController | Select-Object -First 1
@{ ram_gb = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1); cpu = $cpu.Name.Trim(); cores = $cpu.NumberOfCores;
   threads = $cpu.NumberOfLogicalProcessors; gpu = $gpu.Name } | ConvertTo-Json -Compress' | tr -d '\r')

python3 - "$LLM" "$VOICE" "$HW" "$OUTFILE" <<'EOF'
import json, sys, datetime
llm, voice, hw = (json.loads(a) for a in sys.argv[1:4])
today = datetime.date.today().isoformat()
def item(valor, descripcion, metodo):
    return {"valor": valor, "descripcion": descripcion, "fecha": today, "metodo": metodo}
how_llm = ("docs/biblia/build/measure_models.py: misma petición que llm_report.py (esquema JSON, think false, temperatura 0.2), "
           "nota de 2 frases; 1 llamada en frío y mediana de 3 en caliente")
d = {
  "laptop_ram": item(f"{hw['ram_gb']:.0f} GB", "Memoria RAM de la laptop (la GPU integrada usa esta misma memoria)", "Windows, Win32_ComputerSystem"),
  "laptop_cpu": item(f"{hw['cpu']} ({hw['cores']} núcleos, {hw['threads']} hilos)", "Procesador de la laptop", "Windows, Win32_Processor"),
  "laptop_gpu": item(hw["gpu"], "GPU integrada de la laptop", "Windows, Win32_VideoController"),
  "llm_archivo": item(f"{llm['file_gb']:.1f} GB", "Tamaño de qwen3:8b descargado (Q4_K_M)", "Ollama /api/tags"),
  "llm_parametros": item(llm["details"].get("parameter_size", "?"), "Parámetros de qwen3:8b", "Ollama /api/tags"),
  "llm_cuantizacion": item(llm["details"].get("quantization_level", "?"), "Cuantización de qwen3:8b en Ollama", "Ollama /api/tags"),
}
for m, name in (("gpu", "GPU integrada (Vulkan)"), ("cpu", "solo CPU")):
    r = llm[m]
    d[f"llm_{m}_memoria"] = item(f"{r.get('size_gb', 0):.1f} GB", f"Memoria que ocupa qwen3:8b cargado, {name}", "Ollama /api/ps")
    d[f"llm_{m}_carga"] = item(f"{r['load_s']:.1f} s", f"Cargar qwen3:8b en memoria, {name}", how_llm)
    d[f"llm_{m}_reporte"] = item(f"{r['warm_total_s']:.1f} s", f"Escribir un reporte (modelo ya cargado), {name}", how_llm)
    d[f"llm_{m}_frio"] = item(f"{r['cold_total_s']:.1f} s", f"Primer reporte con el modelo sin cargar, {name}", how_llm)
    d[f"llm_{m}_velocidad"] = item(f"{r['tok_s']:.1f} tokens/s", f"Velocidad al escribir, {name}", how_llm)
d["llm_gpu_en_vram"] = item(f"{llm['gpu'].get('vram_gb', 0):.1f} GB", "Parte de qwen3:8b que Ollama pone en la GPU integrada", "Ollama /api/ps")
d["clasificador_ms"] = item(f"{llm['classifier']['median_ms']:.0f} ms", "Clasificar una nota (llamada al servicio de voz, mediana de 20)", "measure_models.py")
d["clasificador_parametros"] = item(f"{voice['keras_params']:,}", "Parámetros del clasificador de Keras", "keras count_params()")
d["clasificador_archivo"] = item(f"{voice['keras_mb']:.1f} MB", "Tamaño del archivo del clasificador (.keras)", "voice/models/triage_classifier.keras")
d["whisper_archivo"] = item(f"{voice['whisper_cache_mb']:.0f} MB", "Tamaño de Whisper small (int8) descargado", "du en la caché del contenedor voice")
import yaml
header = ("# Mediciones de los tres modelos de Enlaza Voz en la laptop del equipo. GENERADO por "
          "docs/biblia/build/measure_models.sh; no editar a mano. collect_numbers.py las carga como mod.<clave>.\n")
open(sys.argv[4], "w", encoding="utf-8").write(header + yaml.safe_dump(d, allow_unicode=True, sort_keys=False, width=200))
print(open(sys.argv[4], encoding="utf-8").read())
EOF
