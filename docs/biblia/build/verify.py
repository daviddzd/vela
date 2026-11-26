"""Final check of "La biblia de Enlaza" (run after build_biblia.sh; writes docs/biblia/out/verificacion.md).

1. Every number the book prints (out/numeros_usados.csv) is recomputed by an INDEPENDENT path, without the code of
   collect_numbers.py where possible: the raw CSV/JSON/YAML file, a direct SQL query, or the live API (/api/business).
2. Every printed value appears in the text of the PDF (pdftotext).
3. The visible text of every screenshot (capturas/*.txt, saved by capture.cjs) has no test data.
4. Digits typed in the chapters outside {{ }} are listed, to review by hand (dates, articles and ports are fine).

    python3 docs/biblia/build/verify.py      (inside the vela-biblia image, on the Compose network)
"""
from __future__ import annotations

import csv
import json
import os
import re
import subprocess
import urllib.request
from http.cookiejar import CookieJar
from pathlib import Path

import yaml

BIBLIA = Path(__file__).resolve().parents[1]
ROOT = BIBLIA.parents[1]
OUT = BIBLIA / "out"
NUM = json.loads((OUT / "numeros.json").read_text(encoding="utf-8"))
USED = list(csv.DictReader(open(OUT / "numeros_usados.csv", encoding="utf-8")))


def close(a, b, tol=0.051) -> bool:
    try:
        return abs(float(a) - float(b)) <= tol * max(1.0, abs(float(b)) * 0.001) or abs(float(a) - float(b)) <= tol
    except (TypeError, ValueError):
        return str(a).strip() == str(b).strip()


