"""Enlaza logo, drawn from geometric shapes (no auto-trace) on a 2048-unit grid, from the measurements of
assets/brand/source/logo_enlaza.jpg (2048 px): a symmetric cross outline (1229 wide, arms 492, corner radius 115,
stroke 82), a heart outline with a check mark inside, all at 45°. Upper-left of the diagonal x + y = C is teal, the
rest navy, as in the original. White "gaps" under the heart and the check make them look interlaced.

    python3 assets/brand/scripts/make_logo.py        # writes assets/brand/*.svg and frontend/public/*.svg
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TEAL, NAVY = "#2AAEAE", "#3A5B76"        # eyedropper medians of the original (scripts output, docs/brand.md)
W = 82                                    # stroke width
CX = CY = 1024
# colour boundary: teal above-left of x + y = 2110; the diagonal ribbon (check mark's long arm) is ALL teal,
# as in the original, and is drawn on top of both halves
B0 = B1 = None
SPLIT = 2110

# cross outline: centre line of the stroke (outer edge minus W/2)
L, A, R = 614.5 - W / 2, 246 - W / 2, 115 - W / 2      # half-length, half-arm, corner radius of the centre line


def cross_path() -> str:
    """Plus-shaped outline with rounded outer corners (centre line), clockwise from the top-left of the top arm."""
    l, a, r = L, A, R
    pts = [(-a, -l), (a, -l), (a, -a), (l, -a), (l, a), (a, a), (a, l), (-a, l), (-a, a), (-l, a), (-l, -a), (-a, -a)]
    outer = {0, 1, 3, 4, 6, 7, 9, 10}                   # the 8 arm-end corners are rounded; the 4 inner ones square
    d = []
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        px, py = pts[i - 1]
        nx, ny = pts[(i + 1) % n]
        if i in outer:
            # come in r before the corner, arc to r after it
            ix, iy = x + (px - x) / max(abs(px - x), abs(py - y)) * r, y + (py - y) / max(abs(px - x), abs(py - y)) * r
            ox, oy = x + (nx - x) / max(abs(nx - x), abs(ny - y)) * r, y + (ny - y) / max(abs(nx - x), abs(ny - y)) * r
            d.append(f"{'M' if i == 0 else 'L'}{CX + ix:.1f},{CY + iy:.1f} Q{CX + x:.1f},{CY + y:.1f} {CX + ox:.1f},{CY + oy:.1f}")
        else:
            d.append(f"L{CX + x:.1f},{CY + y:.1f}")
    return " ".join(d) + " Z"


# heart: two semicircles (centre line radius HR) whose diameters lie at 45°, two 45° sides meeting at the tip
# measured: left side on x - y = -325, right side on x + y = 2371, outer left edge 666 (centre line 707)
HR = 317 / (1 + 2 ** -0.5)                               # lobe radius: S + HR = 1024 - 707
S = HR / 2 ** 0.5
P = (CX - 2 * S, CX - 2 * S + 325)                       # left side point, on x - y = -325
LC = (P[0] + S, P[1] - S)                                # left lobe centre
Q = (CX, P[1] - 2 * S)                                   # notch
TIP = (CX, P[1] + (CX - P[0]))                           # 45° down to the middle
P2 = (2 * CX - P[0], P[1])
TIP_ROUND = 45


def heart_path() -> str:
    k = TIP_ROUND                                        # the tip is rounded, as in the original
    return (f"M{TIP[0] - k:.1f},{TIP[1] - k:.1f} L{P[0]:.1f},{P[1]:.1f} A{HR:.1f},{HR:.1f} 0 0 1 {Q[0]:.1f},{Q[1]:.1f} "
            f"A{HR:.1f},{HR:.1f} 0 0 1 {P2[0]:.1f},{P2[1]:.1f} L{TIP[0] + k:.1f},{TIP[1] - k:.1f} "
            f"Q{TIP[0]:.1f},{TIP[1]:.1f} {TIP[0] - k:.1f},{TIP[1] - k:.1f} Z")


# check mark: short arm from inside the left lobe down to the vertex, long arm up along x + y = 2045 to the
# top-right of the cross and down-left to the bottom of the left arm (the ribbon that "ties" heart and cross)
DIAG = 2045
V = ((DIAG - 18) / 2, (DIAG + 18) / 2)                   # vertex: short arm x - y = -18 meets x + y = DIAG
SHORT0 = (812, 830)
LONG0, LONG1 = (1230, DIAG - 1230), (805, DIAG - 805)


def symbol_body(teal: str = TEAL, navy: str = NAVY, uid: str = "e") -> str:
    """The symbol in 2048 units. The interlacing gaps are MASKS (not white strokes), so the same drawing works on
    any background (white version on dark sections)."""
    gap = W + 34
    heart, short = heart_path(), f"M{SHORT0[0]},{SHORT0[1]} L{V[0]:.1f},{V[1]:.1f}"
    ribbon = f"M{LONG0[0]},{LONG0[1]} L{LONG1[0]},{LONG1[1]}"
    shapes = (f'<g mask="url(#{uid}r)"><path d="{cross_path()}" mask="url(#{uid}h)"/><path d="{heart}"/><path d="{short}"/></g>')
    return f"""<defs>
    <clipPath id="{uid}t"><polygon points="0,0 {SPLIT},0 0,{SPLIT}"/></clipPath>
    <clipPath id="{uid}n"><polygon points="{SPLIT},0 2048,0 2048,2048 0,2048 0,{SPLIT}"/></clipPath>
    <mask id="{uid}h" maskUnits="userSpaceOnUse" x="0" y="0" width="2048" height="2048"><rect width="2048" height="2048" fill="#fff"/>
      <path d="{heart}" fill="none" stroke="#000" stroke-width="{gap}" stroke-linejoin="round"/></mask>
    <mask id="{uid}r" maskUnits="userSpaceOnUse" x="0" y="0" width="2048" height="2048"><rect width="2048" height="2048" fill="#fff"/>
      <path d="{ribbon}" fill="none" stroke="#000" stroke-width="{gap}"/></mask>
  </defs>
  <g fill="none" stroke-width="{W}" stroke-linecap="round" stroke-linejoin="round">
    <g clip-path="url(#{uid}t)" stroke="{teal}">{shapes}</g>
    <g clip-path="url(#{uid}n)" stroke="{navy}">{shapes}</g>
    <path d="{ribbon}" stroke="{teal}"/>
  </g>"""


SYMBOL_BOX = (400, 400, 1248, 1248)                    # the symbol spans 409..1638


def text_path(text: str, font_file: Path, size: float, x: float, baseline: float) -> tuple[str, float]:
    """Outline of `text` in the font (fontTools), `size` units high per em, starting at x; returns (path d, width)."""
    from fontTools.pens.svgPathPen import SVGPathPen
    from fontTools.pens.transformPen import TransformPen
    from fontTools.ttLib import TTFont
    font = TTFont(font_file)
    cmap, glyphs, hmtx = font.getBestCmap(), font.getGlyphSet(), font["hmtx"]
    scale = size / font["head"].unitsPerEm
    pen = SVGPathPen(glyphs)
    cursor = 0.0
    for ch in text:
        name = cmap[ord(ch)]
        glyphs[name].draw(TransformPen(pen, (scale, 0, 0, -scale, x + cursor, baseline)))
        cursor += hmtx[name][0] * scale
    return pen.getCommands(), cursor


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    print("  ", path.relative_to(ROOT))


if __name__ == "__main__":
    fonts = ROOT / "frontend" / "node_modules" / "@fontsource" / "plus-jakarta-sans" / "files"
    bold, semi = fonts / "plus-jakarta-sans-latin-800-normal.woff", fonts / "plus-jakarta-sans-latin-600-normal.woff"
    brand, public = ROOT / "assets" / "brand", ROOT / "frontend" / "public"
    x0, y0, w, h = SYMBOL_BOX
    TEAL_TEXT = "#137273"                               # AA on white (scripts/check_contrast.py)
    for name, teal, navy, word, tag in [("", TEAL, NAVY, NAVY, TEAL_TEXT), ("-blanco", "#FFFFFF", "#FFFFFF", "#FFFFFF", "#FFFFFF")]:
        mark = symbol_body(teal, navy, uid="s" + name.strip("-"))
        sym = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {w} {h}" role="img" aria-label="Enlaza">'
               f'<title>Enlaza</title>{mark}</svg>\n')
        write(brand / f"enlaza-simbolo{name}.svg", sym)
        # full logo: symbol, then "Enlaza" (Plus Jakarta Sans 800) and "cuidado coordinado" (600) to its right
        gap = 160
        d1, w1 = text_path("Enlaza", bold, 760, x0 + w + gap, y0 + 700)
        d2, w2 = text_path("cuidado coordinado", semi, 330, x0 + w + gap + 8, y0 + 1110)
        total = w + gap + max(w1, w2 + 8) + 40
        logo = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {total:.0f} {h}" role="img" '
                f'aria-label="Enlaza · cuidado coordinado"><title>Enlaza · cuidado coordinado</title>{symbol_body(teal, navy, uid="l" + name.strip("-"))}'
                f'<path d="{d1}" fill="{word}"/><path d="{d2}" fill="{tag}"/></svg>\n')
        write(brand / f"enlaza-logo{name}.svg", logo)
    write(public / "logo.svg", (brand / "enlaza-logo.svg").read_text())
    write(public / "logo-white.svg", (brand / "enlaza-logo-blanco.svg").read_text())
    write(public / "logo-mark.svg", (brand / "enlaza-simbolo.svg").read_text())
    # favicon: the symbol on a white rounded square (readable on dark browser tabs too)
    fav = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="300 300 1448 1448"><rect x="300" y="300" width="1448" height="1448" '
           f'rx="300" fill="#FFFFFF"/>{symbol_body(uid="f")}</svg>\n')
    write(public / "favicon.svg", fav)
    write(brand / "enlaza-favicon.svg", fav)
    (brand / "enlaza-symbol-2048.svg").unlink(missing_ok=True)
