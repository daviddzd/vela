#!/usr/bin/env bash
# Build the colloquium deck WITHOUT live demo (screenshots instead) and its script, inside Docker.
# Needs `docker compose up -d` running. The version with live demo (build_presentacion.sh) is not touched.
#
#   bash scripts/build_presentacion_capturas.sh                  # numbers + crops + deck + script + checks
#   bash scripts/build_presentacion_capturas.sh --capturas       # first: screenshots that do not depend on the hour
#   bash scripts/build_presentacion_capturas.sh --capturas-dia   # first: daytime screenshots (staff on shift in INS-A,
#                                                                #  08:00 to 18:00); waits 11 min after the reset
#
# Screenshots: never while someone records or rehearses with the app (they run reset_demo.py before and after, and the
# daytime ones use the demo panel). The click guard (test_guardia.cjs) runs first.
# Output (docs/presentacion/): enlaza_coloquio_capturas.pptx and .pdf, guion_coloquio_capturas.md and .pdf,
# out_capturas/diapositivas/*.png (one image per slide) and out_capturas/verificacion.md.
# If docs/biblia/equipo.yaml exists (local, git-ignored): also the version with names in docs/privado/coloquio/.
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE=vela-presentacion
NET=vela_default
RUN=(docker run --rm --init --ipc=host --user "$(id -u):$(id -g)" --network "$NET" --env-file .env -v "$PWD:/repo" -w /repo)
P=docs/presentacion
O=$P/out_capturas

echo "== Imágenes de Docker (biblia y presentación)"
docker build -q -t vela-biblia docs/biblia/build >/dev/null
docker build -q -t "$IMAGE" "$P/build" >/dev/null

if [[ "${1:-}" == "--capturas" || "${1:-}" == "--capturas-dia" ]]; then
  echo "== Guardia de clics (911, tel:, contraseña)"
  "${RUN[@]}" "$IMAGE" node "$P/build/test_guardia.cjs"
  echo "== Capturas: primero se limpia la operación (reset_demo.py)"
  python3 scripts/reset_demo.py
  DAY=()
  if [[ "$1" == "--capturas-dia" ]]; then
    DAY=(-e DAY=1)
    echo "   espero 11 min: las visitas del plan de cuidado que el worker vuelve a crear dejan de estar «Nueva»"
    sleep 660
  fi
  "${RUN[@]}" -e CAPTURE_OUT="$P/capturas" "${DAY[@]}" "$IMAGE" xvfb-run -a node "$P/build/capturas.cjs" || {
    python3 scripts/reset_demo.py; exit 1; }
  echo "== Se vuelve a limpiar lo que crearon las capturas"
  python3 scripts/reset_demo.py
fi

echo "== Números (el mismo script de la biblia)"
bash scripts/build_biblia.sh --numeros

echo "== Guion (números, cronómetro y notas del orador)"
"${RUN[@]}" "$IMAGE" python3 "$P/build/render_guion_capturas.py"
echo "== Recortes de las capturas"
"${RUN[@]}" "$IMAGE" python3 "$P/build/recortes.py"
echo "== Presentación"
"${RUN[@]}" "$IMAGE" node "$P/build/deck_capturas.cjs"
"${RUN[@]}" -e ERRBARS_DIR=out_capturas "$IMAGE" python3 "$P/build/errbars.py" "$P/enlaza_coloquio_capturas.pptx"
echo "== PDF de la presentación e imágenes de cada diapositiva"
"${RUN[@]}" "$IMAGE" soffice --headless --convert-to pdf --outdir "$P" "$P/enlaza_coloquio_capturas.pptx" >/dev/null
rm -rf "$O/diapositivas" && mkdir -p "$O/diapositivas"
"${RUN[@]}" "$IMAGE" pdftoppm -png -r 110 "$P/enlaza_coloquio_capturas.pdf" "$O/diapositivas/diapositiva"
echo "== PDF del guion"
"${RUN[@]}" -e HTML_DIR=out_capturas -e PDF_NAME=guion_coloquio_capturas.pdf -e FOOTER="Guion del coloquio con capturas · Enlaza" \
  "$IMAGE" node "$P/build/print_pdf.cjs"
mkdir -p "$P/fuentes"
"${RUN[@]}" "$IMAGE" sh -c "cp /usr/local/share/fonts/enlaza/*.ttf $P/fuentes/"
echo "== Verificación"
CHECK=(-e PDF_TEXT_BOTH=1 -e CHECK_OUT=out_capturas -e DECK_NAME=enlaza_coloquio_capturas -e GUION_PDF=guion_coloquio_capturas.pdf)
"${RUN[@]}" "${CHECK[@]}" "$IMAGE" python3 "$P/build/check.py"

if [[ -f docs/biblia/equipo.yaml ]]; then
  echo "== Versión con nombres (docs/privado/coloquio/, fuera de Git)"
  PRIV=docs/privado/coloquio
  NAMES=$("${RUN[@]}" "$IMAGE" python3 -c "import yaml; d = yaml.safe_load(open('docs/biblia/equipo.yaml')) or {}; print('|'.join(d.get('integrantes') or []))")
  "${RUN[@]}" -e NOMBRES="$NAMES" -e OUTFILE="$PRIV/enlaza_coloquio_capturas.pptx" "$IMAGE" node "$P/build/deck_capturas.cjs"
  "${RUN[@]}" -e ERRBARS_DIR=out_capturas "$IMAGE" python3 "$P/build/errbars.py" "$PRIV/enlaza_coloquio_capturas.pptx"
  "${RUN[@]}" "$IMAGE" soffice --headless --convert-to pdf --outdir "$PRIV" "$PRIV/enlaza_coloquio_capturas.pptx" >/dev/null
  rm -rf "$PRIV/diapositivas_capturas" && mkdir -p "$PRIV/diapositivas_capturas"
  "${RUN[@]}" "$IMAGE" pdftoppm -png -r 110 "$PRIV/enlaza_coloquio_capturas.pdf" "$PRIV/diapositivas_capturas/diapositiva"
  "${RUN[@]}" "${CHECK[@]}" -e DECK_DIR="$PRIV" "$IMAGE" python3 "$P/build/check.py"
fi
