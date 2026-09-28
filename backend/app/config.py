"""Backend settings. Everything tunable lives here so the report can cite it.

Every number marked ASSUMPTION is a placeholder that must be replaced with a
cited published value before the final report.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "data"

CITIES = {"pune": {"name": "Pune", "wards_file": DATA / "wards.geojson"}}

# --- Priority score -------------------------------------------------------
# priority = W_HEAT*heat + W_CANOPY*canopy_deficit + W_VULN*vulnerability
# each term min-max normalised to 0-1 across wards. Weights are a design
# choice (RQ5 = test how much the ranking changes if they change).
W_HEAT, W_CANOPY, W_VULN = 0.40, 0.40, 0.20
HEAT_COLUMN = "lst_builtup_mean"      # TEAM_NOTES decision 3 (not lst_mean)
CANOPY_COLUMN = "tree_frac_wc"        # provisional until the U-Net lands (0-1)
# Optional real vulnerability file: columns ward_id, vulnerability (0-1).
VULN_FILE = DATA / "vulnerability.csv"

# --- Cost / impact estimator (ALL ESTIMATES) ------------------------------
TARGET_CANOPY_FRAC = 0.25        # ASSUMPTION: goal canopy share per ward
CROWN_AREA_M2 = 30.0             # ASSUMPTION: mature crown area per tree
COST_PER_TREE_INR = 1000.0       # ASSUMPTION: plant + ~3 yrs upkeep
CO2_KG_PER_TREE_YR = 20.0        # ASSUMPTION: at maturity; needs a citation
# From Person 1's ward-level fit (about 1.2 C per +10 pp tree cover).
# An association across wards, NOT a proven causal cooling effect.
COOLING_C_PER_PP = 0.12
