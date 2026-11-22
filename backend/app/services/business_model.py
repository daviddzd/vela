"""Business model of Vela (docs/spec/08), computed ONLY from data/business/assumptions.csv.

Every input is a row of that file (value, unit, source, url, type real/assumption). The /negocio page can change
the main assumptions (prices, plan mix, customers per year, churn, price adjustment...) and calls this module
again, so all results come from one place and the team can explain each line.

Model, month by month for 5 years (60 months), in NOMINAL pesos (team decision 22 Nov 2026):
  customers   start at 0; each month   customers = customers x (1 - churn) + new
              "new" is constant inside a year and is the number that makes the year end at the target
              (customers_year1 and customer_growth_year2_5). Customers are an expected value (decimals).
  revenue     customers x average revenue per institution (plan mix x plan prices);
              prices rise each year with inflation unless the price adjustment is off (pessimistic case)
  costs       fixed: founders x salary x employer factor + infrastructure
              grow with customers: support (1 person per N institutions, from N on), production hosting
              (from year 2, 1 server + 1 database per N institutions, USD x FIX) and the acquisition cost
              of each new institution. All costs rise each year with inflation.
  results     monthly profit, cumulative cash, break-even month (first month with revenue >= costs and it
              stays so), payback month (cumulative cash back to >= 0), NPV of the 60 monthly flows at each
              NOMINAL annual discount rate. Before taxes; no initial investment (assumption, shown on the page).
"""
from __future__ import annotations

import csv
import math
import os
from functools import lru_cache
from pathlib import Path

MONTHS = 60
CSV_PATH = Path(os.environ.get("BUSINESS_DIR", "/data/business")) / "assumptions.csv"

# What the page may change, with the allowed range (anything else is ignored).
EDITABLE = {
    "plan_basic_price": (0, 100_000), "plan_professional_price": (0, 100_000), "plan_institutional_price": (0, 200_000),
    "plan_mix_basic": (0, 100), "plan_mix_professional": (0, 100), "plan_mix_institutional": (0, 100),
    "customers_year1": (0, 2_000), "customer_growth_year2_5": None, "monthly_churn": (0, 20),
    "price_inflation_adjustment": (0, 1), "institutions_per_support": (1, 500), "cac_per_institution": (0, 500_000),
    "institutions_per_server": (1, 500),
    # recommended scenario
    "recommended_private_cap": (1, 100), "plan_government_price": (0, 100_000), "government_sales_cycle_months": (0, 36),
    "government_cap": (0, 100), "founder_salary_year1_recommended": (0, 100),
}


@lru_cache(maxsize=4)
def _read(path: str) -> tuple[dict, ...]:
    with open(path, encoding="utf-8") as f:
        return tuple(csv.DictReader(f))


def assumptions(path: Path | None = None) -> dict[str, dict]:
    """key -> {value, unit, description_es, source, url, type}; numbers parsed when they are numbers."""
    out = {}
    for row in _read(str(path or CSV_PATH)):
        row = dict(row)
        try:
            row["value"] = float(row["value"])
        except ValueError:
            pass                                     # text values (lists, "no publicado")
        out[row["key"]] = row
    return out


def _targets(text: str) -> list[float]:
    return [float(x) for x in str(text).split(",") if x.strip()]


def inputs(overrides: dict | None = None, path: Path | None = None) -> dict:
    """The values the model uses: the CSV, with the allowed overrides from the page applied."""
    a = assumptions(path)
    v = {k: r["value"] for k, r in a.items()}
    for k, x in (overrides or {}).items():
        if k not in EDITABLE:
            continue
        if k == "customer_growth_year2_5":
            nums = _targets(x if isinstance(x, str) else ",".join(map(str, x)))
            if len(nums) == 4 and all(0 <= n <= 5_000 for n in nums):
                v[k] = ",".join(str(n) for n in nums)
            continue
        lo, hi = EDITABLE[k]
        v[k] = min(max(float(x), lo), hi)
    return v


