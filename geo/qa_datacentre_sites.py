"""QA: Sentinel-2 true-colour chips of each located data centre, hot season 2022 vs 2026.

Checks that each point sits on a large finished building during the LST season,
and shows which sites were still construction ground. The circle marks 500 m,
the first analysis ring.

Usage:  python geo/qa_datacentre_sites.py
Output: data/qa/datacentre_sites_s2.png
"""
import io
import sys

import ee
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import requests
from matplotlib.patches import Circle

from config import HOT_SEASON, METRIC_CRS, QA, RAW

YEARS = (2022, 2026)
HALF_WIDTH_M = 700
PIXELS = 280


def s2_season(year, region):
    start = f"{year}-{HOT_SEASON[0]}"
    end = ee.Date(f"{year}-{HOT_SEASON[1]}").advance(1, "day")
    return (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(region)
        .filterDate(start, end)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 10))
        .median()
    )


def chip(year, lon, lat):
    region = ee.Geometry.Point(lon, lat).buffer(HALF_WIDTH_M).bounds()
    url = s2_season(year, region).getThumbURL({
        "region": region, "crs": METRIC_CRS, "dimensions": PIXELS, "format": "png",
        "bands": ["B4", "B3", "B2"], "min": 200, "max": 2800, "gamma": 1.2,
    })
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    return plt.imread(io.BytesIO(resp.content), format="png")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ee.Initialize()
    sites = pd.read_csv(RAW / "datacentres_pune.csv").dropna(subset=["lat", "lon"]).reset_index(drop=True)

    fig, axes = plt.subplots(len(YEARS), len(sites), figsize=(2.3 * len(sites), 2.5 * len(YEARS)))
    for col, site in sites.iterrows():
        for row, year in enumerate(YEARS):
            ax = axes[row, col]
            ax.imshow(chip(year, site.lon, site.lat), extent=(-HALF_WIDTH_M, HALF_WIDTH_M, -HALF_WIDTH_M, HALF_WIDTH_M))
            ax.add_patch(Circle((0, 0), 500, fill=False, color="white", linewidth=0.8, alpha=0.8))
            ax.plot(0, 0, marker="o", markersize=5, markerfacecolor="none", markeredgecolor="#e34948", markeredgewidth=1.5)
            ax.set_xticks([])
            ax.set_yticks([])
            if row == 0:
                ax.set_title(site.dc_id, fontsize=8)
            if col == 0:
                ax.set_ylabel(f"Mar–May {year}", fontsize=9)
        print(f"{site.dc_id}: done")
    fig.suptitle("Sentinel-2 true colour around each data-centre point (circle = 500 m)", fontsize=11)
    fig.tight_layout()
    out = QA / "datacentre_sites_s2.png"
    fig.savefig(out, dpi=130)
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
