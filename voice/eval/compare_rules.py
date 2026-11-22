"""Rules only: BEFORE vs AFTER the patterns added on 21 Nov 2026 (voice/eval/proposed_rules.yaml, now applied
to config/emergency_rules.yaml), on the internal test split, the whole internal CSV, the external set (the
patterns were written seeing it) and the blind holdout (the only independent check).
Run:  docker compose run --rm voice python -m voice.eval.compare_rules
"""
import re
from pathlib import Path

import pandas as pd
import yaml

from app.services.triage_rules import normalize, rules

ROOT = Path(__file__).resolve().parents[2]
ADDED = {p for ps in yaml.safe_load((ROOT / "voice/eval/proposed_rules.yaml").read_text(encoding="utf-8"))["categories"].values()
         for p in ps}


def compiled(after: bool):
    return [re.compile(p) for c in rules()["categories"].values() for p in c["patterns"] if after or p not in ADDED]


def score(df, pats):
    hit = df.text.map(lambda t: any(p.search(normalize(t)) for p in pats))
    em = df.label == "emergency"
    return {"sensitivity_pct": round(100 * hit[em].mean(), 1), "missed": int((~hit & em).sum()),
            "false_alarms_per_100": round(100 * (hit & ~em).sum() / len(df), 1), "false_alarms": int((hit & ~em).sum())}


internal = pd.read_csv(ROOT / "data/voice/triage_phrases.csv")
sets = {"interno, prueba": internal[internal.split == "test"], "interno, todo el CSV": internal,
        "externo": pd.read_csv(ROOT / "data/voice/external_phrases.csv"),
        "holdout": pd.read_csv(ROOT / "data/voice/holdout_phrases.csv")}
rows = [{"conjunto": n, "reglas": "después" if a else "antes", **score(df, compiled(a))} for n, df in sets.items() for a in (False, True)]
out = pd.DataFrame(rows)
out.to_csv(ROOT / "voice/eval/results/rules_comparison.csv", index=False)
print(out.to_string(index=False))
