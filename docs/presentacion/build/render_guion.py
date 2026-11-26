"""guion_fuente.md -> guion_coloquio.md (numbers filled in) + out/guion.html (for the PDF) + out/notas.json (speaker notes).

    python3 docs/presentacion/build/render_guion.py      (after docs/biblia/build/collect_numbers.py)

- {{ clave }} takes the text from docs/biblia/out/numeros.json, the same numbers as the book. An unknown key stops the build.
- {{ reparto }} becomes the table of who speaks how long, computed from the «Dura» of every part.
- The total may not exceed 9:40 (10 minutes minus 20 s of margin); otherwise the build stops.
- The notes of slide N are the bullets of the section marked {#dN} (for the demo, those of each step).
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[3]
PRES = ROOT / "docs" / "presentacion"
OUT = PRES / "out"
NUM = json.loads((ROOT / "docs/biblia/out/numeros.json").read_text(encoding="utf-8"))
LIMIT = 9 * 60 + 40
USED: dict[str, str] = {}


def secs(t: str) -> int:
    m, s = t.split(":")
    return int(m) * 60 + int(s)


def mmss(n: int) -> str:
    return f"{n // 60}:{n % 60:02d}"


def fill(text: str) -> str:
    def rep(m):
        key = m.group(1)
        if key == "reparto":
            return m.group(0)
        if key not in NUM:
            sys.exit(f"ERROR: guion_fuente.md: número desconocido {{{{ {key} }}}}")
        USED[key] = NUM[key]["text"]
        return NUM[key]["text"]
    return re.sub(r"\{\{\s*([\w.\-]+)\s*\}\}", rep, text)


def parts(src: str) -> list[dict]:
    """Headings with a «Dura» line: level, title, slide id, speaker, seconds, bullets."""
    out, cur = [], None
    for line in src.splitlines():
        if re.match(r"^#{1,2} ", line):      # a new section (## …) ends the notes of the last slide
            cur = None
            continue
        h = re.match(r"^(#{3,4}) (.+?)(?: \{#(d\d+)\})?$", line)
        if h:
            cur = {"level": len(h.group(1)), "title": h.group(2), "id": h.group(3), "who": "", "secs": 0, "bullets": [],
                   "meta": ""}
            out.append(cur)
            continue
        if cur is None:
            continue
        d = re.search(r"\*\*Dura:\*\* (\d+:\d\d)", line)
        if d:
            cur["secs"] = secs(d.group(1))
            cur["meta"] = re.sub(r"\*\*", "", line).strip()
            w = re.search(r"\*\*Habla:\*\* (.+?) ·", line)
            cur["who"] = w.group(1) if w else ""
        elif line.startswith("- "):
            cur["bullets"].append(line[2:].strip())
    return out


def main() -> None:
    raw = (PRES / "guion_fuente.md").read_text(encoding="utf-8")
    src = fill(re.sub(r"<!-- FUENTE.*?-->\n", "", raw, flags=re.S))
    ps = parts(src)
    slides = [p for p in ps if p["level"] == 3 and p["id"]]
    # time: every slide, except the demo (d4), whose time is the sum of its steps (level 4 under it)
    per_person, total = defaultdict(int), 0
    demo_steps = []
    in_demo = False
    for p in ps:
        if p["level"] == 3:
            in_demo = p["id"] == "d4"
            if not in_demo:
                total += p["secs"]
                for who in re.findall(r"Persona \d", p["who"])[:1]:
                    per_person[who] += p["secs"]
        elif in_demo and p["secs"]:
            demo_steps.append(p)
            total += p["secs"]
            per_person[re.findall(r"Persona \d", p["who"])[0]] += p["secs"]
    demo = next(p for p in slides if p["id"] == "d4")
    if sum(s["secs"] for s in demo_steps) != demo["secs"]:
        sys.exit(f"ERROR: los pasos de la demo suman {mmss(sum(s['secs'] for s in demo_steps))}, la diapositiva 4 dice {mmss(demo['secs'])}")
    if total > LIMIT:
        sys.exit(f"ERROR: el guion dura {mmss(total)}; el máximo es {mmss(LIMIT)} (10:00 con 20 s de margen)")

    rows = ["| Parte | Diapositivas | Tiempo |", "|---|---|---|"]
    blocks = [("Problema y solución", ["d1", "d2", "d3"]), ("Demostración en vivo", ["d4"]),
              ("Simulación, voz, seguridad y ética", ["d5", "d6", "d7"]), ("Negocio, pitch, cierre y gracias", ["d8", "d9", "d10", "d11"])]
    for name, ids in blocks:
        rows.append(f"| {name} | {', '.join(i[1:] for i in ids)} | {mmss(sum(p['secs'] for p in slides if p['id'] in ids))} |")
    rows.append(f"| **Total** | | **{mmss(total)}** (margen: {mmss(600 - total)}) |")
    rows += ["", "| Persona | Habla en total |", "|---|---|"]
    rows += [f"| {who} | {mmss(s)} |" for who, s in sorted(per_person.items())]
    md = src.replace("{{ reparto }}", "\n".join(rows))
    header = ("<!-- GENERADO por docs/presentacion/build/render_guion.py desde guion_fuente.md. "
              "No editar aquí: editar guion_fuente.md y correr scripts/build_presentacion.sh. -->\n")
    md = re.sub(r" \{#d\d+\}", "", md)
    (PRES / "guion_coloquio.md").write_text(header + md, encoding="utf-8")

    # speaker notes per slide
    notes = {}
    for p in slides:
        n = int(p["id"][1:])
        text = [p["meta"], ""] + [f"• {b}" for b in p["bullets"]]
        if p["id"] == "d4":
            text = [p["meta"], ""]
            for s in demo_steps:
                text += [f"{s['title']} — {s['meta']}"] + [f"• {b}" for b in s["bullets"]] + [""]
        notes[n] = "\n".join(text).strip()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "notas.json").write_text(json.dumps(notes, ensure_ascii=False, indent=1), encoding="utf-8")

    body = markdown.markdown(md.split("\n", 1)[1], extensions=["tables", "sane_lists"])
    body = body.replace("[ ]", "☐")
    css = (PRES / "build" / "guion.css").read_text(encoding="utf-8")
    (OUT / "guion.html").write_text(f"<!doctype html><html lang='es'><head><meta charset='utf-8'><title>Guion del coloquio · Enlaza"
                                    f"</title><style>{css}</style></head><body>{body}</body></html>", encoding="utf-8")
    with open(OUT / "numeros_usados_guion.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["clave", "texto", "fuente"])
        for k, t in USED.items():
            w.writerow([k, t, NUM[k]["source"]])
    print(f"Guion: {mmss(total)} de 10:00 · " + " · ".join(f"{w} {mmss(s)}" for w, s in sorted(per_person.items()))
          + f" · {len(USED)} números")


if __name__ == "__main__":
    main()
