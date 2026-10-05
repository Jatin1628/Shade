import { useState } from "react";
import { useNavigate } from "react-router-dom";

export default function SignupPage() {
  const navigate = useNavigate();

  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");

  const handleSignup = (e) => {
    e.preventDefault();
    setError("");

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    if (password.length < 6) {
      setError("Password must be at least 6 characters.");
      return;
    }

    const user = {
      name,
      email,
      password,
    };

    localStorage.setItem(
      "shadeUser",
      JSON.stringify(user)
    );

    localStorage.setItem("shadeLoggedIn", "true");

    navigate("/planner");
  };

  return (
    <div className="auth-page">
      <div className="auth-card">

        <div className="auth-logo">🌳</div>

        <h1>Create your account</h1>

        <p className="auth-subtitle">
          Get started with SHADE
        </p>

        <form onSubmit={handleSignup}>

          <label>Name</label>

          <input
            type="text"
            placeholder="Your name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />

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
            placeholder="Create a password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />

          <label>Confirm Password</label>

          <input
            type="password"
            placeholder="Confirm your password"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
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
            Create Account
          </button>

        </form>

        <p className="auth-switch">
          Already have an account?{" "}
          <button
            onClick={() => navigate("/login")}
            className="auth-link"
          >
            Sign In
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