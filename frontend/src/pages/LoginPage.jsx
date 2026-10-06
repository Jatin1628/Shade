import { useState } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";
import { GoogleAuthProvider, signInWithEmailAndPassword, signInWithPopup } from "firebase/auth";
import { auth, firebaseConfigured } from "../firebase";
import { useAuth } from "../auth/authContext";
import { friendlyAuthError } from "../auth/errors";
import "../auth/auth.css";

export default function LoginPage() {
  const { user, loading } = useAuth();
  const from = useLocation().state?.from || "/planner";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // Already signed in (or just finished signing in): go where they were headed.
  if (!loading && user) return <Navigate to={from} replace />;

  async function run(signIn) {
    setError("");
    setBusy(true);
    try {
      await signIn();
    } catch (err) {
      setError(friendlyAuthError(err));
    } finally {
      setBusy(false);
    }
  }

  const handleEmailLogin = (e) => {
    e.preventDefault();
    run(() => signInWithEmailAndPassword(auth, email.trim(), password));
  };
  const handleGoogle = () => run(() => signInWithPopup(auth, new GoogleAuthProvider()));

  return (
    <div className="sh-page">
      <div className="sh-box">
        <h1>Sign in</h1>
        <p className="sh-muted">Sign in to use the planner view and save reports.</p>

        {!firebaseConfigured && (
          <p className="sh-error">
            Firebase is not configured. Copy frontend/.env.example to frontend/.env.local, fill in the
            values from the Firebase console, then restart npm run dev.
          </p>
        )}

        <form onSubmit={handleEmailLogin}>
          <label className="sh-field">
            <span>Email</span>
            <input type="email" autoComplete="email" value={email}
              onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label className="sh-field">
            <span>Password</span>
            <input type="password" autoComplete="current-password" value={password}
              onChange={(e) => setPassword(e.target.value)} required />
          </label>

          {error && <p className="sh-error" role="alert">{error}</p>}

          <button type="submit" className="sh-btn sh-btn-block" disabled={busy || !firebaseConfigured}>
            {busy ? "Signing in..." : "Sign in"}
          </button>
        </form>

        <p className="sh-or">or</p>
        <button type="button" className="sh-btn sh-btn-outline sh-btn-block"
          onClick={handleGoogle} disabled={busy || !firebaseConfigured}>
          Continue with Google
        </button>

        <p className="sh-links">
          No account? <Link className="sh-link" to="/signup" state={{ from }}>Create one</Link>
          {" | "}
          <Link className="sh-link" to="/">Back to home</Link>
        </p>
      </div>
    </div>
  );
}
