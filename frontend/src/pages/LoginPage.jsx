import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function LoginPage() {
  const navigate = useNavigate();

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");

  const handleLogin = (e) => {
    e.preventDefault();
    setError("");

    const savedUser = JSON.parse(
      localStorage.getItem("shadeUser")
    );

    if (!savedUser) {
      setError("No account found. Please create an account first.");
      return;
    }

    if (
      savedUser.email !== email ||
      savedUser.password !== password
    ) {
      setError("Invalid email or password.");
      return;
    }

    localStorage.setItem("shadeLoggedIn", "true");

    navigate("/planner");
  };

  return (
    <div className="auth-page">
      <div className="auth-card">

        <div className="auth-logo">🌳</div>

        <h1>Welcome back</h1>

        <p className="auth-subtitle">
          Sign in to access the SHADE Planner View
        </p>

        <form onSubmit={handleLogin}>

          <label>Email</label>

          <input
            type="email"
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />

          <label>Password</label>

          <input
            type="password"
            placeholder="Enter your password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          {error && (
            <p className="auth-error">
              {error}
            </p>
          )}

          <button
            type="submit"
            className="auth-primary-btn"
          >
            Sign In
          </button>

        </form>

        <p className="auth-switch">
          Don't have an account?{" "}
          <button
            onClick={() => navigate("/signup")}
            className="auth-link"
          >
            Sign Up
          </button>
        </p>

        <button
          className="auth-back-btn"
          onClick={() => navigate("/")}
        >
          ← Back to SHADE
        </button>

      </div>
    </div>
  );
}