#!/usr/bin/env bash
# Build "La biblia de Enlaza" (docs/biblia/biblia_enlaza.pdf) inside Docker. Needs `docker compose up -d` running.
#
#   bash scripts/build_biblia.sh              # numbers + PDF (takes the screenshots only if there are none yet)
#   bash scripts/build_biblia.sh --capturas   # also: reset_demo.py, new screenshots of every screen, reset again
#
# Steps: collect_numbers.py (repo + database) -> build.py (Markdown -> HTML) -> render.cjs (HTML -> PDF).
# The PDF, the HTML and the screenshots are git-ignored: anyone can regenerate them from the repository.
set -euo pipefail
cd "$(dirname "$0")/.."

IMAGE=vela-biblia
NET=vela_default
RUN=(docker run --rm --init --ipc=host --user "$(id -u):$(id -g)" --network "$NET" --env-file .env -v "$PWD:/repo" -w /repo "$IMAGE")

echo "== Imagen de la biblia"
docker build -q -t "$IMAGE" docs/biblia/build >/dev/null

if [[ "${1:-}" == "--capturas" ]] || [[ -z "$(ls -A docs/biblia/capturas 2>/dev/null | grep -v '^\.gitkeep$' || true)" ]]; then
  echo "== Capturas: primero se limpia la operación (reset_demo.py)"
  python3 scripts/reset_demo.py
  mkdir -p docs/biblia/capturas
  "${RUN[@]}" xvfb-run -a node docs/biblia/build/capture.cjs
  echo "== Se vuelve a limpiar lo que crearon las capturas"
  python3 scripts/reset_demo.py
fi

echo "== Números (repositorio y base de datos)"
"${RUN[@]}" python3 docs/biblia/build/collect_numbers.py
echo "== Markdown → HTML"
"${RUN[@]}" python3 docs/biblia/build/build.py
echo "== HTML → PDF"
"${RUN[@]}" node docs/biblia/build/render.cjs
