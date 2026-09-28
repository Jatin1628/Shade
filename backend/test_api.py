"""Run:  .venv\\Scripts\\python -m pytest backend -q"""
from fastapi.testclient import TestClient
from backend.app.main import app
c = TestClient(app)

def test_wards_scored():
    j = c.get("/wards/pune").json()
    assert len(j["features"]) == 41
    ranks = sorted(f["properties"]["priority_rank"] for f in j["features"])
    assert ranks == list(range(1, 42))

def test_ward_detail_and_plan():
    d = c.get("/wards/pune/3").json()
    assert d["action_plan"]["is_estimate"] is True and d["action_plan"]["trees_needed"] > 0

def test_unknowns_404():
    assert c.get("/wards/pune/999").status_code == 404
    assert c.get("/wards/delhi").status_code == 404

def test_reports_need_auth():
    assert c.get("/reports").status_code == 401
