import { FormEvent, useState } from "react";
import { api, ApiError } from "../api/client";
import { useFetch } from "../api/hooks";
import { Badge, Modal } from "../components/ui";

interface User {
  id: number;
  full_name: string;
  email: string;
  role: string;
  is_active: boolean;
  sectors: string[];
}

const ROLES = ["administracao", "gerencia", "diretoria"];
const SECTORS = [
  "control_desk",
  "planejamento",
  "mis",
  "desenvolvimento",
  "infraestrutura",
];

export default function Usuarios() {
  const users = useFetch<User[]>("/users");
  const [show, setShow] = useState(false);

  return (
    <>
      <div className="row between" style={{ marginBottom: 16 }}>
        <p className="muted">Cadastro de diretoria, gerência e administração.</p>
        <button className="btn" onClick={() => setShow(true)}>
          + Novo usuário
        </button>
      </div>

      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Nome</th>
              <th>E-mail</th>
              <th>Cargo</th>
              <th>Setores</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {users.data?.map((u) => (
              <tr key={u.id}>
                <td>{u.full_name}</td>
                <td className="muted">{u.email}</td>
                <td>
                  <Badge value={u.role} />
                </td>
                <td>
                  <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                    {u.sectors.length ? (
                      u.sectors.map((s) => (
                        <span key={s} className="badge gray" style={{ fontSize: 11 }}>
                          {s}
                        </span>
                      ))
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </div>
                </td>
                <td>{u.is_active ? <Badge value="ativo" /> : <Badge value="inativo" />}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {show && (
        <UserModal
          onClose={() => setShow(false)}
          onSaved={() => {
            setShow(false);
            users.reload();
          }}
        />
      )}
    </>
  );
}

function UserModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    role: "administracao",
  });
  const [sectors, setSectors] = useState<string[]>([]);
  const [error, setError] = useState("");

  function toggle(s: string) {
    setSectors((prev) => (prev.includes(s) ? prev.filter((x) => x !== s) : [...prev, s]));
  }

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api.post("/users", { ...form, sectors });
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao criar usuário.");
    }
  }

  return (
    <Modal title="Novo usuário" onClose={onClose}>
      <form onSubmit={submit}>
        <div className="field">
          <label>Nome completo</label>
          <input
            className="input"
            value={form.full_name}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
            required
          />
        </div>
        <div className="field">
          <label>E-mail</label>
          <input
            className="input"
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            required
          />
        </div>
        <div className="row">
          <div className="field" style={{ flex: 1 }}>
            <label>Senha (mín. 8, letras + números)</label>
            <input
              className="input"
              type="password"
              value={form.password}
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              required
            />
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label>Cargo</label>
            <select
              className="input"
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
            >
              {ROLES.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="field">
          <label>Acesso aos setores</label>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {SECTORS.map((s) => (
              <button
                type="button"
                key={s}
                className={`btn ${sectors.includes(s) ? "" : "secondary"}`}
                style={{ padding: "6px 12px", fontSize: 13 }}
                onClick={() => toggle(s)}
              >
                {s}
              </button>
            ))}
          </div>
        </div>
        {error && <p className="error-text">{error}</p>}
        <button className="btn" style={{ width: "100%", marginTop: 8 }}>
          Criar usuário
        </button>
      </form>
    </Modal>
  );
}
