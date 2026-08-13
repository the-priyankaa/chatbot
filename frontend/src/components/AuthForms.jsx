import { useState } from "react";
import { useAuth } from "../context/AuthContext.jsx";

export default function AuthForms() {
  const { login, register } = useAuth();
  const [mode, setMode] = useState("login");
  const [form, setForm] = useState({ username: "", email: "", identifier: "", password: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      if (mode === "login") {
        await login(form.identifier, form.password);
      } else {
        await register(form.username, form.email, form.password);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || "Request failed");
    } finally {
      setBusy(false);
    }
  };

  const switchMode = () => {
    setMode((m) => (m === "login" ? "register" : "login"));
    setError(null);
  };

  return (
    <div className="auth-wrap">
      <div className="auth-card">
        <div className="auth-logo">AI</div>
        <h1>{mode === "login" ? "Welcome back" : "Create your account"}</h1>
        <p className="auth-sub">
          {mode === "login"
            ? "Sign in to continue chatting"
            : "Join AI Chatbot to start a conversation"}
        </p>

        {error && <div className="banner banner-error">{error}</div>}

        <form onSubmit={submit} className="auth-form">
          {mode === "register" && (
            <>
              <input
                value={form.username}
                onChange={(e) => setForm({ ...form, username: e.target.value })}
                placeholder="Username"
                required
                minLength={3}
                autoComplete="username"
              />
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="Email"
                required
                autoComplete="email"
              />
            </>
          )}
          {mode === "login" ? (
            <input
              value={form.identifier}
              onChange={(e) => setForm({ ...form, identifier: e.target.value })}
              placeholder="Username or email"
              required
              autoComplete="username"
            />
          ) : null}
          <input
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            placeholder="Password"
            required
            minLength={8}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
          />
          <button type="submit" disabled={busy}>
            {busy
              ? "Please wait..."
              : mode === "login"
                ? "Sign in"
                : "Create account"}
          </button>
        </form>

        <p className="switch-link">
          {mode === "login" ? (
            <>
              No account?{" "}
              <button className="link-btn" onClick={switchMode}>
                Register
              </button>
            </>
          ) : (
            <>
              Have an account?{" "}
              <button className="link-btn" onClick={switchMode}>
                Sign in
              </button>
            </>
          )}
        </p>
      </div>
    </div>
  );
}
