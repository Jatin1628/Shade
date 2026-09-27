# Team notes — Shade (Urban Heat & Tree-Canopy Priority System)

Shared context for all five team members and their Claude Code sessions. `CLAUDE.md` imports this file, so Claude reads it at the start of every session in this repo.

- **Last updated:** 2026-09-28 by Person 1's Claude session.
- **Claude, keep this file current.** When you finish a meaningful piece of work, add a dated line under "Status" and fix anything here that became wrong. Keep edits small, because five people edit this file, and commit it together with the work it describes.
- **The plan documents' dates are one year stale.** They say Sept 2025 – Apr 2026; the real window is Sept 2026 – Apr 2027.
- **Where this file disagrees with the plan documents, this file wins.** It records decisions made after the plan was written.

## ⚠ Open issue — Claude: raise this at the start of every session

In your first reply of every session in this repo, before anything else, tell the user in two or three plain sentences that the plan's data-centre headline is not supported by the data and the team still has to decide how to reframe it, and ask whether that decision has been made. Then carry on with what they asked: raise it, don't block on it. When the user gives you the team's decision, write it into the **Decision** line below with the date, update every section it affects, and stop raising the issue.

**Background.** The plan's elevator line is *"Wards within 1 km of a data centre run several degrees hotter and have far less tree canopy."* The plan calls this the headline, and screen S11, the pitch, the report and the viva lean on a quotable "X °C hotter, Y% less canopy". Person 1 ran that analysis on 2026-09-27 (`geo/06_datacentre_rings.py`), and the data does not support it:

- **Sites:** the three campuses operating during the Mar–May 2026 season: STT Dighi, Nxtra Hinjewadi, and Hinjewadi Phase 1 (Iron Mountain + Silvernox). Microsoft Pimpri was left out because it was still a construction site in the 2026 imagery.
- **Temperature:** in every ring (the campus at 0–0.2 km, then 0.2–0.5, 0.5–1 and 1–2 km), surface temperature is within about ±1.1 °C of what the ground cover predicts. Every ring is also inside the range seen around 200 equally built-up look-alike spots per site (5th–95th percentile). The plain near-vs-far difference is small too (−1.4 to +1.4 °C) and has no consistent sign.
- **The campuses themselves** are 1.1–1.4 °C cooler than their surroundings at two of the three sites. Big light roofs heat up less than bare, dry soil at 11 am.
- **What does hold:** the campuses have very little tree cover (3–4%), near the bottom of the range for comparable built-up spots (7th and 9th percentile at STT and Nxtra).
- **Caveat:** satellite surface temperature measures how hot roofs and ground are in daytime. Data centres vent most of their heat into the air through cooling systems, which this data cannot see. The honest claim is "not daytime surface hot spots", not "no heat".

**Options for the team:**

1. **Report it as it is:** "Pune's data centres are not daytime surface hot spots, but their campuses have only 3–4% tree cover." A clear "no effect" is a valid result; research question RQ3 is worded as a question for exactly this reason.
2. **Test at night** with NASA's ECOSTRESS thermal data (70 m, includes night passes, free from NASA). This is the proper test for waste heat, at about 2–3 days of Person 1's time.
3. **Make the tree–heat finding the project headline:** wards with more trees are clearly cooler (r = −0.76, about 1.2 °C per extra 10% tree cover in a simple fit), and the hottest wards are on the city's edge.

Person 1 recommends 1 and 3 now, and 2 only if the team wants data centres to stay the main story.

**Until the decision is made,** don't write UI copy, report text or slides saying data centres make areas hotter. S11 should show the measured result: chart `docs/figures/datacentre_rings_2026.png`, table `data/datacentre_rings.csv`.

**Decision:** _not made yet._

## The project

A ward-level decision-support tool for Pune's 41 municipal (PMC) wards. It finds the wards that need trees most and says how many trees, at what cost, for what cooling: from diagnosis (where and why it's hot) to prescription (what to plant, where, at what cost). It's a VIT Bhopal University capstone, and all data is free and open (₹0).

