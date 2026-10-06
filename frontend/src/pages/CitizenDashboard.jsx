import { useEffect, useMemo, useState } from "react";

import {
    MapContainer,
    TileLayer,
    GeoJSON,
    useMap,
} from "react-leaflet";

import L from "leaflet";

import "leaflet/dist/leaflet.css";

import {
    getWards,
    getDataCentres,
    getWard,
} from "../services/api";

import SaveReportButton from "../components/SaveReportButton";
import { formatCount, formatInr } from "../utils/format";

const PUNE_CENTER = [18.5204, 73.8567];

const CITIZEN_LAYERS = {
    priority: {
        label: "Priority",
        getValue: (p) => p.priority_score,
    },
    heat: {
        label: "Heat",
        getValue: (p) => p.lst_builtup_mean,
    },
    canopy: {
        label: "Tree Cover",
        getValue: (p) => (p.tree_frac_wc ?? 0) * 100,
    },
};

function getColor(value, layer) {
    if (value == null) return "#d1d5db";

    if (layer === "heat") {
        if (value >= 46) return "#991b1b";
        if (value >= 44) return "#dc2626";
        if (value >= 42) return "#f97316";
        if (value >= 40) return "#facc15";
        return "#86efac";
    }

    if (layer === "canopy") {
        if (value < 10) return "#991b1b";
        if (value < 20) return "#f97316";
        if (value < 30) return "#facc15";
        if (value < 40) return "#86efac";
        return "#166534";
    }

    // Priority
    if (value >= 0.7) return "#991b1b";
    if (value >= 0.55) return "#dc2626";
    if (value >= 0.4) return "#f97316";
    if (value >= 0.25) return "#facc15";
    if (value >= 0.1) return "#86efac";

    return "#166534";
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
                padding: [20, 20],
            });
        }
    }, [wards, map]);

    return null;
}

