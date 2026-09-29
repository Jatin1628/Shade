import L from "leaflet";
import { useEffect, useMemo, useState } from "react";
import {
  MapContainer,
  TileLayer,
  GeoJSON,
  Marker,
  Popup,
  Circle,
  useMap,
} from "react-leaflet";

import "leaflet/dist/leaflet.css";

import {
  getWards,
  getWard,
  getDataCentres,
} from "./services/api";

import "./index.css";

const PUNE_CENTER = [18.5204, 73.8567];

function DataCentreMarkers({ dataCentres, onSelect }) {
  if (!dataCentres?.sites?.features) return null;

  return (
    <>
      {dataCentres.sites.features.map((feature) => {
        const [lng, lat] = feature.geometry.coordinates;
        const properties = feature.properties;

        return (
          <Marker
            key={properties.dc_id}
            position={[lat, lng]}
            eventHandlers={{
              click: () => onSelect(feature),
            }}
          >
            <Popup>
              <strong>{properties.name}</strong>
              <br />
              Operator: {properties.operator}
              <br />
              Capacity: {properties.capacity_mw} MW
              <br />
              Status: {properties.status}
            </Popup>
          </Marker>
        );
      })}
    </>
  );
}

function DataCentreRings({ dataCentres, selectedDataCentre }) {
  if (!selectedDataCentre) return null;
  if (!dataCentres?.rings?.features) return null;

  const selectedSiteGroup =
    selectedDataCentre.properties?.site_group;

  const selectedRings =
    dataCentres.rings.features.filter(
      (feature) =>
        feature.properties?.site_group === selectedSiteGroup
    );

  return (
    <>
      {selectedRings.map((feature, index) => {
        if (!feature.geometry) return null;

        const ringIndex =
          feature.properties?.ring_index ?? index;

        const isOuterRing = ringIndex >= 3;

        return (
          <GeoJSON
            key={`dc-ring-${selectedSiteGroup}-${ringIndex}`}
            data={feature}
            style={{
              color: isOuterRing ? "#4b8060" : "#27613d",
              weight: ringIndex === 0 ? 2 : 1.2,
              opacity: 0.75,
              fillColor: "#78b98a",
              fillOpacity:
                ringIndex === 0 ? 0.10 : 0.035,
              dashArray:
                ringIndex >= 3 ? "6 5" : undefined,
            }}
          />
        );
      })}
    </>
  );
}


function FitToWards({ wards }) {
  const map = useMap();

  useEffect(() => {
    if (!wards || wards.length === 0) return;

    const geoJsonLayer = new L.GeoJSON({
      type: "FeatureCollection",
      features: wards,
    });

    const bounds = geoJsonLayer.getBounds();

    if (bounds.isValid()) {
      map.fitBounds(bounds, {
        padding: [30, 30],
      });
    }
  }, [wards, map]);

  return null;
}

const LAYERS = {
  priority: {
    label: "Priority Score",
    shortLabel: "Priority",
    getValue: (p) => p.priority_score,
    format: (v) => v?.toFixed(2),
    defaultOpacity: 0.72,
  },

  heat: {
    label: "Surface Temperature",
    shortLabel: "LST",
    getValue: (p) => p.lst_builtup_mean,
    format: (v) => `${v?.toFixed(1)}°C`,
    defaultOpacity: 0.72,
  },

  canopy: {
    label: "Tree Cover",
    shortLabel: "Tree Cover",
    getValue: (p) => (p.tree_frac_wc ?? 0) * 100,
    format: (v) => `${v?.toFixed(1)}%`,
    defaultOpacity: 0.72,
  },

  ndvi: {
    label: "NDVI",
    shortLabel: "NDVI",
    getValue: (p) => p.ndvi_s2_mean,
    format: (v) => v?.toFixed(3),
    defaultOpacity: 0.72,
  },

  builtup: {
    label: "Built-up Area",
    shortLabel: "Built-up",
    getValue: (p) => (p.built_frac_wc ?? 0) * 100,
    format: (v) => `${v?.toFixed(1)}%`,
    defaultOpacity: 0.72,
  },

  vulnerability: {
    label: "Vulnerability",
    shortLabel: "Vulnerability",
    getValue: (p) => p.vulnerability_n,
    format: (v) => v?.toFixed(2),
    defaultOpacity: 0.72,
  },
};

