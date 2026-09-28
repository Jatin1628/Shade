"""Cost / impact estimator. Every output is an ESTIMATE from assumed
coefficients in config.py, not a field measurement."""
from . import config as C


def action_plan(area_km2: float, canopy_frac: float) -> dict:
    gap = max(0.0, C.TARGET_CANOPY_FRAC - canopy_frac)
    canopy_m2 = gap * area_km2 * 1_000_000
    trees = canopy_m2 / C.CROWN_AREA_M2
    return {
        "target_canopy_pct": round(C.TARGET_CANOPY_FRAC * 100, 1),
        "current_canopy_pct": round(canopy_frac * 100, 1),
        "gap_pp": round(gap * 100, 1),
        "trees_needed": int(round(trees)),
        "cost_inr": int(round(trees * C.COST_PER_TREE_INR)),
        "cooling_c_estimate": round(gap * 100 * C.COOLING_C_PER_PP, 2),
        "co2_tonnes_per_year": round(trees * C.CO2_KG_PER_TREE_YR / 1000, 1),
        "is_estimate": True,
        "note": ("Estimates from assumed per-tree coefficients and a ward-level "
                 "association between tree cover and surface temperature. "
                 "Not field measurements."),
    }
