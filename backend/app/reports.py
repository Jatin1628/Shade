"""Saved-report history (S13/S14). Firebase Auth verifies the caller; Firestore
stores a SNAPSHOT so old reports keep the numbers they had on that date.
Storage is skipped on purpose (needs the paid Blaze plan): the PDF is
re-rendered from the snapshot on download.

Setup: Firebase console -> Project settings -> Service accounts -> generate key.
Save it OUTSIDE git, then set  FIREBASE_KEY_PATH=C:\\path\\to\\key.json

DEV MODE (for frontend developers who do NOT have the Firebase key):
  set  SHADE_DEV_AUTH=1  before starting the server. Then the fixed token
  "dev-token" is accepted and reports are kept in server MEMORY (lost on
  restart, never sent to Firestore). It is OFF unless that variable is set,
  and real Firebase tokens keep working either way. Never switch it on for a
  deployed server: anyone could then log in as "dev-user".
"""
import os
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel
from . import config as C
from .scoring import score_wards
from .estimator import action_plan
from .pdf import render_report_pdf

router = APIRouter(prefix="/reports", tags=["reports"])
_db = None

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


def _uid(authorization: str | None) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    token = authorization[7:]
    if DEV_AUTH and token == DEV_TOKEN:
        return DEV_UID
    _firebase()                      # 503 first if Firebase isn't configured
    from firebase_admin import auth
    try:
        return auth.verify_id_token(token)["uid"]
    except Exception:
        raise HTTPException(401, "Invalid or expired token")


# ---- storage: memory for the dev user, Firestore for everyone else ----------
def _is_dev(uid: str) -> bool:
    return DEV_AUTH and uid == DEV_UID


def _put(uid: str, doc: dict) -> str:
    if _is_dev(uid):
        rid = uuid.uuid4().hex[:20]
        _mem.setdefault(uid, {})[rid] = doc
        return rid
    ref = _firebase().collection("users").document(uid).collection("reports").document()
    ref.set(doc)
    return ref.id


def _get(uid: str, rid: str) -> dict | None:
    if _is_dev(uid):
        return _mem.get(uid, {}).get(rid)
    d = _firebase().collection("users").document(uid).collection("reports").document(rid).get()
    return d.to_dict() if d.exists else None


def _all(uid: str) -> list[tuple[str, dict]]:
    if _is_dev(uid):
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
    rid = _put(uid, doc)
    return {"id": rid, **{k: v for k, v in doc.items() if k != "createdAt"}}


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