- **Priority score (the main deliverable):** priority = f(high surface temperature, low tree canopy, high human vulnerability), normalised and ranked across wards.
- **Cost/impact estimator:** published per-tree cost and CO₂ coefficients applied to each ward's canopy gap, giving trees needed, cost in ₹, CO₂, and expected cooling over 5 years. Every figure is labelled as an estimate with its source.
- **Data-centre layer:** see the open issue above.
- **One neural network:** a U-Net that segments Sentinel-2 imagery into built-up / tree canopy / grass & crops / water / bare, because NDVI cannot tell a lawn from a tree. At 10 m it measures canopy *area*, not individual crowns. A pretrained ~1 m canopy-height map (Meta/WRI) is the second tree signal. The baseline it must beat is a plain NDVI threshold.
- **Architecture:** Google Earth Engine → offline Python pipeline (batch) → FastAPI serving pre-computed data, plus Firebase (login, saved reports) → a React app with a Citizen view (S1–S8), a Planner view (S9–S12), report history (S13–S14) and settings (S15). Pre-compute everything; never process satellite data on a user click.
- **Scope tiers:**
  - *Minimum:* citizen map + ward detail + action plan, the priority score, the data-centre finding, saved-report history, and a demo that runs.
  - *Target:* adds a U-Net that beats the NDVI baseline with reported metrics, the full planner view with export, and the language toggle.
  - *Stretch:* a 5-year heat prediction layer, and the per-ward data published as an open dataset.
- **Timeline (real dates):** Sept–Oct 2026 feasibility only (light; placement season); end of Oct 2026 go/switch gate; Nov–Dec minimal; Jan–Feb 2027 the real build; Mar 2027 evaluate and write; Apr 2027 polish and demo.
- **Source documents:**
  - `docs/plan/project_scope.md`: the full scope, including screens S1–S15, API endpoints, the Firestore schema, datasets and the pipeline.
  - `docs/plan/task_division.pdf`: per-person step lists.

## Team

| Person | Role | Owns |
|---|---|---|
| 1 | Geo pipeline lead (repo owner, GitHub `Jatin1628`) | ward boundaries, Earth Engine, surface temperature, data-centre analysis, the `data/` files |
| 2 | ML engineer | Sentinel-2 imagery, NDVI map and baseline, U-Net, per-ward canopy % |
| 3 | Backend & data | FastAPI, Firebase, vulnerability score, priority score, cost/impact estimator |
| 4 | Frontend – citizen | S1–S8 |
| 5 | Frontend – planner, plus integration/QA/demo | S9–S12, merging, keeping `data/` formats consistent, October-gate note, final report, demo |

Claude: if you don't know which person your user is, ask once, then focus on that person's status and next steps.

## Status (as of 2026-09-28)

**Person 1: every step of the task plan is done.**
- **Ward boundaries:** `data/wards.geojson` (41 wards with names). QA is in `data/qa/boundary_qa.md`; the decision note is `docs/city_decision.md` (commit to Pune).
- **Surface temperature for Mar–May 2026:**
  - rasters in `data/raster/` (not in git)
  - per-ward columns in `data/wards.geojson` and `data/wards_lst.csv`
  - the map `docs/figures/lst_2026_pune.png`, which is the October gate's "one LST map"
- **Data centres:**
  - the inventory `data/raw/datacentres_pune.csv`, with sites located on satellite view and checked in `data/qa/datacentre_sites_s2.png`
  - the ring analysis: `data/datacentre_rings.csv`, `data/datacentres.geojson`, `data/datacentre_rings.geojson`, and the chart `docs/figures/datacentre_rings_2026.png`
- **Earth Engine** works on Person 1's laptop (project `shadeai-509915`, free Community tier).

**Person 1: possible next work.**
- The night-time ECOSTRESS test, if the team chooses option 2.
- **The 5-year surface-temperature trend (2021–2026) per ward for S10.** No one is assigned; it likely falls to Person 1. `geo/03_lst_gee.py --year` already works for any year, but `geo/04_ward_lst.py` overwrites the `lst_*` columns on each run, so a per-year table needs a small change.
- **RQ2:** a controlled pixel-level regression of temperature on tree cover (with built-up, bare, water and elevation), to give Person 3 a Pune-specific cooling coefficient. Only a simple ward-level fit exists so far (about 1.2 °C per 10% tree cover).
- **Swap in Person 2's canopy** in the data-centre rings once it's ready. They currently use Dynamic World's tree share as a stand-in.

