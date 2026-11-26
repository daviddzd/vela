# Image that builds the colloquium deck (docs/presentacion/). Based on the image of "La biblia de Enlaza"
# (docs/biblia/build/Dockerfile: Chromium, Python, numbers), plus:
#   - pptxgenjs: writes the .pptx with editable text, native charts and speaker notes
#   - LibreOffice Impress: .pptx -> .pdf (and slide images for the visual check)
#   - librsvg: logo and icon SVG -> PNG (icons: lucide-static, ISC license)
#   - fonttools: brand fonts (Plus Jakarta Sans, Atkinson Hyperlegible, SIL OFL) from the npm packages as TTF,
#     installed here so LibreOffice renders the real fonts, and copied to docs/presentacion/fuentes for PowerPoint
FROM vela-biblia

USER root
RUN apt-get update \
 && apt-get install -y --no-install-recommends libreoffice-impress librsvg2-bin python3-fonttools python3-brotli \
      python3-lxml python3-defusedxml python3-pil python3-pip fontconfig \
 && pip3 install --no-cache-dir --break-system-packages python-pptx==1.0.2 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/biblia
RUN npm install --silent --no-audit --no-fund pptxgenjs@3.12.0 lucide-static@0.460.0

# Brand fonts as TTF (latin + latin-ext subsets merged so «→», «≥» and accents are all there)
COPY make_fonts.py /opt/make_fonts.py
RUN python3 /opt/make_fonts.py /opt/biblia/node_modules/@fontsource /usr/local/share/fonts/enlaza && fc-cache -f >/dev/null
ENV NODE_PATH=/opt/biblia/node_modules HOME=/tmp
