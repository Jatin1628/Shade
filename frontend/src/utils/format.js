// Indian-style number formatting for the action plan.
export function formatInr(value) {
  const n = Number(value);
  if (value == null || Number.isNaN(n)) return "-";
  if (n >= 1e7) return `₹${(n / 1e7).toFixed(2)} crore`;
  if (n >= 1e5) return `₹${(n / 1e5).toFixed(2)} lakh`;
  return `₹${Math.round(n).toLocaleString("en-IN")}`;
}

export function formatCount(value) {
  const n = Number(value);
  return value == null || Number.isNaN(n) ? "-" : Math.round(n).toLocaleString("en-IN");
}
