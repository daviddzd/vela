"""Data augmentation for the triage classifier: more variety from the same labelled phrases.

Four simple, explainable transformations (fixed random seed, so the result is reproducible):
  typo        a few keyboard mistakes: missing / swapped / doubled letters, a neighbouring key, two words joined
  filler      how people start or end a message: "oiga,", "fíjese que", "¿qué hago?"…
  paraphrase  swap who the message is about and common Mexican synonyms (ahora/ahorita, muy/bien…)
  long_mixed  two phrases in one message; the label is the MORE SERIOUS one (the most serious part decides)
The label never changes, except in long_mixed (max of both). Holdout phrases are never used here.
"""
from __future__ import annotations

import random
import re

import pandas as pd

LEVELS = ["routine", "urgent", "emergency"]
NEIGHBOURS = {"a": "sq", "e": "wr", "i": "uo", "o": "ip", "u": "yi", "s": "ad", "n": "bm", "r": "et", "t": "ry",
              "l": "k", "m": "n", "c": "xv", "d": "sf", "p": "o", "b": "vn", "g": "fh", "h": "gj"}
OPENINGS = ["oiga, ", "fíjese que ", "mire, ", "buenas, le escribo porque ", "perdón que moleste pero ", "la verdad ",
            "hola buenas tardes ", "oigan ", "una pregunta, ", "le cuento que ", "ay no sé, ", "disculpe, "]
CLOSINGS = [" por favor", " gracias", " ¿qué hago?", " ayúdenme", " ¿me pueden decir algo?", " quedo pendiente",
            " porfa", " saludos", "", ""]
WHO = ["mi mamá", "mi papá", "mi abuelita", "mi abuelito", "mi esposo", "mi esposa", "la señora", "el señor",
       "don Chuy", "doña Lupe", "mi suegra", "mi tía"]
SYNONYMS = [("ahora", "ahorita"), ("muy", "bien"), ("mucho", "un montón"), ("rápido", "rapidito"),
            ("preocupada", "apurada"), ("también", "tambien"), ("está", "esta"), ("qué", "que")]
JOINERS = [". Y otra cosa, ", ", ah y además ", ". Por cierto ", " y aparte ", ". Oiga, también "]


def typo(text: str, rng: random.Random) -> str:
    chars = list(text)
    for _ in range(rng.randint(1, 3)):
        if len(chars) < 6:
            break
        i = rng.randrange(1, len(chars) - 1)
        kind = rng.choice(["drop", "swap", "double", "neighbour", "join"])
        if kind == "drop":
            del chars[i]
        elif kind == "swap":
            chars[i], chars[i + 1] = chars[i + 1], chars[i]
        elif kind == "double":
            chars.insert(i, chars[i])
        elif kind == "neighbour" and chars[i].lower() in NEIGHBOURS:
            chars[i] = rng.choice(NEIGHBOURS[chars[i].lower()])
        elif kind == "join" and chars[i] == " ":
            del chars[i]
    out = "".join(chars)
    return out.lower() if rng.random() < 0.5 else out


def filler(text: str, rng: random.Random) -> str:
    return rng.choice(OPENINGS) + text[0].lower() + text[1:] + rng.choice(CLOSINGS)


def paraphrase(text: str, rng: random.Random) -> str:
    out = re.sub(r"\b(mi (mamá|papá|abuelita|abuelito|abuela|abuelo|esposo|esposa)|la señora|el señor)\b",
                 lambda m: rng.choice(WHO), text, flags=re.IGNORECASE)
    for a, b in SYNONYMS:
        if rng.random() < 0.5:
            out = re.sub(rf"\b{a}\b", b, out) if rng.random() < 0.5 else re.sub(rf"\b{b}\b", a, out)
    return out


def augment(df: pd.DataFrame, copies: int = 3, mixed: int = 1500, seed: int = 2026) -> pd.DataFrame:
    """df has columns text, label. Returns the originals plus the augmented rows (column `aug` says which)."""
    rng = random.Random(seed)
    rows = [{"text": t, "label": l, "aug": "original"} for t, l in zip(df.text, df.label)]
    for t, l in zip(df.text, df.label):
        for _ in range(copies):
            kind = rng.choice(["typo", "filler", "paraphrase", "paraphrase+typo", "filler+typo"])
            new = t
            for step in kind.split("+"):
                new = {"typo": typo, "filler": filler, "paraphrase": paraphrase}[step](new, rng)
            rows.append({"text": new, "label": l, "aug": kind})
    texts, labels = df.text.tolist(), df.label.tolist()
    for _ in range(mixed):
        i, j = rng.randrange(len(texts)), rng.randrange(len(texts))
        label = LEVELS[max(LEVELS.index(labels[i]), LEVELS.index(labels[j]))]   # the more serious part decides
        rows.append({"text": texts[i].rstrip(".") + rng.choice(JOINERS) + texts[j][0].lower() + texts[j][1:],
                     "label": label, "aug": "long_mixed"})
    return pd.DataFrame(rows).drop_duplicates("text")
