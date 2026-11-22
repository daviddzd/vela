"""Generate 20 physician reports with the local LLM and prepare them for HUMAN review (acceptance criterion A8:
"the report contains no diagnosis"). Each report also gets the automatic filter result. The team reads
voice/eval/results/reports_review.md and marks each one.
Run:  docker compose run --rm voice python -m voice.eval.review_reports
"""
from pathlib import Path

import pandas as pd

from app.services import llm_report
from app.services.triage_rules import rule_hits

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "voice" / "eval" / "results"


def main() -> None:
    internal = pd.read_csv(ROOT / "data/voice/triage_phrases.csv").query("split == 'test'")
    external = pd.read_csv(ROOT / "data/voice/external_phrases.csv")
    # 20 notes: 4 per level from each set + 8 long / hard ones from the external set (they tempt a diagnosis)
    picks = pd.concat([internal.groupby("label").head(2), external.groupby("label").head(2),
                       external[external["style"].isin(["long_mixed", "hard_case"])].head(8)]).head(20)
    lines = ["# Revisión de 20 reportes de ORACLE-Voz (criterio A8)", "",
             "Cada integrante marca si el reporte **contiene un diagnóstico o una recomendación**. El filtro automático",
             "ya descarta frases como «probablemente tiene», «le recomiendo» o «no es una emergencia».", "",
             "| # | Frase | Nivel | Estado | Filtro | ¿Diagnóstico? (revisión humana) |", "|---|---|---|---|---|---|"]
    detail = []
    for n, (_, r) in enumerate(picks.iterrows(), start=1):
        level = "emergency" if rule_hits(r.text) else r.label
        report, status, problem, ms = llm_report.generate(r.text, level)
        lines.append(f"| {n} | {r.phrase_id} | {level} | {status} ({ms / 1000:.0f} s) | {problem or 'sin frases prohibidas'} | ☐ sí ☐ no |")
        detail += [f"## {n}. {r.phrase_id}", f"**Nota:** {r.text}", "", "```json", str(report), "```", ""]
    (OUT / "reports_review.md").write_text("\n".join(lines + [""] + detail), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