**Persons 2–5:** no work in this repo yet.
- **Person 2 (needed for the October gate):** a Sentinel-2 NDVI map and the naive canopy baseline (NDVI > 0.4 = green, % green per ward, CSV `ward_id, green_pct`). The U-Net comes in January.
- **Person 3:** FastAPI skeleton on mock data (`GET /cities`, `/wards/{city}`, `/wards/{city}/{id}`); the Firebase project; find vulnerability data (see decision 7).
- **Person 4:** app scaffold (Vite + React + react-leaflet), then S1–S5 against mock data or `data/wards.geojson`.
- **Person 5:** the October-gate note; get the team's decision on the open issue; S9–S11 skeletons.

**October gate checklist (end of Oct 2026):**
- [x] Pune ward boundaries confirmed (`docs/city_decision.md`)
- [x] One LST map (`docs/figures/lst_2026_pune.png`)
- [ ] One NDVI map (Person 2, Sentinel-2). A Landsat NDVI stand-in exists: `data/raster/ndvi_l8_2026.tif`
- [ ] Naive NDVI canopy baseline (Person 2)
- [ ] Gate note (Person 5)

## Decisions and corrections to the plan (don't undo these)

1. **Ward boundaries:** PMC 2025 delimitation: 41 wards ("prabhags"), finalised 6 Oct 2025 and used in the 15 Jan 2026 election. Geometry from OpenCity (public domain); names from the 2026 election ward list. The 2012, 2017 and 2022 sets are superseded. Pune Cantonment, the ~12 km² hole in the middle of the city, is a separate local body, not a PMC ward, so it gets no score.
2. **Surface temperature:** use Landsat Collection 2 Level-2 `ST_B10`, which is already corrected for the atmosphere and for emissivity. Do not apply the plan's NDVI emissivity correction on top, because that corrects twice. Our own NDVI-emissivity calculation (`lst_ndvi`, from Level-1 brightness temperature) is kept only as a cross-check. It tracks the USGS product closely (r = 0.97 per pixel, 0.99 per ward) and reads about 7 °C cooler because it has no atmospheric correction.
3. **Heat term in the priority score:** use `lst_builtup_mean` (temperature over mostly built-up pixels), not `lst_mean`. In daytime, Pune's hottest surfaces are bare fringe land and the Lohegaon airfield, not where people live. The two rank wards similarly (Spearman ρ = 0.93).
4. **Data-centre analysis:** most of Pune's data centres are outside PMC (Pimpri-Chinchwad, and Hinjewadi under the regional authority PMRDA). So the analysis uses distance rings on a metro-wide raster, not wards. Say "areas within X km of a data centre", never "data-centre wards". Only sites that were operating during the season and were located on satellite imagery are used.
5. **Provisional canopy:** use `tree_frac_wc` (ESA WorldCover 2021) until Person 2's U-Net is ready. Dynamic World's 2026 tree share (`data/raster/trees_dw_2026.tif`) is more current but isn't aggregated to wards yet.
6. **U-Net labels:** a model trained on WorldCover or Dynamic World labels can't be more accurate than those labels, and an examiner may ask why we don't just use WorldCover's tree class. A stronger design:
   - build tree labels from the Meta/WRI canopy-height map (for example, height > 3–5 m = tree)
   - hand-label about 300 test points on high-resolution imagery for the NDVI-vs-U-Net comparison
7. **Vulnerability data:** Census 2011 figures are published for 2011 census wards, not the 2025 wards. A lead, not yet checked: PMC's 2025 ward-structure documents list each new ward's 2011 population (for example, ward 38 has about 1.14 lakh). Otherwise, interpolate by area.
8. **Firebase Storage** has required the paid Blaze plan (with a card) since 3 Feb 2026. Plan: skip Storage. Each saved report keeps its number snapshot in Firestore, and the backend re-renders the PDF on download. Firestore and Auth stay free. Firestore location: `asia-south1` (Mumbai); it can't be changed later.
9. **Frontend:** `create-react-app` is deprecated (Feb 2025), so use Vite. Frontend environment variables then start with `VITE_`. Leaflet with OpenStreetMap tiles needs no API key.
10. **Language (S15):** Pune is Marathi-speaking, so consider Marathi as well as, or instead of, Hindi.
11. **Team size:** the scope document says four people in places, but the team is five. `docs/plan/task_division.pdf` is current.

