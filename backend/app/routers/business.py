"""/negocio (dirección only): business model computed from data/business/assumptions.csv, plus the REAL use of the
prototype (services coordinated per institution, automatic vs manual approvals, recurring revenue from the plan
each institution has contracted). Every number the page shows carries its source or the label "supuesto".
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_role, tenant_db
from app.core.roles import OWNER
from app.services import business_model as bm

router = APIRouter(prefix="/api/business", tags=["business"])
DIRECTION = require_role(OWNER)

MARKET_KEYS = ["population_60_plus_cdmx_2020", "market_care_residences_cdmx", "market_residential_care_cdmx",
               "market_care_spaces_cdmx_2024", "market_jap_residences_2020", "expansion_order"]
COMPETITOR_KEYS = ["competitor_hulipractice_min", "competitor_hulipractice_max", "competitor_huli_clinic_agenda",
                   "competitor_huli_clinic_record", "competitor_doctoralia_starter", "competitor_doctoralia_vip",
                   "competitor_nimbo", "competitor_geriges_min", "competitor_geriges_max", "commission_alternative"]


def usage(db: Session, minutes_per_assignment: float) -> dict:
    """What the prototype really did (seed history + live operation). The owner session sees every institution."""
    per_inst = db.execute(text("""
        SELECT i.institution_id, i.name, i.active, p.name AS plan, p.monthly_price_mxn AS price,
               count(a.assignment_id) FILTER (WHERE a.status <> 'reassigned')                          AS coordinated,
               count(a.assignment_id) FILTER (WHERE a.status <> 'reassigned' AND a.approval = 'auto')      AS auto,
               count(a.assignment_id) FILTER (WHERE a.status <> 'reassigned' AND a.approval = 'coordinator') AS manual,
               count(a.assignment_id) FILTER (WHERE a.status <> 'reassigned' AND a.approval = 'timeout')   AS timeout
        FROM institutions i JOIN subscription_plans p USING (plan_id)
        LEFT JOIN assignments a ON a.institution_id = i.institution_id
        GROUP BY i.institution_id, i.name, i.active, p.name, p.monthly_price_mxn
        ORDER BY i.institution_id""")).mappings().all()
    rows = [dict(r) for r in per_inst]
    total = {k: sum(r[k] for r in rows) for k in ("coordinated", "auto", "manual", "timeout")}
    without_person = total["auto"] + total["timeout"]
    return {
        "institutions": rows, "totals": total,
        "auto_pct": round(100 * total["auto"] / total["coordinated"], 1) if total["coordinated"] else None,
        "hours_saved": round(without_person * minutes_per_assignment / 60, 1),
        # Monthly recurring revenue: the plan each ACTIVE institution has contracted (invoices are empty in the seed)
        "mrr": sum(r["price"] for r in rows if r["active"]),
        "first_activity": db.scalar(text("SELECT min(assigned_at)::date FROM assignments")),
    }


class Overrides(BaseModel):
    values: dict = {}


def _summary(m: dict, overrides: dict | None = None) -> dict:
    """Model + what would make the NPV zero + (only if the CDMX share is too high) the conservative scenario."""
    return {k: v for k, v in m.items() if k != "months"} | {
        "months": [{k: r[k] for k in ("month", "year", "customers", "revenue", "costs", "profit", "cash")} for r in m["months"]],
        "what_if": bm.what_for_npv_zero(overrides),
        "conservative": bm.conservative(overrides) if m["market"]["too_high"] else None}


@router.get("")
def overview(user: CurrentUser = Depends(DIRECTION), db: Session = Depends(tenant_db)) -> dict:
    a = bm.assumptions()
    return {"assumptions": a, "editable": list(bm.EDITABLE), "market": [a[k] for k in MARKET_KEYS if k in a],
            "competitors": [a[k] for k in COMPETITOR_KEYS if k in a],
            "plans": [a[k] for k in ("plan_basic_price", "plan_professional_price", "plan_institutional_price")],
            "usage": usage(db, a["minutes_per_manual_assignment"]["value"]), "model": _summary(bm.model())}


@router.post("/model")
def recompute(body: Overrides, user: CurrentUser = Depends(DIRECTION)) -> dict:
    """Same model with the values changed on the page (only the editable keys, within their range)."""
    return _summary(bm.model(body.values), body.values)