function getColor(value, layer) {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "#9ca3af";
  }

  if (layer === "heat") {
    if (value >= 46) return "#7f1d1d";
    if (value >= 44) return "#dc2626";
    if (value >= 42) return "#f97316";
    if (value >= 40) return "#facc15";
    return "#65a30d";
  }

  if (layer === "canopy") {
    if (value < 10) return "#991b1b";
    if (value < 20) return "#ea580c";
    if (value < 30) return "#eab308";
    if (value < 40) return "#65a30d";
    return "#166534";
  }

  if (layer === "vulnerability") {
    if (value >= 0.75) return "#7f1d1d";
    if (value >= 0.5) return "#dc2626";
    if (value >= 0.25) return "#f97316";
    if (value >= 0.1) return "#facc15";
    return "#65a30d";
  }

  // Priority score
  if (value >= 0.7) return "#7f1d1d";
  if (value >= 0.55) return "#dc2626";
  if (value >= 0.4) return "#f97316";
  if (value >= 0.25) return "#facc15";
  if (value >= 0.1) return "#84cc16";
  return "#15803d";
}

function downloadFile(content, filename, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);

  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  URL.revokeObjectURL(url);
}

function exportGeoJSON(wards) {
  const geojson = {
    type: "FeatureCollection",
    features: wards || [],
  };

  downloadFile(
    JSON.stringify(geojson, null, 2),
    "shade_pune_wards.geojson",
    "application/geo+json"
  );
}

function exportCSV(wards) {
  if (!wards || wards.length === 0) return;

  const rows = wards.map((ward) => ward.properties);

  const columns = Object.keys(rows[0]);

  const csv = [
    columns.join(","),
    ...rows.map((row) =>
      columns
        .map((column) => {
          const value = row[column] ?? "";
          return `"${String(value).replace(/"/g, '""')}"`;
        })
        .join(",")
    ),
  ].join("\n");

  downloadFile(
    csv,
    "shade_pune_wards.csv",
    "text/csv;charset=utf-8"
  );
}

