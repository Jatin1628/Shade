# Geo pipeline (Person 1)

Covers ward boundaries, land surface temperature (LST), and the data-centre buffer analysis.

## Setup

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements-geo.txt
```

### One-time Earth Engine setup (each person who runs `03_lst_gee.py`)

1. Register a Google Cloud project for free non-commercial use at <https://code.earthengine.google.com/register>. Choose unpaid usage, then academic/research.
2. Make sure the Earth Engine API is enabled on that project. The registration flow usually does this.
3. Authenticate once: `.venv\Scripts\earthengine authenticate`. This opens a browser.
4. Save your project once: `.venv\Scripts\earthengine set_project <project-id>`. After that, `03_lst_gee.py` needs no `--project`.

## Run order

Run the scripts from the repo root with `.venv\Scripts\python geo\<script>`.

| Step | Script | Needs | Output |
|---|---|---|---|
| 1 | `01_validate_boundaries.py` | — | `data/qa/boundary_qa.md`, a quick-look PNG per candidate |
| 2 | `02_build_wards.py` | — | `data/wards.geojson`, `data/pune_pmc_outline.geojson` |
| 3 | `03_lst_gee.py` | Earth Engine | `data/raster/*.tif`, `data/raster/scenes_<year>.csv` |
| 4 | `04_ward_lst.py` | step 3 | LST columns in `data/wards.geojson`, plus `data/wards_lst.csv` |
| 5 | `05_lst_maps.py` | step 4 | `docs/figures/lst_<year>_pune.png` (the October-gate LST map) |
| — | `qa_datacentre_sites.py` | verified DC coordinates | `data/qa/datacentre_sites_s2.png` (Sentinel-2 check of each site, 2022 vs 2026) |
| 6 | `06_datacentre_rings.py` | step 3 + verified DC coordinates | `data/datacentre_rings.csv`, `data/datacentres.geojson`, `data/datacentre_rings.geojson` |
| 7 | `07_datacentre_figure.py` | step 6 | `docs/figures/datacentre_rings_<year>.png` |

## Outputs for the team

- **`data/wards.geojson`** (EPSG:4326) has one feature per PMC ward (41).
  - Always present: `ward_id` (1–41), `ward_name`, `city`, `area_km2`.
  - Added by step 4:
    - `lst_mean`: the main heat value for the maps, in °C.
    - `lst_median`, `lst_std`, `lst_p90`: other summaries of the same pixels.
    - `lst_builtup_mean`: LST over built-up pixels only. **Suggested for the priority score's heat term** (Person 3). In daytime, Pune's bare fringe land and the Lohegaon airfield run hotter than where people live, and `lst_mean` counts them. The two rank wards similarly (Spearman ρ = 0.93), but the built-up version measures heat where people actually are.
    - `lst_valid_frac`, `n_obs_mean`: confidence values.
    - `tree_frac_wc`, `built_frac_wc`: WorldCover 2021 fractions. `tree_frac_wc` is a stand-in until Person 2's U-Net canopy is ready.
    - `lst_ndvi_mean`, `ndvi_l8_mean`: the cross-check estimate and Landsat NDVI.
    - `lst_year`: the hot season the values come from.
- **`data/raster/`** holds 30 m GeoTIFFs in EPSG:32643, covering PMC, Pimpri-Chinchwad and Hinjewadi. Nodata is -9999.
- **`data/raw/datacentres_pune.csv`** is the data-centre inventory. Only rows with `use_in_analysis = yes` go into the analysis. Those were located on satellite view and checked against 2026 Sentinel-2 imagery. `site_group` joins points on the same campus. The `approx_*` columns are locality-level and exist only for overview maps.
- **For the data-centre API endpoint and screen (Person 3's `GET /datacentres/{city}`, Person 5's S11):**
  - `data/datacentres.geojson` has every located site, with `use_in_analysis` saying why a site is in or out.
  - `data/datacentre_rings.geojson` has the ring polygons, each with `lst_mean`, `lst_excess` (°C above what the ground cover predicts), `trees_pct`, `built_pct` and `excess_percentile_vs_lookalikes`.
  - `data/datacentre_rings.csv` is the full table.

## Method notes (viva)

- **`lst` is the USGS Collection 2 Level-2 surface temperature (`ST_B10`)**, which is already corrected for the atmosphere and for emissivity. We don't apply an NDVI emissivity correction on top of it, because that would correct it twice.
- **`lst_ndvi` is our own calculation.** It takes Level-1 brightness temperature and applies proportion-of-vegetation emissivity (Sobrino 2004): ε = 0.004·Pv + 0.986, then LST = BT / (1 + (λ·BT/ρ)·ln ε). Step 4 prints how well it agrees with `lst`.
- **LST is not air temperature.** It is how hot the ground and roofs are, as seen from space at about 10:57 am IST (the Landsat overpass) on clear hot-season days (Mar–May).
