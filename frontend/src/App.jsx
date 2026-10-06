import CitizenDashboard from "./pages/CitizenDashboard";

import L from "leaflet";
import { useEffect, useMemo, useRef, useState } from "react";

import { BrowserRouter, Routes, Route } from "react-router-dom";
import LandingPage from "./pages/LandingPage";
import AuthProvider from "./auth/AuthProvider";
import RequireAuth from "./auth/RequireAuth";
import ReportsPage from "./pages/ReportsPage";

import {
  MapContainer,
  TileLayer,
  GeoJSON,
  Marker,
  Popup,
  useMap,
} from "react-leaflet";

import "leaflet/dist/leaflet.css";
import {
  getWards,
  getWard,
  getDataCentres,
} from "./services/api";

import "./index.css";
import "./App.css";

import LoginPage from "./pages/LoginPage";
import SignupPage from "./pages/SignupPage";

const PUNE_CENTER = [18.5204, 73.8567];

// Module-level icon instances so react-leaflet never swaps icons needlessly.
// Selected data-centre marker: same blue Leaflet pin, plus a CSS glow
// (.dc-marker-selected) and a green halo drawn underneath it.
const defaultDataCentreIcon = new L.Icon.Default();

const selectedDataCentreIcon = new L.Icon.Default({
  className: "dc-marker-selected",
});

const selectedHaloIcon = L.divIcon({
  className: "dc-selected-halo",
  iconSize: [52, 52],
  iconAnchor: [26, 49],
});

const isFiniteNumber = (value) =>
  typeof value === "number" && Number.isFinite(value);

function formatSigned(value, digits = 1) {
  if (!isFiniteNumber(value)) return "—";

  const rounded = Number(value.toFixed(digits));
  const sign = rounded < 0 ? "−" : "+";

  return `${sign}${Math.abs(rounded).toFixed(digits)}`;
}

function formatFixed(value, digits = 1) {
  return isFiniteNumber(value) ? value.toFixed(digits) : "—";
}

// "0–0.2 km (campus)" -> { range: "0–0.2 km", tag: "campus" }
function getRingParts(ringLabel) {
  const label = String(ringLabel ?? "");
  const match = label.match(/^(.*?)\s*\(([^)]*)\)\s*$/);

  if (!match) return { range: label, tag: null };

  return { range: match[1], tag: match[2] };
}

// A ring counts as "elevated" only when its surface-temperature excess sits
// above the 95th percentile of the look-alike spots (values from the API).
const LOOKALIKE_UPPER_PERCENTILE = 95;

function buildKeyFinding(rows) {
  const referenceRow = rows.find((row) => /reference/i.test(row.ring ?? ""));

  const rings = rows.filter(
    (row) =>
      !/reference/i.test(row.ring ?? "") &&
      isFiniteNumber(row.lst_minus_reference)
  );

  if (rings.length === 0) return null;

  const hasPercentiles = rings.every((row) =>
    isFiniteNumber(row.excess_percentile_vs_lookalikes)
  );

  let statement =
    "Surface temperature differences from the reference area are shown for each ring.";
  let definition = null;

  if (hasPercentiles) {
    const elevatedCount = rings.filter(
      (row) =>
        row.excess_percentile_vs_lookalikes > LOOKALIKE_UPPER_PERCENTILE
    ).length;

    if (elevatedCount === 0) {
      statement =
        "Surface temperature is not consistently elevated around this site.";
    } else if (elevatedCount === rings.length) {
      statement =
        "Surface temperature is elevated in every ring measured around this site.";
    } else {
      statement = `Surface temperature is elevated in ${elevatedCount} of ${rings.length} rings around this site.`;
    }

    const lookalikeCount = rings.find((row) =>
      isFiniteNumber(row.n_lookalikes)
    )?.n_lookalikes;

    definition = `“Elevated” means above the ${LOOKALIKE_UPPER_PERCENTILE}th percentile of ${
      lookalikeCount ? `${lookalikeCount} ` : ""
    }look-alike built-up spots.`;
  }

  const referenceRange = referenceRow
    ? getRingParts(referenceRow.ring).range
    : null;

  return {
    statement,
    rings: rings.map((row) => {
      const { range, tag } = getRingParts(row.ring);
      const label = tag ? tag.charAt(0).toUpperCase() + tag.slice(1) : range;

      return {
        key: `${row.site_group}-${row.ring_index}`,
        label,
        value: `${formatSigned(row.lst_minus_reference)}°C`,
      };
    }),
    note: `Daytime land-surface temperature, relative to the ${
      referenceRange ? `${referenceRange} ` : ""
    }reference area.`,
    definition,
  };
}

