"""Priority score: hot + few trees + vulnerable = high priority."""
import json
import pandas as pd
from . import config as C


def _minmax(s: pd.Series) -> pd.Series:
    rng = s.max() - s.min()
    return (s - s.min()) / rng if rng else s * 0.0


def load_wards(city: str) -> dict:
    """Return the raw GeoJSON FeatureCollection for a city."""
    with open(C.CITIES[city]["wards_file"], encoding="utf-8") as f:
        return json.load(f)


def score_wards(city: str) -> tuple[dict, pd.DataFrame]:
    """Score every ward. Returns (geojson with scored properties, table)."""
    gj = load_wards(city)
    df = pd.DataFrame([f["properties"] for f in gj["features"]])

    # Person 2's naive NDVI baseline, passed through for comparison
    ndvi_path = C.DATA / "wards_ndvi.csv"
    if ndvi_path.exists():
        df = df.merge(pd.read_csv(ndvi_path)[["ward_id", "ndvi_s2_mean", "green_pct"]],
                      on="ward_id", how="left")

    heat = df[C.HEAT_COLUMN].fillna(df["lst_mean"])
    canopy_deficit = 1 - df[C.CANOPY_COLUMN]

    if C.VULN_FILE.exists():
        v = pd.read_csv(C.VULN_FILE)[["ward_id", "vulnerability"]]
        df = df.merge(v, on="ward_id", how="left")
        vuln, vuln_src = df["vulnerability"], "census"
    else:  # PLACEHOLDER until real census data is found
        vuln, vuln_src = df["built_frac_wc"], "placeholder_built_frac"

    df["heat_n"] = _minmax(heat)
    df["canopy_deficit_n"] = _minmax(canopy_deficit)
    df["vulnerability_n"] = _minmax(vuln)
    df["vulnerability_source"] = vuln_src
    df["priority_score"] = (C.W_HEAT * df["heat_n"]
                            + C.W_CANOPY * df["canopy_deficit_n"]
                            + C.W_VULN * df["vulnerability_n"])
    df["priority_rank"] = df["priority_score"].rank(ascending=False, method="first").astype(int)

    by_id = df.set_index("ward_id").to_dict("index")
    for f in gj["features"]:
        f["properties"] = {"ward_id": f["properties"]["ward_id"],
                           **by_id[f["properties"]["ward_id"]]}
    return gj, df
