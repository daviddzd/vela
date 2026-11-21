"""Check that every emergency phrase triggers at least one rule in config/emergency_rules.yaml,
and report how many non-emergency phrases trigger a rule (false alarms, acceptable by policy)."""
import re, sys, unicodedata
import pandas as pd
import yaml

def normalize(t):
    t = unicodedata.normalize("NFKD", t.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t)

rules = yaml.safe_load(open(sys.argv[1] if len(sys.argv) > 1 else "config/emergency_rules.yaml", encoding="utf-8"))
patterns = [(cat, re.compile(p)) for cat, c in rules["categories"].items() for p in c["patterns"]]
df = pd.read_csv(sys.argv[2] if len(sys.argv) > 2 else "data/voice/triage_phrases.csv")

def match(text):
    n = normalize(text)
    return [cat for cat, rx in patterns if rx.search(n)]

df["rule_hits"] = df.text.map(match)
em = df[df.label == "emergency"]
missed = em[em.rule_hits.str.len() == 0]
false_alarm = df[(df.label != "emergency") & (df.rule_hits.str.len() > 0)]
print(f"emergency phrases: {len(em)}  missed by rules: {len(missed)}")
print(f"non-emergency phrases flagged by rules (false alarms): {len(false_alarm)} of {len(df) - len(em)}")
if len(missed):
    print(missed[["text", "category"]].head(20).to_string())
    sys.exit(1)
if len(false_alarm):
    print(false_alarm[["text", "label"]].head(10).to_string())
