# Urban Heat & Tree-Canopy Priority System — Scope & Implementation Plan

> **Transcribed from the team's original scope document** (shared 2026-09-27). The text below is unchanged apart from formatting.
> Read it together with `TEAM_NOTES.md`, which records later decisions. **Where they disagree, `TEAM_NOTES.md` wins.** In particular:
> - Dates are one year stale: the real build window is Sept 2026 – Apr 2027.
> - The data-centre "headline" (§1, §2.2, S11) is not supported by the 2026 data. See the open issue in `TEAM_NOTES.md`.
> - Pipeline step 2 (NDVI emissivity correction) must not be applied to Landsat `ST_B10`, which is already corrected.
> - Firebase Storage now needs a paid plan, and the team is 5 people, not 4 (see `docs/plan/task_division.pdf`).

Capstone Project — Scope & Implementation Plan. A ward-level decision-support tool for Indian cities. Primary study city: Pune (fallback: Bengaluru).

- **Working title:** Urban Heat & Tree-Canopy Priority System
- **Core idea:** Find the wards that need trees most — and say how many, at what cost, for what cooling
- **Type:** Full-stack + geospatial data pipeline + one neural network (CV)
- **Build window:** Sept 2025 – April 2026
- **Data cost:** ₹0 — all public / open sources

## 1. What we are building, in one breath

**The elevator line:** "Wards within 1 km of a data centre run several degrees hotter and have far less tree canopy. Closing that gap in Ward 12 needs roughly N trees, costs about ₹Z, and would cut local surface temperature by an estimated W°C over five years."

