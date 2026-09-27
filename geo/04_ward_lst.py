"""Aggregate the LST rasters to wards and write the columns into data/wards.geojson.

Columns added (all °C unless noted):
  lst_mean, lst_median, lst_std, lst_p90   hot-season LST over all pixels in the ward
  lst_builtup_mean   LST over mostly built-up pixels only (WorldCover built-up ≥ 50%) —
                     "how hot is it where people live"; bare hills and dry fields on the
                     city edge can run hotter than the built-up core in daytime LST
  lst_ndvi_mean      our own NDVI-emissivity estimate (cross-check only)
  ndvi_l8_mean       Landsat NDVI
  tree_frac_wc       WorldCover 2021 tree fraction (0-1) — provisional canopy until the U-Net layer
  built_frac_wc      WorldCover 2021 built-up fraction (0-1)
  n_obs_mean         mean number of clear Landsat scenes per pixel (confidence)
  lst_valid_frac     share of the ward's pixels with a valid LST (confidence)
  lst_year           hot season the LST is from

Usage:  python geo/04_ward_lst.py [--year 2026] [--raster-dir data/raster]
"""
import argparse
import sys
from pathlib import Path

import geopandas as gpd
import numpy as np
import rasterio
from rasterstats import zonal_stats

from config import DEFAULT_YEAR, METRIC_CRS, RASTER, WARDS

NODATA = -9999.0
BUILTUP_MIN_FRAC = 0.5


def read_band(path):
    with rasterio.open(path) as ds:
        arr = ds.read(1).astype("float64")
        if ds.crs != METRIC_CRS:
            sys.exit(f"{path.name}: expected {METRIC_CRS}, got {ds.crs}")
        return np.where(arr == NODATA, np.nan, arr), ds.transform


def ward_stats(wards, arr, transform, stats):
    return zonal_stats(wards, arr, affine=transform, stats=stats, nodata=np.nan)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    parser.add_argument("--raster-dir", type=Path, default=RASTER)
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    rdir = args.raster_dir

    wards = gpd.read_file(WARDS)
    metric = wards.to_crs(METRIC_CRS)

    lst, transform = read_band(rdir / f"lst_{args.year}.tif")
    built, built_transform = read_band(rdir / "built_frac_wc.tif")
    if lst.shape != built.shape or transform != built_transform:
        sys.exit("lst and built_frac_wc rasters are on different grids — re-run 03_lst_gee.py")

    stats = ward_stats(metric, lst, transform, ["mean", "median", "std", "count", "percentile_90"])
    wards["lst_mean"] = [s["mean"] for s in stats]
    wards["lst_median"] = [s["median"] for s in stats]
    wards["lst_std"] = [s["std"] for s in stats]
    wards["lst_p90"] = [s["percentile_90"] for s in stats]

    pixel_area = abs(transform.a * transform.e)
    # pixels are assigned by centre point, so edge effects can push this slightly past 1
    wards["lst_valid_frac"] = [min(1.0, s["count"] * pixel_area / a) for s, a in zip(stats, metric.area)]

    lst_builtup = np.where(built >= BUILTUP_MIN_FRAC, lst, np.nan)
    wards["lst_builtup_mean"] = [s["mean"] for s in ward_stats(metric, lst_builtup, transform, ["mean"])]

    extra = {
        "lst_ndvi_mean": f"lst_ndvi_{args.year}.tif",
        "ndvi_l8_mean": f"ndvi_l8_{args.year}.tif",
        "n_obs_mean": f"n_obs_{args.year}.tif",
        "tree_frac_wc": "tree_frac_wc.tif",
        "built_frac_wc": "built_frac_wc.tif",
    }
    for column, filename in extra.items():
        arr, tf = read_band(rdir / filename)
        wards[column] = [s["mean"] for s in ward_stats(metric, arr, tf, ["mean"])]

    numeric = [c for c in wards.columns if c not in ("ward_id", "ward_name", "city", "area_km2", "geometry")]
    wards[numeric] = wards[numeric].astype(float).round(3)
    wards["lst_year"] = args.year

    wards.to_file(WARDS, driver="GeoJSON", COORDINATE_PRECISION=6)
    wards.drop(columns="geometry").to_csv(WARDS.with_name("wards_lst.csv"), index=False)

    r = wards["lst_mean"].corr(wards["lst_ndvi_mean"])
    bias = (wards["lst_mean"] - wards["lst_ndvi_mean"]).mean()
    print(f"{len(wards)} wards | city LST mean {wards['lst_mean'].mean():.1f} °C "
          f"(range {wards['lst_mean'].min():.1f}–{wards['lst_mean'].max():.1f})")
    print(f"cross-check: USGS LST vs NDVI-emissivity LST  r = {r:.3f}, mean difference = {bias:+.2f} °C")
    print(f"lowest valid-pixel share: {wards['lst_valid_frac'].min():.0%}")
    print("\nhottest wards:")
    top = wards.nlargest(5, "lst_mean")[["ward_id", "ward_name", "lst_mean", "lst_builtup_mean", "tree_frac_wc"]]
    print(top.to_string(index=False))
    print(f"\nwrote {WARDS.name} and wards_lst.csv")


if __name__ == "__main__":
    main()
