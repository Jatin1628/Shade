"""Cost / impact estimator. Every output is an ESTIMATE, not a measurement.
Coefficients and their sources live in config.py."""
from . import config as C


def action_plan(area_km2: float, canopy_frac: float,
                target_frac: float | None = None,
                crown_m2: float | None = None) -> dict:
    target = C.TARGET_CANOPY_FRAC if target_frac is None else target_frac
    crown = C.CROWN_AREA_M2 if crown_m2 is None else crown_m2

    gap = max(0.0, target - canopy_frac)
    canopy_m2 = gap * area_km2 * 1_000_000          # data-derived, no tree assumption
    trees = canopy_m2 / crown                        # depends on crown-size scenario
    return {
        "target_canopy_pct": round(target * 100, 1),
        "current_canopy_pct": round(canopy_frac * 100, 1),
        "gap_pp": round(gap * 100, 1),
        "canopy_area_needed_ha": round(canopy_m2 / 10_000, 1),
        "crown_area_m2_assumed": crown,
        "trees_needed": int(round(trees)),
        "cost_inr_low": int(round(trees * C.COST_PER_TREE_INR_LOW)),
        "cost_inr_high": int(round(trees * C.COST_PER_TREE_INR_HIGH)),
        "cooling_c_at_target_canopy": round(gap * 100 * C.COOLING_C_PER_PP, 2),
        "co2_tonnes_per_year_young_trees": round(trees * C.CO2_KG_PER_TREE_YR / 1000, 1),
        "is_estimate": True,
        "sources": C.SOURCES,
        "note": ("Estimates, not measurements. Cooling is the cooling associated with "
                 "reaching the target canopy, not a 5-year forecast (trees take years to "
                 "grow). It assumes the whole gap is plantable; real ward land (roads, "
                 "buildings, airfields) limits this. CO2 is for young trees only."),
    }