That single sentence is the whole project: it goes from diagnosis (where and why it's hot) straight to prescription (what to plant, where, at what cost, for what benefit). Most urban-heat projects stop at the map. Ours doesn't.

There are plenty of academic maps of urban heat in Indian cities, and there are polished Western tools (American Forests' Tree Equity Score, WRI's Cool Cities Lab, Google's heat pilots). What does not exist is a usable, ward-level, India-specific tool that a citizen or a municipal planner can open and act on. That gap is the project.

**Two audiences, one engine.** The same processed data drives two front-ends:

- **Citizen view** — a clean colour-coded map. Tap a ward, see how hot it is, how much canopy it has, which native trees suit it, and a plain-language action plan. Download a report.
- **Planner / scientist view** — raw layers (LST, NDVI, canopy, vulnerability), five-year trends, the data-centre analysis, confidence values, and GeoJSON/CSV export for QGIS.

## 2. The core contribution (our novelty)

Three things, chained. Individually each is modest; chained together they are the reason this isn't just another NDVI-vs-temperature study.

### 2.1 The priority score

We combine three independent signals into one ward-level number:

```
Priority = ƒ( high surface temperature , low tree canopy , high human vulnerability )
```

A ward that is hot, treeless, and densely populated by heat-vulnerable people scores Priority 1. The score — not the individual maps — is the primary deliverable.

### 2.2 The data-centre heat-contribution layer (the headline)

This is the piece no comparable student project has. Data-centre build-out is exploding in Pune and Bengaluru, and it is a real, current, heat-relevant story.

- Map known data-centre locations in the study city.
- Draw distance buffers (e.g. 500 m / 1 km / 2 km) using building-footprint data.
- Compare surface temperature and canopy inside vs outside those buffers, and produce a quotable finding: "data-centre-adjacent wards show X°C higher mean LST and Y% lower canopy."

### 2.3 The cost / impact estimator (what makes it policy-ready)

Cheap to build — a lookup table over published per-tree cost and CO₂ sequestration figures, applied to the gap the map already found. It converts a red ward into an action plan:

"Closing Ward 12's canopy gap ≈ N trees · ≈ ₹Z · ≈ −W°C local LST over 5 yrs."

**Honest note for the viva:** the cooling and cost numbers are estimates from published coefficients, not our own field measurements. We will state that plainly and cite the sources — an examiner respects a stated assumption far more than a hidden one.

## 3. Where the neural network lives

The project has exactly one neural network at its core, and it earns its place. We are not bolting on a model to look impressive — the model fixes a real weakness in the naïve approach.

### 3.1 The problem the NN solves

NDVI alone can't see trees. NDVI is a colour formula: it tells you a pixel is "green and leafy," nothing more. A lawn, a cricket outfield, a farm plot and a real shade tree all read as green. But a grass field gives almost no cooling shade, while a tree does. If we score wards on NDVI alone, a ward full of lawns looks "well covered" when it has zero canopy.

### 3.2 What we actually do — and an honest resolution caveat

**Read this before committing the model design:** You cannot outline individual tree crowns on Sentinel-2. Sentinel-2 is 10 m per pixel; many tree crowns are smaller than a single pixel. Any claim of "drawing around every tree" on Sentinel-2 will be picked apart in the viva. So we split the job in two, and each half is defensible:

**Layer A — Tree layer from a pretrained canopy model (defensible, no training needed).** Meta / WRI ~1 m Canopy Height Maps (and DeepForest for crown detection where higher-res tiles exist). These already solve tree detection at a resolution Sentinel-2 can't reach. We consume them as our canopy layer rather than pretending to reproduce them.

**Layer B — Land-cover segmentation with our own U-Net (this is the NN we build).** A U-Net segments each Sentinel-2 tile into classes — built-up / tree-canopy-cover / grass-&-crop / water / bare — which Sentinel-2 can support at the cover (area) level, as opposed to counting individual trees.

**Output:** per-ward % true canopy cover that can't be fooled by a football field — the input to the priority score.

**Why U-Net:** it's the standard encoder-decoder for pixel-wise segmentation, well documented, and small enough to train on free Colab/Kaggle GPUs. We can also start from a pretrained backbone and fine-tune.

### 3.3 Optional stretch — a prediction layer

If Layers A + B are clean and there's time after the January build, add a forecasting layer: use 5–10 years of historical Landsat to project which wards will become heat islands, from canopy-loss and built-up-growth trends. Explicitly optional — we will not promise two models and deliver two half-working ones.

**Scope-control rule:** The prediction layer ships only if canopy segmentation + the priority score + both UIs are done and stable. Otherwise it stays a "future work" slide.

## 4. System architecture

Three stages: an offline data/ML pipeline that does the heavy geospatial work, a backend that stores and serves the results, and two front-ends. The expensive satellite processing happens ahead of time, not on every user click.

```
[ Google Earth Engine ]  Landsat 8/9 thermal · Sentinel-2 · historical archive
            │  export tiles + per-ward stats
            ▼
[ Python ML pipeline ]  U-Net land-cover · canopy-height merge · LST calc
            │  priority score · data-centre buffers · cost/impact
            ▼
[ FastAPI backend ]  REST API  ◄──►  [ Firebase: Auth + Firestore + Storage ]
            │                              saved reports · user history · files
            ▼
[ React front-end ]   Citizen view   ·   Planner / Scientist view
```

### 4.1 Why this split

- **Pre-compute, don't live-compute.** Earth Engine exports and U-Net inference run in batch per city. The live app just serves finished GeoJSON + numbers. Fast, cheap, demo-safe.
- **Firebase for the app layer.** Auth, Firestore (saved reports + history), and Storage (generated PDF/GeoJSON files) — minimal backend code, generous free tier.
- **FastAPI in front of the data.** A thin Python API serves ward data and triggers report generation. Python because the whole pipeline is already Python — one language across the stack.

### 4.2 Component ownership (the four-person rule)

Each core area has one owner who can whiteboard it without notes.

| Area | Owns | Must be able to explain |
|---|---|---|
| Geo pipeline | Earth Engine, LST, NDVI, exports | emissivity correction; why LST ≠ air temp |
| ML / U-Net | segmentation model, canopy merge | U-Net architecture; the 10 m resolution caveat |
| Backend + data | FastAPI, Firestore schema, scoring | how the priority score is composed; API shape |
| Frontend + UX | both React views, maps, reports | the citizen→planner flow; Firebase auth |

## 5. Every UI screen

Fifteen screens across shared auth, the citizen flow, and the planner flow.

### 5.1 Shared / authentication

- **S1 — Splash / Landing.** Project name, one-line value prop, two buttons: Explore as Citizen / Sign in as Planner.
- **S2 — Login / Sign-up (Firebase Auth).** Email + Google sign-in via Firebase. Citizens can browse without an account; an account is only needed to save reports and see history. Planners sign in to unlock the scientist view.
- **S3 — Role / mode select.** After login, choose Citizen or Planner mode (a planner can switch to the simple view any time).

### 5.2 Citizen flow

- **S4 — City & ward search.** Pick the city (Pune by default), then search or tap a ward. Autocomplete on ward name/number.
- **S5 — Heat-map home.** The main screen. A colour-coded ward map — red = urgent, green = healthy — over the city. Legend, layer toggle (Heat / Canopy / Priority), and a "most urgent wards" list beside it.
- **S6 — Ward detail.** Tap a ward → its card: priority rank, mean surface temperature, % tree canopy, population-vulnerability note, and a short recommended-native-species list.
- **S7 — Action plan (diagnosis → prescription).** For the selected ward: trees needed to close the canopy gap, estimated cost, estimated CO₂ and cooling benefit over 5 years, with every figure marked as an estimate and its source noted.
- **S8 — Download / report confirmation.** Generates a PDF + map image, stores them in Firebase Storage, writes a record to the user's history, and offers share/download.

### 5.3 Planner / scientist flow

- **S9 — Analyst dashboard.** Same map, more control. Toggle raw layers independently: LST, NDVI, U-Net land-cover, canopy-height, vulnerability. Opacity sliders, basemap switch.
- **S10 — Ward analytics (time series).** Per-ward charts: 5-year LST trend, canopy trend, and the score breakdown showing how much each factor contributed. Confidence values shown, not hidden.
- **S11 — Data-centre analysis.** The headline screen. Data-centre locations with distance buffers; a side-by-side comparison of LST and canopy inside vs outside buffers; the quotable X°C / Y% result.
- **S12 — Export.** Export per-ward data as GeoJSON and CSV for QGIS/analysis, plus a methodology panel (data sources, emissivity correction, index formulas, assumptions).

### 5.4 Reports & history (needs the backend)

- **S13 — My Reports.** A list of every report the user has generated — ward, city, date, mode — read from Firestore, each row re-openable or re-downloadable.
- **S14 — Saved-report detail.** Reopens a stored report exactly as generated (snapshot of the numbers at that date), so a user can compare an old pull against the current data.
- **S15 — Settings / language.** Account, English/Hindi toggle, units, and default city.

## 6. Backend & data model

### 6.1 What the backend does

- Serve per-ward processed data (score, LST, canopy, vulnerability, geometry) to both front-ends.
- Generate a report on demand (compose the numbers → render a PDF → store the file → write a history record).
- Store and list each user's saved reports (history).
- Serve the data-centre buffer analysis and the cost/impact estimates.

### 6.2 Split of responsibilities

| Concern | Handled by | Notes |
|---|---|---|
| Authentication | Firebase Auth | email + Google; ID tokens verified by FastAPI |
| Saved reports / history | Firestore | one collection per user; see schema below |
| Generated files (PDF/GeoJSON) | Firebase Storage | URL stored on the report record |
| Ward data + scoring API | FastAPI | reads pre-computed data, exposes REST endpoints |
| Heavy geo/ML processing | Offline Python + GEE | batch, not per-request |

### 6.3 Firestore schema (sketch)

```
users/{uid}
  ├─ displayName, email, role: 'citizen'|'planner', lang: 'en'|'hi'
  └─ reports/{reportId}
        ├─ city: 'pune'   ward: 12   mode: 'citizen'
        ├─ createdAt: timestamp
        ├─ snapshot: { lst, canopyPct, priority, vulnerability }
        ├─ actionPlan: { trees, costINR, coolingC, co2t }
        └─ files: { pdfUrl, mapPngUrl, geojsonUrl }
```

**Why store a snapshot:** saved reports capture the numbers as they were on that date. When the pipeline is re-run with newer imagery, an old report still shows its original values — that's what makes the history genuinely useful rather than just a bookmark.

### 6.4 Core API endpoints (FastAPI)

| Method + path | Returns |
|---|---|
| `GET /cities` | available cities and their ward geometry |
| `GET /wards/{city}` | per-ward score, LST, canopy, vulnerability |
| `GET /wards/{city}/{id}` | full detail for one ward + species list |
| `GET /datacentres/{city}` | DC locations, buffers, inside-vs-outside stats |
| `POST /reports` | generate + store a report, return its id + file URLs |
| `GET /reports` (auth) | the signed-in user's report history |

## 7. Datasets — all free / open

| Data | Source | Used for |
|---|---|---|
| Land surface temperature | Landsat 8/9 TIRS via Google Earth Engine | the heat layer (≈30 m, thermal) |
| Vegetation / NDVI | Sentinel-2 via Earth Engine | greenery index (10 m) |
| Tree canopy height | Meta / WRI Canopy Height (~1 m) | the true tree layer (Layer A) |
| Land-cover labels | ESA WorldCover / Dynamic World | training labels for the U-Net |
| Ward boundaries | City muni / open-data portal, OSM | aggregating everything to wards |
| Building footprints | OpenStreetMap / Microsoft footprints | data-centre buffers, built-up area |
| Population / vulnerability | Census 2011 ward data | the vulnerability layer |
| Data-centre locations | public listings / OSM / news | the headline analysis |
| Cost & CO₂ coefficients | published urban-forestry studies | the cost/impact estimator |

**The one real data risk — flag it now, not in March:** Ward boundary shapefiles for Indian cities are inconsistent. This is the single most likely thing to bite us. Mitigation: confirm clean ward boundaries for Pune in the very first feasibility week; if they don't exist, switch to Bengaluru before committing. Everything else aggregates to wards, so this must be solved first.

## 8. The ML / data pipeline, step by step

1. **Acquire & mask** — pull Landsat + Sentinel-2 scenes for the city over the study window in Earth Engine; cloud-mask and composite.
2. **Compute LST** — convert thermal bands to brightness temperature, apply emissivity correction using NDVI-derived emissivity, output surface temperature.
3. **Compute NDVI** — standard index from red/NIR as a first-pass greenery signal.
4. **Segment land-cover (U-Net)** — tile the Sentinel-2 imagery, run the trained U-Net, get per-pixel classes; derive % true canopy cover per area.
5. **Merge canopy-height layer** — overlay the pretrained ~1 m canopy data (Layer A) to sharpen the tree signal beyond Sentinel-2's limit.
6. **Aggregate to wards** — zonal statistics: mean LST, % canopy, built-up %, population per ward.
7. **Compute vulnerability** — combine density + census indicators into a normalized ward vulnerability score.
8. **Compute priority score** — weighted combination of (heat, canopy deficit, vulnerability); normalize and rank wards.
9. **Data-centre buffers** — buffer DC points, run inside-vs-outside zonal stats, produce the X°C / Y% comparison.
10. **Cost / impact** — apply per-tree cost & sequestration coefficients to each ward's canopy gap.
11. **Export** — write per-ward GeoJSON + tiles + stats for the backend to serve.

### 8.1 Training the U-Net

- **Inputs:** Sentinel-2 multi-band tiles. **Labels:** ESA WorldCover / Dynamic World land-cover classes as ground truth.
- **Model:** U-Net (optionally a pretrained encoder backbone), trained on free Colab/Kaggle GPU.
- **Metric:** per-class IoU / F1, reported honestly — especially for the canopy class, which is the one that matters.
- **Baseline to beat:** plain NDVI threshold. Showing "NDVI said 60% green, our model said 22% actual canopy" is the money slide for the ML component.

## 9. Tech stack

| Layer | Choice | Why |
|---|---|---|
| Satellite processing | Google Earth Engine | free, hosted, all imagery pre-loaded |
| ML | Python · PyTorch · U-Net | standard for segmentation; free GPU on Colab/Kaggle |
| Geo processing | Python · rasterio · geopandas | LST/NDVI math, zonal stats, exports |
| Backend API | FastAPI (Python) | one language across data + API; light |
| Auth / DB / files | Firebase (Auth · Firestore · Storage) | minimal ops, free tier |
| Frontend | React | two views share components |
| Maps | Leaflet or Mapbox GL + GeoJSON | interactive choropleth + raster overlays |
| Reports | server-side PDF (report lib) | the downloadable citizen deliverable |

## 10. Timeline (built around placements)

Placement season (roughly Sept–Dec) is the priority. The heavy build is deliberately parked until January; autumn is kept light and is only for de-risking.

| Window | Focus | Concrete output |
|---|---|---|
| Sep–Oct (light, 4–6 h/wk) | Feasibility only | Pune ward boundaries confirmed; one LST map; one NDVI map; naïve NDVI canopy baseline |
| End Oct | GATE | go / switch-city decision made on evidence |
| Nov–Dec (minimal) | Placements | repo alive; literature notes; nothing new started |
| Jan–Feb (heavy) | The real build | full pipeline · trained U-Net · priority score · both UIs · backend + history |
| March | Evaluate & write | U-Net metrics vs NDVI baseline; DC finding; error analysis; report |
| April | Buffer & demo | polish, fix what breaks, rehearse the demo |

**The October gate:** If clean Pune ward boundaries can't be found, or the naïve baseline can't be beaten, we switch city or narrow scope — in October, when it's cheap. Not in March, when it isn't.

## 11. What "done" looks like

- **Minimum (must ship):** one city, working citizen map + ward detail + action plan, the priority score, the data-centre finding, and saved-report history. A demo that runs.
- **Target:** the above + trained U-Net beating the NDVI baseline with reported metrics + the full planner view with export + Hindi toggle.
- **Stretch:** the 5-year prediction layer, and the per-ward data published as an open dataset for the city.
