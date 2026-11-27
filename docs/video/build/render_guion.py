"""guion_fuente.md -> guion_narracion.md (numbers filled in) + out/escenas.json (one entry per scene, for the build).

- {{ clave }} takes the text from docs/biblia/out/numeros.json, the same numbers as the book and the colloquium deck.
  An unknown key stops the build (no number is ever typed by hand).
- Prints the words and the estimated length of each part (the voice reads about WPM words per minute), so the team can
  check that video 1 lands in 18-22 min and video 2 in about 4 min before anything is recorded.

Run from the repository root:  python3 docs/video/build/render_guion.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
VIDEO = ROOT / "docs/video"
NUM = json.loads((ROOT / "docs/biblia/out/numeros.json").read_text(encoding="utf-8"))
WPM = 140  # measured with Piper es_MX-claude-high, length_scale 1.12 (see build/voz.py)

# Derived keys: the same figure, worded for a sentence. Each one asserts the shape of its source so it cannot drift.
assert NUM["bm.ltv_cac"]["text"].endswith(" : 1"), NUM["bm.ltv_cac"]["text"]
NUM["bm.ltv_cac_veces"] = {"text": NUM["bm.ltv_cac"]["text"].removesuffix(" : 1")}   # "21.9 : 1" -> "21.9"


def fill(text: str) -> str:
    """Replace every {{ key }} with its text from numeros.json; stop on an unknown key."""
    def rep(m: re.Match) -> str:
        key = m.group(1)
        if key not in NUM:
            sys.exit(f"ERROR: guion_fuente.md: número desconocido {{{{ {key} }}}}")
        return NUM[key]["text"]
    return re.sub(r"\{\{\s*([\w.\-]+)\s*\}\}", rep, text)


def scenes(md: str) -> list[dict]:
    """Split the filled script into scenes: video, part, id, title, what is shown and what is said."""
    out: list[dict] = []
    video = part = None
    cur = None
    mode = None
    for line in md.splitlines():
        if m := re.match(r"^# Video (\d)", line):
            video, part, cur = int(m.group(1)), None, None
        elif m := re.match(r"^## (.+)", line):
            part, cur = m.group(1).strip(), None
        elif m := re.match(r"^### Escena ([\w.]+) · (.+)", line):
            cur = {"video": video, "part": part or "", "id": m.group(1), "title": m.group(2).strip(), "shown": "", "said": ""}
            out.append(cur)
            mode = None
        elif cur is not None:
            if line.startswith("**Se ve:**"):
                cur["shown"], mode = line.removeprefix("**Se ve:**").strip(), "shown"
            elif line.startswith("**Dice:**"):
                mode = "said"
            elif line.strip() and mode == "said":
                cur["said"] = (cur["said"] + " " + line.strip()).strip()
    return out


def main() -> None:
    src = (VIDEO / "guion_fuente.md").read_text(encoding="utf-8")
    md = fill(src)
    header = ("<!-- GENERADO por docs/video/build/render_guion.py desde guion_fuente.md. "
              "No editar aquí: editar guion_fuente.md. -->\n")
    (VIDEO / "guion_narracion.md").write_text(header + md, encoding="utf-8")
    sc = scenes(md)
    (VIDEO / "out").mkdir(exist_ok=True)
    (VIDEO / "out/escenas.json").write_text(json.dumps(sc, ensure_ascii=False, indent=1), encoding="utf-8")

    for v in (1, 2):
        total = 0
        print(f"== Video {v}")
        parts: dict[str, int] = {}
        for s in sc:
            if s["video"] == v:
                parts[s["part"]] = parts.get(s["part"], 0) + len(s["said"].split())
        for p, w in parts.items():
            total += w
            print(f"  {w:5d} palabras ≈ {w / WPM:4.1f} min  {p or '(sin parte)'}")
        print(f"  {total:5d} palabras ≈ {total / WPM:4.1f} min de narración")


if __name__ == "__main__":
    main()
