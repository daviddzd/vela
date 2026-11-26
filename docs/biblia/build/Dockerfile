# Image that builds "La biblia de Enlaza" (docs/biblia/biblia_enlaza.pdf).
# Based on the same Playwright image used for the UI checks: it already has Chromium.
#   - Python (markdown, yaml, psycopg2): collect_numbers.py and build.py
#   - poppler-utils (pdftoppm, pdftotext): page previews and the final check of numbers in the PDF
#   - Node (playwright, pagedjs, mermaid, fonts): capture.cjs and render.cjs
FROM mcr.microsoft.com/playwright:v1.65.1-noble

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3-markdown python3-yaml python3-psycopg2 poppler-utils \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/biblia
RUN npm init -y >/dev/null \
 && npm install --silent --no-audit --no-fund playwright@1.65.1 pagedjs@0.4.3 mermaid@11.4.1 \
      @fontsource/atkinson-hyperlegible@5 @fontsource/plus-jakarta-sans@5
# render.cjs and capture.cjs use require(), which honours NODE_PATH
ENV NODE_PATH=/opt/biblia/node_modules HOME=/tmp
