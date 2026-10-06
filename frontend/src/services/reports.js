import { auth } from "../firebase";
import { API_BASE } from "../config";

// Every call here sends the signed-in user's Firebase ID token to the backend:
//   Authorization: Bearer <token>
// getIdToken() refreshes the token by itself when it has expired.
async function authHeaders() {
  const devToken = import.meta.env.VITE_DEV_TOKEN; // optional, offline use only
  if (devToken) return { Authorization: `Bearer ${devToken}` };

  const user = auth?.currentUser;
  if (!user) throw new Error("Please sign in first.");
  return { Authorization: `Bearer ${await user.getIdToken()}` };
}

async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: { ...(options.headers || {}), ...(await authHeaders()) },
    });
  } catch (err) {
    if (err instanceof TypeError) {
      throw new Error(`Cannot reach the backend at ${API_BASE}. Is it running?`, { cause: err });
    }
    throw err;
  }

  if (!response.ok) {
    let detail = "";
    try {
      detail = (await response.json()).detail;
    } catch {
      /* body was not JSON */
    }
    if (response.status === 401) throw new Error("Your sign-in was not accepted. Sign out and sign in again.");
    throw new Error(detail || `Request failed (${response.status}).`);
  }
  return response;
}

export async function saveReport(wardId, { city = "pune", mode = "citizen" } = {}) {
  const response = await request("/reports", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ city, ward_id: wardId, mode }),
  });
  return response.json();
}

export async function listReports() {
  return (await request("/reports")).json();
}

export async function downloadReportPdf(reportId, filename) {
  const blob = await (await request(`/reports/${reportId}/pdf`)).blob();
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename || `shade-report-${reportId}.pdf`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
