import { FormEvent, useState } from "react";
import { api, ApiError } from "../api/client";
import { useFetch } from "../api/hooks";
import { Badge, Modal, money } from "../components/ui";

interface Debtor {
  id: number;
  full_name: string;
  document_masked: string;
  email: string | null;
  contact_status: string;
  is_anonymized: boolean;
}
interface Debt {
  id: number;
  debtor_id: number;
  contract_ref: string;
  portfolio: string;
  creditor: string;
  current_amount: number;
  status: string;
  risk_score: number;
}
interface Interaction {
  id: number;
  debtor_id: number;
  channel: string;
  result: string;
  notes: string | null;
  created_at: string;
}
interface Notification {
  id: number;
  debtor_id: number;
  channel: string;
  template: string;
  subject: string;
  status: string;
  created_at: string;
}

const PORTFOLIOS = ["ativa", "consignado", "concierge", "bancario"];
const CHANNELS = ["telefone", "sms", "email", "whatsapp", "discador"];
const RESULTS = [
  "cpc",
  "cpca",
  "promessa",
  "recado",
  "sem_contato",
  "numero_errado",
  "nao_atende",
  "acordo_fechado",
];

export default function Cobranca() {
  const [q, setQ] = useState("");
  const debtors = useFetch<Debtor[]>(`/collection/debtors?q=${encodeURIComponent(q)}`, [q]);
  const debts = useFetch<Debt[]>("/collection/debts");
  const interactions = useFetch<Interaction[]>("/collection/interactions?limit=25");
  const notifications = useFetch<Notification[]>("/notifications?limit=25");
  const [showDebtor, setShowDebtor] = useState(false);
  const [showDebt, setShowDebt] = useState(false);
  const [showInter, setShowInter] = useState(false);
  const [showNotif, setShowNotif] = useState(false);

  const debtorName = (id: number) =>
    debtors.data?.find((d) => d.id === id)?.full_name ?? `#${id}`;

  return (
    <>
      <div className="row between" style={{ marginBottom: 16 }}>
        <input
          className="input"
          style={{ maxWidth: 320 }}
          placeholder="Buscar devedor por nome ou documento…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <div className="row">
          <button className="btn secondary" onClick={() => setShowDebtor(true)}>
            + Devedor
          </button>
          <button className="btn secondary" onClick={() => setShowInter(true)}>
            + Tabulação
          </button>
          <button className="btn secondary" onClick={() => setShowNotif(true)}>
            + Notificar
          </button>
          <button className="btn" onClick={() => setShowDebt(true)}>
            + Dívida
          </button>
        </div>
      </div>

      <div className="grid cols-2">
        <div className="card">
          <h3>Devedores</h3>
          <table style={{ marginTop: 12 }}>
            <thead>
              <tr>
                <th>Nome</th>
                <th>Documento</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {debtors.data?.map((d) => (
                <tr key={d.id}>
                  <td>{d.full_name}</td>
                  <td className="muted">{d.document_masked}</td>
                  <td>
                    {d.is_anonymized ? <Badge value="anonimizado" /> : <Badge value="ativo" />}
                  </td>
                </tr>
              ))}
              {!debtors.data?.length && (
                <tr>
                  <td colSpan={3} className="muted">
                    Nenhum devedor.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        <div className="card">
          <h3>Dívidas</h3>
          <table style={{ marginTop: 12 }}>
            <thead>
              <tr>
                <th>Contrato</th>
                <th>Carteira</th>
                <th>Saldo</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {debts.data?.slice(0, 30).map((d) => (
                <tr key={d.id}>
                  <td>{d.contract_ref}</td>
                  <td style={{ textTransform: "capitalize" }}>{d.portfolio}</td>
                  <td>{money(d.current_amount)}</td>
                  <td>
                    <Badge value={d.status} />
                  </td>
                  <td>
                    <PayButton debt={d} onPaid={() => { debts.reload(); }} />
                  </td>
                </tr>
              ))}
              {!debts.data?.length && (
                <tr>
                  <td colSpan={5} className="muted">
                    Nenhuma dívida.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      <div className="section-title">Histórico de contatos (tabulação)</div>
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Data</th>
              <th>Devedor</th>
              <th>Canal</th>
              <th>Resultado</th>
              <th>Observação</th>
            </tr>
          </thead>
          <tbody>
            {interactions.data?.map((i) => (
              <tr key={i.id}>
                <td className="muted">
                  {new Date(i.created_at).toLocaleString("pt-BR")}
                </td>
                <td>{debtorName(i.debtor_id)}</td>
                <td style={{ textTransform: "capitalize" }}>{i.channel}</td>
                <td>
                  <Badge value={i.result} />
                </td>
                <td className="muted">{i.notes ?? "—"}</td>
              </tr>
            ))}
            {!interactions.data?.length && (
              <tr>
                <td colSpan={5} className="muted">
                  Nenhum contato registrado.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="section-title">Notificações (régua de comunicação)</div>
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Data</th>
              <th>Devedor</th>
              <th>Modelo</th>
              <th>Canal</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {notifications.data?.map((n) => (
              <tr key={n.id}>
                <td className="muted">
                  {new Date(n.created_at).toLocaleString("pt-BR")}
                </td>
                <td>{debtorName(n.debtor_id)}</td>
                <td>{n.template}</td>
                <td style={{ textTransform: "capitalize" }}>{n.channel}</td>
                <td>
                  <Badge value={n.status} />
                </td>
              </tr>
            ))}
            {!notifications.data?.length && (
              <tr>
                <td colSpan={5} className="muted">
                  Nenhuma notificação enviada.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {showDebtor && (
        <DebtorModal
          onClose={() => setShowDebtor(false)}
          onSaved={() => {
            setShowDebtor(false);
            debtors.reload();
          }}
        />
      )}
      {showNotif && (
        <NotificationModal
          debtors={debtors.data ?? []}
          onClose={() => setShowNotif(false)}
          onSaved={() => {
            setShowNotif(false);
            notifications.reload();
          }}
        />
      )}
      {showInter && (
        <InteractionModal
          debtors={debtors.data ?? []}
          onClose={() => setShowInter(false)}
          onSaved={() => {
            setShowInter(false);
            interactions.reload();
            debtors.reload();
          }}
        />
      )}
      {showDebt && (
        <DebtModal
          debtors={debtors.data ?? []}
          onClose={() => setShowDebt(false)}
          onSaved={() => {
            setShowDebt(false);
            debts.reload();
          }}
        />
      )}
    </>
  );
}

function PayButton({ debt, onPaid }: { debt: Debt; onPaid: () => void }) {
  const [busy, setBusy] = useState(false);
  if (debt.status === "quitada") return <span className="muted">✓</span>;
  return (
    <button
      className="btn ghost"
      disabled={busy}
      onClick={async () => {
        setBusy(true);
        try {
          await api.post("/collection/payments", {
            debt_id: debt.id,
            amount: debt.current_amount,
            method: "pix",
          });
          onPaid();
        } finally {
          setBusy(false);
        }
      }}
    >
      Quitar
    </button>
  );
}

function DebtorModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({ full_name: "", document: "", email: "" });
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api.post("/collection/debtors", form);
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao salvar.");
    }
  }
  return (
    <Modal title="Novo devedor" onClose={onClose}>
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
          <label>CPF / CNPJ</label>
          <input
            className="input"
            value={form.document}
            onChange={(e) => setForm({ ...form, document: e.target.value })}
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
          />
        </div>
        {error && <p className="error-text">{error}</p>}
        <button className="btn" style={{ width: "100%" }}>
          Salvar
        </button>
      </form>
    </Modal>
  );
}

function DebtModal({
  debtors,
  onClose,
  onSaved,
}: {
  debtors: Debtor[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState({
    debtor_id: debtors[0]?.id ?? 0,
    contract_ref: "",
    portfolio: "ativa",
    creditor: "",
    original_amount: 0,
    current_amount: 0,
    days_overdue: 0,
  });
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api.post("/collection/debts", {
        ...form,
        debtor_id: Number(form.debtor_id),
        original_amount: Number(form.original_amount),
        current_amount: Number(form.current_amount),
        days_overdue: Number(form.days_overdue),
      });
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao salvar.");
    }
  }

  return (
    <Modal title="Nova dívida" onClose={onClose}>
      <form onSubmit={submit}>
        <div className="field">
          <label>Devedor</label>
          <select
            className="input"
            value={form.debtor_id}
            onChange={(e) => setForm({ ...form, debtor_id: Number(e.target.value) })}
            required
          >
            {debtors.map((d) => (
              <option key={d.id} value={d.id}>
                {d.full_name}
              </option>
            ))}
          </select>
        </div>
        <div className="row">
          <div className="field" style={{ flex: 1 }}>
            <label>Contrato</label>
            <input
              className="input"
              value={form.contract_ref}
              onChange={(e) => setForm({ ...form, contract_ref: e.target.value })}
              required
            />
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label>Carteira</label>
            <select
              className="input"
              value={form.portfolio}
              onChange={(e) => setForm({ ...form, portfolio: e.target.value })}
            >
              {PORTFOLIOS.map((p) => (
                <option key={p} value={p}>
                  {p}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="field">
          <label>Credor</label>
          <input
            className="input"
            value={form.creditor}
            onChange={(e) => setForm({ ...form, creditor: e.target.value })}
            required
          />
        </div>
        <div className="row">
          <div className="field" style={{ flex: 1 }}>
            <label>Valor original</label>
            <input
              className="input"
              type="number"
              value={form.original_amount}
              onChange={(e) => setForm({ ...form, original_amount: Number(e.target.value) })}
            />
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label>Valor atual</label>
            <input
              className="input"
              type="number"
              value={form.current_amount}
              onChange={(e) => setForm({ ...form, current_amount: Number(e.target.value) })}
            />
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label>Dias atraso</label>
            <input
              className="input"
              type="number"
              value={form.days_overdue}
              onChange={(e) => setForm({ ...form, days_overdue: Number(e.target.value) })}
            />
          </div>
        </div>
        {error && <p className="error-text">{error}</p>}
        <button className="btn" style={{ width: "100%" }}>
          Salvar
        </button>
      </form>
    </Modal>
  );
}

function InteractionModal({
  debtors,
  onClose,
  onSaved,
}: {
  debtors: Debtor[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState({
    debtor_id: debtors[0]?.id ?? 0,
    channel: "telefone",
    result: "cpc",
    notes: "",
  });
  const [error, setError] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    try {
      await api.post("/collection/interactions", {
        ...form,
        debtor_id: Number(form.debtor_id),
        notes: form.notes || null,
      });
      onSaved();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao salvar.");
    }
  }

  return (
    <Modal title="Registrar contato / tabulação" onClose={onClose}>
      <form onSubmit={submit}>
        <div className="field">
          <label>Devedor</label>
          <select
            className="input"
            value={form.debtor_id}
            onChange={(e) => setForm({ ...form, debtor_id: Number(e.target.value) })}
            required
          >
            {debtors.map((d) => (
              <option key={d.id} value={d.id}>
                {d.full_name}
              </option>
            ))}
          </select>
        </div>
        <div className="row">
          <div className="field" style={{ flex: 1 }}>
            <label>Canal</label>
            <select
              className="input"
              value={form.channel}
              onChange={(e) => setForm({ ...form, channel: e.target.value })}
            >
              {CHANNELS.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label>Resultado (tabulação)</label>
            <select
              className="input"
              value={form.result}
              onChange={(e) => setForm({ ...form, result: e.target.value })}
            >
              {RESULTS.map((r) => (
                <option key={r} value={r}>
                  {r}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="field">
          <label>Observação</label>
          <textarea
            className="input"
            rows={3}
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
          />
        </div>
        {error && <p className="error-text">{error}</p>}
        <button className="btn" style={{ width: "100%" }}>
          Salvar tabulação
        </button>
      </form>
    </Modal>
  );
}

const NOTIF_TEMPLATES = [
  { key: "lembrete", label: "Lembrete de pendência" },
  { key: "proposta", label: "Proposta de negociação" },
  { key: "acordo_confirmado", label: "Acordo confirmado" },
];

function NotificationModal({
  debtors,
  onClose,
  onSaved,
}: {
  debtors: Debtor[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState({
    debtor_id: debtors[0]?.id ?? 0,
    template: "lembrete",
    channel: "email",
  });
  const [error, setError] = useState("");
  const [result, setResult] = useState("");

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setResult("");
    try {
      const n = await api.post<{ status: string }>("/notifications", {
        ...form,
        debtor_id: Number(form.debtor_id),
      });
      if (n.status === "bloqueado_lgpd") {
        setError(
          "Envio bloqueado: titular sem base legal/consentimento para comunicação (LGPD)."
        );
        return;
      }
      setResult(`Notificação registrada (status: ${n.status}).`);
      setTimeout(onSaved, 700);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Erro ao enviar.");
    }
  }

  return (
    <Modal title="Enviar notificação" onClose={onClose}>
      <form onSubmit={submit}>
        <div className="field">
          <label>Devedor</label>
          <select
            className="input"
            value={form.debtor_id}
            onChange={(e) => setForm({ ...form, debtor_id: Number(e.target.value) })}
            required
          >
            {debtors.map((d) => (
              <option key={d.id} value={d.id}>
                {d.full_name}
              </option>
            ))}
          </select>
        </div>
        <div className="row">
          <div className="field" style={{ flex: 1 }}>
            <label>Modelo</label>
            <select
              className="input"
              value={form.template}
              onChange={(e) => setForm({ ...form, template: e.target.value })}
            >
              {NOTIF_TEMPLATES.map((t) => (
                <option key={t.key} value={t.key}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div className="field" style={{ flex: 1 }}>
            <label>Canal</label>
            <select
              className="input"
              value={form.channel}
              onChange={(e) => setForm({ ...form, channel: e.target.value })}
            >
              <option value="email">email</option>
              <option value="sms">sms</option>
              <option value="whatsapp">whatsapp</option>
            </select>
          </div>
        </div>
        {error && <p className="error-text">{error}</p>}
        {result && <p style={{ color: "var(--success)", fontSize: 13 }}>{result}</p>}
        <button className="btn" style={{ width: "100%", marginTop: 4 }}>
          Enviar
        </button>
      </form>
    </Modal>
  );
}
