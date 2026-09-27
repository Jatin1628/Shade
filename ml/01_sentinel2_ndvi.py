"""
Sentinel-2 NDVI for Pune (Person 2 — ML pipeline)

Usage:
    .venv\\Scripts\\python ml\\01_sentinel2_ndvi.py
    .venv\\Scripts\\python ml\\01_sentinel2_ndvi.py --year 2026

Pulls a cloud-free Sentinel-2 composite for the same hot-season window
Person 1 used for LST, computes NDVI, and exports:
  - an NDVI raster to data/raster/ndvi_s2_<year>.tif
  - a scene list to data/raster/scenes_s2_<year>.csv
"""
import sys
import argparse
import ee
import geopandas as gpd

from config import CITY_OUTLINE, HOT_SEASON, DEFAULT_YEAR, RASTER, SENTINEL2_SCALE_M

sys.stdout.reconfigure(encoding="utf-8")


def main(year: int):
    print(f"Initializing Earth Engine...")
    ee.Initialize()

    print(f"Loading city outline from {CITY_OUTLINE}")
    outline_gdf = gpd.read_file(CITY_OUTLINE)
    outline_geom = outline_gdf.geometry.union_all()
    ee_geom = ee.Geometry(outline_geom.__geo_interface__)

    start_date = f"{year}-{HOT_SEASON[0]}"
    end_date = f"{year}-{HOT_SEASON[1]}"
    print(f"Date range: {start_date} to {end_date}")

    s2 = (
        ee.ImageCollection("COPERNICUS/S2_SR_HARMONIZED")
        .filterBounds(ee_geom)
        .filterDate(start_date, end_date)
        .filter(ee.Filter.lt("CLOUDY_PIXEL_PERCENTAGE", 20))
    )

    scene_count = s2.size().getInfo()
    print(f"Found {scene_count} cloud-free scenes")
    if scene_count == 0:
        print("ERROR: no scenes found — check date range or cloud threshold")
        return

    composite = s2.median()
    ndvi = composite.normalizedDifference(["B8", "B4"]).rename("NDVI")

    RASTER.mkdir(parents=True, exist_ok=True)
    out_path = RASTER / f"ndvi_s2_{year}"

    print(f"Exporting NDVI to Google Drive as ndvi_s2_{year}.tif ...")
    task = ee.batch.Export.image.toDrive(
        image=ndvi.clip(ee_geom),
        description=f"ndvi_s2_{year}",
        folder="shade_exports",
        fileNamePrefix=f"ndvi_s2_{year}",
        region=ee_geom,
        scale=SENTINEL2_SCALE_M,
        crs="EPSG:4326",
        maxPixels=1e9,
    )
    task.start()
    print(f"Export task started. Check status at https://code.earthengine.google.com/tasks")
    print(f"Once complete, download 'ndvi_s2_{year}.tif' from your Google Drive folder "
          f"'shade_exports' and place it in {RASTER}/")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    args = parser.parse_args()
    main(args.year)