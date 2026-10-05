"""Saved-report history (S13/S14).

LOGIN CHECK (any laptop): the frontend signs in with Firebase and sends the ID
token as  Authorization: Bearer <token>.  We verify it with Google's PUBLIC
signing keys (no secret needed), checking signature, expiry, audience (our
project id) and issuer. So real Firebase logins work on every machine.

STORAGE: if FIREBASE_KEY_PATH points to a service-account key, reports go to
Firestore (persistent). Otherwise they are kept in server MEMORY (lost on
restart) so teammates can build and demo without the secret key. The POST
response says which one was used ("storage").

DEV MODE (offline only): SHADE_DEV_AUTH=1 also accepts the fixed token
"dev-token" (user "dev-user", memory storage). Never enable on a shared server.

Firestore setup: Firebase console -> Project settings -> Service accounts ->
generate key, keep it OUTSIDE git, set  FIREBASE_KEY_PATH=C:\\path\\to\\key.json
"""
import os
import uuid

import cachecontrol
import requests
from google.auth.exceptions import TransportError
from google.auth.transport import requests as g_requests
from google.oauth2 import id_token as g_id_token
from datetime import datetime, timezone
from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel
from . import config as C
from .scoring import score_wards
from .estimator import action_plan
from .pdf import render_report_pdf

router = APIRouter(prefix="/reports", tags=["reports"])
_db = None

PROJECT_ID = os.environ.get("FIREBASE_PROJECT_ID", "shade-capstone")
_session = cachecontrol.CacheControl(requests.Session())   # caches Google's public keys


def _http(url, method="GET", **kw):
    """HTTP transport for fetching Google's public keys (5 s timeout, cached)."""
    kw.setdefault("timeout", 5)
    return g_requests.Request(session=_session)(url, method=method, **kw)


DEV_AUTH = os.environ.get("SHADE_DEV_AUTH") == "1"
DEV_TOKEN, DEV_UID = "dev-token", "dev-user"
_mem: dict[str, dict[str, dict]] = {}          # uid -> {report_id: doc}   (dev mode only)
if DEV_AUTH:
    print("WARNING: SHADE_DEV_AUTH=1 -> fixed dev token accepted, reports kept in memory. Local use only.")


def _firebase():
    """Lazy init so the rest of the API runs with no Firebase setup."""
    global _db
    if _db is None:
        key = os.environ.get("FIREBASE_KEY_PATH")
        if not key or not os.path.exists(key):
            raise HTTPException(503, "Firebase not configured (set FIREBASE_KEY_PATH)")
        import firebase_admin
        from firebase_admin import credentials, firestore
        if not firebase_admin._apps:
            firebase_admin.initialize_app(credentials.Certificate(key))
        _db = firestore.client()
    return _db


def _verify_firebase_token(token: str) -> str:
    """Return the Firebase user id (uid) for a valid ID token, else raise 401/503."""
    bad = HTTPException(401, "Invalid or expired token")
    if token.count(".") != 2:                       # not a JWT: reject without any network call
        raise bad
    try:
        claims = g_id_token.verify_firebase_token(
            token, _http, audience=PROJECT_ID, clock_skew_in_seconds=10)
    except TransportError:
        raise HTTPException(503, "Could not reach Google to verify the login token")
    except Exception as e:                          # bad signature, expired, wrong audience...
        print("Token verification failed:", e)
        raise bad
    if claims.get("iss") != f"https://securetoken.google.com/{PROJECT_ID}" or not claims.get("sub"):
        print("Token verification failed: wrong issuer or missing subject")
        raise bad
    return claims["sub"]