def average_revenue(v: dict, year: int = 1) -> float:
    """Average monthly revenue per institution (plan mix x prices) in a given year."""
    mix = [v["plan_mix_basic"], v["plan_mix_professional"], v["plan_mix_institutional"]]
    total = sum(mix) or 1.0                                     # the mix is normalized to 100 %
    prices = [v["plan_basic_price"], v["plan_professional_price"], v["plan_institutional_price"]]
    arpa = sum(m / total * p for m, p in zip(mix, prices))
    return arpa * (_index(v, year) if v["price_inflation_adjustment"] >= 0.5 else 1.0)


def _index(v: dict, year: int) -> float:
    """Price level of year 1..5 relative to year 1 (annual inflation)."""
    return (1 + v["inflation_annual_oct_2026"] / 100) ** (year - 1)


def fixed_costs(v: dict, year: int = 1, founder_pct_year1: float = 100) -> float:
    """Founders' salaries + infrastructure. `founder_pct_year1` < 100: founders earn less in year 1 (recommended)."""
    pct = founder_pct_year1 / 100 if year == 1 else 1.0
    base = v["founders"] * v["founder_salary_year1"] * v["employer_cost_factor"] * pct + v["infra_monthly_year1"]
    return base * _index(v, year)


def _costs(v: dict, year: int, customers: float, new: float, founder_pct_year1: float = 100) -> dict:
    """Monthly costs: fixed + those that grow with customers (support, production hosting, acquisition)."""
    idx = _index(v, year)
    support_people = math.floor(customers / v["institutions_per_support"])
    servers = math.ceil(customers / v["institutions_per_server"]) if year >= v["hosting_start_year"] else 0
    return {"fixed": fixed_costs(v, year, founder_pct_year1),
            "support": support_people * v["support_salary_reference"] * v["employer_cost_factor"] * idx,
            "hosting": servers * (v["hosting_server_usd"] + v["hosting_database_usd"]) * v["usd_mxn_fix"] * idx,
            "acquisition": new * v["cac_per_institution"] * idx}


def simulate(v: dict) -> list[dict]:
    churn = v["monthly_churn"] / 100
    targets = [v["customers_year1"], *_targets(v["customer_growth_year2_5"])]
    keep = 1 - churn
    sum_keep = sum(keep ** k for k in range(12))                # new customers added in the 12 months
    customers, edomex, rows = 0.0, 0.0, []
    for year in range(1, 6):
        start = customers
        new = max(0.0, (targets[year - 1] - start * keep ** 12) / sum_keep)
        # Expansion order CDMX -> Edomex: from edomex_start_year, a share of the new customers is in Edomex
        new_edomex = new * v["edomex_share_of_new"] / 100 if year >= v["edomex_start_year"] else 0.0
        for m in range(12):
            lost = customers * churn
            customers = customers - lost + new
            edomex = edomex * keep + new_edomex
            costs = _costs(v, year, customers, new)
            revenue = customers * average_revenue(v, year)
            rows.append({"month": (year - 1) * 12 + m + 1, "year": year, "customers": customers, "new": new,
                         "customers_edomex": edomex, "customers_cdmx": customers - edomex,
                         "customers_jalisco": 0.0, "customers_nuevoleon": 0.0, "government": 0.0,
                         "lost": lost, "revenue": revenue, **{f"cost_{k}": c for k, c in costs.items()},
                         "costs": sum(costs.values()), "profit": revenue - sum(costs.values())})
    cash = 0.0
    for r in rows:
        cash += r["profit"]
        r["cash"] = cash
    return rows


def npv(rows: list[dict], annual_rate_pct: float) -> float:
    """Net present value of the monthly profits at a NOMINAL annual rate (monthly compounding equivalent)."""
    monthly = (1 + annual_rate_pct / 100) ** (1 / 12) - 1
    return sum(r["profit"] / (1 + monthly) ** r["month"] for r in rows)