## Results so far (Mar–May 2026)

- **Data:** 10 cloud-free Landsat 8/9 passes from 5 Mar to 16 May 2026, each at about 10:57 am IST. Every pixel has 6–10 clear views.
- **Averages:** 43.8 °C across PMC (by area). Ward averages range from 39.6 to 47.0 °C.
- **Hottest wards** (all with under 10% tree cover): 3 Vimannagar–Lohegaon (47.0 °C), 41 Mohammadwadi–Undri (46.6), 1 Kalas–Dhanori–Lohegaon (46.5).
- **Coolest wards** (38–43% tree cover): 29 Deccan Gymkhana–Happy Colony (39.6), 27 Navi Peth–Parvati (40.1), 12 Shivajinagar–Model Colony (40.2).
- **Tree cover vs ward temperature:** r = −0.76, about −1.2 °C per extra 10% tree cover in a simple fit.
- **Built-up share vs temperature:** r = −0.38. In daytime, the dense old core is cooler than the bare fringe.
- **Data centres:** see the open issue.

## Research questions

**Main question:** Which wards of Pune most urgently need tree canopy, judged jointly by surface heat, canopy deficit and residents' vulnerability, and what planting, at what cost, would close each ward's gap?

| | Question | Owner | Status |
|---|---|---|---|
| RQ1 | Does a Sentinel-2 U-Net separate trees from grass and crops better than an NDVI threshold, and does it change which wards are prioritised? | P2 | not started |
| RQ2 | How much cooler is the surface where canopy is higher, controlling for built-up cover, water and elevation? | P1 → P3 | simple fit only |
| RQ3 | Are areas near data centres hotter and less green than comparable areas? | P1 | done: no daytime surface hot spot |
| RQ4 | For top-priority wards: how many trees to reach a target canopy, at what cost, with what cooling and CO₂? | P3 | not started |
| RQ5 | How stable is the ranking when the score weights change? (optional) | P3 | not started |

**Limits to state in the report:**
- The study covers the 41 PMC wards.
- Temperature is land surface temperature at about 11 am in Mar–May 2026, not air or night-time heat.
- The findings are associations, not causes.
- Cost, CO₂ and cooling figures are estimates.

## Repo map

```
CLAUDE.md               imports this file for Claude Code
TEAM_NOTES.md           this file
requirements-geo.txt    Python packages for the geo pipeline
geo/                    Person 1's pipeline: scripts numbered in run order, settings in
                        geo/config.py, how-to in geo/README.md
data/
  wards.geojson         THE ward file (41 wards); everyone reads this
  wards_lst.csv         the same columns without geometry
  datacentre_rings.csv, datacentres.geojson, datacentre_rings.geojson   data-centre results (S11)
  pune_pmc_outline.geojson   city outline
  raster/               30 m GeoTIFFs (not in git; rebuild with geo/03_lst_gee.py) + scenes_2026.csv
  raw/                  source downloads: boundary candidates, ward names, data-centre inventory
  qa/                   boundary QA report, site imagery checks
docs/
  city_decision.md      why Pune and the 2025 boundaries
  figures/              lst_2026_pune.png, datacentre_rings_2026.png
  plan/                 project_scope.md, task_division.pdf
```

## Data formats (what other code can rely on)

- **`data/wards.geojson`:** EPSG:4326, one feature per ward.
  - Always present: `ward_id` (1–41), `ward_name`, `city` (`pune`), `area_km2`.
  - From the temperature step:
    - `lst_mean`, `lst_median`, `lst_std`, `lst_p90`, `lst_builtup_mean` (°C)
    - confidence: `lst_valid_frac`, `n_obs_mean`
    - `tree_frac_wc`, `built_frac_wc` (0–1, WorldCover 2021)
    - cross-check: `lst_ndvi_mean`, `ndvi_l8_mean`
    - `lst_year`
