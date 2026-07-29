import { FormEvent, useState } from "react";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../api/client";

export default function Login() {
  const { login } = useAuth();
  const [email, setEmail] = useState("admin@controldesk.example.com");
  const [password, setPassword] = useState("Admin@123456");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Falha ao conectar ao servidor."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="login-wrap">
      <form className="card login-card" onSubmit={submit}>
        <div className="brand">
          <span className="dot" />
          ControlDesk
        </div>
        <p className="muted" style={{ marginTop: 4, marginBottom: 22 }}>
          Plataforma de Cobrança de Dívidas
        </p>

        <div className="field">
          <label>E-mail corporativo</label>
          <input
            className="input"
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
          />
        </div>
        <div className="field">
          <label>Senha</label>
          <input
            className="input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </div>

        {error && <p className="error-text">{error}</p>}

        <button className="btn" style={{ width: "100%", marginTop: 8 }} disabled={loading}>
          {loading ? "Entrando…" : "Entrar"}
        </button>

        <p className="muted" style={{ fontSize: 12, marginTop: 18, textAlign: "center" }}>
          Credenciais de demonstração pré-preenchidas.
        </p>
      </form>
    </div>
  );
}
