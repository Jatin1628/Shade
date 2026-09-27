"""Shared paths and settings for the ML pipeline (Person 2).

Values that must stay in sync with Person 1's geo/config.py:
CITY, WARDS, CITY_OUTLINE, METRIC_CRS, HOT_SEASON, DEFAULT_YEAR.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RASTER = DATA / "raster"

CITY = "pune"
WARDS = DATA / "wards.geojson"
CITY_OUTLINE = DATA / "pune_pmc_outline.geojson"

# UTM zone 43N — metric CRS for all area/distance work in Pune
# (matches geo/config.py — needed for zonal stats against data/wards.geojson)
METRIC_CRS = "EPSG:32643"

# Pre-monsoon hot season — same window as Person 1's LST, so NDVI and LST
# are directly comparable (same satellite passes, same conditions)
HOT_SEASON = ("03-01", "05-31")
DEFAULT_YEAR = 2026

SENTINEL2_SCALE_M = 10