"""diapositivas.yaml -> one HTML page per slide (docs/video/out/diapositivas/<id>.html), brand identity of Enlaza.

The numbers are filled exactly like the narration script (render_guion.fill: numeros.json, unknown key = stop).
diapositivas.cjs then takes a 1920x1080 PNG of each page into docs/privado/video/diapositivas/ (git-ignored).
Brand tokens: docs/brand.md (navy, deep, teal-text, sky, ink, muted, warn, danger; Plus Jakarta Sans for titles,
Atkinson Hyperlegible for text). Run inside the vela-video image:  python3 docs/video/build/diapositivas.py
"""
from __future__ import annotations

import html
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from render_guion import fill  # noqa: E402

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / "docs/video/out/diapositivas"
FONTS = ROOT / "docs/presentacion/fuentes"
PUBLIC = ROOT / "frontend/public"

CSS = f"""
@font-face {{ font-family: Jakarta; src: url('file://{FONTS}/PlusJakartaSans-Bold.ttf'); font-weight: 700; }}
@font-face {{ font-family: Atkinson; src: url('file://{FONTS}/AtkinsonHyperlegible-Regular.ttf'); font-weight: 400; }}
@font-face {{ font-family: Atkinson; src: url('file://{FONTS}/AtkinsonHyperlegible-Bold.ttf'); font-weight: 700; }}
* {{ box-sizing: border-box; margin: 0; }}
body {{ width: 1920px; height: 1080px; font-family: Atkinson; color: #1B2B38; font-size: 38px; line-height: 1.35;
       background: linear-gradient(180deg, #EAF4F8 0, #F4F9FB 260px, #fff 520px); padding: 72px 96px; position: relative; }}
.logo {{ position: absolute; top: 56px; right: 96px; height: 64px; }}
h1 {{ font-family: Jakarta; font-size: 72px; line-height: 1.1; color: #3A5B76; margin-bottom: 40px; max-width: 1450px; }}
.foot {{ position: absolute; left: 96px; bottom: 44px; font-size: 26px; color: #4F5F6B; }}
.card {{ background: #fff; border: 3px solid rgba(58,91,118,.15); border-radius: 28px; padding: 30px 36px; }}
.num {{ font-family: Jakarta; font-size: 68px; color: #137273; line-height: 1.05; }}
.lbl {{ font-weight: 700; color: #3A5B76; }}
.grid {{ display: grid; gap: 28px; }}
.note {{ margin-top: 36px; font-size: 32px; color: #4F5F6B; }}
.frase {{ font-size: 46px; font-weight: 700; color: #1B3349; margin-bottom: 40px; max-width: 1600px; }}
.row {{ display: flex; align-items: stretch; gap: 18px; }}
.step {{ flex: 1; font-size: 32px; }}
.arrow {{ align-self: center; font-family: Jakarta; font-size: 56px; color: #137273; }}
.warn {{ border: 4px solid #8A5A00; background: #FFF8EB; border-radius: 24px; padding: 24px 32px; font-size: 34px; }}
.danger {{ border: 4px solid #B42318; background: #FDF0EF; border-radius: 24px; padding: 24px 32px; }}
.deep {{ background: #1B3349; color: #fff; }}
.deep h1 {{ color: #fff; font-size: 104px; }}
"""


def esc(s: str) -> str:
    return html.escape(fill(str(s)))


def cards(items, cols: int, cls: str = "") -> str:
    out = "".join(f'<div class="card {cls}"><div class="num">{esc(a)}</div><div>{esc(b)}</div></div>' for a, b in items)
    return f'<div class="grid" style="grid-template-columns: repeat({cols}, 1fr)">{out}</div>'


def steps(items) -> str:
    parts = [f'<div class="card step"><div class="lbl" style="font-size:38px">{esc(a)}</div><div>{esc(b)}</div></div>'
             for a, b in items]
    return '<div class="row">' + '<div class="arrow">→</div>'.join(parts) + "</div>"


