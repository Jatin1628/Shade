"""Validate candidate ward-boundary files for the study city.

Checks each candidate for: feature count, unique ward IDs, invalid geometries,
overlaps between wards, and gaps (holes) inside the dissolved city outline.
Writes a markdown report and a quick-look PNG per candidate.

Usage:  python geo/01_validate_boundaries.py
"""
import sys
from pathlib import Path

import geopandas as gpd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import Polygon
from shapely.validation import make_valid

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw" / "boundaries"
OUT = ROOT / "data" / "qa"

# UTM zone 43N — metric CRS for Pune (and Bengaluru)
METRIC_CRS = "EPSG:32643"

# Slivers below this are digitising noise, not real overlaps/gaps
MIN_ISSUE_M2 = 1_000

# file name -> ward-ID column (None = guess)
CANDIDATES = {
    "pmc-electoral-wards_2025.kml": "qwr",  # OpenCity: current 41-prabhag delimitation (final Oct 2025)
    "pune-electoral-wards_2022.geojson": "wardnum",  # DataMeet: 58 wards, superseded
    "pune-electoral-wards_2017.geojson": "ward",  # DataMeet: 41 wards, pre-2021 city limits
    "pune-electoral-wards_2012.geojson": None,
    "pune-admin-wards_2017.geojson": None,  # 15 admin wards — too coarse, reference only
}


def guess_id_column(gdf):
    for col in ("wardnum", "ward", "ward_no", "wardno", "ward_id", "id", "name", "Name"):
        if col in gdf.columns:
            return col
    return None


def find_overlaps(gdf, id_col):
    left = gdf[[id_col, "geometry"]].reset_index(drop=True)
    pairs = gpd.sjoin(left, left, predicate="intersects", how="inner")
    pairs = pairs[pairs.index < pairs["index_right"]]
    rows = []
    for i, j in zip(pairs.index, pairs["index_right"]):
        area = left.geometry[i].intersection(left.geometry[j]).area
        if area >= MIN_ISSUE_M2:
            rows.append((left[id_col][i], left[id_col][j], area))
    return sorted(rows, key=lambda r: -r[2])


def find_gaps(gdf):
    """Holes in the dissolved outline = land that belongs to no ward."""
    outline = gdf.union_all()
    polys = getattr(outline, "geoms", [outline])
    holes = [Polygon(ring) for p in polys for ring in p.interiors]
    return [h for h in holes if h.area >= MIN_ISSUE_M2], len(polys)


def validate(filename, id_col):
    name = Path(filename).stem
    gdf = gpd.read_file(RAW / filename)
    if gdf.crs is None:
        gdf = gdf.set_crs("EPSG:4326")
    id_col = id_col or guess_id_column(gdf)
    if id_col is None:
        gdf["_row"] = range(1, len(gdf) + 1)
        id_col = "_row"

    invalid = int((~gdf.geometry.is_valid).sum())
    gdf["geometry"] = gdf.geometry.apply(make_valid)
    m = gdf.to_crs(METRIC_CRS)

    ids = m[id_col]
    overlaps = find_overlaps(m, id_col)
    gaps, n_parts = find_gaps(m)
    areas_km2 = m.area / 1e6

    lines = [
        f"## {name}",
        "",
        f"- Features: **{len(m)}**  |  ID column: `{id_col}`  |  columns: {list(gdf.columns.drop('geometry'))}",
        f"- Unique IDs: {ids.nunique()} (duplicates: {int(ids.duplicated().sum())}, missing: {int(ids.isna().sum())})",
        f"- Invalid geometries (before repair): {invalid}",
        f"- Total area: {areas_km2.sum():.1f} km²  |  ward area min/median/max: "
        f"{areas_km2.min():.2f} / {areas_km2.median():.2f} / {areas_km2.max():.2f} km²",
        f"- Dissolved outline parts: {n_parts} (1 = one contiguous city)",
        f"- Overlapping ward pairs (≥ {MIN_ISSUE_M2} m²): **{len(overlaps)}**, "
        f"total {sum(a for *_, a in overlaps) / 1e6:.3f} km²",
        f"- Interior gaps (≥ {MIN_ISSUE_M2} m²): **{len(gaps)}**, total {sum(g.area for g in gaps) / 1e6:.3f} km²",
    ]
    for a, b, area in overlaps[:5]:
        lines.append(f"  - overlap {a} × {b}: {area / 1e4:.2f} ha")

    fig, ax = plt.subplots(figsize=(8, 8))
    m.plot(ax=ax, column=id_col, cmap="tab20", edgecolor="black", linewidth=0.4, categorical=True)
    if gaps:
        gpd.GeoSeries(gaps, crs=METRIC_CRS).plot(ax=ax, color="red")
    for _, row in m.iterrows():
        pt = row.geometry.representative_point()
        ax.annotate(str(row[id_col]), (pt.x, pt.y), fontsize=6, ha="center")
    ax.set_title(f"{name} — {len(m)} wards (red = gaps)")
    ax.set_axis_off()
    fig.savefig(OUT / f"{name}.png", dpi=130, bbox_inches="tight")
    plt.close(fig)

    return "\n".join(lines)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sections = [validate(filename, col) for filename, col in CANDIDATES.items()]
    report = "# Ward boundary QA\n\n" + "\n\n".join(sections) + "\n"
    (OUT / "boundary_qa.md").write_text(report, encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")  # Windows consoles default to cp1252
    print(report)


if __name__ == "__main__":
    main()
