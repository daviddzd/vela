"""SIRAG-D results (read-only). The simulation runs offline (docker compose run --rm sim) and writes CSV
files to simulation/results/; this endpoint only reads them. Nothing here touches the operation data."""
import csv
import json
import math
import os
from pathlib import Path

from fastapi import APIRouter, Depends

from app.core.deps import CurrentUser, require_role
from app.core.roles import COORDINATOR, OWNER

router = APIRouter(prefix="/api/simulation", tags=["simulation"])
FILES = ("summary", "window", "tests", "validation", "sensitivity", "sensitivity_tests", "contingency_effect")


def results_dir() -> Path:
    return Path(os.environ.get("SIM_RESULTS_DIR", Path(__file__).resolve().parents[3] / "simulation" / "results"))


def _value(v: str):
    """CSV text -> number when it is one (NaN -> None), else the text."""
    if v in ("", "nan", "NaN"):
        return None
    try:
        f = float(v)
        return None if math.isnan(f) else f
    except ValueError:
        return {"True": True, "False": False}.get(v, v)


def _read(name: str) -> list[dict]:
    with open(results_dir() / f"{name}.csv", encoding="utf-8") as f:
        return [{k: _value(v) for k, v in row.items()} for row in csv.DictReader(f)]


@router.get("/results")
def results(user: CurrentUser = Depends(require_role(COORDINATOR, OWNER))) -> dict:
    base = results_dir()
    if not (base / "summary.csv").exists():
        return {"available": False}
    return {"available": True, "info": json.loads((base / "run_info.json").read_text(encoding="utf-8")),
            **{name: _read(name) for name in FILES if (base / f"{name}.csv").exists()}}
