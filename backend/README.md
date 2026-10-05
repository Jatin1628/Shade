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

## Frontend developers: using /reports without the Firebase key
Only the backend owner has the service-account key, so on your laptop the real
login check returns 503. Use dev mode:

    PowerShell:   $env:SHADE_DEV_AUTH="1"
                  .venv\Scripts\python -m uvicorn backend.app.main:app --reload

Then send the header  `Authorization: Bearer dev-token`  on POST /reports,
GET /reports, GET /reports/{id} and GET /reports/{id}/pdf.
Reports are kept in server memory (gone on restart). Dev mode is OFF by default;
never enable it on a deployed server.

For the real flow (production/demo): sign in with the Firebase SDK in React,
call `await auth.currentUser.getIdToken()` and send that as the Bearer token.
