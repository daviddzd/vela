#!/usr/bin/env bash
# Build the explainer videos of Enlaza (docs/video/). Needs `docker compose up -d` running and uv on the PATH.
#
#   bash scripts/build_video.sh 2              # video 2 (demo of the colloquium, ~4 min): record + narrate + montage
#   bash scripts/build_video.sh 1              # video 1 (Enlaza explained, ~20 min)
#   bash scripts/build_video.sh 2 --montar     # only narration + montage again, reusing the recordings
#
# Output (git-ignored): docs/privado/video/<name>.mp4 (subtitles burnt in), <name>.srt, <name>_descripcion.txt
# (chapters with their minute). In Git: the narration script (docs/video/guion_fuente.md) and these scripts.
#
# Steps: numbers (same script as the bible) -> guion_narracion.md -> narration with Piper (habla.py refuses any digit,
# symbol or URL in the text the voice reads) -> click-guard test -> reset_demo.py -> recording (grabar.cjs) ->
# reset_demo.py -> montage (montar.py, ffmpeg).
#
# Recording rules (team decision, 26 Nov 2026): record when nobody is using https://enlaza.zenthinks.com (this script
# stops if the audit log shows activity in the last 15 minutes; FORZAR=1 skips that check); reset_demo.py before
# and after; never click a tel: link; the password is only typed into a password field; the voice is typed.
set -euo pipefail
cd "$(dirname "$0")/.."

VIDEO="${1:?Uso: bash scripts/build_video.sh 1|2 [--montar]}"
MODE="${2:-}"
NET=vela_default
RUN=(docker run --rm --init --ipc=host --user "$(id -u):$(id -g)" --network "$NET" -v "$PWD:/repo" -w /repo vela-video)
PIPER=(uv run -q --with piper-tts==1.8.0 --with num2words python3)

echo "== Imágenes (biblia + ffmpeg)"
docker build -q -t vela-biblia docs/biblia/build >/dev/null
docker build -q -t vela-video docs/video/build >/dev/null

echo "== Números y guion de narración"
bash scripts/build_biblia.sh --numeros >/dev/null
python3 docs/video/build/render_guion.py

echo "== Narración (Piper, es_MX-claude-high)"
ids=$(python3 -c "import json;print(','.join(s['id'] for s in json.load(open('docs/video/out/escenas.json')) if s['video']==$VIDEO))")
"${PIPER[@]}" docs/video/build/voz.py --escenas "$ids"

if [[ "$MODE" != "--montar" ]]; then
  echo "== Guardia de llamadas (ningún clic en tel:, 911 ni 800 911 2000)"
  "${RUN[@]}" node docs/video/build/test_guardia.cjs

  echo "== ¿Alguien está usando Enlaza? (bitácora, últimos 15 minutos)"
  busy=$(docker compose exec -T db sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -At -c "SELECT count(*) FROM audit_log WHERE user_id IS NOT NULL AND occurred_at > now() - interval '"'"'15 minutes'"'"'"')
  if [[ "$busy" != "0" && "${FORZAR:-0}" != "1" ]]; then
    echo "Hay $busy acciones de usuarios en los últimos 15 minutos: no se graba (FORZAR=1 si son del propio equipo)."; exit 1
  fi

  echo "== Grabación: primero se limpia la operación (reset_demo.py)"
  python3 scripts/reset_demo.py
  trap 'echo "== Se vuelve a limpiar (reset_demo.py)"; python3 scripts/reset_demo.py' EXIT
  "${RUN[@]}" env VIDEO="$VIDEO" xvfb-run -a node docs/video/build/grabar.cjs
fi

echo "== Montaje (ffmpeg)"
"${RUN[@]}" python3 docs/video/build/montar.py --video "$VIDEO"
