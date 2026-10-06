# 🌳 SHADE — Urban Heat & Tree-Canopy Intelligence

> **A ward-level decision-support system for identifying urban heat-vulnerable areas and prioritising tree-canopy interventions across Pune.**

SHADE combines **land-surface temperature, vegetation, tree-cover, built-up area and vulnerability data** to identify wards where urban greening can have the greatest impact.

It provides two interfaces:

- 🌱 **Citizen View** — simple, accessible ward-level heat, canopy and action-plan information.
- 🏙️ **Planner View** — analytical layers, ward analytics, data-centre analysis, exports and methodology.

The project currently focuses on **41 municipal wards of Pune**.

---

## ✨ Key Features

### 🌱 Citizen View

Citizens can explore Pune without creating an account.

- Interactive Pune ward map
- Search wards by number or name
- Priority, Heat and Tree Cover views
- Most urgent wards list
- Ward-level statistics
- Land Surface Temperature (LST)
- Tree-cover percentage
- Vulnerability Score
- NDVI and built-up indicators
- Ward-specific action plans
- Estimated trees required
- Estimated intervention cost
- Estimated cooling benefit
- Estimated CO₂ impact
- Firebase authentication when saving reports
- Save reports
- Download generated PDF reports
- View saved reports
- Google Sign-In and Email/Password authentication
- Resizable sidebar for better map exploration

The project design intentionally distinguishes between **planning estimates** and field measurements. Cost, tree-count, cooling and CO₂ values are presented as estimates based on the available coefficients and assumptions.

---

## 🏙️ Planner View

The Planner dashboard provides a more detailed analytical interface for urban planners and researchers.

### Map Layers

- Priority Score
- Land Surface Temperature
- Tree Cover
- NDVI
- Built-up Area
- Vulnerability Score

The map uses ward-level choropleths rather than pixel-level raster heatmaps.

### Ward Analytics

Selecting a ward provides:

- Priority score
- Priority rank
- Mean LST
- Tree-cover percentage
- NDVI
- Built-up percentage
- Vulnerability Score
- Score contribution breakdown
- Available observations/confidence information

### Data-Centre Analysis

The Planner View also provides:

- Data-centre locations
- Distance rings
- Ring-level analysis
- LST comparison
- Tree-cover comparison
- Reference/look-alike comparisons
- Data-centre-specific analysis

The analysis is presented as a **measured surface-temperature comparison** rather than claiming that data centres directly cause surrounding areas to be hotter.

### Export & Methodology

Planner users can also access:

- GeoJSON export
- CSV export
- Dataset information
- Methodology
- Data-source descriptions
- Analysis assumptions

---

# 🧠 How SHADE Works

SHADE combines three major signals into a ward-level priority score:

```text
                    ┌─────────────────────┐
                    │  Surface Heat (LST) │
                    └──────────┬──────────┘
                               │
                               ▼
┌────────────────┐      ┌───────────────┐      ┌──────────────────┐
│ Tree Canopy    │ ───► │ Priority      │ ◄─── │ Vulnerability    │
│ Deficit        │      │ Score         │      │ Score            │
└────────────────┘      └───────┬───────┘      └──────────────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │ Ward Prioritisation │
                     └──────────┬──────────┘
                                │
                                ▼
                     ┌─────────────────────┐
                     │ Action Plan         │
                     │ Trees / Cost /      │
                     │ Cooling / CO₂       │
                     └─────────────────────┘
```

The project's core idea is:

> **Find the wards that need trees most — and translate that diagnosis into an actionable intervention plan.**

---

# 🛰️ Data & Methodology

SHADE integrates processed geospatial datasets rather than performing heavy satellite processing during normal application use.

### Surface Temperature

Land Surface Temperature is derived from **Landsat thermal imagery**.

LST represents **surface temperature**, not air temperature.

### Vegetation

Vegetation information uses:

- Sentinel-2 NDVI
- Provisional WorldCover 2021 tree-cover data

NDVI represents vegetation greenness and should not be interpreted as an exact tree-canopy measurement.

### Vulnerability

The vulnerability layer is a **normalized 0–1 relative score** based on the available census-derived vulnerability data.

It should therefore be interpreted as a relative indicator rather than a direct measure of individual-level vulnerability.

### Priority Score

The priority score combines:

```text
Heat
+
Canopy Deficit
+
Vulnerability
```

to rank wards according to intervention need.

---

# 🏗️ System Architecture

```text
                    ┌──────────────────────┐
                    │     React Frontend   │
                    │                      │
                    │  Citizen │ Planner   │
                    └──────────┬───────────┘
                               │
                               │ HTTP / REST
                               ▼
                    ┌──────────────────────┐
                    │      FastAPI         │
                    │       Backend        │
                    └──────────┬───────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
        Ward Data        Data Centre       Reports
        & Scoring         Analysis          & Auth
              │                │                │
              └────────────────┼────────────────┘
                               │
                               ▼
                    ┌──────────────────────┐
                    │ Processed Geospatial │
                    │       Data           │
                    └──────────────────────┘

                    Firebase
                       │
             ┌─────────┴─────────┐
             │                   │
          Firebase Auth       Firestore
```

