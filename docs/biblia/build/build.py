"""Turn the Markdown chapters of "La biblia de Enlaza" into one HTML book (docs/biblia/out/biblia.html).

render.cjs then prints that HTML to PDF with Chromium (Mermaid diagrams + Paged.js for pages).

What a chapter may write (everything else is ordinary Markdown):
  {{ clave }}                  a number collected by collect_numbers.py (unknown key -> the build stops)
  {{ tabla clave1 clave2 ... }} a "Dato | Valor | Fuente" table with those numbers
  {{ paginas cap-a cap-b }}   how many pages from chapter cap-a up to chapter cap-b (counted after the layout, render.cjs)
  {{ equipo.integrantes }}     a value from equipo.yaml (local, git-ignored; names joined "A, B, C y D")
  [[término]] / [[término|texto]]  a glossary term (must exist in glosario.yaml); links to the glossary
  @ref(cap-id)                 a cross reference: "cap. 3 «Arquitectura» (p. 41)"
  ```mermaid ... ```           a diagram, drawn by Mermaid in the browser
  ![Pie de foto](capturas/x.png)  a screenshot; a missing file shows a visible box and a warning
  !!! pregunta "¿...?"         a question with its model answer (also: nota, cuidado, ejemplo)

The order of the book is in contenido.yaml. Run:  python3 docs/biblia/build/build.py
"""
from __future__ import annotations

import html
import json
import re
import shutil
import sys
import unicodedata
from pathlib import Path

import markdown
import yaml

BIBLIA = Path(__file__).resolve().parents[1]
ROOT = BIBLIA.parents[1]
OUT = BIBLIA / "out"
ERRORS: list[str] = []
WARNINGS: list[str] = []


def slug(text: str) -> str:
    """'Seguridad por fila (RLS)' -> 'seguridad-por-fila-rls'."""
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", t).strip("-")


# ----------------------------------------------------------------------------------------------------------------
# Inputs
# ----------------------------------------------------------------------------------------------------------------
NUMBERS: dict = json.loads((OUT / "numeros.json").read_text(encoding="utf-8"))
# equipo.yaml is local (git-ignored: real names); the empty template equipo.example.yaml is versioned
_team_file = BIBLIA / "equipo.yaml" if (BIBLIA / "equipo.yaml").exists() else BIBLIA / "equipo.example.yaml"
TEAM: dict = yaml.safe_load(_team_file.read_text(encoding="utf-8")) or {}
GLOSSARY: list[dict] = yaml.safe_load((BIBLIA / "glosario.yaml").read_text(encoding="utf-8")) or []
CONTENT: dict = yaml.safe_load((BIBLIA / "contenido.yaml").read_text(encoding="utf-8"))

REFERENCES: list[dict] = yaml.safe_load((BIBLIA / "referencias.yaml").read_text(encoding="utf-8")) or []
CITED: list[tuple[str, str]] = []
NOT_CITATIONS = {"Particulares", "UNRC", "Censo", "ENSANUT", "ENASEM", "TomTom", "DOF", "INEGI", "DENUE"}  # name + year, not a citation        # (where, "Autor, año") found in the chapters, checked against REFERENCES

TERMS: dict[str, dict] = {}
for entry in GLOSSARY:
    for name in [entry["termino"], *entry.get("tambien", [])]:
        TERMS[name.lower()] = entry
    entry["id"] = "g-" + slug(entry["termino"])

USED_NUMBERS: dict[str, list[str]] = {}
FIRST_USE: dict[str, str] = {}          # glossary id -> anchor of its first use in the book


# Without equipo.yaml (or with it empty) nothing prints "____": the names fall back to a neutral phrase.
TEAM_FALLBACK = {"integrantes": "los cuatro integrantes del equipo"}


