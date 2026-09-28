"""Saved-report history (S13/S14). Firebase Auth verifies the caller; Firestore
stores a SNAPSHOT so old reports keep the numbers they had on that date.
Storage is skipped on purpose (needs the paid Blaze plan): the PDF is
re-rendered from the snapshot on download.

Setup: Firebase console -> Project settings -> Service accounts -> generate key.
Save it OUTSIDE git, then set  FIREBASE_KEY_PATH=C:\\path\\to\\key.json
"""
import os
from datetime import datetime, timezone
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from . import config as C
from .scoring import score_wards
from .estimator import action_plan

router = APIRouter(prefix="/reports", tags=["reports"])
_db = None


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
    _firebase()                      # 503 first if Firebase isn't configured
    from firebase_admin import auth
    try:
        return auth.verify_id_token(authorization[7:])["uid"]
    except Exception:
        raise HTTPException(401, "Invalid or expired token")


class ReportIn(BaseModel):
    city: str = "pune"
    ward_id: int
    mode: str = "citizen"          # 'citizen' | 'planner'


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
        "actionPlan": action_plan(float(r["area_km2"]), float(r[C.CANOPY_COLUMN])),
    }
    ref = _firebase().collection("users").document(uid).collection("reports").document()
    ref.set(doc)
    return {"id": ref.id, **{k: v for k, v in doc.items() if k != "createdAt"}}


@router.get("")
def list_reports(authorization: str | None = Header(None)):
    uid = _uid(authorization)
    q = (_firebase().collection("users").document(uid).collection("reports")
         .order_by("createdAt", direction="DESCENDING").limit(50))
    return [{"id": d.id, **d.to_dict(), "createdAt": d.to_dict()["createdAt"].isoformat()}
            for d in q.stream()]


@router.get("/{report_id}")
def get_report(report_id: str, authorization: str | None = Header(None)):
    uid = _uid(authorization)
    d = _firebase().collection("users").document(uid).collection("reports").document(report_id).get()
    if not d.exists:
        raise HTTPException(404, "Report not found")
    out = d.to_dict(); out["createdAt"] = out["createdAt"].isoformat()
    return {"id": d.id, **out}
