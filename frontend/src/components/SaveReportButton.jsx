import { useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useAuth } from "../auth/authContext";
import { downloadReportPdf, saveReport } from "../services/reports";
import "../auth/auth.css";

// Drop into a ward's action plan:  <SaveReportButton key={wardId} wardId={wardId} />
// (the key resets the box when the selected ward changes)
export default function SaveReportButton({ wardId, mode = "citizen" }) {
  const { user, loading, logout } = useAuth();
  const location = useLocation();
  const [busy, setBusy] = useState(false);
  const [saved, setSaved] = useState(null);
  const [error, setError] = useState("");

  const offlineDev = Boolean(import.meta.env.VITE_DEV_TOKEN);

  async function run(action) {
    setError("");
    setBusy(true);
    try {
      await action();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (loading) return null;

  if (!user && !offlineDev) {
    return (
      <div className="sh-save">
        <p>
          <Link className="sh-link" to="/login" state={{ from: location.pathname }}>Sign in</Link>
          {" "}to save this report and download it as a PDF.
        </p>
      </div>
    );
  }

  return (
    <div className="sh-save">
      {!saved ? (
        <div className="sh-row">
          <button type="button" className="sh-btn" disabled={busy}
            onClick={() => run(async () => setSaved(await saveReport(wardId, { mode })))}>
            {busy ? "Saving..." : "Save report"}
          </button>
        </div>
      ) : (
        <>
          <p>
            Report saved for ward {saved.ward}.
            {saved.storage === "memory" && " (Stored temporarily on the server: it is lost when the server restarts.)"}
          </p>
          <div className="sh-row">
            <button type="button" className="sh-btn" disabled={busy}
              onClick={() => run(() => downloadReportPdf(saved.id, `shade-ward-${saved.ward}.pdf`))}>
              {busy ? "Preparing..." : "Download PDF"}
            </button>
            <Link className="sh-link" to="/reports">My reports</Link>
          </div>
        </>
      )}

      {error && <p className="sh-error" role="alert">{error}</p>}

      {user && (
        <p style={{ marginTop: 10, color: "#555" }}>
          Signed in as {user.displayName || user.email}.{" "}
          <button type="button" className="sh-link" onClick={logout}>Sign out</button>
        </p>
      )}
    </div>
  );
}
