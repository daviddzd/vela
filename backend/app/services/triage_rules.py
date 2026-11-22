"""ORACLE-Voz emergency rules (config/emergency_rules.yaml). They run FIRST; a hit is always `emergency`
and the classifier can only raise a level, never lower a rule match (CLAUDE.md rule 6).
Normalization: lowercase, accents removed, spaces collapsed (same as data/generator/check_emergency_rules.py).
There is no negation handling on purpose: a false alarm is acceptable, a missed emergency is not.
"""
from __future__ import annotations

import os
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import yaml

LEVELS = ["routine", "urgent", "emergency"]


def normalize(text: str) -> str:
    t = unicodedata.normalize("NFKD", text.lower())
    t = "".join(c for c in t if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", t).strip()


def _config_dir() -> Path:
    return Path(os.environ.get("CONFIG_DIR", Path(__file__).resolve().parents[3] / "config"))


@lru_cache
def rules() -> dict:
    return yaml.safe_load((_config_dir() / "emergency_rules.yaml").read_text(encoding="utf-8"))


@lru_cache
def _patterns() -> list[tuple[str, re.Pattern]]:
    return [(cat, re.compile(p)) for cat, c in rules()["categories"].items() for p in c["patterns"]]


def rule_hits(text: str) -> list[str]:
    """Categories whose patterns match the normalized text (empty list = no rule fired)."""
    n = normalize(text)
    return sorted({cat for cat, rx in _patterns() if rx.search(n)})


def final_level(hits: list[str], classifier_label: str | None) -> str:
    """Rule hit -> emergency, always. Otherwise the classifier's label (None = classifier unavailable)."""
    if hits:
        return "emergency"
    return classifier_label or "urgent"   # rules-only fallback: never "routine" without the classifier


def max_level(a: str, b: str) -> str:
    return a if LEVELS.index(a) >= LEVELS.index(b) else b
