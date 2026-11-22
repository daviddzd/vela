"""ORACLE-Voz text evaluation of the WHOLE system (rules first, then the Keras classifier, final = the higher).

Three sets, reported separately:
  internal  the `test` split of data/voice/triage_phrases.csv (the rules were written seeing this whole file,
            so 100 % here does NOT show that they generalize)
  external  data/voice/external_phrases.csv: 150 new phrases in another style, labelled before running the
            rules (see git history); the rules were NOT changed to pass it. Its misses led to the rule
            additions of 21 Nov 2026, so it is no longer independent for the RULES.
  holdout   data/voice/holdout_phrases.csv: 150 phrases written blind (without the rules or the other sets),
            committed before any evaluation. Never used to train or to adjust rules: the ONLY honest test.
Since 21 Nov 2026 the classifier is trained on internal + external, so only `holdout` measures the classifier.
Metrics: emergency sensitivity (recall), macro F1, confusion matrix, false alarms per 100 notes; every missed
emergency is listed. Run:  docker compose run --rm voice python -m voice.eval.evaluate
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from sklearn.metrics import confusion_matrix, f1_score

from app.services.triage_rules import LEVELS, max_level, rule_hits
from voice.triage import classifier

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "voice" / "eval" / "results"


def run(df: pd.DataFrame, model) -> pd.DataFrame:
    df = df.copy()
    df["rule_hits"] = df.text.map(rule_hits)
    df["rules_only"] = df.rule_hits.map(lambda h: "emergency" if h else None)
    df["classifier"] = [p["label"] for p in classifier.predict(model, df.text.tolist())]
    df["final"] = [max_level("emergency", c) if h else c for h, c in zip(df.rule_hits, df.classifier)]
    return df


def metrics(df: pd.DataFrame) -> dict:
    em = df[df.label == "emergency"]
    non_em = df[df.label != "emergency"]
    cm = confusion_matrix(df.label, df.final, labels=LEVELS)
    return {
        "n": len(df), "emergencies": len(em),
        "emergency_sensitivity_pct": round(100 * (em.final == "emergency").mean(), 1),
        "emergency_sensitivity_rules_only_pct": round(100 * (em.rule_hits.str.len() > 0).mean(), 1),
        "macro_f1": round(f1_score(df.label, df.final, labels=LEVELS, average="macro"), 3),
        "false_alarms_per_100_notes": round(100 * (non_em.final == "emergency").sum() / len(df), 1),
        "false_alarms": int((non_em.final == "emergency").sum()),
        "confusion_matrix": {"labels (rows = true, cols = predicted)": LEVELS, "values": cm.tolist()},
    }


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    model = classifier.load()
    internal = pd.read_csv(ROOT / "data" / "voice" / "triage_phrases.csv")
    internal = internal[internal.split == "test"]
    external = pd.read_csv(ROOT / "data" / "voice" / "external_phrases.csv")
    holdout = pd.read_csv(ROOT / "data" / "voice" / "holdout_phrases.csv")
    report = {}
    for name, df in (("internal_test", internal), ("external", external), ("holdout", holdout)):
        res = run(df, model)
        res.to_csv(OUT / f"predictions_{name}.csv", index=False)
        report[name] = metrics(res)
        report[name]["used_for_training_or_rules"] = name != "holdout"
        missed = res[(res.label == "emergency") & (res.final != "emergency")]
        report[name]["missed_emergencies"] = missed[["phrase_id", "text", "category", "classifier"]].to_dict("records")
    (OUT / "metrics.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    for name, m in report.items():
        tag = "" if name == "holdout" else "  [ya usado para entrenar/ajustar: no es prueba independiente]"
        print(f"\n== {name}{tag}: n={m['n']}  sensibilidad emergencia {m['emergency_sensitivity_pct']} % "
              f"(solo reglas {m['emergency_sensitivity_rules_only_pct']} %)  F1 macro {m['macro_f1']}  "
              f"falsas alarmas {m['false_alarms_per_100_notes']} por 100 notas")
        print("   matriz (filas = real, columnas = predicho):", LEVELS, m["confusion_matrix"]["values"])
        for x in m["missed_emergencies"]:
            print(f"   SE ESCAPA {x['phrase_id']} [{x['category']}] clasificador={x['classifier']}: {x['text']}")


if __name__ == "__main__":
    main()
