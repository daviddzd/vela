"""Business model (docs/spec/08): the base case reproduces the spec's numbers, every input comes from
assumptions.csv, the page can change only the editable assumptions, and /negocio is for dirección only."""
from app.services import business_model as bm
from tests.conftest import login


def test_base_case_matches_the_spec():
    m = bm.model()
    assert round(m["average_revenue_year1"]) == 5500                  # 40/45/15 % of 2,500 / 6,000 / 12,000
    assert round(m["fixed_costs_year1"]) == 98461                     # 4 x 17,678 x 1.35 + 3,000
    assert m["breakeven_institutions_static"] == 18
    assert [round(y["customers_end"]) for y in m["years"]] == [5, 15, 30, 50, 75]   # targets reached with churn
    assert [n["rate_pct"] for n in m["npv"]] == [15, 25, 35]
    npvs = [n["npv"] for n in m["npv"]]
    assert npvs[0] > npvs[1] > npvs[2]                                 # a higher discount rate, a lower NPV


def test_every_input_has_a_source_or_is_labelled_assumption():
    for key, row in bm.assumptions().items():
        assert row["type"] in ("real", "assumption"), key
        if row["type"] == "real":
            assert row["source"] and row["url"].startswith("https://"), key
        else:                                    # an assumption says who assumed it (or what it is based on)
            assert row["source"], key


def test_overrides_recompute_and_only_editable_keys_count():
    base = bm.model()
    cheaper = bm.model({"plan_professional_price": 3000})
    assert cheaper["average_revenue_year1"] < base["average_revenue_year1"]
    assert bm.model({"founders": 1})["fixed_costs_year1"] == base["fixed_costs_year1"]   # not editable: ignored
    assert bm.model({"monthly_churn": 999})["inputs"]["monthly_churn"] == 20             # clamped to its range


def test_pessimistic_case_without_price_adjustment_is_worse():
    base, pessimistic = bm.model(), bm.model({"price_inflation_adjustment": 0})
    assert pessimistic["years"][4]["revenue"] < base["years"][4]["revenue"]
    assert pessimistic["npv"][1]["npv"] < base["npv"][1]["npv"]


def test_costs_that_grow_with_customers():
    m = bm.model()
    year1, year5 = m["years"][0], m["years"][4]
    assert year1["cost_hosting"] == 0 and year5["cost_hosting"] > 0               # production hosting from year 2
    assert year1["cost_support"] == 0 and year5["cost_support"] > 0               # 1 person per 25 institutions
    assert year5["cost_acquisition"] > year1["cost_acquisition"]


def test_business_page_is_for_direction_with_real_usage(tx_client):
    login(tx_client, "coordinacion.a@ejemplo.test")
    assert tx_client.get("/api/business").status_code == 403
    login(tx_client, "owner@ejemplo.test")
    d = tx_client.get("/api/business").json()
    u = d["usage"]
    assert u["totals"]["coordinated"] == u["totals"]["auto"] + u["totals"]["manual"] + u["totals"]["timeout"]
    assert u["mrr"] == sum(i["price"] for i in u["institutions"] if i["active"])
    r = tx_client.post("/api/business/model", json={"values": {"monthly_churn": 3}}).json()
    assert r["inputs"]["monthly_churn"] == 3 and len(r["months"]) == 60


def test_investment_is_the_deepest_cumulative_cash():
    m = bm.model()
    rows = bm.simulate(bm.inputs())
    worst = min(rows, key=lambda r: r["cash"])
    assert round(m["investment"]["amount"]) == round(-worst["cash"]) and m["investment"]["month"] == worst["month"]


def test_unit_economics_formulas():
    u = bm.model()["unit"]
    assert abs(u["ltv"] - u["margin_month"] / 0.015) < 1e-6                     # margin x 1 / churn
    assert abs(u["ltv_cac"] - u["ltv"] / u["cac"]) < 1e-9
    assert abs(u["cac_payback_months"] - u["cac"] / u["margin_month"]) < 1e-9


def test_each_lever_found_makes_the_npv_zero():
    w = bm.what_for_npv_zero()
    rate = w["rate_pct"]
    targets = bm.inputs()["customer_growth_year2_5"].split(",")
    for extra in ({"plan_professional_price": w["plan_professional_price"]}, {"cac_per_institution": w["cac"]},
                  {"customer_growth_year2_5": ",".join([*targets[:3], str(w["customers_year5"])])}):
        assert abs(bm.npv(bm.simulate(bm.inputs(extra)), rate)) < 50              # pesos: zero within rounding


def test_market_share_uses_denue_and_shows_the_conservative_case_when_too_high(tx_client):
    m = bm.model()
    mk = m["market"]
    assert mk["cdmx"]["target_establishments"] == 88 + 22 + 7                       # private residences, day centers, home nursing
    assert abs(mk["cdmx"]["customers_year5"] + mk["edomex"]["customers_year5"] - m["years"][4]["customers_end"]) < 1e-6
    login(tx_client, "owner@ejemplo.test")
    d = tx_client.get("/api/business").json()["model"]
    assert d["market"]["too_high"] is True and d["conservative"]["factor_pct"] == 50
    assert round(d["conservative"]["customers"][4]) == round(m["years"][4]["customers_end"] / 2)