function App() {
  const [wards, setWards] = useState([]);
  const [selectedWard, setSelectedWard] = useState(null);
  const [wardDetails, setWardDetails] = useState(null);
  const [wardDetailsLoading, setWardDetailsLoading] = useState(false);
  const [dataCentres, setDataCentres] = useState(null);
  const [dcLoading, setDcLoading] = useState(false);
  const [selectedDataCentre, setSelectedDataCentre] = useState(null);
  const [activeLayer, setActiveLayer] = useState("priority");

  const [layerOpacity, setLayerOpacity] = useState({
    priority: 0.72,
    heat: 0.72,
    canopy: 0.72,
    ndvi: 0.72,
    builtup: 0.72,
    vulnerability: 0.72,
  });

  const toggleLayer = (layerKey) => {
    // Clicking the currently active layer turns the choropleth off.
    if (activeLayer === layerKey) {
      setActiveLayer(null);
      return;
    }

    // Otherwise this becomes the only visible choropleth layer.
    setActiveLayer(layerKey);
  };

  const changeOpacity = (layerKey, value) => {
    setLayerOpacity((previous) => ({
      ...previous,
      [layerKey]: Number(value),
    }));
  };

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    getWards()
      .then((data) => {
        setWards(data);
        setLoading(false);
      })
      .catch((err) => {
        console.error(err);
        setError("Unable to connect to the backend.");
        setLoading(false);
      });
  }, []);

  useEffect(() => {
    setDcLoading(true);

    getDataCentres()
      .then((data) => {
        console.log("Data centre API:", data);
        setDataCentres(data);
      })
      .catch((error) => {
        console.error("Failed to load data centres:", error);
        setDataCentres(null);
      })
      .finally(() => {
        setDcLoading(false);
      });
  }, []);

  const geoJsonData = useMemo(
    () => ({
      type: "FeatureCollection",
      features: wards,
    }),
    [wards]
  );

  const layerStyle = (feature) => {
    if (!activeLayer) {
      return {
        fillColor: "transparent",
        weight: 0,
        color: "transparent",
        fillOpacity: 0,
      };
    }

    const properties = feature.properties;
    const value = LAYERS[activeLayer].getValue(properties);

    return {
      fillColor: getColor(value, activeLayer),

      weight:
        selectedWard?.properties?.ward_id === properties.ward_id
          ? 3
          : 1,

      color:
        selectedWard?.properties?.ward_id === properties.ward_id
          ? "#111827"
          : "#ffffff",

      fillOpacity: layerOpacity[activeLayer],
    };
  };

  const onEachWard = (feature, layer) => {
    const properties = feature.properties;

    layer.bindTooltip(
      `<strong>Ward ${properties.ward_id}</strong><br/>
       ${properties.ward_name}`,
      {
        sticky: true,
      }
    );

    layer.on({
      click: async () => {
        setSelectedWard(feature);
        setWardDetailsLoading(true);

        try {
          const details = await getWard(
            feature.properties.ward_id
          );

          setWardDetails(details);
        } catch (error) {
          console.error("Failed to load ward details:", error);
          setWardDetails(null);
        } finally {
          setWardDetailsLoading(false);
        }
      },
      mouseover: (event) => {
        event.target.setStyle({
          weight: 3,
          color: "#111827",
          fillOpacity: 0.9,
        });
      },
      mouseout: (event) => {
        event.target.setStyle(layerStyle(feature));
      },
    });
  };

  const selectedProperties = selectedWard?.properties;
  const detailData = wardDetails?.properties || wardDetails;

  const heatContribution =
    detailData?.heat_n != null
      ? detailData.heat_n * 0.4
      : null;

  const canopyContribution =
    detailData?.canopy_deficit_n != null
      ? detailData.canopy_deficit_n * 0.4
      : null;

  const vulnerabilityContribution =
    detailData?.vulnerability_n != null
      ? detailData.vulnerability_n * 0.2
      : null;

  return (
    <div className="app">
      {/* HEADER */}
      <header className="topbar">
        <div className="brand">
          <div className="brand-icon">🌳</div>

          <div>
            <h1>SHADE</h1>
            <span>Urban Heat & Tree-Canopy Intelligence</span>
          </div>
        </div>

        <div className="header-right">
          <span className="city-badge">PUNE</span>
          <span className="planner-badge">PLANNER VIEW</span>
        </div>
      </header>

      {loading && (
        <div className="loading-screen">
          <div className="loader"></div>
          <p>Loading Pune ward data...</p>
        </div>
      )}

      {error && (
        <div className="error-screen">
          <h2>Backend connection failed</h2>
          <p>{error}</p>
          <p>
            Make sure FastAPI is running at{" "}
            <strong>127.0.0.1:8000</strong>.
          </p>
        </div>
      )}

      {!loading && !error && (
        <main className="dashboard">
          {/* LEFT SIDEBAR */}
          <aside className="sidebar">
            <section className="sidebar-section">
              <div className="section-label">MAP LAYERS</div>

              <div className="layer-controls">
                {Object.entries(LAYERS).map(([key, layer]) => {
                  const isActive = activeLayer === key;

                  return (
                    <div
                      key={key}
                      className={`layer-control ${isActive ? "active-layer" : ""
                        }`}
                    >
                      <div className="layer-row">
                        <label className="layer-checkbox">
                          <input
                            type="checkbox"
                            checked={isActive}
                            onChange={() => toggleLayer(key)}
                          />

                          <span className="custom-checkbox"></span>

                          <span className="layer-name">
                            {layer.shortLabel}
                          </span>
                        </label>

                        <span className="layer-status">
                          {isActive ? "ACTIVE" : ""}
                        </span>
                      </div>

                      {isActive && (
                        <div className="opacity-control">
                          <div className="opacity-label">
                            <span>Opacity</span>

                            <span>
                              {Math.round(layerOpacity[key] * 100)}%
                            </span>
                          </div>

                          <input
                            type="range"
                            min="0.1"
                            max="1"
                            step="0.05"
                            value={layerOpacity[key]}
                            onChange={(e) =>
                              changeOpacity(key, e.target.value)
                            }
                          />
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>

              <p className="layer-help">
                One ward-level layer can be displayed at a time.
                Select a layer to change the map view.
              </p>
            </section>

            <section className="sidebar-section">
              <div className="section-label">DATASET STATUS</div>

              <div className="status-card">
                <div className="status-dot"></div>

                <div>
                  <strong>Live API data</strong>
                  <span>{wards.length} Pune wards loaded</span>
                </div>
              </div>
            </section>

            <section className="sidebar-section">
              <div className="section-label">CURRENT LAYER</div>

              <div className="layer-title">
                {activeLayer
                  ? LAYERS[activeLayer].label
                  : "No layer selected"}
              </div>

              <div className="legend">
                <div className="legend-item">
                  <span
                    className="legend-color legend-high"
                  ></span>

                  <span>
                    {activeLayer === "priority"
                      ? "Higher priority"
                      : activeLayer === "heat"
                        ? "Higher temperature"
                        : activeLayer === "canopy"
                          ? "Lower tree cover"
                          : activeLayer === "ndvi"
                            ? "Higher NDVI"
                            : activeLayer === "builtup"
                              ? "Higher built-up"
                              : "Higher vulnerability"}
                  </span>
                </div>

                <div className="legend-item">
                  <span
                    className="legend-color legend-low"
                  ></span>

                  <span>
                    {activeLayer === "priority"
                      ? "Lower priority"
                      : activeLayer === "heat"
                        ? "Lower temperature"
                        : activeLayer === "canopy"
                          ? "Higher tree cover"
                          : activeLayer === "ndvi"
                            ? "Lower NDVI"
                            : activeLayer === "builtup"
                              ? "Lower built-up"
                              : "Lower vulnerability"}
                  </span>
                </div>
              </div>
            </section>
            <section className="sidebar-section selected-section">
              <div className="section-label">WARD ANALYTICS</div>

              {!selectedProperties && (
                <div className="empty-card">
                  <div className="empty-icon">⌖</div>

                  <p>
                    Click any ward on the map to inspect its
                    heat, canopy and vulnerability analysis.
                  </p>
                </div>
              )}

              {selectedProperties && (
                <div className="analytics-card">

                  {/* WARD HEADER */}
                  <div className="ward-number">
                    WARD {selectedProperties.ward_id}
                  </div>

                  <h2>{selectedProperties.ward_name}</h2>

                  {/* SCORE */}
                  <div className="score-box">
                    <div>
                      <span>PRIORITY SCORE</span>

                      <strong>
                        {selectedProperties.priority_score?.toFixed(2)}
                      </strong>
                    </div>

                    <div className="rank-box">
                      <span>RANK</span>

                      <strong>
                        #{selectedProperties.priority_rank}
                      </strong>
                    </div>
                  </div>

                  {/* KEY INDICATORS */}
                  <div className="analytics-title">
                    KEY INDICATORS
                  </div>

                  <div className="metric-grid">

                    <div>
                      <span>LST</span>

                      <strong>
                        {selectedProperties.lst_builtup_mean?.toFixed(1)}°C
                      </strong>
                    </div>

                    <div>
                      <span>TREE COVER</span>

                      <strong>
                        {(
                          (selectedProperties.tree_frac_wc ?? 0) * 100
                        ).toFixed(1)}%
                      </strong>
                    </div>

                    <div>
                      <span>VULNERABILITY</span>

                      <strong>
                        {selectedProperties.vulnerability_n?.toFixed(2)}
                      </strong>
                    </div>

                    <div>
                      <span>NDVI</span>

                      <strong>
                        {selectedProperties.ndvi_s2_mean?.toFixed(3)}
                      </strong>
                    </div>

                  </div>

                  {/* SCORE BREAKDOWN */}
                  <div className="analytics-title">
                    SCORE BREAKDOWN
                  </div>

                  {wardDetailsLoading ? (
                    <div className="detail-loading">
                      Loading score analysis...
                    </div>
                  ) : wardDetails ? (

                    <div className="contribution-list">

                      <div className="contribution-row">
                        <div className="contribution-info">
                          <span>Heat</span>

                          <strong>
                            {heatContribution?.toFixed(2)}
                          </strong>
                        </div>

                        <div className="contribution-bar">
                          <div
                            style={{
                              width: `${Math.min(
                                (heatContribution ?? 0) * 100,
                                100
                              )}%`,
                            }}
                          ></div>
                        </div>
                      </div>


                      <div className="contribution-row">
                        <div className="contribution-info">
                          <span>Canopy deficit</span>

                          <strong>
                            {canopyContribution?.toFixed(2)}
                          </strong>
                        </div>

                        <div className="contribution-bar">
                          <div
                            style={{
                              width: `${Math.min(
                                (canopyContribution ?? 0) * 100,
                                100
                              )}%`,
                            }}
                          ></div>
                        </div>
                      </div>


                      <div className="contribution-row">
                        <div className="contribution-info">
                          <span>Vulnerability</span>

                          <strong>
                            {vulnerabilityContribution?.toFixed(2)}
                          </strong>
                        </div>

                        <div className="contribution-bar">
                          <div
                            style={{
                              width: `${Math.min(
                                (vulnerabilityContribution ?? 0) * 100,
                                100
                              )}%`,
                            }}
                          ></div>
                        </div>
                      </div>

                    </div>

                  ) : (
                    <div className="detail-loading">
                      Detailed scoring data unavailable.
                    </div>
                  )}


                  {/* TREND */}
                  <div className="analytics-title">
                    HISTORICAL TREND
                  </div>

                  <div className="coming-soon">
                    <span className="coming-icon">◷</span>

                    <div>
                      <strong>5-year trend coming soon</strong>

                      <p>
                        Historical LST and canopy trend data
                        is not currently available in the API.
                      </p>
                    </div>
                  </div>


                  {/* CONFIDENCE */}
                  <div className="analytics-title">
                    DATA CONFIDENCE
                  </div>

                  <div className="confidence-box">

                    <div>
                      <span>LST valid fraction</span>

                      <strong>
                        {selectedProperties.lst_valid_frac != null
                          ? `${(
                            selectedProperties.lst_valid_frac * 100
                          ).toFixed(0)}%`
                          : "N/A"}
                      </strong>
                    </div>

                    <div>
                      <span>Observations</span>

                      <strong>
                        {selectedProperties.n_obs_mean != null
                          ? selectedProperties.n_obs_mean.toFixed(1)
                          : "N/A"}
                      </strong>
                    </div>

                  </div>

                </div>
              )}
            </section>

            {/* DATA CENTRE ANALYSIS */}
            <section className="sidebar-section">
              <div className="section-label">DATA CENTRE ANALYSIS</div>

              {!selectedDataCentre ? (
                <div className="empty-state">
                  <strong>Select a data centre</strong>
                  <p>
                    Click a data-centre marker on the map to view
                    temperature and tree-cover analysis by distance ring.
                  </p>
                </div>
              ) : (
                <>
                  <div className="dc-summary">
                    <div className="dc-name">
                      {selectedDataCentre.properties?.name}
                    </div>

                    <div className="dc-meta">
                      {selectedDataCentre.properties?.operator}
                    </div>

                    <div className="dc-details">
                      <span>
                        {selectedDataCentre.properties?.capacity_mw
                          ? `Capacity: ${selectedDataCentre.properties.capacity_mw} MW`
                          : "Capacity: Not available"}
                      </span>

                      <span>
                        {selectedDataCentre.properties?.status}
                      </span>
                    </div>
                  </div>

                  <div className="dc-ring-title">
                    RING ANALYSIS
                  </div>

                  <div className="dc-ring-list">
                    {(() => {
                      const rows =
                        dataCentres?.table?.filter(
                          (row) =>
                            row.site_group ===
                            selectedDataCentre.properties?.site_group
                        ) || [];

                      if (rows.length === 0) {
                        return (
                          <div className="dc-analysis-unavailable">
                            <strong>Not included in analysis</strong>
                            <p>
                              This site is under construction or partly
                              operational and is excluded from the current
                              surface-temperature and tree-cover analysis.
                            </p>
                          </div>
                        );
                      }

                      return rows
                        .sort((a, b) => a.ring_index - b.ring_index)
                        .map((row) => (
                          <div
                            className="dc-ring-card"
                            key={`${row.site_group}-${row.ring_index}`}
                          >
                            <div className="dc-ring-name">
                              {row.ring}
                            </div>

                            <div className="dc-metric-grid">
                              <div>
                                <span>LST</span>
                                <strong>
                                  {row.lst_mean?.toFixed(1)}°C
                                </strong>
                              </div>

                              <div>
                                <span>Tree Cover</span>
                                <strong>
                                  {row.trees_pct?.toFixed(1)}%
                                </strong>
                              </div>

                              <div>
                                <span>LST vs Reference</span>
                                <strong>
                                  {row.lst_minus_reference >= 0 ? "+" : ""}
                                  {row.lst_minus_reference?.toFixed(1)}°C
                                </strong>
                              </div>

                              <div>
                                <span>Trees vs Reference</span>
                                <strong>
                                  {row.trees_minus_reference_pct >= 0
                                    ? "+"
                                    : ""}
                                  {row.trees_minus_reference_pct?.toFixed(1)}%
                                </strong>
                              </div>
                            </div>
                          </div>
                        ));
                    })()}
                  </div>
                </>
              )}
            </section>

            {/* EXPORT */}
            <section className="sidebar-section">
              <div className="section-label">EXPORT</div>

              <div className="export-actions">
                <button
                  className="export-button"
                  onClick={() => exportGeoJSON(wards)}
                  disabled={!wards || wards.length === 0}
                >
                  Export GeoJSON
                </button>

                <button
                  className="export-button"
                  onClick={() => exportCSV(wards)}
                  disabled={!wards || wards.length === 0}
                >
                  Export CSV
                </button>
              </div>

              <p className="export-note">
                Export the current 41-ward Pune dataset for
                GIS and analysis workflows.
              </p>
            </section>

            {/* METHODOLOGY */}
            <section className="sidebar-section">
              <div className="section-label">METHODOLOGY</div>

              <div className="methodology-card">

                <div className="methodology-item">
                  <strong>Study Area</strong>
                  <span>
                    Pune Municipal Corporation · 41 wards
                  </span>
                </div>

                <div className="methodology-item">
                  <strong>Surface Temperature</strong>
                  <span>
                    Landsat 8/9 thermal imagery · Mar–May 2026
                  </span>
                </div>

                <div className="methodology-item">
                  <strong>Vegetation</strong>
                  <span>
                    Sentinel-2 NDVI and provisional WorldCover 2021 tree-cover data
                  </span>
                </div>

                <div className="methodology-item">
                  <strong>Priority Score</strong>
                  <span>
                    Heat · canopy deficit · vulnerability
                  </span>
                </div>

                <div className="methodology-item">
                  <strong>Data Centre Analysis</strong>
                  <span>
                    Distance-ring comparison of surface temperature
                    and tree cover against reference areas
                  </span>
                </div>

                <div className="methodology-item">
                  <strong>Important Limitation</strong>
                  <span>
                    Satellite LST represents daytime land-surface
                    temperature, not air temperature or nighttime heat.
                  </span>
                </div>

              </div>
            </section>

          </aside>

          {/* MAP */}
          <section className="map-area">
            <div className="map-heading">
              <div>
                <h2>Pune Urban Heat Map</h2>
                <p>
                  41 municipal wards · click a ward for detailed analysis
                </p>
              </div>

              <div className="map-stat">
                <span>ACTIVE LAYER</span>
                <strong>
                  {activeLayer
                    ? LAYERS[activeLayer].label
                    : "No layer selected"}
                </strong>
              </div>
            </div>

            <MapContainer
              center={PUNE_CENTER}
              zoom={11}
              className="map"
              scrollWheelZoom={true}
            >
              <TileLayer
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              />

              <FitToWards wards={wards} />

              {activeLayer && (
                <GeoJSON
                  key={activeLayer}
                  data={geoJsonData}
                  style={layerStyle}
                  onEachFeature={onEachWard}
                />
              )}

              <DataCentreMarkers
                dataCentres={dataCentres}
                onSelect={setSelectedDataCentre}
              />

              <DataCentreRings
                dataCentres={dataCentres}
                selectedDataCentre={selectedDataCentre}
              />
            </MapContainer>
          </section>
        </main>
      )}

      {/* FOOTER */}
      {!loading && !error && (
        <footer className="footer">
          <span>SHADE · Planner Intelligence Platform</span>

          <span>
            LST data · Landsat 8/9 · 2026 study window
          </span>
        </footer>
      )}
    </div>
  );
}

export default App;