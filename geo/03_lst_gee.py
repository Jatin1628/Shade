"""Hot-season land surface temperature (LST) for Pune from Landsat 8 + 9, via Earth Engine.

Two LST estimates are produced:

  lst       USGS Collection 2 Level-2 surface temperature (ST_B10). It is already
            atmospherically corrected and emissivity-corrected (ASTER GED emissivity,
            adjusted with NDVI), so it is the value we publish.
  lst_ndvi  Our own single-channel estimate: Level-1 brightness temperature (B10)
            corrected with NDVI-derived emissivity (proportion-of-vegetation method).
            Kept as a cross-check and to show the method. It has no atmospheric
            correction, so it reads several degrees cooler than `lst` (about 7 °C
            for Pune, Mar-May 2026) while tracking the same pattern (pixel r ≈ 0.97).

Do not apply the NDVI emissivity correction to ST_B10 as well: it is already
emissivity-corrected, so that would correct it twice.

Also exported: Landsat NDVI, the number of clear scenes per pixel (a confidence
layer), ESA WorldCover 2021 tree / built-up fractions (a provisional canopy
stand-in until the U-Net layer is ready), Dynamic World land-cover shares for the
same season (current land cover, used to compare like with like in the
data-centre analysis) and NASADEM elevation — all at 30 m.

Usage:
  python geo/03_lst_gee.py [--project <gcp-project-id>] [--year 2026] [--drive] [--bands lst built_dw ...]

  --project can be left out after running `earthengine set_project <gcp-project-id>` once.

  Default: downloads one GeoTIFF per band into data/raster/.
  --drive: queues Earth Engine export tasks to Google Drive instead (for larger areas).
"""
import argparse
import csv
import os
import sys

import ee
import rasterio
import requests

from config import DEFAULT_YEAR, HOT_SEASON, LANDSAT_SCALE_M, METRIC_CRS, METRO_BBOX, RASTER

NODATA = -9999.0

# QA_PIXEL bits 0-4: fill, dilated cloud, cirrus, cloud, cloud shadow
QA_REJECT_BITS = 0b11111

# Proportion-of-vegetation emissivity (Sobrino et al. 2004; Avdan & Jovanovska 2016)
NDVI_SOIL, NDVI_VEG = 0.2, 0.5
EMISSIVITY_WATER = 0.991
B10_WAVELENGTH_UM = 10.895  # Landsat 8/9 TIRS band 10 effective wavelength
RHO_UM_K = 14388.0  # h*c/k_B, in µm·K


def clear_mask(img):
    return img.select("QA_PIXEL").bitwiseAnd(QA_REJECT_BITS).eq(0)


def prep_l2(img):
    """Level-2 scene -> lst (°C, USGS product) + ndvi_l8, cloud-masked."""
    sr = img.select(["SR_B4", "SR_B5"]).multiply(0.0000275).add(-0.2)
    ndvi = sr.normalizedDifference(["SR_B5", "SR_B4"]).rename("ndvi_l8")
    st = img.select("ST_B10")
    lst = st.multiply(0.00341802).add(149.0).subtract(273.15).rename("lst")
    return (
        lst.addBands(ndvi)
        .updateMask(clear_mask(img).And(st.gt(0)))
        .copyProperties(img, ["system:time_start"])
    )


def prep_toa(img):
    """Level-1 TOA scene -> lst_ndvi (°C) from brightness temperature + NDVI emissivity."""
    bt = img.select("B10")  # at-sensor brightness temperature, K
    ndvi = img.normalizedDifference(["B5", "B4"])
    pv = ndvi.subtract(NDVI_SOIL).divide(NDVI_VEG - NDVI_SOIL).clamp(0, 1).pow(2)
    emissivity = pv.multiply(0.004).add(0.986).where(ndvi.lt(0), EMISSIVITY_WATER)
    lst = bt.divide(
        bt.multiply(B10_WAVELENGTH_UM / RHO_UM_K).multiply(emissivity.log()).add(1)
    ).subtract(273.15)
    return lst.rename("lst_ndvi").updateMask(clear_mask(img)).copyProperties(img, ["system:time_start"])


def landsat(collection_ids, region, start, end):
    col = ee.ImageCollection(collection_ids[0])
    for cid in collection_ids[1:]:
        col = col.merge(ee.ImageCollection(cid))
    return col.filterBounds(region).filterDate(start, end).filter(ee.Filter.lt("CLOUD_COVER", 20))


def worldcover_fractions():
    wc = ee.ImageCollection("ESA/WorldCover/v200").first().select("Map")
    return (
        ee.Image.cat([wc.eq(10).rename("tree_frac_wc"), wc.eq(50).rename("built_frac_wc")])
        .reduceResolution(reducer=ee.Reducer.mean(), maxPixels=1024)
        .reproject(crs=METRIC_CRS, scale=LANDSAT_SCALE_M)
    )


DW_CLASSES = ["trees", "built", "bare", "water", "grass", "crops", "shrub_and_scrub"]


