"""Checks of the colloquium deck and script -> docs/presentacion/out/verificacion.md (stops the build on a failure).

1. Every number printed (out/numeros_usados.csv, out/numeros_usados_guion.csv) appears in the text of its PDF.
2. Every text on the slides is 24 pt or more, except the source lines, the chart note and the slide number (14 pt).
3. Every character on the slides exists in the brand fonts (so nothing falls back to another font).
4. Every slide has speaker notes, and nothing on a slide goes past the edge of the slide.
"""
import csv
import os
import re
import subprocess
import sys
from pathlib import Path

from fontTools.ttLib import TTFont
from pptx import Presentation
from pptx.util import Emu

PRES = Path(__file__).resolve().parents[1]
OUT = PRES / "out"
SMALL_OK = ("Fuente", "Nota de la gráfica")
FONTS = Path("/usr/local/share/fonts/enlaza")


def pdf_text(pdf: Path) -> str:
    t = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout
    return re.sub(r"\s+", " ", t)


def main() -> None:
    # DECK_DIR: check another copy of the deck (the private one with names); the script is checked only in docs/presentacion
    deck_dir = Path(os.environ["DECK_DIR"]).resolve() if os.environ.get("DECK_DIR") else PRES
    problems, report = [], [f"# Verificación de la presentación y el guion ({deck_dir.name})", ""]
    # 1. numbers in the PDFs
    pairs = [("numeros_usados.csv", deck_dir / "enlaza_coloquio.pdf")]
    if deck_dir == PRES:
        pairs.append(("numeros_usados_guion.csv", PRES / "guion_coloquio.pdf"))
    for csv_name, pdf_path in pairs:
        pdf = pdf_path.name
        text = pdf_text(pdf_path)
        rows = list(csv.DictReader(open(OUT / csv_name, encoding="utf-8")))
        drawn = [r for r in rows if r.get("uso") == "gráfica"]      # error bars: drawn, not printed
        rows = [r for r in rows if r.get("uso") != "gráfica"]
        missing = [r for r in rows if re.sub(r"\s+", " ", r["texto"]) not in text]
        report.append(f"- {pdf}: {len(rows)} números impresos de numeros.json; no aparecen en el PDF: **{len(missing)}**"
                      + (f" (más {len(drawn)} dibujados como intervalos de confianza)" if drawn else ""))
        problems += [f"{pdf}: «{r['texto']}» ({r['clave']}) no aparece" for r in missing]
    # 2-4. the slides
    deck = Presentation(deck_dir / "enlaza_coloquio.pptx")
    sw, sh = deck.slide_width, deck.slide_height
    cmaps = {f.stem: set(TTFont(f).getBestCmap()) for f in FONTS.glob("*.ttf")}
    small, glyphs, edges, notes = [], set(), [], 0
    for n, slide in enumerate(deck.slides, 1):
        if slide.has_notes_slide and slide.notes_slide.notes_text_frame.text.strip():
            notes += 1
        else:
            problems.append(f"diapositiva {n}: sin notas del orador")
        for shp in slide.shapes:
            if shp.left is not None and (shp.left < 0 or shp.top < 0 or shp.left + shp.width > sw + Emu(5000)
                                         or shp.top + shp.height > sh + Emu(5000)):
                edges.append(f"diapositiva {n}: «{shp.name}» sale de la diapositiva")
            if not shp.has_text_frame:
                continue
            for p in shp.text_frame.paragraphs:
                for r in p.runs:
                    if not r.text.strip():
                        continue
                    size = r.font.size.pt if r.font.size else None
                    if size is not None and size < 24 and not shp.name.startswith(SMALL_OK):
                        small.append(f"diapositiva {n}: «{r.text[:40]}» a {size:g} pt")
                    face = r.font.name or ""
                    key = "PlusJakartaSans" if "Jakarta" in face else "AtkinsonHyperlegible"
                    style = "Bold" if r.font.bold else "Regular"
                    for ch in r.text:
                        if ord(ch) > 32 and ord(ch) not in cmaps[f"{key}-{style}"]:
                            glyphs.add(f"«{ch}» (U+{ord(ch):04X}) en {key}-{style}, diapositiva {n}")
    problems += small + sorted(glyphs) + edges
    report += [f"- Diapositivas: {len(deck.slides)}; con notas del orador: {notes}",
               f"- Textos de menos de 24 pt (fuera de fuentes, nota de la gráfica y número): **{len(small)}**",
               f"- Caracteres que no existen en las fuentes de la marca: **{len(glyphs)}**",
               f"- Elementos fuera de la diapositiva: **{len(edges)}**", ""]
    if problems:
        report += ["## Problemas", ""] + [f"- {p}" for p in problems]
    if deck_dir == PRES:
        (OUT / "verificacion.md").write_text("\n".join(report) + "\n", encoding="utf-8")
    print("\n".join(report))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
