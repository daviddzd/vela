"""WCAG 2.x contrast of every text/background pair the Enlaza palette uses (docs/brand.md). Exits 1 if any fails.

    python3 scripts/check_contrast.py

AA: 4.5:1 for normal text, 3:1 for large text (>= 24 px, or >= 18.7 px bold) and for icons / UI boundaries.
"""
import sys

PALETTE = {
    "teal":      "#2AAEAE",   # logo teal (eyedropper): accents, icons, decorations - NOT text on white
    "teal-text": "#137273",   # darker teal for the highlighted word in titles and teal text
    "navy":      "#3A5B76",   # logo navy (eyedropper): titles, primary buttons
    "navy-dark": "#2C465C",   # hover of primary buttons
    "deep":      "#1B3349",   # deep blue for section backgrounds (white text on it)
    "sky":       "#EAF4F8",   # very light blue: gradients behind section headers
    "sky-soft":  "#F4F9FB",   # the light end of the gradient
    "white":     "#FFFFFF",
    "ink":       "#1B2B38",   # body text
    "muted":     "#4F5F6B",   # secondary text
    "ok":        "#1D7447",
    "warn":      "#8A5A00",
    "danger":    "#B42318",
    "ok-soft":   "#E7F4EC", "warn-soft": "#FBF1DC", "danger-soft": "#FBE9E7", "teal-soft": "#E3F5F5",
}

# (foreground, background, minimum, what)
PAIRS = [
    ("ink", "white", 4.5, "body text"), ("ink", "sky", 4.5, "body text on section header"),
    ("muted", "white", 4.5, "secondary text"), ("muted", "sky", 4.5, "secondary text on section header"),
    ("navy", "white", 4.5, "titles, links"), ("navy", "sky", 4.5, "titles on section header"),
    ("teal-text", "white", 4.5, "highlighted word / teal text"), ("teal-text", "sky", 4.5, "highlighted word on header"),
    ("teal-text", "teal-soft", 4.5, "icon circle label"),
    ("white", "navy", 4.5, "primary button"), ("white", "navy-dark", 4.5, "primary button hover"),
    ("white", "deep", 4.5, "text on deep section"), ("sky", "deep", 4.5, "light text on deep section"),
    ("teal", "deep", 3.0, "teal figures/icons on deep section"),
    ("ok", "white", 4.5, "status ok"), ("warn", "white", 4.5, "status warn"), ("danger", "white", 4.5, "status danger"),
    ("ok", "ok-soft", 4.5, "status ok badge"), ("warn", "warn-soft", 4.5, "status warn badge"),
    ("danger", "danger-soft", 4.5, "status danger badge"), ("white", "danger", 4.5, "911 button"),
    ("ink", "warn-soft", 4.5, "amber notice text"),
    ("teal-text", "white", 3.0, "icons that carry meaning / focus ring on white (non-text)"),
    ("navy", "teal-soft", 3.0, "icon in teal circle"),
]


def lum(hex_: str) -> float:
    c = [int(hex_[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def ratio(a: str, b: str) -> float:
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


if __name__ == "__main__":
    bad = 0
    for fg, bg, need, what in PAIRS:
        r = ratio(PALETTE[fg], PALETTE[bg])
        ok = r >= need
        bad += not ok
        print(f"{'OK   ' if ok else 'FALLA'} {r:5.2f} (mín. {need}) {fg:10} sobre {bg:11} — {what}")
    print(f"teal del logo sobre blanco: {ratio(PALETTE['teal'], '#FFFFFF'):.2f} (< 3): solo decorativo (logo, degradados, fondos de círculos); nunca texto, íconos con significado ni foco")
    sys.exit(1 if bad else 0)