def _first(rows: list[dict], test) -> int | None:
    """First month from which `test` holds until the end (None = never inside the 5 years)."""
    for i, r in enumerate(rows):
        if all(test(x) for x in rows[i:]):
            return r["month"]
    return None


def model(overrides: dict | None = None, path: Path | None = None) -> dict:
    v = inputs(overrides, path)
    rows = simulate(v)
    arpa1 = average_revenue(v, 1)
    breakeven = _first(rows, lambda r: r["profit"] >= 0)
    payback = _first(rows, lambda r: r["cash"] >= 0)
    years = []
    for y in range(1, 6):
        ys = [r for r in rows if r["year"] == y]
        years.append({"year": y, "customers_end": ys[-1]["customers"], "new": sum(r["new"] for r in ys),
                      "lost": sum(r["lost"] for r in ys), "revenue": sum(r["revenue"] for r in ys),
                      "costs": sum(r["costs"] for r in ys), "profit": sum(r["profit"] for r in ys),
                      "cost_fixed": sum(r["cost_fixed"] for r in ys), "cost_support": sum(r["cost_support"] for r in ys),
                      "cost_hosting": sum(r["cost_hosting"] for r in ys),
                      "cost_acquisition": sum(r["cost_acquisition"] for r in ys),
                      "cash_end": ys[-1]["cash"], "arpa": average_revenue(v, y)})
    rates = [v["discount_rate_low"], v["discount_rate_base"], v["discount_rate_high"]]
    worst = min(rows, key=lambda r: r["cash"])
    return {
        # Investment needed = the deepest point of the cumulative cash (what must be financed before it recovers)
        "investment": {"amount": -worst["cash"] if worst["cash"] < 0 else 0.0, "month": worst["month"] if worst["cash"] < 0 else None},
        "unit": unit_economics(v),
        "market": market(v, rows),
        "inputs": {k: v[k] for k in EDITABLE},
        "average_revenue_year1": arpa1,
        "fixed_costs_year1": fixed_costs(v, 1),
        # The classic one-line break-even of the spec: fixed costs of year 1 / average revenue
        "breakeven_institutions_static": math.ceil(fixed_costs(v, 1) / arpa1) if arpa1 > 0 else None,
        "breakeven_month": breakeven, "breakeven_year": math.ceil(breakeven / 12) if breakeven else None,
        "payback_month": payback,
        "npv": [{"rate_pct": r, "npv": npv(rows, r)} for r in rates],
        "years": years, "months": rows,
    }


# ---- unit economics, what-if, market -----------------------------------------------------------------

def unit_economics(v: dict) -> dict:
    """One institution, year-1 prices, steady operation (hosting included):
      monthly margin = average revenue - support and hosting that each institution adds
      lifetime       = 1 / monthly churn (months)          LTV = margin x lifetime (not discounted)
      CAC payback    = CAC / monthly margin (months)"""
    support = v["support_salary_reference"] * v["employer_cost_factor"] / v["institutions_per_support"]
    hosting = (v["hosting_server_usd"] + v["hosting_database_usd"]) * v["usd_mxn_fix"] / v["institutions_per_server"]
    margin = average_revenue(v, 1) - support - hosting
    churn = v["monthly_churn"] / 100
    cac = v["cac_per_institution"]
    ltv = margin / churn if churn > 0 else None
    return {"margin_month": margin, "variable_cost_month": support + hosting, "lifetime_months": 1 / churn if churn > 0 else None,
            "ltv": ltv, "cac": cac, "ltv_cac": ltv / cac if ltv is not None and cac > 0 else None,
            "cac_payback_months": cac / margin if margin > 0 else None}


