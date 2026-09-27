# City decision: Pune (boundary gate)

**Recommendation: commit to Pune.** Clean ward boundaries exist for the current ward system, so there is no need to fall back to Bengaluru.

Prepared by Person 1 (geo pipeline), 27 Sep 2026. QA script: `geo/01_validate_boundaries.py`. Full QA output: `data/qa/boundary_qa.md`.

## Boundaries we use

**PMC Electoral Wards 2025**: 41 prabhags (wards), the current delimitation. The ward structure was finalised on 6 Oct 2025 and used for the 15 Jan 2026 PMC election.

- Geometry comes from [OpenCity: PMC Wards Info](https://data.opencity.in/dataset/pune-wards-info) (KML, public domain). The digitisation method is not documented.
- Ward names come from the [2026 PMC election ward list](https://en.wikipedia.org/wiki/2026_Pune_Municipal_Corporation_election).
- Output: `data/wards.geojson`, 41 wards, with fields `ward_id` (1–41), `ward_name`, `city`, `area_km2`. The CRS is EPSG:4326.

| Check | Result |
|---|---|
| Wards present | 41 of 41, IDs 1–41, no duplicates |
| Invalid geometries | 0 |
| Contiguous city | Yes (one outline) |
| Overlaps between wards | 3 digitising slivers (2 ha total), removed in `geo/02_build_wards.py` |
| Gaps inside the city | 5 holes, 12.3 km², explained below |
| Total area | 480 km² |

The gaps are not errors. They are areas outside PMC's jurisdiction, mainly **Pune Cantonment** (Camp), which is governed by its own cantonment board. Every earlier boundary version, back to 2012, has the same ~12 km² of holes.

## Candidates considered

| Candidate | Wards | Why not used |
|---|---|---|
| DataMeet 2022 electoral wards | 58 | Superseded by the 2025 delimitation |
| DataMeet 2017 electoral wards | 41 | Old city limits (257 km²); misses the villages merged in 2021 |
| DataMeet 2012 electoral wards | 76 | Old city limits |
| PMC admin wards 2017 | 15 | Too coarse for ward-level prescriptions |

## Limitations the team should know

1. **Pune Cantonment has no ward score.** It is a separate local body with no PMC ward. The citizen map will show a hole in the middle of the city. We could add it later as a single extra zone if planners ask.
2. **Census 2011 data doesn't come on 2025 ward boundaries** (affects Person 3). A possible shortcut: the 2025 delimitation was drawn using Census 2011 populations, and PMC's draft ward-structure documents quote populations per ward (for example, Ward 38 has about 1.14 lakh people). If that per-ward table can be downloaded, the vulnerability layer can use it directly. Otherwise it needs areal interpolation from 2011 census wards. This lead has not been checked yet.
3. **Most data centres are outside PMC.** Of about 15 facilities listed publicly, only Nxtra Pune I in Kharadi (ward 4) is inside PMC. The rest are in Pimpri-Chinchwad (STT Dighi, Microsoft Pimpri and Bhosari, AdaniConneX) or in Hinjewadi, which falls under PMRDA (the Pune regional development authority). The data-centre analysis therefore has to be pixel-based, with distance rings around each site. It can't compare PMC wards. The LST raster already covers the wider metro area for this reason. The headline should read "areas within 1 km of a data centre…", not "data-centre-adjacent wards…".