def _uid(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization[7:].strip()
    if DEV_AUTH and token == DEV_TOKEN:
        return DEV_UID
    return _verify_firebase_token(token)


# ---- storage: memory for the dev user, Firestore for everyone else ----------
def _firestore_ready() -> bool:
    key = os.environ.get("FIREBASE_KEY_PATH")
    return bool(key) and os.path.exists(key)


def _use_memory(uid: str) -> bool:
    return (DEV_AUTH and uid == DEV_UID) or not _firestore_ready()


def _put(uid: str, doc: dict) -> str:
    if _use_memory(uid):
        rid = uuid.uuid4().hex[:20]
        _mem.setdefault(uid, {})[rid] = doc
        return rid
    ref = _firebase().collection("users").document(uid).collection("reports").document()
    ref.set(doc)
    return ref.id


def _get(uid: str, rid: str) -> dict | None:
    if _use_memory(uid):
        return _mem.get(uid, {}).get(rid)
    d = _firebase().collection("users").document(uid).collection("reports").document(rid).get()
    return d.to_dict() if d.exists else None


def _all(uid: str) -> list[tuple[str, dict]]:
    if _use_memory(uid):
        items = list(_mem.get(uid, {}).items())
    else:
        q = (_firebase().collection("users").document(uid).collection("reports")
             .order_by("createdAt", direction="DESCENDING").limit(50))
        items = [(d.id, d.to_dict()) for d in q.stream()]
    return sorted(items, key=lambda kv: kv[1]["createdAt"], reverse=True)[:50]


def _out(rid: str, doc: dict) -> dict:
    return {"id": rid, **doc, "createdAt": doc["createdAt"].isoformat()}


class ReportIn(BaseModel):
    city: str = "pune"
    ward_id: int
    mode: str = "citizen"          # 'citizen' | 'planner'
    target_pct: float | None = None   # scenario: target canopy %
    crown_m2: float | None = None     # scenario: canopy per tree


@router.post("")
def create_report(body: ReportIn, authorization: str | None = Header(None)):
    uid = _uid(authorization)
    if body.city not in C.CITIES:
        raise HTTPException(404, "Unknown city")
    _, df = score_wards(body.city)
    row = df[df["ward_id"] == body.ward_id]
    if row.empty:
        raise HTTPException(404, "No such ward")
    r = row.iloc[0]
    doc = {                          # numbers computed server-side, never trusted from client
        "city": body.city, "ward": body.ward_id, "wardName": r["ward_name"],
        "mode": body.mode, "createdAt": datetime.now(timezone.utc),
        "snapshot": {"lst": float(r[C.HEAT_COLUMN]), "canopyPct": float(r[C.CANOPY_COLUMN]) * 100,
                     "priority": float(r["priority_score"]), "rank": int(r["priority_rank"]),
                     "vulnerability": float(r["vulnerability_n"]),
                     "vulnerabilitySource": r["vulnerability_source"]},
        "actionPlan": action_plan(float(r["area_km2"]), float(r[C.CANOPY_COLUMN]),
                                  None if body.target_pct is None else body.target_pct / 100,
                                  body.crown_m2),
    }
    mem = _use_memory(uid)
    rid = _put(uid, doc)
    return {"id": rid, "storage": "memory" if mem else "firestore",
            **{k: v for k, v in doc.items() if k != "createdAt"}}


@router.get("")
def list_reports(authorization: str | None = Header(None)):
    uid = _uid(authorization)
    return [_out(rid, doc) for rid, doc in _all(uid)]


@router.get("/{report_id}")
def get_report(report_id: str, authorization: str | None = Header(None)):
    uid = _uid(authorization)
    doc = _get(uid, report_id)
    if doc is None:
        raise HTTPException(404, "Report not found")
    return _out(report_id, doc)


@router.get("/{report_id}/pdf")
def report_pdf(report_id: str, authorization: str | None = Header(None)):
    """Re-render the PDF from the saved snapshot (no Storage needed)."""
    uid = _uid(authorization)
    doc = _get(uid, report_id)
    if doc is None:
        raise HTTPException(404, "Report not found")
    rep = {**doc, "createdAt": doc["createdAt"].isoformat()}
    return Response(render_report_pdf(rep), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="shade_ward{rep["ward"]}_{report_id[:6]}.pdf"'})
