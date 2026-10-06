// Where the backend runs. Override in .env.local with VITE_API_BASE.
export const API_BASE = import.meta.env.VITE_API_BASE || "http://127.0.0.1:8000";

// Planner pages require a Firebase login. Set VITE_REQUIRE_LOGIN=0 in .env.local
// to switch the guard off (for example if Firebase is down during a demo).
export const REQUIRE_LOGIN = import.meta.env.VITE_REQUIRE_LOGIN !== "0";
