"""Data-centre heat analysis: surface temperature and tree cover in distance rings around
Pune's operating data centres, compared with (a) what the land cover predicts and (b)
equally built-up look-alike spots elsewhere.

Method, per site group (a campus of one or more data-centre points):
  1. Rings by distance to the nearest point of the group: the campus itself (0-0.2 km),
     then 0.2-0.5, 0.5-1, 1-2 km, and a 2-4 km reference ring. Mostly-water pixels,
     and pixels within 2 km of another group, are left out.
  2. On the reference ring, fit LST ~ Dynamic World land-cover shares + elevation
     (same Mar-May season as the LST).
  3. Excess heat of a ring = mean(observed LST - LST predicted from its land cover).
     Positive means hotter than its land cover explains.
  4. Look-alike test: repeat 1-3 around look-alike centres — built-up pixels at least
     4 km from any data centre whose surrounding 0.5 km is as built-up as the site's
     (±10 points). Report where the data centre falls in that distribution.
     Data centres that were construction sites during the season are not used.
     Pixels near 30 m are spatially correlated (Landsat thermal is 100 m native), so
     this comparison, not a pixel-level p-value, is the fair test.

Usage:   python geo/06_datacentre_rings.py [--year 2026] [--lookalikes 200]
Outputs: data/datacentre_rings.csv, data/datacentres.geojson, data/datacentre_rings.geojson
"""
import argparse
import sys

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from shapely.geometry import Point

from config import DATA, METRIC_CRS, RASTER, RAW, DEFAULT_YEAR

NODATA = -9999.0
RINGS_M = [0, 200, 500, 1000, 2000, 4000]
RING_LABELS = ["0–0.2 km (campus)", "0.2–0.5 km", "0.5–1 km", "1–2 km", "2–4 km (reference)"]
REFERENCE = len(RING_LABELS) - 1
NEIGHBOURHOOD_M = 500  # look-alikes are matched on built-up share within this distance
# shrub_dw is the left-out share (the shares sum to ~1)
COVARIATES = ["built_dw", "trees_dw", "bare_dw", "grass_dw", "crops_dw", "water_dw", "elevation"]
WATER_MAX = 0.5
OTHER_GROUP_EXCLUSION_M = 2000
LOOKALIKE_MIN_GAP_M = 4000
MATCH_TOLERANCE = 0.10
CENTRE_BUILT_MIN = 0.5
SEED = 42


def load_rasters(year):
    files = {"lst": f"lst_{year}.tif", "elevation": "elevation.tif"}
    files.update({c: f"{c}_{year}.tif" for c in COVARIATES if c != "elevation"})
    arrays, grid = {}, None
    for key, name in files.items():
        with rasterio.open(RASTER / name) as ds:
            this = (ds.crs.to_string(), ds.transform, ds.shape)
            if grid is not None and this != grid:
                sys.exit(f"{name} is on a different grid — re-run 03_lst_gee.py")
            grid = this
            a = ds.read(1).astype("float64")
            a[a == NODATA] = np.nan
            arrays[key] = a
    return arrays, grid[1], grid[2]


def local_mean(a, radius_px):
    """Mean over a square window with the same area as a circle of this radius (integral image)."""
    half = int(round(radius_px * np.sqrt(np.pi) / 2))
    filled = np.nan_to_num(a)
    ok = np.isfinite(a).astype(float)
    pad = lambda x: np.pad(x, ((half + 1, half), (half + 1, half)), mode="constant")
    s, n = pad(filled).cumsum(0).cumsum(1), pad(ok).cumsum(0).cumsum(1)
    k = 2 * half + 1
    window = lambda c: c[k:, k:] - c[:-k, k:] - c[k:, :-k] + c[:-k, :-k]
    with np.errstate(invalid="ignore", divide="ignore"):
        return window(s) / window(n)