def rows(rel: str) -> list[dict]:
    with open(ROOT / rel, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------- independent recomputation per family of keys
def independent(key: str):
    """The value recomputed without collect_numbers.py, or None if there is no independent path."""
    p = key.split(".")
    if p[0] == "seed" and len(p) == 2 and (ROOT / f"database/seed/{p[1]}.csv").exists():
        return len(rows(f"database/seed/{p[1]}.csv"))
    if p[0] == "sim" and len(p) == 4:
        for r in rows("simulation/results/summary.csv"):
            if (r["scenario"], r["policy"], r["metric"]) == tuple(p[1:]):
                return float(r["mean"])
    if p[0] == "voz" and len(p) == 3 and p[1] in ("internal_test", "external", "holdout"):
        m = json.loads((ROOT / "voice/eval/results/metrics.json").read_text(encoding="utf-8"))[p[1]]
        field = {"n": "n", "emergencies": "emergencies", "sens": "emergency_sensitivity_pct",
                 "sens_rules": "emergency_sensitivity_rules_only_pct", "f1": "macro_f1", "fa100": "false_alarms_per_100_notes"}.get(p[2])
        if field:
            return m[field]
        if p[2] == "missed":
            return len(m["missed_emergencies"])
    if p[0] == "neg" and len(p) == 2:
        for r in rows("data/business/assumptions.csv"):
            if r["key"] == p[1]:
                return r["value"]
    if p[0] == "cfg":
        sim = yaml.safe_load(open(ROOT / "config/simulation.yaml", encoding="utf-8"))
        direct = {"auto_apply_after": sim["approval"]["auto_apply_after_minutes"], "urgent_within": sim["approval"]["urgent_within_minutes"],
                  "hold_minutes": sim["approval"]["hold_minutes"], "late_tolerance": sim["dispatch"]["late_tolerance_minutes"],
                  "not_closed_after": sim["dispatch"]["not_closed_after_minutes"], "replications": sim["experiments"]["replications"],
                  "horizon_days": sim["experiments"]["horizon_days"], "workdays": sim["staffing"]["workdays_per_week"]}
        return direct.get(p[1])
    if p[0] == "db" and p[1].startswith("rls_"):
        import psycopg2
        conn = psycopg2.connect(os.environ["DATABASE_URL"].replace("postgresql+psycopg://", "postgresql://"))
        setting = {"rls_patients_none": None, "rls_patients_insa": "INS-A", "rls_patients_all": "*",
                   "rls_vpatients_none": None, "rls_persons_none": None}.get(p[1], "skip")
        table = {"rls_vpatients_none": "v_patients", "rls_persons_none": "v_persons"}.get(p[1], "patients")
        if setting == "skip":
            return None
        with conn, conn.cursor() as cur:
            if setting:
                cur.execute("SELECT set_config('app.institution_id', %s, true)", (setting,))
            cur.execute(f"SELECT count(*) FROM {table}")
            v = cur.fetchone()[0]
        conn.close()
        return v
    if p[0] == "bm" and p[1] in ("arpa1", "fixed1", "breakeven_month", "payback_month"):
        return BUSINESS_API.get(p[1])
    return None


def business_api() -> dict:
    """The same figures, but asked to the running app (/api/business) as Dirección."""
    try:
        jar = CookieJar()
        op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        req = urllib.request.Request("http://proxy:8080/api/auth/login", data=json.dumps(
            {"email": "owner@ejemplo.test", "password": "Demo2026!"}).encode(), headers={"Content-Type": "application/json"})
        op.open(req, timeout=10)
        m = json.loads(op.open("http://proxy:8080/api/business", timeout=20).read())["model"]
        return {"arpa1": m["average_revenue_year1"], "fixed1": m["fixed_costs_year1"], "breakeven_month": m["breakeven_month"],
                "payback_month": m["payback_month"]}
    except Exception as e:  # noqa: BLE001
        print("AVISO: no se pudo consultar /api/business:", e)
        return {}


BUSINESS_API = business_api()


def main() -> None:
    pdf_text = subprocess.run(["pdftotext", str(BIBLIA / "biblia_enlaza.pdf"), "-"], capture_output=True, text=True).stdout
    pdf_flat = re.sub(r"\s+", " ", pdf_text)
    ok = mismatch = derived = 0
    problems, missing_pdf = [], []
    for u in USED:
        k, text = u["clave"], u["texto"]
        v = NUM[k]["value"]
        ind = independent(k)
        if ind is None:
            derived += 1
        elif close(v, ind):
            ok += 1
        else:
            mismatch += 1
            problems.append(f"| `{k}` | {text} | {ind} | {u['fuente']} |")
        if re.sub(r"\s+", " ", text) not in pdf_flat and text.replace(" ", " ") not in pdf_flat:
            missing_pdf.append(f"`{k}` = «{text}»")

    # screenshots: no test data in the visible text
    bad_words = re.compile(r"\b(pytest|prueba de|test_|dummy|lorem|asdf|foo|qwerty|xxx|TEST)\b", re.I)
    shots = sorted((BIBLIA / "capturas").glob("*.txt"))
    dirty = []
    for t in shots:
        # the demo accounts use the reserved .test domain (ejemplo.test, enlaza.test): that is not test data
        for m in bad_words.finditer(re.sub(r"[\w.-]+@[\w.-]+\.test\b", "", t.read_text(encoding="utf-8"))):
            dirty.append(f"{t.name}: «{m.group(0)}»")
    pngs = len(list((BIBLIA / "capturas").glob("*.png")))

    # digits typed in the chapters outside {{ }}, code, links and dates
    typed = []
    chapters = [m for d in ("guia", "parte1", "parte2", "parte3", "parte4", "parte5", "anexos") for m in sorted((BIBLIA / d).glob("*.md"))]
    for md in chapters:
        for i, line in enumerate(md.read_text(encoding="utf-8").splitlines(), 1):
            t = re.sub(r"\{\{.*?\}\}|`[^`]*`|\([^)]*\.(png|md|yaml|csv|py)\)|https?://\S+|@ref\([^)]*\)", "", line)
            t = re.sub(r"\b\d{1,2} (de )?(ene|feb|mar|abr|may|jun|jul|ago|sep|oct|nov|dic)\w*\.?( de)? ?(20\d\d)?", "", t)
            t = re.sub(r"\b(19|20)\d\d\b|\bart(s)?\. ?\d+|\bA\d{1,2}\b|#\d+|\b\d{3,5}\b(?= ?(px|×))|PAC-\d+|REQ-\d+|INS-\w", "", t)
            for n in re.findall(r"(?<![\w.])\d+(?:[.,]\d+)?\s?%", t):
                typed.append(f"{md.relative_to(BIBLIA)}:{i}: «{n}»")

    report = [
        "# Verificación final de La biblia de Enlaza", "",
        f"- Números distintos que imprime el libro: **{len(USED)}**",
        f"- Recalculados por un camino independiente y **coinciden**: **{ok}**",
        f"- **No coinciden**: **{mismatch}**",
        f"- Sin camino independiente (derivados con el mismo código, se revisan por su fuente): {derived}",
        f"- Valores que no aparecen en el texto del PDF: {len(missing_pdf)}",
        f"- Capturas revisadas: {pngs} imágenes, {len(shots)} textos; con posibles datos de prueba: **{len(dirty)}**",
        f"- Porcentajes escritos a mano en los capítulos: {len(typed)}", "",
    ]
    if problems:
        report += ["## No coinciden", "", "| Clave | Libro | Recalculado | Fuente |", "|---|---|---|---|", *problems, ""]
    if missing_pdf:
        report += ["## No aparecen en el PDF (revisar)", "", *[f"- {x}" for x in missing_pdf[:80]], ""]
    if dirty:
        report += ["## Capturas con posibles datos de prueba", "", *[f"- {x}" for x in dirty], ""]
    if typed:
        report += ["## Porcentajes escritos a mano (revisar uno por uno)", "", *[f"- {x}" for x in typed], ""]
    (OUT / "verificacion.md").write_text("\n".join(report), encoding="utf-8")
    print("\n".join(report[:10]))


if __name__ == "__main__":
    main()
