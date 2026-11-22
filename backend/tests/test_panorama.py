"""Panorama-AM API: scoped by RLS, owner-only institution filter, anonymous population, sources."""
from pathlib import Path

from sqlalchemy import text

from app.core.db import tenant_session
from app.routers import panorama
from tests.conftest import login


def test_coordinator_metrics_are_only_from_own_institution(client):
    login(client, "coordinacion.a@ejemplo.test")
    a = client.get("/api/panorama/operation").json()
    forced = client.get("/api/panorama/operation", params={"institution": "INS-B"}).json()
    assert forced == a                                              # parameter ignored for a coordinator
    assert {s["institution_id"] for s in a["staff_load"]} == {"INS-A"}
    assert [i["institution_id"] for i in client.get("/api/panorama/institutions").json()] == ["INS-A"]


def test_owner_can_filter_by_institution(client):
    login(client, "owner@ejemplo.test")
    all_ = client.get("/api/panorama/operation").json()
    only_b = client.get("/api/panorama/operation", params={"institution": "INS-B"}).json()
    assert {s["institution_id"] for s in only_b["staff_load"]} == {"INS-B"}
    assert len({s["institution_id"] for s in all_["staff_load"]}) == 5
    assert len(client.get("/api/panorama/institutions").json()) == 5


def test_family_and_caregiver_cannot_open_panorama(client):
    for email in ("fam-0001@ejemplo.test", "cui-003@ejemplo.test"):
        login(client, email)
        assert client.get("/api/panorama/population").status_code == 403


def test_punctuality_and_unattended_match_direct_sql(client):
    login(client, "coordinacion.a@ejemplo.test")
    api = client.get("/api/panorama/operation", params={"from": "2026-10-21", "to": "2026-11-19"}).json()
    with tenant_session("INS-A") as s:
        on_time, arrived, unattended, decided = s.execute(text("""
            SELECT count(*) FILTER (WHERE a.arrived_at <= r.scheduled_for + interval '15 minutes'),
                   count(*) FILTER (WHERE a.arrived_at IS NOT NULL),
                   count(*) FILTER (WHERE r.status = 'unattended'),
                   count(*) FILTER (WHERE r.status IN ('closed','completed','unattended'))
            FROM service_requests r LEFT JOIN assignments a ON a.request_id = r.request_id AND a.status = 'active'
            WHERE (r.scheduled_for AT TIME ZONE 'America/Mexico_City')::date
                  BETWEEN '2026-10-21' AND '2026-11-19'""")).one()
    assert api["on_time_pct"] == round(100 * on_time / arrived, 1)
    assert api["unattended_pct"] == round(100 * unattended / decided, 1)


def test_population_is_aggregated_and_anonymous(client):
    login(client, "coordinacion.a@ejemplo.test")
    body = client.get("/api/panorama/population").json()
    assert body["city"]["persons"] == 20000 and len(body["districts"]) == 16
    text_dump = str(body)
    for forbidden in ("person_id", "first_name", "paternal_surname", "birth_date", "PS-"):
        assert forbidden not in text_dump


def test_prevalence_references_have_source_and_flag_the_adjustment(client):
    login(client, "coordinacion.a@ejemplo.test")
    conditions = {c["condition"]: c for c in client.get("/api/panorama/population").json()["conditions"]}
    assert conditions["hypertension"]["reference"]["survey"] == "ENSANUT 2018-19"
    arthritis = conditions["arthritis"]["reference"]
    assert arthritis["survey"] == "ENASEM 2024" and arthritis["adjusted"] is True
    assert arthritis["reference_pct"] == round(18.0 * 42.4 / 74.5, 1)         # 10.2
    assert all(c["reference"] is None or c["reference"]["url"].startswith("https://") for c in conditions.values())


def test_boundaries_and_fallback_to_points(client, monkeypatch, tmp_path):
    login(client, "coordinacion.a@ejemplo.test")
    official = client.get("/api/panorama/boundaries").json()
    assert official["available"] and len(official["geojson"]["features"]) == 16
    assert set(official["geojson"]["features"][0]["properties"]) == {"district_id", "name"}
    # Without the file (fresh clone before downloading): district centroids instead.
    panorama._boundaries.cache_clear()
    monkeypatch.setattr(panorama, "reference_dir", lambda: Path(tmp_path))
    fallback = client.get("/api/panorama/boundaries").json()
    panorama._boundaries.cache_clear()
    assert fallback["available"] is False and len(fallback["points"]) == 16


def test_air_thresholds_come_from_the_yaml(client):
    login(client, "coordinacion.a@ejemplo.test")
    air = client.get("/api/panorama/air", params={"station": "SAC"}).json()
    assert air["thresholds"] == {"o3_ppb_1h": 155, "pm25_ugm3_24h": 97.5, "watch_fraction": 0.85}
    assert air["station"] == "SAC" and len(air["series"]) == 7 * 24


def test_traffic_peak(client):
    login(client, "coordinacion.a@ejemplo.test")
    t = client.get("/api/panorama/traffic").json()
    assert len(t["cells"]) == 48 and t["peak"]["hour"] == 18 and t["peak"]["day_type"] == "weekday"


def test_baseline_and_with_vela_are_separated(client):
    login(client, "coordinacion.a@ejemplo.test")
    op = client.get("/api/panorama/operation", params={"from": "2026-10-21", "to": "2026-11-19"}).json()
    assert set(op["periods"]) == {"baseline", "vela"}
    assert op["periods"]["baseline"]["on_time_pct"] == op["on_time_pct"]          # seed history only
    assert {d["period"] for d in op["daily"]} == {"baseline"}
    with tenant_session("*") as s:
        assert s.scalar(text("SELECT count(*) FROM service_requests WHERE is_baseline")) == 2864


def test_broad_multimorbidity_and_its_ensanut_reference(client):
    login(client, "coordinacion.a@ejemplo.test")
    pop = client.get("/api/panorama/population").json()
    assert pop["city"]["multimorbidity_broad_pct"] == 57.9                      # docs/spec/09
    ref = pop["indicator_reference"]["multimorbidity_broad_pct"]
    assert ref["reference_pct"] == 55.6 and "7 condiciones" in ref["note"]


def test_staff_hours_include_estimated_travel(client):
    """avg hours per worked day = on-site time + dispatcher travel estimate, so it exceeds on-site time alone."""
    login(client, "coordinacion.a@ejemplo.test")
    op = client.get("/api/panorama/operation", params={"from": "2026-10-21", "to": "2026-11-19"}).json()
    laura = next(s for s in op["staff_load"] if s["caregiver_id"] == "CUI-001")
    with tenant_session("INS-A") as s:
        on_site = s.scalar(text("""SELECT sum(extract(epoch FROM finished_at - arrived_at)) / 3600
                                     / count(DISTINCT (arrived_at AT TIME ZONE 'America/Mexico_City')::date)
                                   FROM assignments WHERE caregiver_id = 'CUI-001' AND finished_at IS NOT NULL"""))
    assert laura["avg_hours_per_day"] > round(float(on_site), 1)
