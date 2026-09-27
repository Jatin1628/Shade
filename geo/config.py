"""Shared paths and settings for the geo pipeline (Person 1)."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
RAW = DATA / "raw"
RASTER = DATA / "raster"
QA = DATA / "qa"

CITY = "pune"
WARDS = DATA / "wards.geojson"
CITY_OUTLINE = DATA / "pune_pmc_outline.geojson"

# UTM zone 43N — metric CRS for all area/distance work in Pune
METRIC_CRS = "EPSG:32643"

# Raster extent: PMC plus Pimpri-Chinchwad and Hinjewadi, because most of
# Pune's data centres sit outside PMC limits (Dighi, Bhosari, Pimpri, Hinjewadi).
# (west, south, east, north) in lon/lat.
METRO_BBOX = (73.60, 18.38, 74.08, 18.78)

# Pre-monsoon hot season — clearest skies and the strongest heat signal
HOT_SEASON = ("03-01", "05-31")
DEFAULT_YEAR = 2026

LANDSAT_SCALE_M = 30
