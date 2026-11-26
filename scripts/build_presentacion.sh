#!/usr/bin/env bash
# Build the colloquium deck and its script inside Docker. Needs `docker compose up -d` running.
#
#   bash scripts/build_presentacion.sh              # numbers + deck + script (screenshots only if there are none yet)
#   bash scripts/build_presentacion.sh --capturas   # also: reset_demo.py, new 16:9 screenshots of the demo, reset again
#
# Output (docs/presentacion/): enlaza_coloquio.pptx and .pdf, guion_coloquio.md and .pdf, fuentes/ (brand fonts to
# install on Windows), out/diapositivas/*.png (one image per slide, to check them) and out/verificacion.md.
# The numbers come from the same script as "La biblia de Enlaza" (docs/biblia/build/collect_numbers.py).
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE=vela-presentacion
NET=vela_default
RUN=(docker run --rm --init --ipc=host --user "$(id -u):$(id -g)" --network "$NET" --env-file .env -v "$PWD:/repo" -w /repo)
P=docs/presentacion

echo "== Imágenes de Docker (biblia y presentación)"
docker build -q -t vela-biblia docs/biblia/build >/dev/null
docker build -q -t "$IMAGE" "$P/build" >/dev/null

if [[ "${1:-}" == "--capturas" ]] || [[ -z "$(ls -A "$P/capturas" 2>/dev/null || true)" ]]; then
  echo "== Capturas 16:9: primero se limpia la operación (reset_demo.py)"
  python3 scripts/reset_demo.py
  mkdir -p "$P/capturas"
  "${RUN[@]}" -e CAPTURE_OUT="$P/capturas" -e VIEWPORT=1440x810 -e ONLY=coordinacion_tablero,solicitud,urgente,contingencia,voz \
    "$IMAGE" xvfb-run -a node docs/biblia/build/capture.cjs
  echo "== Se vuelve a limpiar lo que crearon las capturas"
  python3 scripts/reset_demo.py
fi

echo "== Números (el mismo script de la biblia)"
bash scripts/build_biblia.sh --numeros

echo "== Guion (números, tiempos y notas del orador)"
"${RUN[@]}" "$IMAGE" python3 "$P/build/render_guion.py"
echo "== Presentación"
"${RUN[@]}" "$IMAGE" node "$P/build/deck.cjs"
"${RUN[@]}" "$IMAGE" python3 "$P/build/errbars.py"
echo "== PDF de la presentación e imágenes de cada diapositiva"
"${RUN[@]}" "$IMAGE" soffice --headless --convert-to pdf --outdir "$P" "$P/enlaza_coloquio.pptx" >/dev/null
rm -rf "$P/out/diapositivas" && mkdir -p "$P/out/diapositivas"
"${RUN[@]}" "$IMAGE" pdftoppm -png -r 110 "$P/enlaza_coloquio.pdf" "$P/out/diapositivas/diapositiva"
echo "== PDF del guion"
"${RUN[@]}" "$IMAGE" node "$P/build/print_pdf.cjs"
mkdir -p "$P/fuentes"
"${RUN[@]}" "$IMAGE" sh -c "cp /usr/local/share/fonts/enlaza/*.ttf $P/fuentes/"
echo "== Verificación"
"${RUN[@]}" "$IMAGE" python3 "$P/build/check.py"
