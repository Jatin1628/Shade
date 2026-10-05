"""Run:  .venv\\Scripts\\python -m pytest backend -q"""
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.estimator import action_plan
from backend.app.pdf import render_report_pdf, inr

c = TestClient(app)


def test_wards_scored():
    j = c.get("/wards/pune").json()
    assert len(j["features"]) == 41
    ranks = sorted(f["properties"]["priority_rank"] for f in j["features"])
    assert ranks == list(range(1, 42))


def test_ward_detail_and_plan():
    p = c.get("/wards/pune/3").json()["action_plan"]
    assert p["is_estimate"] is True and p["trees_needed"] > 0
    assert p["cost_inr_low"] < p["cost_inr_high"]
    assert p["sources"]["co2"]


def test_scenario_params_change_plan():
    base = c.get("/wards/pune/3").json()["action_plan"]
    hi = c.get("/wards/pune/3?target_pct=35").json()["action_plan"]
    big = c.get("/wards/pune/3?crown_m2=60").json()["action_plan"]
    assert hi["trees_needed"] > base["trees_needed"]
    assert big["trees_needed"] < base["trees_needed"]
    assert c.get("/wards/pune/3?target_pct=99").status_code == 422


def test_no_gap_means_no_trees():
    assert action_plan(10.0, 0.40)["trees_needed"] == 0   # already above target


def test_unknowns_404():
    assert c.get("/wards/pune/999").status_code == 404
    assert c.get("/wards/delhi").status_code == 404


def test_reports_need_auth():
    assert c.get("/reports").status_code == 401
    assert c.get("/reports/abc/pdf").status_code == 401


def test_pdf_renders():
    plan = action_plan(39.685, 0.041)
    rep = {"ward": 3, "wardName": "Vimannagar - Lohegaone", "city": "pune",
           "createdAt": "2026-09-28T15:59:29+00:00",
           "snapshot": {"rank": 1, "priority": 0.85, "lst": 45.99, "canopyPct": 4.1,
                        "vulnerability": 0.27, "vulnerabilitySource": "placeholder_built_frac"},
           "actionPlan": plan}
    pdf = render_report_pdf(rep)
    assert pdf[:4] == b"%PDF" and len(pdf) > 2000
    assert inr(27_647_216) == "Rs 2.76 crore"


def test_vulnerability_uses_census_when_file_present():
    from backend.app import config as C
    ward = c.get("/wards/pune/3").json()
    expected = "census" if C.VULN_FILE.exists() else "placeholder_built_frac"
    assert ward["vulnerability_source"] == expected


# ---- dev-auth mode (lets frontend devs use /reports without the Firebase key) ----
import pytest
from backend.app import reports as R

H = {"Authorization": "Bearer dev-token"}


def test_dev_token_rejected_when_dev_mode_off(monkeypatch):
    monkeypatch.setattr(R, "DEV_AUTH", False)
    # 503 (no Firebase key on this machine) or 401 (key present, token invalid): never 200
    assert c.get("/reports", headers=H).status_code in (401, 503)


def test_dev_mode_roundtrip(monkeypatch):
    monkeypatch.setattr(R, "DEV_AUTH", True)
    R._mem.clear()
    r = c.post("/reports", headers=H, json={"city": "pune", "ward_id": 3, "mode": "citizen"})
    assert r.status_code == 200
    rid = r.json()["id"]
    assert r.json()["snapshot"]["rank"] >= 1
    lst = c.get("/reports", headers=H).json()
    assert [x["id"] for x in lst] == [rid]
    assert c.get(f"/reports/{rid}", headers=H).json()["ward"] == 3
    pdf = c.get(f"/reports/{rid}/pdf", headers=H)
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"
    assert c.get("/reports/nope", headers=H).status_code == 404
    assert c.post("/reports", headers=H, json={"ward_id": 999}).status_code == 404
    assert c.get("/reports").status_code == 401           # still needs a token
    R._mem.clear()