def dynamic_world_shares(region, start, end):
    """Season-mean Dynamic World class probabilities, averaged from 10 m up to 30 m."""
    dw = (
        ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
        .filterBounds(region)
        .filterDate(start, end)
        .select(DW_CLASSES)
        .mean()
        .setDefaultProjection(METRIC_CRS, None, 10)
    )
    return (
        dw.reduceResolution(reducer=ee.Reducer.mean(), maxPixels=64)
        .reproject(crs=METRIC_CRS, scale=LANDSAT_SCALE_M)
        .rename([f"{c.split('_')[0]}_dw" for c in DW_CLASSES])
    )


def save_scene_list(col, path):
    props = ["LANDSAT_PRODUCT_ID", "SPACECRAFT_ID", "DATE_ACQUIRED", "SCENE_CENTER_TIME", "CLOUD_COVER"]
    columns = [col.aggregate_array(p).getInfo() for p in props]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(props)
        writer.writerows(sorted(zip(*columns), key=lambda r: r[2]))
    return len(columns[0])


def download_band(image, band, region, path):
    url = image.select(band).getDownloadURL(
        {"region": region, "scale": LANDSAT_SCALE_M, "crs": METRIC_CRS, "format": "GEO_TIFF"}
    )
    resp = requests.get(url, timeout=600)
    resp.raise_for_status()
    path.write_bytes(resp.content)
    with rasterio.open(path, "r+") as ds:
        ds.nodata = NODATA


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--project", default=os.environ.get("EE_PROJECT"), help="Google Cloud project ID (default: saved project)"
    )
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR)
    parser.add_argument("--drive", action="store_true", help="export to Google Drive instead of downloading")
    parser.add_argument("--bands", nargs="+", help="fetch only these bands (default: all)")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    try:
        # with no --project / EE_PROJECT, falls back to the one saved by `earthengine set_project`
        ee.Initialize(project=args.project)
    except Exception as exc:  # not authenticated / no project / project not registered for Earth Engine
        sys.exit(
            f"Earth Engine init failed: {exc}\n"
            "Run `earthengine authenticate`, then `earthengine set_project <gcp-project-id>` "
            "(or pass --project)."
        )

    region = ee.Geometry.Rectangle(list(METRO_BBOX))
    start, end = f"{args.year}-{HOT_SEASON[0]}", f"{args.year}-{HOT_SEASON[1]}"
    # filterDate's end is exclusive; advance one day so the last day of the season is kept
    end = ee.Date(end).advance(1, "day")

    l2 = landsat(["LANDSAT/LC08/C02/T1_L2", "LANDSAT/LC09/C02/T1_L2"], region, start, end)
    toa = landsat(["LANDSAT/LC08/C02/T1_TOA", "LANDSAT/LC09/C02/T1_TOA"], region, start, end)

    RASTER.mkdir(parents=True, exist_ok=True)
    n_scenes = save_scene_list(l2, RASTER / f"scenes_{args.year}.csv")
    print(f"{n_scenes} Landsat 8/9 scenes, {start} .. {HOT_SEASON[1]} (scene cloud < 20%)")
    if n_scenes == 0:
        sys.exit("No scenes found — check the year / date window.")

    l2_clean = l2.map(prep_l2)
    season = (
        l2_clean.median()
        .addBands(toa.map(prep_toa).median())
        .addBands(l2_clean.select("lst").count().rename("n_obs"))
        .unmask(NODATA)
        .toFloat()
    )
    dw = dynamic_world_shares(region, start, end).unmask(NODATA)
    elevation = ee.Image("NASA/NASADEM_HGT/001").select("elevation").unmask(NODATA)
    image = ee.Image.cat([season, worldcover_fractions(), dw, elevation]).toFloat()

    outputs = {
        "lst": f"lst_{args.year}.tif",
        "lst_ndvi": f"lst_ndvi_{args.year}.tif",
        "ndvi_l8": f"ndvi_l8_{args.year}.tif",
        "n_obs": f"n_obs_{args.year}.tif",
        "tree_frac_wc": "tree_frac_wc.tif",
        "built_frac_wc": "built_frac_wc.tif",
        **{band: f"{band}_{args.year}.tif" for band in dw.bandNames().getInfo()},
        "elevation": "elevation.tif",
    }
    if args.bands:
        unknown = set(args.bands) - set(outputs)
        if unknown:
            sys.exit(f"unknown bands: {sorted(unknown)}; choose from {list(outputs)}")
        outputs = {band: outputs[band] for band in args.bands}
    for band, filename in outputs.items():
        if args.drive:
            task = ee.batch.Export.image.toDrive(
                image=image.select(band),
                description=f"shade_{filename[:-4]}",
                folder="shade_exports",
                fileNamePrefix=filename[:-4],
                region=region,
                scale=LANDSAT_SCALE_M,
                crs=METRIC_CRS,
                maxPixels=1e9,
            )
            task.start()
            print(f"queued Drive export: {filename}")
        else:
            download_band(image, band, region, RASTER / filename)
            print(f"downloaded data/raster/{filename}")

    if args.drive:
        print("Download the files from Drive/shade_exports into data/raster/ when the tasks finish.")


if __name__ == "__main__":
    main()
