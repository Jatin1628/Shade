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


# ---- real Firebase-token verification (signed locally; no network needed) ----
import datetime
import json
import time

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from google.auth import crypt, jwt as g_jwt
from google.auth.exceptions import TransportError

PID = R.PROJECT_ID


@pytest.fixture(scope="module")
def signing():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "test")])
    cert = (x509.CertificateBuilder().subject_name(name).issuer_name(name)
            .public_key(key.public_key()).serial_number(1)
            .not_valid_before(datetime.datetime(2020, 1, 1))
            .not_valid_after(datetime.datetime(2099, 1, 1))
            .sign(key, hashes.SHA256()))
    priv = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                             serialization.NoEncryption())
    return crypt.RSASigner.from_string(priv, key_id="k1"), cert.public_bytes(serialization.Encoding.PEM).decode()


@pytest.fixture
def firebase_login(monkeypatch, signing):
    """Pretend to be Google: serve our test public key, and never touch Firestore."""
    signer, cert_pem = signing

    class Resp:
        status = 200
        data = json.dumps({"k1": cert_pem}).encode()

    calls = []
    monkeypatch.setattr(R, "_http", lambda url, method="GET", **kw: (calls.append(url), Resp())[1])
    monkeypatch.setattr(R, "_firestore_ready", lambda: False)
    monkeypatch.setattr(R, "DEV_AUTH", False)
    R._mem.clear()

    def token(sub="user-1", aud=PID, iss=None, exp_in=3600):
        now = int(time.time())
        claims = {"iss": iss or f"https://securetoken.google.com/{PID}", "aud": aud,
                  "sub": sub, "iat": now - 5, "exp": now + exp_in, "auth_time": now - 5}
        return {"Authorization": "Bearer " + g_jwt.encode(signer, claims).decode()}

    token.calls = calls
    yield token
    R._mem.clear()


def test_valid_firebase_token_saves_and_lists(firebase_login):
    h = firebase_login("alice")
    r = c.post("/reports", headers=h, json={"city": "pune", "ward_id": 3})
    assert r.status_code == 200 and r.json()["storage"] == "memory"
    assert [x["id"] for x in c.get("/reports", headers=h).json()] == [r.json()["id"]]


def test_users_cannot_see_each_others_reports(firebase_login):
    rid = c.post("/reports", headers=firebase_login("alice"), json={"ward_id": 3}).json()["id"]
    assert c.get("/reports", headers=firebase_login("bob")).json() == []
    assert c.get(f"/reports/{rid}", headers=firebase_login("bob")).status_code == 404


@pytest.mark.parametrize("kwargs", [
    {"aud": "some-other-project"},
    {"iss": "https://securetoken.google.com/some-other-project"},
    {"exp_in": -3600},
    {"sub": ""},
])
def test_bad_firebase_tokens_rejected(firebase_login, kwargs):
    assert c.get("/reports", headers=firebase_login(**kwargs)).status_code == 401


def test_garbage_token_rejected_without_network(firebase_login):
    assert c.get("/reports", headers={"Authorization": "Bearer abc"}).status_code == 401
    assert firebase_login.calls == []                     # no call to Google for a non-JWT


def test_google_unreachable_gives_503(monkeypatch, firebase_login):
    def boom(url, method="GET", **kw):
        raise TransportError("offline")
    monkeypatch.setattr(R, "_http", boom)
    assert c.get("/reports", headers=firebase_login()).status_code == 503


def test_forged_signature_rejected(firebase_login):
    """Token signed with someone else's key (same key id) must NOT be accepted."""
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    priv = other.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                               serialization.NoEncryption())
    forger = crypt.RSASigner.from_string(priv, key_id="k1")
    now = int(time.time())
    forged = g_jwt.encode(forger, {"iss": f"https://securetoken.google.com/{PID}", "aud": PID,
                                   "sub": "admin", "iat": now - 5, "exp": now + 3600}).decode()
    assert c.get("/reports", headers={"Authorization": f"Bearer {forged}"}).status_code == 401