- **Rasters in `data/raster/`:** EPSG:32643 (UTM 43N), 30 m, 1699 × 1487 pixels covering PMC, Pimpri-Chinchwad and Hinjewadi. Nodata is −9999. Files:
  - `lst_2026`, `lst_ndvi_2026`, `ndvi_l8_2026`, `n_obs_2026`
  - `tree_frac_wc`, `built_frac_wc`
  - Dynamic World shares `{trees,built,bare,water,grass,crops,shrub}_dw_2026`
  - `elevation`
- **Data centres:**
  - `data/datacentres.geojson`: every located site, with `use_in_analysis` saying why it's in or out.
  - `data/datacentre_rings.geojson`: ring polygons with `lst_mean`, `lst_excess` (°C above what the ground cover predicts), `trees_pct`, `built_pct`, `excess_percentile_vs_lookalikes`.

## Running the geo pipeline

1. **Set up Python:** `python -m venv .venv`, then `.venv\Scripts\python -m pip install -r requirements-geo.txt`.
2. **Set up Earth Engine** (each person on their own Google account):
   - Register a free non-commercial project at https://code.earthengine.google.com/register: Scientific research, Regional scope, category Adaptation, **Community** tier (no card).
   - A research question you can use on the form: "Which wards of Pune, India most need tree planting to reduce urban heat, based on Landsat land surface temperature, Sentinel-2 tree-canopy mapping and population vulnerability, and are areas near data centres hotter?"
   - Then run `.venv\Scripts\earthengine authenticate` and `.venv\Scripts\earthengine set_project <id>`.
3. **Run the scripts** `geo/01_…` to `geo/07_…` from the repo root, in order; see `geo/README.md`. Step 3 downloads the rasters: about 3 minutes for the temperature layers and about 10 more for the Dynamic World layers (`--bands` fetches a subset).

## Conventions

- Team laptops run Windows with Python 3.13. Each person makes their own `.venv` (not committed).
- Scripts print summaries and call `sys.stdout.reconfigure(encoding="utf-8")`, because Windows consoles default to cp1252.
- Match the existing code style: a short docstring with Usage at the top of each script, paths and settings in `geo/config.py`, and no hard-coded absolute paths.
- Don't commit `.venv/`, rasters (`data/raster/*.tif`), or secrets (`.env`, Firebase service-account keys).
- `data/wards.geojson` and `data/raw/datacentres_pune.csv` belong to Person 1. Change them through the scripts, not by hand.
- Charts use one light-mode palette so the figures match. See `geo/05_lst_maps.py`.
  - text: `#0b0b0b` / `#52514e` / `#898781`; background: `#fcfcfb`
  - series: `#2a78d6`, `#eb6834`, `#1baf7a`
  - temperature: blue ↔ red with a grey midpoint (`#f0efec`)
- Git remote: https://github.com/Jatin1628/Shade (branch `main`). The root `README.md` was saved as UTF-16 by PowerShell; re-save it as UTF-8 when you next edit it.

## Glossary

- **LST:** land surface temperature, meaning how hot roofs and ground are, from satellite thermal bands. Not air temperature.
- **NDVI:** a greenness index from red and near-infrared light. It can't tell a lawn from a tree.
- **PMC / PCMC / PMRDA:** Pune Municipal Corporation (our 41 wards) / Pimpri-Chinchwad Municipal Corporation / Pune Metropolitan Region Development Authority (covers Hinjewadi).
- **Prabhag:** a PMC electoral ward.
- **Dynamic World:** Google's 10 m land-cover map, updated from every Sentinel-2 pass. We use its Mar–May 2026 average shares.
- **Look-alike spots:** equally built-up places at least 4 km from any data centre, used as the comparison in the data-centre analysis.
- **Excess heat:** measured temperature minus what the ground cover and elevation predict.
- **EECU-hours:** Earth Engine's compute quota unit. The Community tier gives 150 per month per project.