def _bisect(f, lo: float, hi: float, steps: int = 60) -> float | None:
    """x in [lo, hi] with f(x) = 0, if f changes sign there (f is monotonic in our uses); else None."""
    flo, fhi = f(lo), f(hi)
    if flo == 0:
        return lo
    if flo * fhi > 0:
        return None
    for _ in range(steps):
        mid = (lo + hi) / 2
        if (f(mid) > 0) == (fhi > 0):
            hi, fhi = mid, f(mid)
        else:
            lo = mid
    return (lo + hi) / 2


def what_for_npv_zero(overrides: dict | None = None) -> dict:
    """Each lever SEPARATELY (the others as on the page): the value that makes the NPV at the base rate exactly 0.
    An analysis of how far the plan is, not a target."""
    base = dict(overrides or {})
    v = inputs(base)
    rate = v["discount_rate_base"]
    targets = _targets(v["customer_growth_year2_5"])

    def npv_with(extra: dict) -> float:
        return npv(simulate(inputs({**base, **extra})), rate)

    price = _bisect(lambda x: npv_with({"plan_professional_price": x}), 0, 100_000)
    year5 = _bisect(lambda x: npv_with({"customer_growth_year2_5": ",".join(str(n) for n in [*targets[:3], x])}),
                    targets[2], 5_000)
    cac = _bisect(lambda x: npv_with({"cac_per_institution": x}), 0, 500_000)
    return {"rate_pct": rate, "npv_now": npv(simulate(v), rate),
            "plan_professional_price": price, "current_professional_price": v["plan_professional_price"],
            "customers_year5": year5, "current_customers_year5": targets[3],
            "cac": cac, "current_cac": v["cac_per_institution"]}


SEGMENTS = [("residences", "Residencias (asilos)"), ("day_centers", "Centros de día"), ("home_nursing", "Enfermería a domicilio")]


def market(v: dict, rows: list[dict]) -> dict:
    """Year-5 customers by region (expansion order) against the establishments that match Vela's customers
    (DENUE 05/2026). Private establishments are the target; public ones are shown apart."""
    def count(region: str, private: bool) -> float:
        total = 0.0
        for seg, _ in SEGMENTS:
            key = f"denue_{seg}_{'private' if private else 'public'}_{region}" if seg != "home_nursing" else f"denue_{seg}_{region}"
            if seg == "home_nursing" and not private:
                continue                                   # DENUE has one class for home nursing (no public/private split)
            total += v.get(key, 0) if isinstance(v.get(key), float) else 0
        return total
    last = rows[-1]
    out = {}
    for region in ("cdmx", "edomex"):
        target = count(region, True) + (0 if v["target_market_private_only"] >= 0.5 else count(region, False))
        customers = last[f"customers_{region}"]
        out[region] = {"customers_year5": customers, "target_establishments": target,
                       "public_establishments": count(region, False),
                       "share_pct": 100 * customers / target if target else None}
    out["alert_pct"] = v["market_share_alert"]
    out["too_high"] = (out["cdmx"]["share_pct"] or 0) > v["market_share_alert"]
    return out


def conservative(overrides: dict | None = None) -> dict:
    """Same model with fewer customers each year (conservative_customer_factor of the targets)."""
    v = inputs(overrides)
    f = v["conservative_customer_factor"] / 100
    targets = [v["customers_year1"], *_targets(v["customer_growth_year2_5"])]
    m = model({**(overrides or {}), "customers_year1": targets[0] * f,
               "customer_growth_year2_5": ",".join(str(round(x * f, 2)) for x in targets[1:])})
    return {"factor_pct": v["conservative_customer_factor"], "customers": [y["customers_end"] for y in m["years"]],
            "breakeven_month": m["breakeven_month"], "payback_month": m["payback_month"], "npv": m["npv"],
            "investment": m["investment"], "market": m["market"], "years": [{k: y[k] for k in ("year", "revenue", "costs", "profit", "cash_end")} for y in m["years"]]}


# ---- scenarios: base, conservative, recommended (team decision 22 Nov 2026) ----------------------------

