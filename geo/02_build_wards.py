"""Build the canonical data/wards.geojson from the 2025 PMC ward boundaries.

- Geometry: OpenCity "PMC Electoral Wards 2025" (41 prabhags, final Oct 2025).
- Names: 2026 PMC election ward list (Wikipedia), parsed into
  data/raw/pmc_ward_names_2025.csv.
- Removes the digitising slivers where neighbouring wards overlap, so every
  pixel counts towards exactly one ward in zonal statistics.

Usage:  python geo/02_build_wards.py
"""
import re
import sys

import geopandas as gpd
import pandas as pd
from shapely.validation import make_valid

from config import CITY, CITY_OUTLINE, METRIC_CRS, RAW, WARDS

SOURCE = RAW / "boundaries" / "pmc-electoral-wards_2025.kml"
NAMES = RAW / "pmc_ward_names_2025.csv"


def tidy_name(name):
    return re.sub(r"\s*-\s*", " - ", name).replace("GhorpadePeth", "Ghorpade Peth").strip()


def remove_overlaps(gdf):
    """Clip each ward by the wards before it (in ID order); keeps polygon parts only."""
    taken = None
    geoms = []
    for geom in gdf.geometry:
        if taken is not None:
            geom = geom.difference(taken)
        geom = make_valid(geom)
        if geom.geom_type == "GeometryCollection":
            geom = gpd.GeoSeries(
                [g for g in geom.geoms if g.geom_type in ("Polygon", "MultiPolygon")]
            ).union_all()
        geoms.append(geom)
        taken = geom if taken is None else taken.union(geom)
    return gdf.set_geometry(geoms, crs=gdf.crs)


def main():
    sys.stdout.reconfigure(encoding="utf-8")

    raw = gpd.read_file(SOURCE)
    wards = gpd.GeoDataFrame(
        {"ward_id": raw["qwr"].round().astype(int)}, geometry=raw.geometry.apply(make_valid), crs=raw.crs
    ).to_crs(METRIC_CRS)
    wards = wards.sort_values("ward_id").reset_index(drop=True)

    names = pd.read_csv(NAMES)
    names["ward_name"] = names["ward_name"].map(tidy_name)
    wards = wards.merge(names, on="ward_id", how="left", validate="1:1")
    assert wards["ward_name"].notna().all(), "ward without a name"
    assert list(wards["ward_id"]) == list(range(1, 42)), "expected ward IDs 1..41"

    before = wards.area.sum()
    wards = remove_overlaps(wards)
    wards["area_km2"] = (wards.area / 1e6).round(3)
    wards["city"] = CITY

    overlap_left = wards.area.sum() - wards.union_all().area
    print(f"wards: {len(wards)}  total area: {wards.area.sum() / 1e6:.1f} km²  "
          f"(slivers removed: {(before - wards.area.sum()) / 1e4:.2f} ha, overlap left: {overlap_left:.1f} m²)")

    out = wards[["ward_id", "ward_name", "city", "area_km2", "geometry"]].to_crs("EPSG:4326")
    out.to_file(WARDS, driver="GeoJSON", COORDINATE_PRECISION=6)

    outline = gpd.GeoDataFrame({"city": [CITY]}, geometry=[wards.union_all()], crs=METRIC_CRS)
    outline.to_crs("EPSG:4326").to_file(CITY_OUTLINE, driver="GeoJSON", COORDINATE_PRECISION=6)

    print(f"bounds (lon/lat): {[round(v, 3) for v in out.total_bounds]}")
    print(f"wrote {WARDS.relative_to(WARDS.parents[1])} and {CITY_OUTLINE.name}")


if __name__ == "__main__":
    main()