def body(s: dict) -> str:
    t = s["tipo"]
    if t in ("portada", "cierre"):
        return (f'<img src="file://{PUBLIC}/logo-white.svg" style="height:150px;margin:120px 0 70px">'
                f'<h1>{esc(s["titulo"])}</h1><div style="font-size:52px;font-weight:700">{esc(s["subtitulo"])}</div>')
    if t == "problema":
        rows = "".join(f'<div class="card"><span class="lbl">{esc(a)}</span> · {esc(b)}</div>' for a, b in s["puntos"])
        return (f'<div class="grid" style="grid-template-columns: 620px 1fr; align-items:start">'
                f'<div class="card"><div class="num" style="font-size:96px">{esc(s["cifra"])}</div>'
                f'<div>{esc(s["cifra_texto"])}</div><div class="note" style="margin-top:20px">Fuente: {esc(s["fuente"])}</div></div>'
                f'<div class="grid">{rows}</div></div>')
    if t == "solucion":
        items = "".join(f'<div class="card" style="font-size:33px"><div class="lbl" style="font-size:40px">{esc(a)}</div>{esc(b)}</div>'
                        for a, b in s["puntos"])
        return (f'<div class="frase">{esc(s["frase"])}</div>'
                f'<div class="grid" style="grid-template-columns: repeat(3, 1fr)">{items}</div>')
    if t in ("flujo", "enlace"):
        return steps(s["pasos"])
    if t == "analogia":
        rows = "".join(f'<div class="card" style="padding:16px 32px;font-size:36px"><span class="lbl">{esc(a)}</span>'
                       f' <span style="color:#137273;font-weight:700">→</span> {esc(b)}</div>' for a, b in s["filas"])
        return f'<div class="grid" style="grid-template-columns: 1fr 1fr; gap: 20px">{rows}</div>'
    if t == "edificio":
        return f'<div class="frase">{esc(s["frase"])}</div>' + cards(s["cifras"], 3)
    if t == "modelos":
        models = steps([(f"{a}", f"{b} · {c}") for a, b, c in s["modelos"]])
        lv = s["niveles"]
        levels = (f'<div class="grid" style="grid-template-columns:1fr 1fr;margin-top:40px">'
                  f'<div class="danger"><span class="lbl" style="color:#B42318">■ {esc(lv[0][0])}</span> → {esc(lv[0][1])}</div>'
                  f'<div class="warn"><span class="lbl" style="color:#8A5A00">▲ {esc(lv[1][0])}</span> → {esc(lv[1][1])}</div></div>')
        return models + levels
    if t == "materia":
        return (f'<div style="font-size:36px;margin-bottom:34px"><span class="lbl">Qué hicimos.</span> {esc(s["hicimos"])}</div>'
                + cards(s["cifras"], 2) +
                f'<div class="warn" style="margin-top:34px"><span class="lbl" style="color:#8A5A00">▲ Limitación honesta.</span> '
                f'{esc(s["limite"])}</div>')
    if t == "numeros":
        return cards(s["cifras"], 3)
    raise SystemExit(f"ERROR: tipo de diapositiva desconocido: {t}")


def page(sid: str, s: dict) -> str:
    deep = s["tipo"] in ("portada", "cierre")
    logo = "" if deep else f'<img class="logo" src="file://{PUBLIC}/logo.svg">'
    title = "" if deep else f"<h1>{esc(s['titulo'])}</h1>"
    note = f'<div class="note">{esc(s["nota"])}</div>' if s.get("nota") and not deep else ""
    foot = esc(s["nota"]) if deep and s.get("nota") else "Enlaza · cuidado coordinado — Prototipo académico · datos sintéticos"
    return (f'<!doctype html><html lang="es-MX"><head><meta charset="utf-8"><style>{CSS}</style></head>'
            f'<body class="{"deep" if deep else ""}">{logo}{title}{body(s)}{note}'
            f'<div class="foot" style="{"color:#fff" if deep else ""}">{foot}</div></body></html>')


def main() -> None:
    slides = yaml.safe_load((ROOT / "docs/video/diapositivas.yaml").read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    for sid, s in slides.items():
        (OUT / f"{sid}.html").write_text(page(sid, s), encoding="utf-8")
    print(f"{len(slides)} diapositivas en {OUT}")


if __name__ == "__main__":
    main()
