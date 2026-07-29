import { FormEvent, useState } from "react";
import { api, ApiError } from "../api/client";
import { useFetch } from "../api/hooks";
import { Badge, Modal, money } from "../components/ui";

interface Debtor {
  id: number;
  full_name: string;
  document_masked: string;
  email: string | null;
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

const PORTFOLIOS = ["ativa", "consignado", "concierge", "bancario"];

export default function Cobranca() {
  const [q, setQ] = useState("");
  const debtors = useFetch<Debtor[]>(`/collection/debtors?q=${encodeURIComponent(q)}`, [q]);
  const debts = useFetch<Debt[]>("/collection/debts");
  const [showDebtor, setShowDebtor] = useState(false);
  const [showDebt, setShowDebt] = useState(false);

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

      {showDebtor && (
        <DebtorModal
          onClose={() => setShowDebtor(false)}
          onSaved={() => {
            setShowDebtor(false);
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
