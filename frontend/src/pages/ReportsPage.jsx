import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useAuth } from "../auth/authContext";
import { downloadReportPdf, listReports } from "../services/reports";
import "../auth/auth.css";

export default function ReportsPage() {
  const { user, logout } = useAuth();
  const [reports, setReports] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    listReports()
      .then((data) => !cancelled && setReports(data))
      .catch((err) => !cancelled && setError(err.message));
    return () => {
      cancelled = true;
    };
  }, []);

  async function download(report) {
    setError("");
    try {
      await downloadReportPdf(report.id, `shade-ward-${report.ward}.pdf`);
    } catch (err) {
      setError(err.message);
    }
  }

  return (
    <div className="sh-page">
      <div className="sh-wide">
        <h1>My reports</h1>
        <p className="sh-muted">
          {user ? `Signed in as ${user.displayName || user.email}. ` : ""}
          <Link className="sh-link" to="/citizen">Back to the map</Link>
          {user && (<> | <button type="button" className="sh-link" onClick={logout}>Sign out</button></>)}
        </p>

        {error && <p className="sh-error" role="alert">{error}</p>}
        {!reports && !error && <p>Loading...</p>}
        {reports && reports.length === 0 && (
          <p className="sh-note">No saved reports yet. Open a ward on the map and choose Save report.</p>
        )}

        {reports && reports.length > 0 && (
          <table className="sh-table">
            <thead>
              <tr><th>Ward</th><th>Saved</th><th>Priority rank</th><th>Mode</th><th>PDF</th></tr>
            </thead>
            <tbody>
              {reports.map((r) => (
                <tr key={r.id}>
                  <td>{r.ward} - {r.wardName}</td>
                  <td>{new Date(r.createdAt).toLocaleString()}</td>
                  <td>{r.snapshot?.rank}</td>
                  <td>{r.mode}</td>
                  <td><button type="button" className="sh-link" onClick={() => download(r)}>Download</button></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