function DataCentreMarkers({ dataCentres, selectedDataCentre, onSelect }) {
  if (!dataCentres?.sites?.features) return null;

  const selectedId = selectedDataCentre?.properties?.dc_id;

  return (
    <>
      {dataCentres.sites.features.map((feature) => {
        const [lng, lat] = feature.geometry.coordinates;
        const properties = feature.properties;
        const isSelected = selectedId === properties.dc_id;

        return (
          <Marker
            key={properties.dc_id}
            position={[lat, lng]}
            icon={isSelected ? selectedDataCentreIcon : defaultDataCentreIcon}
            zIndexOffset={isSelected ? 1000 : 0}
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

      {selectedId &&
        dataCentres.sites.features
          .filter((feature) => feature.properties.dc_id === selectedId)
          .map((feature) => {
            const [lng, lat] = feature.geometry.coordinates;

            return (
              <Marker
                key={`halo-${selectedId}`}
                position={[lat, lng]}
                icon={selectedHaloIcon}
                interactive={false}
                keyboard={false}
                zIndexOffset={-1000}
              />
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
    legend: { startLabel: "High", endLabel: "Low", reversed: true },
  },

  heat: {
    label: "Surface Temperature",
    shortLabel: "LST",
    getValue: (p) => p.lst_builtup_mean,
    format: (v) => `${v?.toFixed(1)}°C`,
    defaultOpacity: 0.72,
    legend: { startLabel: "Cooler", endLabel: "Hotter", reversed: false },
  },

  canopy: {
    label: "Tree Cover",
    shortLabel: "Tree Cover",
    getValue: (p) => (p.tree_frac_wc ?? 0) * 100,
    format: (v) => `${v?.toFixed(1)}%`,
    defaultOpacity: 0.72,
    legend: { startLabel: "Low", endLabel: "High", reversed: false },
  },

  ndvi: {
    label: "NDVI",
    shortLabel: "NDVI",
    getValue: (p) => p.ndvi_s2_mean,
    format: (v) => v?.toFixed(3),
    defaultOpacity: 0.72,
    legend: { startLabel: "Low", endLabel: "High", reversed: false },
  },

  builtup: {
    label: "Built-up Area",
    shortLabel: "Built-up",
    getValue: (p) => (p.built_frac_wc ?? 0) * 100,
    format: (v) => `${v?.toFixed(1)}%`,
    defaultOpacity: 0.72,
    legend: { startLabel: "Low", endLabel: "High", reversed: false },
  },

  vulnerability: {
    label: "Vulnerability Score",
    shortLabel: "Vulnerability Score",
    getValue: (p) => p.vulnerability_n,
    format: (v) => v?.toFixed(2),
    defaultOpacity: 0.72,
    legend: { startLabel: "Low", endLabel: "High", reversed: false },
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

// ---- Legend helpers -------------------------------------------------------
// The legend samples getColor() itself, so it always shows exactly the colours
// the map paints, over the min–max range of the currently loaded wards.
const LEGEND_STEPS = 48;

function getLayerRange(wards, layerKey) {
  if (!layerKey || !LAYERS[layerKey]) return null;

  const { getValue } = LAYERS[layerKey];

  let min = Infinity;
  let max = -Infinity;

  wards.forEach((ward) => {
    const value = getValue(ward.properties ?? {});

    if (isFiniteNumber(value)) {
      min = Math.min(min, value);
      max = Math.max(max, value);
    }
  });

  return min <= max ? { min, max } : null;
}

function buildLegendGradient(layerKey, min, max, reversed) {
  const colors = [];

  for (let i = 0; i < LEGEND_STEPS; i += 1) {
    const t = (i + 0.5) / LEGEND_STEPS;
    const value = min + (max - min) * (reversed ? 1 - t : t);

    colors.push(getColor(value, layerKey));
  }

  // Merge runs of identical colours into hard-edged stops (mirrors the map's classes).
  const stops = [];
  let start = 0;

  for (let i = 1; i <= LEGEND_STEPS; i += 1) {
    if (i === LEGEND_STEPS || colors[i] !== colors[start]) {
      const from = ((start / LEGEND_STEPS) * 100).toFixed(2);
      const to = ((i / LEGEND_STEPS) * 100).toFixed(2);

      stops.push(`${colors[start]} ${from}% ${to}%`);
      start = i;
    }
  }

  return `linear-gradient(to right, ${stops.join(", ")})`;
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

function PlannerDashboard() {
  const [wards, setWards] = useState([]);
  const [selectedWard, setSelectedWard] = useState(null);
  const [wardDetails, setWardDetails] = useState(null);
  const [wardDetailsLoading, setWardDetailsLoading] = useState(false);
  const [dataCentres, setDataCentres] = useState(null);
  const [dcLoading, setDcLoading] = useState(false);
  const [selectedDataCentre, setSelectedDataCentre] = useState(null);
  const [activeLayer, setActiveLayer] = useState("priority");
  const [plannerSidebarWidth, setPlannerSidebarWidth] = useState(380);

  const handlePlannerResizeStart = (e) => {
    e.preventDefault();

    const handleMouseMove = (event) => {
      const newWidth = Math.min(
        560,
        Math.max(320, event.clientX)
      );

      setPlannerSidebarWidth(newWidth);
    };

    const handleMouseUp = () => {
      document.removeEventListener("mousemove", handleMouseMove);
      document.removeEventListener("mouseup", handleMouseUp);

      document.body.style.cursor = "";
      document.body.style.userSelect = "";
    };

    document.addEventListener("mousemove", handleMouseMove);
    document.addEventListener("mouseup", handleMouseUp);

    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";
  };

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

  // ---- UI-only state (no effect on data or API calls) ----
  const [methodologyOpen, setMethodologyOpen] = useState(false);
  const [exportNotice, setExportNotice] = useState("");
  const exportNoticeTimer = useRef(null);
  const sidebarRef = useRef(null);
  const dcSectionRef = useRef(null);

  useEffect(() => {
    return () => {
      clearTimeout(exportNoticeTimer.current);
    };
  }, []);

  // Bring the data-centre section into view when a site is selected.
  useEffect(() => {
    if (!selectedDataCentre) return;

    const sidebar = sidebarRef.current;
    const section = dcSectionRef.current;

    if (!sidebar || !section) return;

    const prefersReducedMotion =
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

    const top =
      sidebar.scrollTop +
      (section.getBoundingClientRect().top -
        sidebar.getBoundingClientRect().top) -
      8;

    sidebar.scrollTo({
      top: Math.max(0, top),
      behavior: prefersReducedMotion ? "auto" : "smooth",
    });
  }, [selectedDataCentre]);

  // Reveal the methodology panel when it is expanded near the bottom of the sidebar.
  useEffect(() => {
    if (!methodologyOpen) return;

    const panel = document.getElementById("methodology-panel");

    if (!panel) return;

    const prefersReducedMotion =
      window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

    panel.scrollIntoView({
      block: "nearest",
      behavior: prefersReducedMotion ? "auto" : "smooth",
    });
  }, [methodologyOpen]);

  const handleExport = (format) => {
    try {
      if (format === "geojson") {
        exportGeoJSON(wards);
        setExportNotice("✓ GeoJSON exported");
      } else {
        exportCSV(wards);
        setExportNotice("✓ CSV exported");
      }
    } catch (err) {
      console.error("Export failed:", err);
      setExportNotice("Export failed. Please try again.");
    }

    clearTimeout(exportNoticeTimer.current);
    exportNoticeTimer.current = setTimeout(() => {
      setExportNotice("");
    }, 2800);
  };

  const legendRange = useMemo(
    () => getLayerRange(wards, activeLayer),
    [wards, activeLayer]
  );

  const legendGradient = useMemo(() => {
    if (!legendRange || !activeLayer) return null;

    return buildLegendGradient(
      activeLayer,
      legendRange.min,
      legendRange.max,
      LAYERS[activeLayer].legend.reversed
    );
  }, [legendRange, activeLayer]);

  // Ring rows of the selected data-centre site (same filter as before, sorted by ring).
  const selectedRingRows = useMemo(() => {
    const siteGroup = selectedDataCentre?.properties?.site_group;

    if (!siteGroup || !Array.isArray(dataCentres?.table)) return [];

    return dataCentres.table
      .filter((row) => row.site_group === siteGroup)
      .sort((a, b) => a.ring_index - b.ring_index);
  }, [dataCentres, selectedDataCentre]);

  const keyFinding = useMemo(
    () => buildKeyFinding(selectedRingRows),
    [selectedRingRows]
  );

  const dcSiteCount = dataCentres?.sites?.features?.length ?? 0;

  const dcStatus = dcLoading
    ? { tone: "is-loading", text: "Loading data-centre sites…" }
    : dcSiteCount > 0
      ? {
        tone: "",
        text: `${dcSiteCount} data-centre site${dcSiteCount === 1 ? "" : "s"
          } loaded`,
      }
      : { tone: "is-unavailable", text: "Data-centre layer unavailable" };

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
          {!loading && !error && wards.length > 0 && (
            <span className="live-indicator">
              <span className="live-dot" aria-hidden="true"></span>
              LIVE DATA
            </span>
          )}

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
        <main
          className="dashboard"
          style={{
            "--planner-sidebar-width": `${plannerSidebarWidth}px`,
          }}
        >
          {/* LEFT SIDEBAR */}
          <aside className="sidebar" ref={sidebarRef}>
            {/* MAP LAYERS */}
            <section className="sidebar-section">
              <div className="section-header">
                <h2 className="section-label">MAP LAYERS</h2>
              </div>

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
                            aria-label={`${layer.shortLabel} layer opacity`}
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

            {/* DATASET STATUS */}
            <section className="sidebar-section">
              <div className="section-header">
                <h2 className="section-label">DATASET STATUS</h2>
              </div>

              <div className="status-card">
                <div className="status-row">
                  <div className="status-dot"></div>

                  <div>
                    <strong>Live API data</strong>
                    <span>{wards.length} Pune wards loaded</span>
                  </div>
                </div>

                <div className="status-row">
                  <div className={`status-dot ${dcStatus.tone}`}></div>

                  <div>
                    <strong>Data centres</strong>
                    <span>{dcStatus.text}</span>
                  </div>
                </div>
              </div>
            </section>

            {/* WARD ANALYTICS */}
            <section className="sidebar-section">
              <div className="section-header">
                <h2 className="section-label">WARD ANALYTICS</h2>
              </div>

              {!selectedProperties && (
                <div className="empty-card">
                  <div className="empty-icon">⌖</div>

                  <p>
                    Click any ward on the map to inspect its heat,
                    canopy and vulnerability indicators.
                  </p>
                </div>
              )}

              {selectedProperties && (
                <div className="analytics-card">

                  {/* WARD HEADER */}
                  <div className="ward-number">
                    WARD {selectedProperties.ward_id}
                  </div>

                  <h3>{selectedProperties.ward_name}</h3>

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
                      <span>VULNERABILITY SCORE</span>

                      <strong>
                        {selectedProperties.vulnerability_n?.toFixed(2)}
                      </strong>

                      <small>Normalized 0–1 index</small>
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
            <section
              ref={dcSectionRef}
              className={`sidebar-section dc-section ${selectedDataCentre ? "is-prominent" : ""
                }`}
            >
              <div className="section-header">
                <h2 className="section-label">DATA CENTRE ANALYSIS</h2>
              </div>

              {!selectedDataCentre ? (
                <div className="empty-state">
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

                  {selectedRingRows.length === 0 ? (
                    <div className="dc-analysis-unavailable">
                      <strong>Not included in analysis</strong>
                      <p>
                        This site is under construction or partly
                        operational and is excluded from the current
                        surface-temperature and tree-cover analysis.
                      </p>
                    </div>
                  ) : (
                    <>
                      <div className="dc-ring-title">
                        RING ANALYSIS
                      </div>

                      <div className="dc-ring-list">
                        {selectedRingRows.map((row) => {
                          const { range, tag } = getRingParts(row.ring);

                          return (
                            <div
                              className={`dc-ring-card ${tag ? `is-${String(tag).toLowerCase()}` : ""
                                }`}
                              key={`${row.site_group}-${row.ring_index}`}
                            >
                              <div className="dc-ring-head">
                                <span className="dc-ring-name">
                                  {range}
                                </span>

                                {tag && (
                                  <span className="dc-ring-tag">
                                    {tag}
                                  </span>
                                )}
                              </div>

                              <div className="dc-metric-grid">
                                <div className="dc-metric primary">
                                  <strong>
                                    {formatFixed(row.lst_mean)}
                                    <small>°C</small>
                                  </strong>
                                  <span>Surface temp</span>
                                </div>

                                <div className="dc-metric primary">
                                  <strong>
                                    {formatFixed(row.trees_pct)}
                                    <small>%</small>
                                  </strong>
                                  <span>Tree cover</span>
                                </div>

                                <div className="dc-metric">
                                  <strong>
                                    {formatSigned(row.lst_minus_reference)}
                                    <small>°C</small>
                                  </strong>
                                  <span>vs reference</span>
                                </div>

                                <div className="dc-metric">
                                  <strong>
                                    {formatSigned(
                                      row.trees_minus_reference_pct
                                    )}
                                    <small>%</small>
                                  </strong>
                                  <span>vs reference</span>
                                </div>
                              </div>
                            </div>
                          );
                        })}
                      </div>

                      {keyFinding && (
                        <div className="dc-key-finding">
                          <div className="dc-key-label">KEY FINDING</div>

                          <p className="dc-key-statement">
                            {keyFinding.statement}
                          </p>

                          <ul className="dc-key-list">
                            {keyFinding.rings.map((ring) => (
                              <li key={ring.key}>
                                <span>{ring.label}</span>
                                <strong>{ring.value}</strong>
                              </li>
                            ))}
                          </ul>

                          <p className="dc-key-note">{keyFinding.note}</p>

                          {keyFinding.definition && (
                            <p className="dc-key-note">
                              {keyFinding.definition}
                            </p>
                          )}
                        </div>
                      )}
                    </>
                  )}
                </>
              )}
            </section>

            {/* EXPORT */}
            <section className="sidebar-section">
              <div className="section-header">
                <h2 className="section-label">EXPORT</h2>
              </div>

              <div className="export-actions">
                <button
                  className="export-button"
                  onClick={() => handleExport("geojson")}
                  disabled={!wards || wards.length === 0}
                >
                  <span className="export-icon" aria-hidden="true">↓</span>
                  Export GeoJSON
                </button>

                <button
                  className="export-button"
                  onClick={() => handleExport("csv")}
                  disabled={!wards || wards.length === 0}
                >
                  <span className="export-icon" aria-hidden="true">↓</span>
                  Export CSV
                </button>
              </div>

              <p className="export-status" role="status" aria-live="polite">
                {exportNotice}
              </p>

              <p className="export-note">
                Export the current 41-ward Pune dataset for
                GIS and analysis workflows.
              </p>
            </section>

            {/* METHODOLOGY */}
            <section className="sidebar-section">
              <button
                type="button"
                className="section-toggle"
                aria-expanded={methodologyOpen}
                aria-controls="methodology-panel"
                onClick={() => setMethodologyOpen((open) => !open)}
              >
                <span className="section-label">METHODOLOGY</span>
                <span className="section-toggle-icon" aria-hidden="true">
                  {methodologyOpen ? "▴" : "▾"}
                </span>
              </button>

              {methodologyOpen && (
                <div className="methodology-card" id="methodology-panel">

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
              )}
            </section>

          </aside>

          {/* SIDEBAR RESIZER */}
          <div
            className="planner-sidebar-resizer"
            onMouseDown={handlePlannerResizeStart}
            role="separator"
            aria-orientation="vertical"
            aria-label="Resize planner sidebar"
          >
            <span />
          </div>


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

            <div className="citizen-map">
              <MapContainer
                center={[18.52, 73.85]}
                zoom={11}
                style={{ height: "100%", width: "100%" }}
              >
                <TileLayer
                  attribution='&copy; OpenStreetMap contributors'
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
                  selectedDataCentre={selectedDataCentre}
                  onSelect={setSelectedDataCentre}
                />

                <DataCentreRings
                  dataCentres={dataCentres}
                  selectedDataCentre={selectedDataCentre}
                />
              </MapContainer>
            </div>

            {activeLayer && legendRange && legendGradient && (
              <div
                className="map-legend"
                role="group"
                aria-label={`${LAYERS[activeLayer].label} legend`}
              >
                <div className="legend-title">
                  {LAYERS[activeLayer].label}
                </div>

                {activeLayer === "vulnerability" && (
                  <div className="legend-subtitle">
                    Normalized 0–1 index
                  </div>
                )}

                <div className="legend-scale">
                  <span className="legend-end">
                    {LAYERS[activeLayer].legend.startLabel}
                  </span>

                  <span
                    className="legend-bar"
                    style={{ background: legendGradient }}
                  ></span>

                  <span className="legend-end">
                    {LAYERS[activeLayer].legend.endLabel}
                  </span>
                </div>

                <div className="legend-values">
                  <span>
                    {LAYERS[activeLayer].format(
                      LAYERS[activeLayer].legend.reversed
                        ? legendRange.max
                        : legendRange.min
                    )}
                  </span>

                  <span>
                    {LAYERS[activeLayer].format(
                      LAYERS[activeLayer].legend.reversed
                        ? legendRange.min
                        : legendRange.max
                    )}
                  </span>
                </div>
              </div>
            )}
          </section>
        </main>
      )}

      {/* FOOTER */}
      {!loading && !error && (
        <footer className="footer">
          <span>SHADE · Planner Intelligence Platform</span>

          <span>
            {wards.length} PMC wards · Landsat 8/9 · Mar–May 2026
          </span>
        </footer>
      )}
    </div>
  );
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>

        <Route path="/" element={<LandingPage />} />

        <Route path="/login" element={<LoginPage />} />

        <Route path="/signup" element={<SignupPage />} />

        <Route path="/citizen" element={<CitizenDashboard />} />

        <Route
          path="/planner"
          element={
            <RequireAuth>
              <PlannerDashboard />
            </RequireAuth>
          }
        />

        <Route
          path="/reports"
          element={
            <RequireAuth>
              <ReportsPage />
            </RequireAuth>
          }
        />

      </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;