export default function CitizenDashboard() {
    const [wards, setWards] = useState([]);
    const [search, setSearch] = useState("");
    const [selectedWard, setSelectedWard] = useState(null);
    const [wardDetail, setWardDetail] = useState(null);
    const [wardDetailLoading, setWardDetailLoading] = useState(false);
    const [activeLayer, setActiveLayer] = useState("priority");
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function loadWards() {
            try {
                setLoading(true);

                const data = await getWards();

                setWards(data);
            } catch (error) {
                console.error("Failed to load wards:", error);
            } finally {
                setLoading(false);
            }
        }

        loadWards();
    }, []);

    useEffect(() => {
        if (!selectedWard) {
            setWardDetail(null);
            return;
        }

        async function loadWardDetail() {
            try {
                setWardDetailLoading(true);

                const detail = await getWard(selectedWard.properties.ward_id);

                setWardDetail(detail);
            } catch (error) {
                console.error("Failed to load ward detail:", error);
                setWardDetail(null);
            } finally {
                setWardDetailLoading(false);
            }
        }

        loadWardDetail();
    }, [selectedWard]);

    const currentCanopyPct = wardDetail
        ? wardDetail.tree_frac_wc * 100
        : null;

    const plan = wardDetail?.action_plan;

    const targetCanopyPct = plan?.target_canopy_pct ?? 25;

    const canopyGapPct = wardDetail
        ? Math.max(targetCanopyPct - currentCanopyPct, 0)
        : null;

    const filteredWards = useMemo(() => {
        if (!search.trim()) return [];

        const query = search.toLowerCase();

        return wards
            .filter((ward) => {
                const p = ward.properties;

                return (
                    String(p.ward_id).includes(query) ||
                    String(p.ward_name ?? "").toLowerCase().includes(query)
                );
            })
            .slice(0, 8);
    }, [wards, search]);

    const urgentWards = useMemo(() => {
        return [...wards]
            .sort(
                (a, b) =>
                    (b.properties.priority_score ?? 0) -
                    (a.properties.priority_score ?? 0)
            )
            .slice(0, 5);
    }, [wards]);

    const layerStyle = (feature) => {
        const properties = feature.properties;

        const value =
            CITIZEN_LAYERS[activeLayer].getValue(properties);

        const isSelected =
            selectedWard?.properties?.ward_id ===
            properties.ward_id;

        return {
            fillColor: getColor(value, activeLayer),
            weight: isSelected ? 3 : 1,
            color: isSelected ? "#111827" : "#ffffff",
            fillOpacity: 0.72,
        };
    };

    const handleWardClick = (feature) => {
        setSelectedWard(feature);
        setSearch("");
    };

    return (
        <div className="citizen-page">

            {/* HEADER */}
            <header className="citizen-header">
                <div>
                    <div className="citizen-brand">🌳 SHADE</div>
                    <p>Urban Heat & Tree-Canopy Intelligence</p>
                </div>

                <button
                    className="citizen-planner-link"
                    onClick={() => {
                        window.location.href = "/planner";
                    }}
                >
                    Planner View
                </button>
            </header>

            <main className="citizen-map-layout">

                {/* SIDEBAR */}
                <aside className="citizen-sidebar">

                    <section className="citizen-welcome">
                        <span className="citizen-eyebrow">
                            PUNE · 41 WARDS
                        </span>

                        <h1>Explore your neighbourhood</h1>

                        <p>
                            Discover heat, tree cover and priority
                            areas across Pune.
                        </p>
                    </section>

                    {/* SEARCH */}
                    <section className="citizen-search-section">

                        <label htmlFor="ward-search">
                            Find your ward
                        </label>

                        <input
                            id="ward-search"
                            type="text"
                            placeholder="Search ward number or name..."
                            value={search}
                            onChange={(e) => setSearch(e.target.value)}
                        />

                        {search && (
                            <div className="citizen-search-results">

                                {filteredWards.length === 0 ? (
                                    <div className="citizen-no-results">
                                        No matching ward found.
                                    </div>
                                ) : (
                                    filteredWards.map((ward) => {
                                        const p = ward.properties;

                                        return (
                                            <button
                                                key={p.ward_id}
                                                onClick={() =>
                                                    handleWardClick(ward)
                                                }
                                            >
                                                <strong>
                                                    Ward {p.ward_id}
                                                </strong>

                                                <span>
                                                    {p.ward_name}
                                                </span>
                                            </button>
                                        );
                                    })
                                )}

                            </div>
                        )}

                    </section>

                    {/* LAYER TOGGLE */}
                    <section className="citizen-layer-section">

                        <div className="citizen-section-title">
                            EXPLORE BY
                        </div>

                        <div className="citizen-layer-toggle">

                            {Object.entries(CITIZEN_LAYERS).map(
                                ([key, layer]) => (
                                    <button
                                        key={key}
                                        className={
                                            activeLayer === key
                                                ? "active"
                                                : ""
                                        }
                                        onClick={() =>
                                            setActiveLayer(key)
                                        }
                                    >
                                        {layer.label}
                                    </button>
                                )
                            )}

                        </div>

                    </section>

                    {/* URGENT WARDS */}
                    <section className="urgent-section">

                        <div className="citizen-section-heading">
                            <div>
                                <div className="citizen-section-title">
                                    PRIORITY AREAS
                                </div>

                                <p>
                                    Wards where heat, tree-cover gaps and vulnerability indicate greater need.
                                </p>
                            </div>
                        </div>

                        {loading ? (
                            <p className="citizen-muted">
                                Loading...
                            </p>
                        ) : (
                            urgentWards.map((ward) => {
                                const p = ward.properties;

                                return (
                                    <button
                                        className="urgent-ward"
                                        key={p.ward_id}
                                        onClick={() =>
                                            setSelectedWard(ward)
                                        }
                                    >
                                        <span>
                                            #{p.priority_rank ?? "-"}
                                        </span>

                                        <div>
                                            <strong>
                                                Ward {p.ward_id}
                                            </strong>

                                            <small>
                                                {p.ward_name}
                                            </small>
                                        </div>

                                        <b>
                                            {p.priority_score?.toFixed(2)}
                                        </b>
                                    </button>
                                );
                            })
                        )}

                    </section>

                    {/* SELECTED WARD */}
                    {selectedWard && (
                        <section className="ward-detail">
                            <div className="section-label">SELECTED WARD</div>

                            {wardDetailLoading ? (
                                <p>Loading ward details...</p>
                            ) : wardDetail ? (
                                <>
                                    <div className="ward-detail-header">
                                        <div>
                                            <h2>
                                                Ward {wardDetail.ward_id}
                                            </h2>

                                            <p>{wardDetail.ward_name}</p>
                                        </div>

                                        <div className="priority-badge">
                                            <span>Priority Rank</span>
                                            <strong>#{wardDetail.priority_rank}</strong>
                                        </div>
                                    </div>

                                    <div className="ward-stats-grid">

                                        <div className="ward-stat-card">
                                            <span>MEAN LST</span>
                                            <strong>
                                                {wardDetail.lst_mean?.toFixed(1)}°C
                                            </strong>
                                        </div>

                                        <div className="ward-stat-card">
                                            <span>TREE COVER</span>
                                            <strong>
                                                {(wardDetail.tree_frac_wc * 100).toFixed(1)}%
                                            </strong>
                                        </div>

                                        <div className="ward-stat-card">
                                            <span>VULNERABILITY SCORE</span>
                                            <strong>
                                                {wardDetail.vulnerability?.toFixed(2)}
                                            </strong>
                                        </div>

                                        <div className="ward-stat-card">
                                            <span>PRIORITY SCORE</span>
                                            <strong>
                                                {wardDetail.priority_score?.toFixed(2)}
                                            </strong>
                                        </div>

                                    </div>

                                    <div className="vulnerability-note">
                                        <strong>Vulnerability Score</strong>

                                        <p>
                                            Normalized 0–1 index based on the available
                                            census-derived vulnerability data.
                                        </p>
                                    </div>

                                    <div className="ward-environment">
                                        <h3>Environmental Indicators</h3>

                                        <p>
                                            <strong>NDVI:</strong>{" "}
                                            {wardDetail.ndvi_s2_mean?.toFixed(2)}
                                        </p>

                                        <p>
                                            <strong>Built-up area:</strong>{" "}
                                            {(wardDetail.built_frac_wc * 100).toFixed(1)}%
                                        </p>
                                    </div>
                                </>
                            ) : (
                                <p>Unable to load ward details.</p>
                            )}
                        </section>
                    )}

                    {wardDetail && (
                        <section className="action-plan">

                            <div className="section-label">
                                ACTION PLAN
                            </div>

                            <div className="action-plan-header">
                                <div>
                                    <h2>Close the canopy gap</h2>

                                    <p>
                                        An estimated intervention plan for Ward{" "}
                                        {wardDetail.ward_id}.
                                    </p>
                                </div>

                                <div className="estimate-badge">
                                    ESTIMATES
                                </div>
                            </div>

                            <div className="canopy-gap">

                                <div className="canopy-value">
                                    <span>CURRENT TREE COVER</span>
                                    <strong>
                                        {currentCanopyPct.toFixed(1)}%
                                    </strong>
                                </div>

                                <div className="canopy-arrow">
                                    →
                                </div>

                                <div className="canopy-value target">
                                    <span>TARGET CANOPY</span>
                                    <strong>
                                        {targetCanopyPct.toFixed(0)}%
                                    </strong>
                                </div>

                                <div className="canopy-value gap">
                                    <span>CANOPY GAP</span>
                                    <strong>
                                        {canopyGapPct.toFixed(1)}%
                                    </strong>
                                </div>

                            </div>

                            <div className="action-metrics">

                                <div className="action-metric">
                                    <span>TREES NEEDED</span>
                                    <strong>
                                        {plan ? formatCount(plan.trees_needed) : "Pending"}
                                    </strong>
                                    <small>
                                        {plan
                                            ? `Assuming ${plan.crown_area_m2_assumed} m² of canopy per tree`
                                            : "Waiting for the backend"}
                                    </small>
                                </div>

                                <div className="action-metric">
                                    <span>ESTIMATED COST</span>
                                    <strong>
                                        {plan
                                            ? `${formatInr(plan.cost_inr_low)} – ${formatInr(plan.cost_inr_high)}`
                                            : "Pending"}
                                    </strong>
                                    <small>
                                        Low: sapling and planting. High: adds guard, watering and about
                                        3 years of upkeep (high end still awaiting PMC's rate).
                                    </small>
                                </div>

                                <div className="action-metric">
                                    <span>COOLING AT TARGET CANOPY</span>
                                    <strong>
                                        {plan ? `about ${plan.cooling_c_at_target_canopy} °C` : "Pending"}
                                    </strong>
                                    <small>
                                        From the tree cover vs temperature pattern across Pune's wards.
                                        An association, not a proven effect.
                                    </small>
                                </div>

                                <div className="action-metric">
                                    <span>CO₂ PER YEAR</span>
                                    <strong>
                                        {plan
                                            ? `about ${formatCount(plan.co2_tonnes_per_year_young_trees)} t`
                                            : "Pending"}
                                    </strong>
                                    <small>For young trees (1 to 10 years old).</small>
                                </div>

                            </div>

                            <div className="estimate-note">
                                <strong>About these estimates</strong>

                                <p>
                                    Action-plan values are intended as planning estimates,
                                    not field measurements. Tree count, cost, cooling and
                                    CO₂ impact require published coefficients and assumptions.
                                </p>
                            </div>

                            <SaveReportButton
                                key={wardDetail.ward_id}
                                wardId={wardDetail.ward_id}
                            />

                        </section>
                    )}

                </aside>

                { }
                <section className="citizen-map">

                    <MapContainer
                        center={PUNE_CENTER}
                        zoom={11}
                        scrollWheelZoom={true}
                    >

                        <TileLayer
                            attribution='&copy; OpenStreetMap contributors'
                            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                        />

                        <FitToWards wards={wards} />

                        {wards.length > 0 && (
                            <GeoJSON
                                key={activeLayer}
                                data={{
                                    type: "FeatureCollection",
                                    features: wards,
                                }}
                                style={layerStyle}
                                onEachFeature={(feature, layer) => {
                                    layer.on({
                                        click: () =>
                                            handleWardClick(feature),
                                    });

                                    layer.bindTooltip(
                                        `Ward ${feature.properties.ward_id} · ${feature.properties.ward_name
                                        }`,
                                        {
                                            sticky: true,
                                        }
                                    );
                                }}
                            />
                        )}

                    </MapContainer>

                    {/* LEGEND */}
                    <div className="citizen-map-legend">

                        <strong>
                            {CITIZEN_LAYERS[activeLayer].label}
                        </strong>

                        <div className="legend-gradient" />

                        <div className="legend-labels">
                            <span>
                                {activeLayer === "canopy"
                                    ? "Low"
                                    : "Lower"}
                            </span>

                            <span>
                                {activeLayer === "canopy"
                                    ? "High"
                                    : "Higher"}
                            </span>
                        </div>

                    </div>

                </section>

            </main>

        </div>
    );
}