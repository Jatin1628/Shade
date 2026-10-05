import { useNavigate } from "react-router-dom";

export default function LandingPage() {
  const navigate = useNavigate();

  return (
    <div className="landing-page">

      {/* NAVBAR */}
      <header className="landing-nav">

        <div className="landing-brand">
          <span className="brand-icon">🌳</span>

          <span className="brand-name">SHADE</span>

          <span className="brand-divider"></span>

          <span className="brand-subtitle">
            Urban Heat & Tree-Canopy Intelligence
          </span>
        </div>

        <button
          className="landing-planner-link"
          onClick={() => navigate("/login")}
        >
          Planner Login
        </button>

      </header>


      {/* HERO */}
      <main className="landing-hero">

        {/* LEFT SIDE */}
        <section className="landing-hero-content">

          <div className="landing-eyebrow">
            PUNE · 41 MUNICIPAL WARDS
          </div>

          <h1>
            Making Pune
            <br />
            <span>cooler & greener.</span>
          </h1>

          <p className="landing-description">
            SHADE brings together heat, tree-cover and vulnerability
            data to understand where urban greening can have the
            greatest impact.
          </p>

          <div className="landing-actions">

            <button
              className="landing-btn primary"
              onClick={() => navigate("/citizen")}
            >
              Explore as Citizen
              <span>→</span>
            </button>

            <button
              className="landing-btn secondary"
              onClick={() => navigate("/login")}
            >
              Planner Login
            </button>

          </div>

          <p className="landing-note">
            Explore your ward or discover Pune's priority areas.
          </p>

        </section>


        {/* RIGHT SIDE — DATA VISUAL */}
        <section className="landing-visual">

          <div className="visual-card">

            <div className="visual-header">
              <div>
                <span className="visual-label">PUNE</span>
                <h3>Urban Heat Priority</h3>
              </div>

              <span className="visual-live">
                ● LIVE DATA
              </span>
            </div>


            {/* Abstract ward map */}
            <div className="visual-map">

              <div className="map-grid"></div>

              <div className="ward ward-1"></div>
              <div className="ward ward-2"></div>
              <div className="ward ward-3"></div>
              <div className="ward ward-4"></div>
              <div className="ward ward-5"></div>
              <div className="ward ward-6"></div>
              <div className="ward ward-7"></div>
              <div className="ward ward-8"></div>
              <div className="ward ward-9"></div>
              <div className="ward ward-10"></div>
              <div className="ward ward-11"></div>
              <div className="ward ward-12"></div>

            </div>


            {/* Legend */}
            <div className="visual-legend">

              <span>Lower priority</span>

              <div className="priority-gradient"></div>

              <span>Higher priority</span>

            </div>


            {/* Bottom metrics */}
            <div className="visual-metrics">

              <div>
                <strong>41</strong>
                <span>Wards</span>
              </div>

              <div>
                <strong>Heat</strong>
                <span>Surface temperature</span>
              </div>

              <div>
                <strong>Canopy</strong>
                <span>Tree-cover gaps</span>
              </div>

              <div>
                <strong>Priority</strong>
                <span>Intervention focus</span>
              </div>

            </div>

          </div>

        </section>

      </main>


      {/* BOTTOM INFORMATION */}
      <section className="landing-features">

        <div className="feature-item">
          <div className="feature-number">01</div>

          <div>
            <h3>Understand heat</h3>
            <p>
              Explore land-surface temperature across Pune's wards.
            </p>
          </div>
        </div>


        <div className="feature-item">
          <div className="feature-number">02</div>

          <div>
            <h3>Find canopy gaps</h3>
            <p>
              See where tree cover and vegetation are limited.
            </p>
          </div>
        </div>


        <div className="feature-item">
          <div className="feature-number">03</div>

          <div>
            <h3>Prioritize action</h3>
            <p>
              Combine heat, canopy and vulnerability into a priority view.
            </p>
          </div>
        </div>

      </section>

    </div>
  );
}