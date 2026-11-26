"""Brand fonts as installable TTF files, from the @fontsource npm packages (SIL Open Font License).

    python3 make_fonts.py <node_modules/@fontsource> <out_dir>

Each @fontsource weight comes split by alphabet (latin, latin-ext…). The latin and latin-ext WOFF files are merged
into one TTF per weight, and the name table is set so Windows/PowerPoint group them as one family with Regular and
Bold: "Plus Jakarta Sans" and "Atkinson Hyperlegible".
"""
import sys
from pathlib import Path

from fontTools.merge import Merger
from fontTools.ttLib import TTFont

FAMILIES = {"plus-jakarta-sans": "Plus Jakarta Sans", "atkinson-hyperlegible": "Atkinson Hyperlegible"}
WEIGHTS = {400: "Regular", 700: "Bold"}


def main() -> None:
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    tmp = out / "_tmp"
    tmp.mkdir(exist_ok=True)
    for pkg, family in FAMILIES.items():
        for weight, style in WEIGHTS.items():
            parts = []
            for subset in ("latin", "latin-ext"):
                woff = src / pkg / "files" / f"{pkg}-{subset}-{weight}-normal.woff"
                f = TTFont(woff)
                f.flavor = None
                p = tmp / f"{subset}.ttf"
                f.save(p)
                parts.append(str(p))
            font = Merger().merge(parts)
            ps = f"{family.replace(' ', '')}-{style}"
            names = {1: family, 2: style, 4: f"{family} {style}" if style != "Regular" else family, 6: ps,
                     16: family, 17: style, 3: f"{ps};enlaza"}
            name = font["name"]
            for nid, text in names.items():
                name.setName(text, nid, 3, 1, 0x409)
                name.setName(text, nid, 1, 0, 0)
            font["OS/2"].usWeightClass = weight
            font["OS/2"].fsSelection = (font["OS/2"].fsSelection & ~0b1100001) | (0b100000 if weight == 700 else 0b1000000)
            font["head"].macStyle = 1 if weight == 700 else 0
            font.save(out / f"{ps}.ttf")
            print(out / f"{ps}.ttf")
    for p in tmp.iterdir():
        p.unlink()
    tmp.rmdir()


if __name__ == "__main__":
    main()