---

# 🛠️ Technology Stack

## Frontend

- React
- Vite
- React Router
- Leaflet
- React-Leaflet
- Recharts
- CSS

## Backend

- Python
- FastAPI
- Uvicorn
- GeoPandas / geospatial processing
- Report generation

## Authentication & Reports

- Firebase Authentication
- Email/Password authentication
- Google Sign-In
- Firestore for persistent report storage when configured

## Geospatial / Data

- Landsat
- Sentinel-2
- WorldCover
- GeoJSON
- OpenStreetMap basemap

---

# 📁 Project Structure

```text
SHADE/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── reports.py
│   │   ├── scoring.py
│   │   ├── estimator.py
│   │   └── pdf.py
│   │
│   ├── tools/
│   └── test_api.py
│
├── data/
│   ├── wards.geojson
│   ├── vulnerability.csv
│   └── ward_population.csv
│
├── frontend/
│   ├── public/
│   │
│   └── src/
│       ├── assets/
│       ├── auth/
│       │   ├── AuthProvider.jsx
│       │   ├── RequireAuth.jsx
│       │   ├── authContext.js
│       │   └── errors.js
│       │
│       ├── components/
│       │   └── ResizableSidebar.jsx
│       │
│       ├── pages/
│       │   ├── LandingPage.jsx
│       │   ├── CitizenDashboard.jsx
│       │   ├── LoginPage.jsx
│       │   ├── SignupPage.jsx
│       │   └── ReportsPage.jsx
│       │
│       ├── services/
│       │   ├── api.js
│       │   └── reports.js
│       │
│       ├── App.jsx
│       ├── App.css
│       ├── index.css
│       └── main.jsx
│
├── docs/
├── requirements-backend.txt
├── requirements-geo.txt
├── requirements-ml.txt
└── README.md
```

---

# 🚀 Getting Started

## Prerequisites

Make sure the following are installed:

- **Git**
- **Python 3.x**
- **Node.js 20.19 or newer**
- npm

Check your Node version:

```bash
node -v
```

It should be **20.19 or newer**.

Check Python:

```bash
python --version
```

---

# 1. Clone the Repository

```bash
git clone https://github.com/Jatin1628/Shade.git
cd Shade
```

---

# 2. Backend Setup

Open a terminal in the project root.

Create a Python virtual environment:

### Windows — Git Bash

```bash
python -m venv .venv
```

Activate it:

```bash
source .venv/Scripts/activate
```

You should see:

```text
(.venv)
```

Install backend dependencies:

```bash
pip install -r requirements-backend.txt
```

Start the FastAPI server:

```bash
cd backend
uvicorn app.main:app --reload
```

The backend will run at:

```text
http://127.0.0.1:8000
```

FastAPI Swagger documentation is available at:

```text
http://127.0.0.1:8000/docs
```

---

# 3. Frontend Setup

Open a **second terminal**.

From the project root:

```bash
cd frontend
```

Install dependencies:

```bash
npm install
```

---

## 🔐 Firebase Configuration

SHADE uses Firebase Authentication for user login and report management.

Supported authentication methods:

- Email/Password
- Google Sign-In

### Configure Firebase

Before running the frontend, create the following file:

```text
frontend/.env.local
---

# 4. Start the Frontend

From:

```text
frontend/
```

run:

```bash
npm run dev
```

Vite will normally start at:

```text
http://localhost:5173
```

If port `5173` is already occupied, Vite may use another port such as:

```text
http://localhost:5174
```

Use the URL shown in the terminal.

### Important

Use:

```text
http://localhost:5173
```

or the port Vite provides.

Do not manually replace it with:

```text
http://127.0.0.1:5173
```

when testing the Firebase frontend configuration.

---

# 🔗 Application Routes

| Route | Purpose | Authentication |
|---|---|---|
| `/` | Landing page | Public |
| `/citizen` | Citizen dashboard | Public |
| `/login` | Login | Public |
| `/signup` | Account creation | Public |
| `/planner` | Planner dashboard | Required |
| `/reports` | Saved reports | Required |

Citizens can explore the map without logging in. Authentication is required when accessing protected functionality such as saving/viewing reports and the Planner View.

---

# 🔌 Backend API

Base URL:

```text
http://127.0.0.1:8000
```

### Ward Data

Get all Pune wards:

```http
GET /wards/pune
```

Get the most urgent wards:

```http
GET /wards/pune/top?n=10
```

Get a specific ward:

```http
GET /wards/pune/{ward_id}
```

### Data Centres

```http
GET /datacentres/pune
```

### Reports

Save a report:

```http
POST /reports
```

Get saved reports:

```http
GET /reports
```

Download a report:

```http
GET /reports/{report_id}/pdf
```

Open the complete API documentation at:

```text
http://127.0.0.1:8000/docs
```

---

# 🔐 Authentication

SHADE uses **Firebase Authentication**.

Supported methods:

- Email + Password
- Google Sign-In

The frontend obtains a Firebase ID token after authentication and sends it to protected backend endpoints using:

```text
Authorization: Bearer <Firebase ID token>
```

### Report Storage

There are two possible backend configurations.

### With Firebase service-account configuration

Reports can be stored persistently using Firestore.

### Without the service-account key

SHADE automatically uses **temporary in-memory report storage**.

This is useful for:

- development
- testing
- demonstrations
- team members who don't have the private Firebase service-account key

Temporary reports disappear when the backend server restarts.

**Never commit the Firebase service-account key to GitHub.**

---

# 🧪 Testing the Application

After starting both backend and frontend:

### Citizen Flow

1. Open:

```text
http://localhost:5173/citizen
```

2. Search for a ward.
3. Select a ward.
4. Explore:
   - Priority
   - Heat
   - Tree Cover
5. Open the ward details.
6. View the Action Plan.
7. Sign in if you want to save a report.
8. Click **Save Report**.
9. Download the PDF.
10. Open **My Reports**.

### Planner Flow

1. Open:

```text
http://localhost:5173/planner
```

2. Sign in if required.
3. Explore the available map layers.
4. Change layer opacity.
5. Select a ward.
6. Review ward analytics.
7. Explore data-centre analysis.
8. Try GeoJSON/CSV export.
9. Review the methodology section.

---

# 📊 Current Data Interpretation

### Priority Score

Higher score = greater intervention priority.

It combines:

```text
Heat + Canopy Deficit + Vulnerability
```

### LST

LST means:

> **Land Surface Temperature**

It is **not air temperature**.

### NDVI

NDVI measures vegetation greenness and is broader than tree-cover measurement.

### Tree Cover

The current tree-cover baseline uses provisional WorldCover-derived data.

### Vulnerability Score

The vulnerability score is a normalized:

```text
0 – 1
```

relative index based on the available census-derived data.

---

# ⚠️ Important Limitations

SHADE is a **decision-support and planning tool**, not a replacement for field surveys.

### Ward-level data

The current application serves processed values at the **ward level** rather than pixel-level raster layers.

Therefore, the map displays a **ward-level choropleth** rather than a continuous satellite heatmap.

### Vulnerability data

The vulnerability layer is based on available census-derived data and should be interpreted as a relative score.

### Action-plan estimates

Tree counts, costs, cooling and CO₂ values are **planning estimates**.

They depend on assumptions such as:

- canopy-per-tree estimates
- planting costs
- maintenance scenarios
- cooling coefficients
- CO₂ sequestration assumptions

They should not be interpreted as field measurements.

### Data-centre analysis

The data-centre analysis compares measured surface-temperature and vegetation characteristics around analysed sites.

It should not automatically be interpreted as proof that data centres cause surrounding areas to become hotter.

---

# 🎯 Project Goals

SHADE aims to bridge the gap between:

```text
Satellite / Geospatial Data
           ↓
     Urban Diagnosis
           ↓
    Ward Prioritisation
           ↓
    Action Planning
           ↓
     Decision Support
```

Instead of simply showing **where Pune is hot**, the system attempts to answer:

> **Where should urban greening be prioritised, why, and what could an intervention look like?**

---

# 👥 Project Workstreams

The project was divided into major workstreams covering:

1. **Geospatial Pipeline**
   - Ward boundaries
   - LST
   - Data-centre analysis

2. **ML / Canopy Analysis**
   - Vegetation and canopy modelling

3. **Backend & Data**
   - FastAPI
   - Firebase
   - Scoring
   - Action-plan estimation
   - Reports

4. **Citizen Frontend**
   - Landing
   - Citizen map
   - Ward details
   - Action plans
   - Reports

5. **Planner & Integration**
   - Planner dashboard
   - Advanced analytical layers
   - Data-centre analysis
   - Exports
   - Methodology
   - Integration and QA

The project specification defines the Citizen flow as S1–S8 and the Planner/integration flow as S9–S12. Urban Heat & Tree-Canopy Priori…

---

# 🔮 Future Improvements

Potential extensions include:

- Historical 5-year LST trends
- Historical canopy trends
- Improved tree-canopy segmentation
- More detailed native-species recommendations
- Additional Indian cities
- Improved vulnerability datasets
- Field validation
- More detailed intervention optimisation
- Persistent cloud-based report storage for all environments
- Additional planner export formats

---

# 📜 License

This project was developed as an academic capstone project.

---

# 🌳 SHADE

**Urban Heat & Tree-Canopy Intelligence**

> **Making Pune cooler & greener.**
