import { useState } from "react";
import { Link, Navigate, useLocation } from "react-router-dom";
import {
  GoogleAuthProvider,
  createUserWithEmailAndPassword,
  signInWithPopup,
  updateProfile,
} from "firebase/auth";
import { auth, firebaseConfigured } from "../firebase";
import { useAuth } from "../auth/authContext";
import { friendlyAuthError } from "../auth/errors";
import "../auth/auth.css";

export default function SignupPage() {
  const { user, loading } = useAuth();
  const from = useLocation().state?.from || "/planner";

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  if (!loading && user) return <Navigate to={from} replace />;

  async function handleSignup(e) {
    e.preventDefault();
    setError("");
    if (password !== confirm) return setError("Passwords do not match.");
    if (password.length < 6) return setError("Password must be at least 6 characters.");

    setBusy(true);
    try {
      const cred = await createUserWithEmailAndPassword(auth, email.trim(), password);
      if (name.trim()) await updateProfile(cred.user, { displayName: name.trim() });
    } catch (err) {
      setError(friendlyAuthError(err));
    } finally {
      setBusy(false);
    }
  }

  async function handleGoogle() {
    setError("");
    setBusy(true);
    try {
      await signInWithPopup(auth, new GoogleAuthProvider());
    } catch (err) {
      setError(friendlyAuthError(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="sh-page">
      <div className="sh-box">
        <h1>Create account</h1>
        <p className="sh-muted">An account lets you save and re-download reports.</p>

        {!firebaseConfigured && (
          <p className="sh-error">
            Firebase is not configured. Copy frontend/.env.example to frontend/.env.local, fill in the
            values from the Firebase console, then restart npm run dev.
          </p>
        )}

        <form onSubmit={handleSignup}>
          <label className="sh-field">
            <span>Name</span>
            <input type="text" autoComplete="name" value={name} onChange={(e) => setName(e.target.value)} />
          </label>
          <label className="sh-field">
            <span>Email</span>
            <input type="email" autoComplete="email" value={email}
              onChange={(e) => setEmail(e.target.value)} required />
          </label>
          <label className="sh-field">
            <span>Password</span>
            <input type="password" autoComplete="new-password" value={password}
              onChange={(e) => setPassword(e.target.value)} required />
          </label>
          <label className="sh-field">
            <span>Confirm password</span>
            <input type="password" autoComplete="new-password" value={confirm}
              onChange={(e) => setConfirm(e.target.value)} required />
          </label>

          {error && <p className="sh-error" role="alert">{error}</p>}

          <button type="submit" className="sh-btn sh-btn-block" disabled={busy || !firebaseConfigured}>
            {busy ? "Creating account..." : "Create account"}
          </button>
        </form>

        <p className="sh-or">or</p>
        <button type="button" className="sh-btn sh-btn-outline sh-btn-block"
          onClick={handleGoogle} disabled={busy || !firebaseConfigured}>
          Continue with Google
        </button>

        <p className="sh-links">
          Already have an account? <Link className="sh-link" to="/login" state={{ from }}>Sign in</Link>
          {" | "}
          <Link className="sh-link" to="/">Back to home</Link>
        </p>
      </div>
    </div>
  );
}
