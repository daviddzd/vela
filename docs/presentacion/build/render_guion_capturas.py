"""guion_capturas_fuente.md -> guion_coloquio_capturas.md + out_capturas/guion.html (for the PDF) + out_capturas/notas.json.

    python3 docs/presentacion/build/render_guion_capturas.py      (after docs/biblia/build/collect_numbers.py)

The script of the version WITHOUT live demo. It reuses fill() and parts() of render_guion.py (the live-demo version,
unchanged) and adds:
- the total must be between 9:30 and 9:45, otherwise the build stops;
- a cumulative stopwatch: every slide gets «Cronómetro: start → end»; {{ crono_dN }} is the time at the end of slide N;
- no slide may ask for more than 2.6 spoken words per second (what is in parentheses is an action and is not counted);
- {{ reparto }} becomes the table of who speaks how long.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import markdown

sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_guion as rg  # noqa: E402  (fill, parts, mmss, secs and the numbers)

PRES = rg.PRES
OUT = PRES / "out_capturas"
MIN_TOTAL, MAX_TOTAL = 9 * 60 + 30, 9 * 60 + 45
MAX_WPS = 2.6


def spoken_words(bullets: list[str]) -> int:
    said = " ".join(re.sub(r"\([^)]*\)", " ", b) for b in bullets)
    return len(re.findall(r"[\wáéíóúñü$%.,−]+", said))


def main() -> None:
    raw = (PRES / "guion_capturas_fuente.md").read_text(encoding="utf-8")
    raw = re.sub(r"<!-- FUENTE.*?-->\n", "", raw, flags=re.S)
    # first pass with the stopwatch placeholders untouched (fill() leaves only {{ reparto }} as is)
    src = rg.fill(re.sub(r"\{\{\s*crono_d(\d+)\s*\}\}", r"@@crono_\1@@", raw))
    slides = [p for p in rg.parts(src) if p["level"] == 3 and p["id"]]
    per_person, total, problems, clock = defaultdict(int), 0, [], {}
    for p in slides:
        start = total
        total += p["secs"]
        clock[p["id"]] = (start, total)
        for who in re.findall(r"Persona \d", p["who"])[:1]:
            per_person[who] += p["secs"]
        if p["secs"]:
            wps = spoken_words(p["bullets"]) / p["secs"]
            if wps > MAX_WPS:
                problems.append(f"{p['title']}: {wps:.1f} palabras por segundo (máximo {MAX_WPS})")
    if not MIN_TOTAL <= total <= MAX_TOTAL:
        problems.append(f"el guion dura {rg.mmss(total)}; debe quedar entre {rg.mmss(MIN_TOTAL)} y {rg.mmss(MAX_TOTAL)}")
    if problems:
        sys.exit("ERROR: " + "; ".join(problems))

    rows = ["| Parte | Diapositivas | Tiempo | Cronómetro al terminar |", "|---|---|---|---|"]
    blocks = [("Problema, solución y cómo funciona", 1, 3), ("La app en capturas: los cuatro pasos", 4, 7),
              ("Las seis materias", 8, 13), ("Gracias y siguiente paso", 14, 14)]
    for name, a, b in blocks:
        ids = [f"d{i}" for i in range(a, b + 1)]
        rows.append(f"| {name} | {a}–{b} | {rg.mmss(sum(p['secs'] for p in slides if p['id'] in ids))} | {rg.mmss(clock[ids[-1]][1])} |")
    rows.append(f"| **Total** | | **{rg.mmss(total)}** (margen: {rg.mmss(600 - total)}) | |")
    rows += ["", "| Persona | Habla en total | Diapositivas |", "|---|---|---|"]
    for who, s in sorted(per_person.items()):
        mine = [p["id"][1:] for p in slides if who in p["who"] and p["secs"]]
        rows.append(f"| {who} | {rg.mmss(s)} | {', '.join(mine)} |")
    md = src.replace("{{ reparto }}", "\n".join(rows))
    md = re.sub(r"@@crono_(\d+)@@", lambda m: rg.mmss(clock[f"d{m.group(1)}"][1]), md)
    # the stopwatch on every «Habla» line
    out_lines, cur = [], None
    for line in md.splitlines():
        h = re.match(r"^### .+\{#(d\d+)\}$", line)
        if h:
            cur = h.group(1)
        if cur and line.startswith("**Habla:**") and clock[cur][1] > clock[cur][0]:
            a, b = clock[cur]
            line += f" · **Cronómetro:** {rg.mmss(a)} → {rg.mmss(b)}"
        out_lines.append(line)
    md = "\n".join(out_lines) + "\n"
    header = ("<!-- GENERADO por docs/presentacion/build/render_guion_capturas.py desde guion_capturas_fuente.md. "
              "No editar aquí: editar guion_capturas_fuente.md y correr scripts/build_presentacion_capturas.sh. -->\n")
    md = re.sub(r" \{#d\d+\}", "", md)
    (PRES / "guion_coloquio_capturas.md").write_text(header + md, encoding="utf-8")

    notes = {}
    for p in slides:
        a, b = clock[p["id"]]
        meta = p["meta"] + (f" · Cronómetro: {rg.mmss(a)} → {rg.mmss(b)}" if b > a else "")
        notes[int(p["id"][1:])] = "\n".join([meta, ""] + [f"• {x}" for x in p["bullets"]]).strip()
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "notas.json").write_text(json.dumps(notes, ensure_ascii=False, indent=1), encoding="utf-8")

    body = markdown.markdown(md, extensions=["tables", "sane_lists"]).replace("[ ]", "☐")
    css = (PRES / "build" / "guion.css").read_text(encoding="utf-8")
    (OUT / "guion.html").write_text("<!doctype html><html lang='es'><head><meta charset='utf-8'><title>Guion del coloquio "
                                    f"con capturas · Enlaza</title><style>{css}</style></head><body>{body}</body></html>",
                                    encoding="utf-8")
    with open(OUT / "numeros_usados_guion.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["clave", "texto", "fuente"])
        for k, t in rg.USED.items():
            w.writerow([k, t, rg.NUM[k]["source"]])
    print(f"Guion con capturas: {rg.mmss(total)} de 10:00 · " + " · ".join(f"{w} {rg.mmss(s)}" for w, s in sorted(per_person.items()))
          + f" · {len(rg.USED)} números")


if __name__ == "__main__":
    main()