class Grid:
    def __init__(self, transform, shape):
        self.t, self.shape = transform, shape

    def window(self, xs, ys, reach):
        t, (h, w) = self.t, self.shape
        c0 = max(0, int((min(xs) - reach - t.c) / t.a))
        c1 = min(w, int((max(xs) + reach - t.c) / t.a) + 1)
        r0 = max(0, int((max(ys) + reach - t.f) / t.e))
        r1 = min(h, int((min(ys) - reach - t.f) / t.e) + 1)
        rows, cols = np.mgrid[r0:r1, c0:c1]
        return (slice(r0, r1), slice(c0, c1)), t.c + (cols + 0.5) * t.a, t.f + (rows + 0.5) * t.e

    def distance(self, px, py, points):
        return np.min([np.hypot(px - x, py - y) for x, y in points], axis=0)


def ring_stats(points, arrays, valid, grid, exclude=()):
    """Per-ring LST, land cover and land-cover-adjusted excess around a set of points."""
    xs, ys = zip(*points)
    win, px, py = grid.window(xs, ys, RINGS_M[-1])
    dist = grid.distance(px, py, points)
    ok = valid[win] & (dist < RINGS_M[-1])
    for other in exclude:
        ok &= grid.distance(px, py, other) >= OTHER_GROUP_EXCLUSION_M
    ring = np.digitize(dist[ok], RINGS_M) - 1
    y = arrays["lst"][win][ok]
    X = np.column_stack([np.ones(len(y))] + [arrays[c][win][ok] for c in COVARIATES])
    ref = ring == REFERENCE
    if ref.sum() < 5 * X.shape[1] or (ring == 0).sum() == 0:
        return None
    beta, *_ = np.linalg.lstsq(X[ref], y[ref], rcond=None)
    resid = y - X @ beta
    out = []
    for i, label in enumerate(RING_LABELS):
        m = ring == i
        out.append({
            "ring": label, "ring_index": i, "n_px": int(m.sum()),
            "lst_mean": y[m].mean(), "lst_excess": resid[m].mean(),
            "trees_pct": 100 * arrays["trees_dw"][win][ok][m].mean(),
            "built_pct": 100 * arrays["built_dw"][win][ok][m].mean(),
            "bare_pct": 100 * arrays["bare_dw"][win][ok][m].mean(),
        })
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    parser.add_argument("--lookalikes", type=int, default=200)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    sites = pd.read_csv(RAW / "datacentres_pune.csv")
    used = sites[sites["use_in_analysis"].eq("yes") & sites["lat"].notna()].copy()
    pts = gpd.GeoDataFrame(used, geometry=gpd.points_from_xy(used.lon, used.lat), crs=4326).to_crs(METRIC_CRS)
    groups = {g: list(zip(d.geometry.x, d.geometry.y)) for g, d in pts.groupby("site_group", sort=False)}
    for g, p in groups.items():
        spread = max(np.hypot(x1 - x2, y1 - y2) for x1, y1 in p for x2, y2 in p)
        assert spread < 1000, f"{g}: points {spread:.0f} m apart — not one campus?"

    arrays, transform, shape = load_rasters(args.year)
    grid = Grid(transform, shape)
    valid = np.all([np.isfinite(a) for a in arrays.values()], axis=0) & (arrays["water_dw"] <= WATER_MAX)
    print(f"valid pixels: {valid.mean():.1%} of {shape[0]}x{shape[1]}")

    # look-alike candidates: built-up centres far from every data centre and from the raster edge
    all_points = [p for ps in groups.values() for p in ps]
    built_local = local_mean(arrays["built_dw"], NEIGHBOURHOOD_M / transform.a)
    win, px, py = grid.window([transform.c, transform.c + transform.a * shape[1]],
                              [transform.f, transform.f + transform.e * shape[0]], 0)
    far = grid.distance(px, py, all_points) >= LOOKALIKE_MIN_GAP_M
    edge = RINGS_M[-1] + 500
    inside = ((px - transform.c > edge) & (transform.c + transform.a * shape[1] - px > edge)
              & (transform.f - py > edge) & (py - (transform.f + transform.e * shape[0]) > edge))
    base_candidates = valid & far & inside & (arrays["built_dw"] >= CENTRE_BUILT_MIN)
    rng = np.random.default_rng(SEED)

    rows = []
    for g, points in groups.items():
        others = [p for h, ps in groups.items() if h != g for p in ps]
        dc = ring_stats(points, arrays, valid, grid, exclude=[others] if others else ())
        near = [r for r, outer in zip(dc, RINGS_M[1:]) if outer <= NEIGHBOURHOOD_M]
        target = sum(r["built_pct"] * r["n_px"] for r in near) / sum(r["n_px"] for r in near) / 100
        cand = np.argwhere(base_candidates & (np.abs(built_local - target) <= MATCH_TOLERANCE))
        if len(cand) < 30:
            sys.exit(f"{g}: only {len(cand)} look-alike candidates — widen MATCH_TOLERANCE")
        pick = cand[rng.choice(len(cand), size=min(args.lookalikes, len(cand)), replace=False)]
        looks = []
        for r, c in pick:
            centre = [(transform.c + (c + 0.5) * transform.a, transform.f + (r + 0.5) * transform.e)]
            s = ring_stats(centre, arrays, valid, grid, exclude=[all_points])
            if s:
                looks.append(s)
        print(f"{g}: {len(points)} point(s), built-up within {NEIGHBOURHOOD_M} m {target:.0%}, "
              f"{len(cand)} matching candidates, {len(looks)} look-alikes used")
        for i, ring in enumerate(dc):
            exc = np.array([s[i]["lst_excess"] for s in looks])
            dtree = np.array([s[i]["trees_pct"] - s[REFERENCE]["trees_pct"] for s in looks])
            ring_dtree = ring["trees_pct"] - dc[REFERENCE]["trees_pct"]
            rows.append({
                "site_group": g, **ring,
                "lst_minus_reference": ring["lst_mean"] - dc[REFERENCE]["lst_mean"],
                "trees_minus_reference_pct": ring_dtree,
                "lookalike_excess_p5": np.percentile(exc, 5), "lookalike_excess_p50": np.percentile(exc, 50),
                "lookalike_excess_p95": np.percentile(exc, 95),
                "excess_percentile_vs_lookalikes": 100 * (exc < ring["lst_excess"]).mean(),
                "trees_diff_percentile_vs_lookalikes": 100 * (dtree < ring_dtree).mean(),
                "n_lookalikes": len(looks),
            })

    table = pd.DataFrame(rows)
    num = table.select_dtypes("number").columns.drop(["ring_index", "n_px", "n_lookalikes"])
    table[num] = table[num].round(2)
    table.to_csv(DATA / "datacentre_rings.csv", index=False)

    # map layers for the app (S11): points with their status, and ring polygons with the numbers
    everyone = sites[sites["lat"].notna()]
    gpd.GeoDataFrame(
        everyone[["dc_id", "name", "operator", "status", "capacity_mw", "use_in_analysis", "site_group"]],
        geometry=gpd.points_from_xy(everyone.lon, everyone.lat), crs=4326,
    ).to_file(DATA / "datacentres.geojson", driver="GeoJSON")
    polys = []
    for g, points in groups.items():
        discs = [gpd.GeoSeries([Point(p).buffer(r) for p in points]).union_all() for r in RINGS_M[1:]]
        for i, (inner, outer) in enumerate(zip([None] + discs[:-1], discs)):
            polys.append({"site_group": g, "ring": RING_LABELS[i], "geometry": outer if inner is None else outer.difference(inner)})
    rings_gdf = gpd.GeoDataFrame(polys, crs=METRIC_CRS).merge(
        table[["site_group", "ring", "lst_mean", "lst_excess", "trees_pct", "built_pct",
               "excess_percentile_vs_lookalikes"]], on=["site_group", "ring"])
    rings_gdf.to_crs(4326).to_file(DATA / "datacentre_rings.geojson", driver="GeoJSON", COORDINATE_PRECISION=6)

    show = ["site_group", "ring", "n_px", "lst_mean", "lst_minus_reference", "lst_excess",
            "lookalike_excess_p5", "lookalike_excess_p95", "excess_percentile_vs_lookalikes",
            "trees_pct", "trees_minus_reference_pct", "trees_diff_percentile_vs_lookalikes", "built_pct", "bare_pct"]
    with pd.option_context("display.width", 250, "display.max_columns", 30):
        print(table[show].to_string(index=False))
    print("\nwrote data/datacentre_rings.csv, data/datacentres.geojson, data/datacentre_rings.geojson")


if __name__ == "__main__":
    main()
