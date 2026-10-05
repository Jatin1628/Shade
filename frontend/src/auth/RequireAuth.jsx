import { Navigate, useLocation } from "react-router-dom";
import { REQUIRE_LOGIN } from "../config";
import { useAuth } from "./authContext";

// <RequireAuth><PlannerDashboard /></RequireAuth>
// Sends signed-out visitors to /login and brings them back afterwards.
export default function RequireAuth({ children }) {
  const { user, loading } = useAuth();
  const location = useLocation();

  if (!REQUIRE_LOGIN) return children;
  if (loading) return <p className="sh-loading">Checking sign-in...</p>;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  return children;
}
