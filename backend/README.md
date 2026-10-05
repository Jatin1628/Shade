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

## /reports: login and storage (no secret key needed to log in)
Real Firebase logins work on ANY laptop. The server checks the ID token with
Google's public keys (project id `shade-capstone`, override with
`FIREBASE_PROJECT_ID`). It needs internet access to Google for that.

Where reports are stored:
- `FIREBASE_KEY_PATH` set to the service-account key -> Firestore (persistent).
- not set -> server memory (lost on restart). The POST response shows
  `"storage": "memory"` or `"firestore"`.

Frontend: sign in with the Firebase SDK, then send
`Authorization: Bearer <await auth.currentUser.getIdToken()>`.

Offline only (no internet): `$env:SHADE_DEV_AUTH="1"` makes the fixed token
`dev-token` work. Never enable it on a shared or deployed server.