REGIONS = ["cdmx", "edomex", "jalisco", "nuevoleon"]


def private_count(v: dict, region: str) -> float:
    """Establishments that match Vela's private customers in a state (DENUE 05/2026)."""
    keys = [f"denue_residences_private_{region}", f"denue_day_centers_private_{region}", f"denue_home_nursing_{region}"]
    return sum(v[k] for k in keys if isinstance(v.get(k), float))


def public_day_centers(v: dict, region: str) -> float:
    k = f"denue_day_centers_public_{region}"
    return v[k] if isinstance(v.get(k), float) else 0.0


def _path(targets: list[float], churn: float, start_month: int) -> list[tuple[float, float]]:
    """(customers, new) for months 1..60: nobody before start_month; inside each year a constant number of new
    customers so the year ends at its target (the same rule as the base model)."""
    keep, customers, out = 1 - churn, 0.0, []
    for year in range(1, 6):
        months = range((year - 1) * 12 + 1, year * 12 + 1)
        n = sum(1 for m in months if m >= start_month)
        new = max(0.0, (targets[year - 1] - customers * keep ** n) / sum(keep ** k for k in range(n))) if n else 0.0
        for m in months:
            if m >= start_month:
                customers = customers * keep + new
            out.append((customers, new if m >= start_month else 0.0))
    return out


def _open_month(v: dict, region: str) -> int:
    year = {"cdmx": 1, "edomex": v["edomex_start_year"], "jalisco": v["recommended_new_states_year"],
            "nuevoleon": v["recommended_new_states_year"]}[region]
    return int((year - 1) * 12 + 1)


def recommended_targets(v: dict) -> dict[str, list[float]]:
    """Private customers per state and year: the base targets, but no state above `recommended_private_cap` % of its
    private establishments. States are filled in the expansion order (CDMX, Edomex, then Jalisco and Nuevo León)."""
    totals = [v["customers_year1"], *_targets(v["customer_growth_year2_5"])]
    cap = {r: private_count(v, r) * v["recommended_private_cap"] / 100 for r in REGIONS}
    out = {r: [] for r in REGIONS}
    for year, total in enumerate(totals, start=1):
        left = total
        for group in (["cdmx"], ["edomex"], ["jalisco", "nuevoleon"]):
            open_ = [r for r in group if _open_month(v, r) <= year * 12]
            for r in group:
                take = min(cap[r], left / len(open_)) if r in open_ else 0.0
                out[r].append(take)
            left -= sum(out[r][-1] for r in group)
    return out


def simulate_recommended(v: dict) -> list[dict]:
    churn = v["monthly_churn"] / 100
    private = {r: _path(t, churn, _open_month(v, r)) for r, t in recommended_targets(v).items()}
    gov_cap = {r: public_day_centers(v, r) * v["government_cap"] / 100 for r in REGIONS}
    gov = {r: _path([gov_cap[r]] * 5, churn, _open_month(v, r) + int(v["government_sales_cycle_months"])) for r in REGIONS}
    rows, cash = [], 0.0
    for i in range(60):
        month, year = i + 1, i // 12 + 1
        priv = {r: private[r][i][0] for r in REGIONS}
        g = sum(gov[r][i][0] for r in REGIONS)
        customers = sum(priv.values()) + g
        new = sum(private[r][i][1] + gov[r][i][1] for r in REGIONS)
        gov_price = v["plan_government_price"] * (_index(v, year) if v["price_inflation_adjustment"] >= 0.5 else 1.0)
        revenue = sum(priv.values()) * average_revenue(v, year) + g * gov_price
        costs = _costs(v, year, customers, new, v["founder_salary_year1_recommended"])
        cash += revenue - sum(costs.values())
        rows.append({"month": month, "year": year, "customers": customers, "new": new, "government": g,
                     **{f"customers_{r}": priv[r] for r in REGIONS}, **{f"government_{r}": gov[r][i][0] for r in REGIONS},
                     "revenue": revenue, **{f"cost_{k}": c for k, c in costs.items()}, "costs": sum(costs.values()),
                     "profit": revenue - sum(costs.values()), "cash": cash})
    return rows


