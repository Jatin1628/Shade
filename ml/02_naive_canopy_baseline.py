"""
Naive NDVI canopy baseline (Person 2 — ML pipeline)

Usage:
    .venv\\Scripts\\python ml\\02_naive_canopy_baseline.py
    .venv\\Scripts\\python ml\\02_naive_canopy_baseline.py --year 2026 --threshold 0.4

Thresholds the Sentinel-2 NDVI raster (NDVI > threshold = "green"),
zonal-stats it against data/wards.geojson, and writes the naive
per-ward canopy baseline to data/wards_ndvi.csv.

This is the baseline the January U-Net must beat — it can't tell a
lawn or farm plot from a real tree.
"""
import sys
import argparse
import numpy as np
import pandas as pd
import geopandas as gpd
import rasterio
from rasterstats import zonal_stats

from config import WARDS, RASTER, METRIC_CRS, DEFAULT_YEAR, DATA

sys.stdout.reconfigure(encoding="utf-8")


def main(year: int, threshold: float):
    ndvi_path = RASTER / f"ndvi_s2_{year}.tif"
    if not ndvi_path.exists():
        print(f"ERROR: {ndvi_path} not found. Did you download it from Google Drive?")
        return

    print(f"Loading wards from {WARDS}")
    wards = gpd.read_file(WARDS)

    print(f"Loading NDVI raster: {ndvi_path}")
    with rasterio.open(ndvi_path) as src:
        raster_crs = src.crs

    # Reproject wards to match the raster's CRS for accurate zonal stats
    wards_reproj = wards.to_crs(raster_crs)

    print(f"Computing mean NDVI per ward...")
    stats = zonal_stats(
        wards_reproj,
        str(ndvi_path),
        stats=["mean", "count"],
        nodata=np.nan,
    )

    wards["ndvi_s2_mean"] = [s["mean"] for s in stats]

    # Naive baseline: threshold NDVI, get % of ward pixels above it
    print(f"Computing naive canopy baseline (NDVI > {threshold})...")
    green_stats = zonal_stats(
        wards_reproj,
        str(ndvi_path),
        stats=["count"],
        add_stats={
            "green_count": lambda x: np.sum(x.compressed() > threshold) if hasattr(x, "compressed") else np.sum(x[~np.isnan(x)] > threshold)
        },
        nodata=np.nan,
    )

    green_pct = []
    for gs in green_stats:
        total = gs.get("count", 0)
        green = gs.get("green_count", 0)
        pct = (green / total * 100) if total > 0 else np.nan
        green_pct.append(round(pct, 2))

    wards["green_pct"] = green_pct

    out_cols = ["ward_id", "ward_name", "ndvi_s2_mean", "green_pct"]
    out_df = wards[out_cols].copy()
    out_df["ndvi_s2_mean"] = out_df["ndvi_s2_mean"].round(3)

    out_path = DATA / "wards_ndvi.csv"
    out_df.to_csv(out_path, index=False)
    print(f"\nSaved: {out_path}")
    print(f"\nPreview:")
    print(out_df.sort_values("green_pct").to_string(index=False))

    # Quick sanity check against Person 1's existing tree_frac_wc
    if "tree_frac_wc" in wards.columns:
        wards["tree_frac_wc_pct"] = wards["tree_frac_wc"] * 100
        corr = wards["green_pct"].corr(wards["tree_frac_wc_pct"])
        print(f"\nCorrelation with existing tree_frac_wc (WorldCover): r = {corr:.3f}")
        print("(Expect a positive but imperfect correlation — WorldCover is a "
              "different source/year, and this NDVI baseline over-counts grass/crops.)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    parser.add_argument("--threshold", type=float, default=0.4)
    args = parser.parse_args()
    main(args.year, args.threshold)