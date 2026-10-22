import { useState } from "react";
import { GraduationCap } from "lucide-react";
import api from "../services/api";

export default function LoginPage({ onLogin }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const response = await api.post("/auth/login", { email, password });
      localStorage.setItem("erp-token", response.data.access_token);
      onLogin(response.data.user);
    } catch (requestError) {
      setError(requestError.response?.data?.detail || "Unable to sign in. Check the API connection.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-shell">
      <form className="login-card" onSubmit={submit}>
        <div className="brand-mark large"><GraduationCap size={27} /></div>
        <p className="eyebrow">CAMPUSONE ERP</p>
        <h1>Welcome back</h1>
        <p className="muted">Sign in to your college workspace.</p>
        <label>Username or email<input type="text" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} required /></label>
        <label>Password<input type="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} required minLength={8} /></label>
        {error && <div className="alert error">{error}</div>}
        <button className="primary-button full" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
      </form>
    </main>
  );
}