def scenario_summary(v: dict, rows: list[dict]) -> dict:
    worst = min(rows, key=lambda r: r["cash"])
    last = rows[-1]
    shares = {r: {"customers": last[f"customers_{r}"], "establishments": private_count(v, r),
                  "share_pct": 100 * last[f"customers_{r}"] / private_count(v, r) if private_count(v, r) else None}
              for r in REGIONS}
    public = sum(public_day_centers(v, r) for r in REGIONS)
    return {"investment": {"amount": max(0.0, -worst["cash"]), "month": worst["month"] if worst["cash"] < 0 else None},
            "breakeven_month": _first(rows, lambda r: r["profit"] >= 0), "payback_month": _first(rows, lambda r: r["cash"] >= 0),
            "npv": [{"rate_pct": r, "npv": npv(rows, r)} for r in (v["discount_rate_low"], v["discount_rate_base"], v["discount_rate_high"])],
            "customers_year5": last["customers"], "private_year5": last["customers"] - last["government"],
            "government_year5": last["government"],
            "government_share_pct": 100 * last["government"] / public if public else None, "public_day_centers": public,
            "shares": shares, "revenue_year5": sum(r["revenue"] for r in rows if r["year"] == 5)}


def scenarios(overrides: dict | None = None) -> dict:
    """Base, conservative and recommended side by side; if the recommended NPV at the base rate is still negative,
    which single lever would make it zero (analysis, not a target)."""
    base_o = dict(overrides or {})
    v = inputs(base_o)
    f = v["conservative_customer_factor"] / 100
    totals = [v["customers_year1"], *_targets(v["customer_growth_year2_5"])]
    cons_o = {**base_o, "customers_year1": totals[0] * f, "customer_growth_year2_5": ",".join(str(round(x * f, 4)) for x in totals[1:])}
    out = {"base": scenario_summary(v, simulate(v)), "conservative": scenario_summary(inputs(cons_o), simulate(inputs(cons_o))),
           "recommended": scenario_summary(v, simulate_recommended(v)),
           "recommended_targets": recommended_targets(v), "rate_pct": v["discount_rate_base"]}
    # What the recommended result depends on: the same scenario without each of its two new assumptions
    def rec_npv_with(extra: dict) -> float:
        return npv(simulate_recommended(inputs({**base_o, **extra})), v["discount_rate_base"])
    out["recommended_without"] = {"government": rec_npv_with({"government_cap": 0}),
                                  "founder_cut": rec_npv_with({"founder_salary_year1_recommended": 100}),
                                  "both": rec_npv_with({"government_cap": 0, "founder_salary_year1_recommended": 100})}
    rec_npv = out["recommended"]["npv"][1]["npv"]
    out["recommended_positive"] = rec_npv >= 0
    if rec_npv < 0:
        def rec(extra: dict) -> float:
            return npv(simulate_recommended(inputs({**base_o, **extra})), v["discount_rate_base"])
        out["recommended_missing"] = {
            "plan_professional_price": _bisect(lambda x: rec({"plan_professional_price": x}), 0, 100_000),
            "current_professional_price": v["plan_professional_price"],
            "plan_government_price": _bisect(lambda x: rec({"plan_government_price": x}), 0, 100_000),
            "current_government_price": v["plan_government_price"],
            "cac": _bisect(lambda x: rec({"cac_per_institution": x}), 0, 500_000), "current_cac": v["cac_per_institution"],
            "recommended_private_cap": _bisect(lambda x: rec({"recommended_private_cap": x}), v["recommended_private_cap"], 100),
            "current_private_cap": v["recommended_private_cap"]}
    return out
