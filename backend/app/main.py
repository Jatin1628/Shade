"""Shade API. Run from the repo root:
    .venv\\Scripts\\python -m uvicorn backend.app.main:app --reload
Docs UI: http://127.0.0.1:8000/docs
"""
import json
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from . import config as C
from .scoring import score_wards
from .estimator import action_plan
from .reports import router as reports_router

app = FastAPI(title="Shade API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"],  # tighten before deploy
                   allow_methods=["*"], allow_headers=["*"])


app.include_router(reports_router)


def _city(city: str) -> str:
    if city not in C.CITIES:
        raise HTTPException(404, f"Unknown city '{city}'")
    return city


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/cities")
def cities():
    return [{"id": k, "name": v["name"]} for k, v in C.CITIES.items()]


@app.get("/wards/{city}")
def wards(city: str):
    """GeoJSON FeatureCollection with scored properties (map-ready)."""
    gj, _ = score_wards(_city(city))
    return gj


@app.get("/wards/{city}/top")
def top_wards(city: str, n: int = 10):
    """Most urgent wards, no geometry (sidebar list). Defined before {ward_id}."""
    _, df = score_wards(_city(city))
    cols = ["ward_id", "ward_name", "priority_rank", "priority_score",
            "lst_builtup_mean", "tree_frac_wc"]
    return df.sort_values("priority_rank").head(n)[cols].to_dict("records")


@app.get("/wards/{city}/{ward_id}")
def ward_detail(city: str, ward_id: int,
                target_pct: float | None = Query(None, ge=5, le=60,
                                                 description="Scenario: target canopy %"),
                crown_m2: float | None = Query(None, ge=5, le=150,
                                               description="Scenario: canopy per tree, m2")):
    gj, df = score_wards(_city(city))
    row = df[df["ward_id"] == ward_id]
    if row.empty:
        raise HTTPException(404, f"No ward {ward_id}")
    r = row.iloc[0].to_dict()
    return {**r, "action_plan": action_plan(
        r["area_km2"], r[C.CANOPY_COLUMN],
        None if target_pct is None else target_pct / 100, crown_m2),
            "score_weights": {"heat": C.W_HEAT, "canopy": C.W_CANOPY,
                              "vulnerability": C.W_VULN}}


@app.get("/datacentres/{city}")
def datacentres(city: str):
    """Serves Person 1's data-centre outputs exactly as measured."""
    _city(city)
    paths = {"sites": C.DATA / "datacentres.geojson",
             "rings": C.DATA / "datacentre_rings.geojson"}
    csv = C.DATA / "datacentre_rings.csv"
    if not all(p.exists() for p in paths.values()) or not csv.exists():
        raise HTTPException(404, "Data-centre files not found in data/")
    out = {k: json.load(open(p, encoding="utf-8")) for k, p in paths.items()}
    out["table"] = pd.read_csv(csv).to_dict("records")
    return out
