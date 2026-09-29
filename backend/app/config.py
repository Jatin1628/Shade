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
# Scenario settings: the API lets a caller override these per request
# (?target_pct=30&crown_m2=40), so they are inputs, not claimed facts.
TARGET_CANOPY_FRAC = 0.25        # SCENARIO: goal canopy share per ward
CROWN_AREA_M2 = 30.0             # SCENARIO: canopy area one tree adds at maturity.
                                 # No Pune-specific source found; varies a lot by species/age.

# Cost per tree is shown as a RANGE, not one invented number.
# LOW  = sapling + planting only (no aftercare)
#   Rs 5   PMC subsidised native sapling price, Van Mahotsav 2026
#          (Pune Pulse, 5 Jun 2026, mypunepulse.com)
#   Rs 50  low end of commercial planting service Rs 50-150/tree
#          (growbilliontrees.com; commercial source, weak)
COST_PER_TREE_INR_LOW = 55.0
# HIGH = adds tree guard, watering and ~3 years upkeep.
#   ASSUMPTION, NOT CITED. Replace with PMC Garden/Tree Authority Dept
#   Schedule of Rates for plantation (ask the department).
COST_PER_TREE_INR_HIGH = 1000.0

# CO2 for NEWLY PLANTED trees (age 1-10 yr): 2.25 kg CO2 / tree / yr.
# Vandariya et al. (2025), "Carbon Sequestration Potential of Urban Tree
# Species: A Case Study from Porbandar, India", Cities and the Environment
# 18(2), Art. 5. One Gujarat city; species/age dependent. Mature trees
# sequester far more but take decades.
CO2_KG_PER_TREE_YR = 2.25

# Cooling: from this project's own ward-level fit for Pune (about 1.2 C per
# +10 pp tree cover, r = -0.76; TEAM_NOTES). A cross-sectional ASSOCIATION,
# not a proven causal effect, and a long extrapolation for big gaps.
COOLING_C_PER_PP = 0.12

SOURCES = {
    "cost_low": "PMC native sapling Rs 5 (Pune Pulse, 5 Jun 2026) + planting Rs 50 (growbilliontrees.com)",
    "cost_high": "Assumption: guard + watering + ~3 yrs upkeep; not cited yet",
    "co2": "Vandariya et al. 2025, Cities and the Environment 18(2), Porbandar; trees aged 1-10 yr",
    "cooling": "Project analysis: Pune ward-level tree cover vs Landsat LST, Mar-May 2026 (association)",
    "crown_area": "Scenario setting, adjustable; no Pune-specific source",
}