def team_value(path: str) -> str:
    node = TEAM
    for part in path.split("."):
        node = node.get(part) if isinstance(node, dict) else None
    if node in (None, "", []):
        if path in TEAM_FALLBACK:
            return TEAM_FALLBACK[path]
        raise SystemExit(f"ERROR: equipo.{path} está vacío o no existe en equipo.yaml / equipo.example.yaml")
    if isinstance(node, list):                     # "A, B, C y D"
        return ", ".join(node[:-1]) + " y " + node[-1] if len(node) > 1 else node[0]
    return str(node)


# ----------------------------------------------------------------------------------------------------------------
# Chapter processing
# ----------------------------------------------------------------------------------------------------------------
class Chapter:
    def __init__(self, path: Path, label: str, kind: str):
        self.path, self.label, self.kind = path, label, kind
        self.text = path.read_text(encoding="utf-8")
        m = re.search(r"^# (.+?)\s*\{#([a-z0-9-]+)\}\s*$", self.text, re.M)
        if not m:
            raise SystemExit(f"{path}: the first heading must be '# Título {{#cap-id}}'")
        self.title, self.id = m.group(1).strip(), m.group(2)
        self.text = self.text[: m.start()] + self.text[m.end():]
        self.html = ""


def users_table() -> str:
    """Demo accounts from the seed (database/seed/users.csv): e-mail, role, institution, what they open first."""
    import csv as _csv
    inst = {r["institution_id"]: r["name"] for r in _csv.DictReader(open(ROOT / "database/seed/institutions.csv", encoding="utf-8"))}
    roles = {"owner": ("Dirección", "/panorama"), "coordinator": ("Coordinación", "/tablero"), "physician": ("Medicina", "/reportes-voz"),
             "caregiver": ("Cuidado / enfermería", "/mis-visitas"), "family": ("Familia", "/familia")}
    rows = []
    for u in _csv.DictReader(open(ROOT / "database/seed/users.csv", encoding="utf-8")):
        r, home = roles[u["role"]]
        rows.append(f"<tr><td><code>{html.escape(u['email'])}</code></td><td>{r}</td>"
                    f"<td>{html.escape(inst.get(u['institution_id'], 'Todas'))}</td><td><code>{home}</code></td></tr>")
    return ('<table class="usuarios"><thead><tr><th>Correo</th><th>Rol</th><th>Institución</th><th>Inicio</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table>")


def number_html(key: str, where: str) -> str:
    if key not in NUMBERS:
        ERRORS.append(f"{where}: número desconocido {{{{ {key} }}}}")
        return f'<span class="missing">¿{html.escape(key)}?</span>'
    USED_NUMBERS.setdefault(key, []).append(where)
    d = NUMBERS[key]
    return f'<span class="num" title="{html.escape(d["source"])}">{html.escape(d["text"])}</span>'


def table_html(keys: list[str], where: str) -> str:
    rows = []
    for k in keys:
        if k not in NUMBERS:
            ERRORS.append(f"{where}: número desconocido en tabla: {k}")
            continue
        d = NUMBERS[k]
        USED_NUMBERS.setdefault(k, []).append(where)
        rows.append(f"<tr><td>{html.escape(d['label'])}</td><td class=\"v\">{html.escape(d['text'])}</td>"
                    f"<td class=\"src\">{html.escape(d['source'])}</td></tr>")
    return ('<table class="numeros"><thead><tr><th>Dato</th><th>Valor</th><th>Fuente</th></tr></thead><tbody>'
            + "".join(rows) + "</tbody></table>")


def preprocess(ch: Chapter, chapters_by_id: dict[str, Chapter]) -> tuple[str, list[str]]:
    """Replace the bible's own marks before Markdown runs. Returns (text, mermaid sources)."""
    text, where = ch.text, ch.path.relative_to(BIBLIA).as_posix()
    mermaids: list[str] = []

    def keep_mermaid(m):
        # numbers inside a diagram are plain text (no HTML)
        src = re.sub(r"\{\{\s*([\w.\-]+)\s*\}\}",
                     lambda k: (USED_NUMBERS.setdefault(k.group(1), []).append(where) or NUMBERS[k.group(1)]["text"])
                     if k.group(1) in NUMBERS else (ERRORS.append(f"{where}: número desconocido {k.group(1)}") or "?"),
                     m.group(1))
        mermaids.append(src)
        return f"\n\nMERMAIDBLOCK{len(mermaids) - 1}\n\n"
    text = re.sub(r"```mermaid\n(.*?)```", keep_mermaid, text, flags=re.S)

    def braces(m):
        inner = m.group(1).strip()
        if inner.startswith("tabla "):
            return "\n\n" + table_html(inner.split()[1:], where) + "\n\n"
        if inner.startswith("paginas "):          # pages from chapter A up to (not including) chapter B: counted by render.cjs
            a, b = inner.split()[1:3]
            return f'<span class="pagecount" data-from="{a}" data-to="{b}">000</span>'
        if inner == "tabla_usuarios":
            return "\n\n" + users_table() + "\n\n"
        if inner.startswith("equipo."):
            return html.escape(team_value(inner[len("equipo."):]))
        return number_html(inner, where)
    text = re.sub(r"\{\{(.+?)\}\}", braces, text)

    seen_here: set[str] = set()

    def term(m):
        name, _, shown = m.group(1).partition("|")
        entry = TERMS.get(name.strip().lower())
        shown = shown or name
        if not entry:
            ERRORS.append(f"{where}: término sin glosario [[{name}]]")
            return shown
        gid = entry["id"]
        if gid in seen_here:
            return f'<a class="term" href="#{gid}">{shown}</a>'
        seen_here.add(gid)
        anchor = f"u-{ch.id}-{gid}"
        FIRST_USE.setdefault(gid, anchor)
        return f'<a class="term first" id="{anchor}" href="#{gid}">{shown}</a>'
    text = re.sub(r"\[\[(.+?)\]\]", term, text)

    def ref(m):
        target = m.group(1)
        if target in chapters_by_id:
            c = chapters_by_id[target]
            return f'<a class="xref" href="#{target}">{c.label} «{c.title}»</a>'
        # a section inside a chapter: written as cap-id/seccion
        cap, _, sec = target.partition("/")
        if cap in chapters_by_id and sec:
            c = chapters_by_id[cap]
            return f'<a class="xref" href="#{cap}--{sec}">{c.label}, «{sec.replace("-", " ")}»</a>'
        ERRORS.append(f"{where}: referencia desconocida @ref({target})")
        return target
    text = re.sub(r"@ref\(([a-z0-9/-]+)\)", ref, text)
    # author-year citations: "Cairo (2019)", "(Kloog et al., 2014)", "Hernández-Sampieri y Mendoza, 2018"
    for m in re.finditer(r"([A-ZÁÉÍÓÚÑ][\w'’\-]+(?: [A-ZÁÉÍÓÚÑ][\w'’\-]+)?(?: et al\.)?(?: y [A-ZÁÉÍÓÚÑ][\w\-]+)?)"
                         r"(?:, | \()((?:19|20)\d\d)\)?", text):
        if m.group(1) not in NOT_CITATIONS:
            CITED.append((where, m.group(1)))
    return text, mermaids


def caption_html(alt: str) -> str:
    """Caption text: escape it, then turn `code` into <code> and **bold** into <strong>."""
    t = html.escape(alt, quote=False)
    t = re.sub(r"`([^`]+)`", r"<code>\1</code>", t)
    return re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", t)


FIG_COUNTER = [0]
TABLE_IDS = iter(range(1, 10**6))


def fig_id() -> str:
    FIG_COUNTER[0] += 1
    return str(FIG_COUNTER[0])


def figure(m) -> str:
    alt, src, cls = m.group(1), m.group(2), (m.group(4) or "")
    plain = re.sub(r"[`*]", "", alt)
    path = BIBLIA / src
    if not path.exists():
        WARNINGS.append(f"falta la imagen {src}")
        return (f'<figure class="shot {cls} missing-shot"><div>Falta la captura <code>{html.escape(src)}</code></div>'
                f"<figcaption>{caption_html(alt)}</figcaption></figure>")
    return f'<figure class="shot {cls}" data-fig="{fig_id()}"><img src="../{src}" alt="{html.escape(plain)}"><figcaption>{caption_html(alt)}</figcaption></figure>'


MD_EXT = ["tables", "attr_list", "admonition", "footnotes", "md_in_html", "sane_lists", "def_list", "fenced_code"]


def render(ch: Chapter, chapters_by_id: dict[str, Chapter]) -> None:
    text, mermaids = preprocess(ch, chapters_by_id)
    # Images alone on their line become figures with a caption
    text = re.sub(r"^!\[([^\]]*)\]\(([^)]+)\)(\{\.([a-z]+)\})?\s*$", lambda m: "\n" + figure(m) + "\n", text, flags=re.M)
    body = markdown.markdown(text, extensions=MD_EXT, output_format="html5")
    for i, src in enumerate(mermaids):
        block = f'<figure class="diagram" data-fig="{fig_id()}"><pre class="mermaid">{html.escape(src)}</pre></figure>'
        body = body.replace(f"<p>MERMAIDBLOCK{i}</p>", block)
    # ids for h2 sections (cap-id--slug) so they can be referenced and appear in the PDF outline
    body = re.sub(r"<h2>(.*?)</h2>",
                  lambda m: f'<h2 id="{ch.id}--{slug(re.sub("<[^>]+>", "", m.group(1)))}">{m.group(1)}</h2>', body)
    # every table gets an id, so render.cjs can move a table whose header would be alone at the bottom of a page
    body = re.sub(r"<table(?![^>]*data-tbl)", lambda m: f'<table data-tbl="{ch.id}-{next(TABLE_IDS)}"', body)
    ch.html = body


# ----------------------------------------------------------------------------------------------------------------
# Book assembly
# ----------------------------------------------------------------------------------------------------------------
def load_chapters() -> tuple[list[dict], dict[str, Chapter]]:
    parts, by_id, n = [], {}, 0
    for part in CONTENT["partes"]:
        chs = []
        for i, f in enumerate(part.get("capitulos", [])):
            path = BIBLIA / f
            if not path.exists():
                WARNINGS.append(f"capítulo pendiente: {f}")
                continue
            kind = part.get("tipo", "capitulo")
            if kind == "capitulo":
                n += 1
                label = f"cap. {n}"
            elif kind == "anexo":
                label = f"anexo {chr(ord('A') + i)}"
            else:
                label = part["titulo"]
            ch = Chapter(path, label, kind)
            ch.number = n if kind == "capitulo" else (chr(ord("A") + i) if kind == "anexo" else "")
            chs.append(ch)
            by_id[ch.id] = ch
        if chs or part.get("generado"):
            parts.append({**part, "chapters": chs})
    return parts, by_id


def glossary_html() -> str:
    items = []
    for e in sorted(GLOSSARY, key=lambda e: slug(e["termino"])):
        first = FIRST_USE.get(e["id"])
        where = f' <a class="firstuse" href="#{first}">primera vez</a>' if first else ""
        also = f' <span class="also">También: {", ".join(e["tambien"])}.</span>' if e.get("tambien") else ""
        before = f' <span class="also">Antes se llamaba: {e["antes"]}.</span>' if e.get("antes") else ""
        items.append(f'<dt id="{e["id"]}">{html.escape(e["termino"])}</dt>'
                     f'<dd>{markdown.markdown(e["definicion"], extensions=["attr_list"])[3:-4]}{also}{before}{where}</dd>')
    return '<dl class="glossary">' + "".join(items) + "</dl>"


def team_authors() -> str:
    """APA authors from equipo.yaml (local file): "Pérez López, A., …, & Gómez Ruiz, M. L." (last two words = surnames)."""
    names = TEAM.get("integrantes") or []
    if not names:
        return "Equipo del proyecto Enlaza."
    out = []
    for n in names:
        w = n.split()
        given, surnames = w[:-2] or w[:1], w[-2:] if len(w) > 2 else w[1:]
        out.append(f"{' '.join(surnames)}, {' '.join(g[0] + '.' for g in given)}")
    return (", ".join(out[:-1]) + ", & " + out[-1]) if len(out) > 1 else out[0]


def references_html() -> str:
    """Annex: every reference in APA 7, alphabetical (hanging indent)."""
    def key(r):
        t = r["apa"].replace("{autores_equipo}", team_authors())
        return unicodedata.normalize("NFKD", t).encode("ascii", "ignore").decode().lower()
    items = []
    for r in sorted(REFERENCES, key=key):
        apa = html.escape(r["apa"].replace("{autores_equipo}", team_authors()), quote=False)
        apa = re.sub(r"\*([^*]+)\*", r"<em>\1</em>", apa)
        apa = re.sub(r"(https?://\S+)", r'<a href="\1">\1</a>', apa)
        items.append(f"<p class=\"ref\">{apa}</p>")
    return "".join(items)


def check_references() -> None:
    """Every source URL of the data has a reference; every author-year citation in the text has a reference."""
    known_urls = {u for r in REFERENCES for u in (r.get("urls") or [])}
    import csv as _csv
    with open(ROOT / "data/business/assumptions.csv", encoding="utf-8") as f:
        for row in _csv.DictReader(f):
            u = row["url"].strip()
            if u.startswith("http") and u not in known_urls:
                ERRORS.append(f"referencias.yaml: falta la referencia de {u} ({row['key']} en assumptions.csv)")
    for u in re.findall(r"https?://[^\s`)]+", (ROOT / "docs/spec/09_datos.md").read_text(encoding="utf-8")):
        u = u.rstrip(".,")
        if u not in known_urls:
            ERRORS.append(f"referencias.yaml: falta la referencia de {u} (docs/spec/09_datos.md)")
    names = [c.lower() for r in REFERENCES for c in r.get("cita", [])]
    for where, author in CITED:
        a = author.lower().replace(" et al.", "").strip()
        if not any(a.startswith(n) or n.startswith(a.split(" y ")[0].split(",")[0]) for n in names):
            ERRORS.append(f"{where}: la cita «{author}» no tiene referencia en referencias.yaml")


def toc_html(parts: list[dict]) -> str:
    out = ['<nav class="toc" id="indice"><h1 class="toc-title">Índice</h1><ol>']
    for p in parts:
        if p.get("titulo_indice") is False:
            continue
        out.append(f'<li class="toc-part"><a href="#{p["id"]}">{html.escape(p["titulo"])}</a></li>')
        for ch in p["chapters"]:
            num = f'<span class="toc-num">{ch.number}</span>' if ch.number != "" else '<span class="toc-num"></span>'
            out.append(f'<li class="toc-ch">{num}<a href="#{ch.id}">{html.escape(ch.title)}</a></li>')
            for m in re.finditer(r'<h2 id="([^"]+)">(.*?)</h2>', ch.html):
                if p.get("subindice", True):
                    out.append(f'<li class="toc-sec"><a href="#{m.group(1)}">{re.sub("<[^>]+>", "", m.group(2))}</a></li>')
    out.append("</ol></nav>")
    return "".join(out)


def cover_html() -> str:
    names = TEAM.get("integrantes") or []
    team = "".join(f"<li>{html.escape(n)}</li>" for n in names) or "<li>Equipo Enlaza</li>"
    return f"""
<section class="cover">
  <img class="cover-logo" src="assets/logo-white.svg" alt="Enlaza · cuidado coordinado">
  <h1 class="cover-title">La biblia de <span>Enlaza</span></h1>
  <p class="cover-sub">Todo el proyecto explicado: qué hace, cómo funciona y por qué se decidió así</p>
  <div class="cover-meta">
    <p>{html.escape(team_value("escuela"))} · {html.escape(team_value("carrera"))} · <span class="nowrap">{html.escape(team_value("periodo"))}</span></p>
    <p class="cover-team-h">Equipo</p><ul class="cover-team">{team}</ul>
  </div>
  <p class="cover-foot">Prototipo académico · todos los datos son sintéticos · generado desde el repositorio</p>
</section>"""


def build(only: str | None = None) -> None:
    parts, by_id = load_chapters()
    for p in parts:
        for ch in p["chapters"]:
            render(ch, by_id)
    body = [cover_html(), toc_html(parts)]
    for p in parts:
        if not p.get("sin_portadilla"):
            body.append(f'<section class="part-title" id="{p["id"]}"><p class="part-kicker">{html.escape(p.get("kicker", ""))}</p>'
                        f'<h1>{html.escape(p["titulo"])}</h1><p class="part-desc">{html.escape(p.get("descripcion", ""))}</p></section>')
        else:
            body.append(f'<span id="{p["id"]}"></span>')
        for ch in p["chapters"]:
            kicker = {"capitulo": f"Capítulo {ch.number}", "anexo": f"Anexo {ch.number}"}.get(ch.kind, "")
            body.append(f'<section class="chapter {ch.kind}" id="{ch.id}" data-title="{html.escape(ch.title)}">'
                        f'<p class="ch-kicker">{kicker}</p><h1 class="ch-title">{html.escape(ch.title)}</h1>{ch.html}</section>')
        if p.get("generado") == "glosario":
            body.append('<section class="chapter anexo" id="anexo-referencias" data-title="Referencias">'
                        '<p class="ch-kicker">Anexo</p><h1 class="ch-title">Referencias (APA 7)</h1>'
                        '<p>Todas las fuentes de los datos (<code>data/business/assumptions.csv</code>, '
                        '<code>docs/spec/09_datos.md</code>) y las citadas en el libro, en formato APA 7. La compilación se detiene '
                        'si una fuente de los datos o una cita del texto no tiene su referencia.</p>' + references_html() + "</section>")
            body.append('<section class="chapter anexo" id="anexo-glosario" data-title="Glosario">'
                        '<p class="ch-kicker">Anexo</p><h1 class="ch-title">Glosario</h1>'
                        '<p>Cada término técnico del libro, explicado en palabras sencillas. «Primera vez» lleva a la página '
                        'donde aparece por primera vez.</p>' + glossary_html() + "</section>")

    page = f"""<!doctype html>
<html lang="es-MX"><head><meta charset="utf-8"><title>La biblia de Enlaza</title>
<link rel="stylesheet" href="assets/fonts.css"><link rel="stylesheet" href="../build/style.css">
</head><body>{''.join(body)}</body></html>"""
    OUT.mkdir(exist_ok=True)
    (OUT / "biblia.html").write_text(page, encoding="utf-8")

    # assets next to the HTML: logo + fonts (from the image's node_modules when available)
    assets = OUT / "assets"
    assets.mkdir(exist_ok=True)
    for name in ("logo.svg", "logo-white.svg", "logo-mark.svg"):
        shutil.copy(ROOT / "frontend/public" / name, assets / name)

    with open(OUT / "numeros_usados.csv", "w", encoding="utf-8") as f:
        f.write("clave,texto,fuente,donde\n")
        for k, places in sorted(USED_NUMBERS.items()):
            d = NUMBERS[k]
            f.write(f'"{k}","{d["text"]}","{d["source"]}","{"; ".join(sorted(set(places)))}"\n')

    check_references()
    for w in WARNINGS:
        print("AVISO:", w)
    if ERRORS:
        for e in ERRORS:
            print("ERROR:", e, file=sys.stderr)
        raise SystemExit(1)
    print(f"HTML listo: {OUT / 'biblia.html'} ({len(USED_NUMBERS)} números distintos usados)")


if __name__ == "__main__":
    build()
