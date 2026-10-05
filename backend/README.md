# Shade backend

Run (repo root):  `uvicorn backend.app.main:app --reload`  ->  http://127.0.0.1:8000/docs
Test:             `python -m pytest backend -q`
Reports need `FIREBASE_KEY_PATH` (service-account key, kept OUTSIDE the repo).

## Replacing the vulnerability placeholder with real data
1. Open `data/ward_population_template.csv`, fill `population` (and `sc_pop`, `st_pop`
   if available) for all 41 wards from the State Election Commission / PMC final
   prabhag table (2011 Census basis). Save as `data/ward_population.csv`.
2. `python -m backend.tools.build_vulnerability`
3. Restart the server. `vulnerability_source` switches from
   `placeholder_built_frac` to `census`.

## Scenario settings (estimator)
`GET /wards/pune/3?target_pct=30&crown_m2=40` recomputes the action plan.
Coefficients and their sources are in `backend/app/config.py`.
