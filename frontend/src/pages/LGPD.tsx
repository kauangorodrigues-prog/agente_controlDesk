import { useState } from "react";
import { api } from "../api/client";
import { useFetch } from "../api/hooks";
import { Badge } from "../components/ui";
import { useAuth } from "../context/AuthContext";

interface DSR {
  id: number;
  requester_document: string;
  request_type: string;
  status: string;
  created_at: string;
}
interface AuditLog {
  id: number;
  actor_email: string | null;
  action: string;
  entity: string;
  entity_id: string | null;
  created_at: string;
}
interface Notice {
  controlador: string;
  encarregado_dpo: string;
  finalidades: string[];
  bases_legais: string[];
  direitos_do_titular: string[];
  retencao_dias: number;
}

const DSR_STATUSES = ["recebida", "em_analise", "concluida", "recusada"];

export default function LGPD() {
  const { hasMinRole } = useAuth();
  const notice = useFetch<Notice>("/lgpd/privacy-notice");
  const requests = useFetch<DSR[]>("/lgpd/requests");
  const logs = useFetch<AuditLog[]>(hasMinRole("gerencia") ? "/lgpd/audit-logs?limit=40" : null);

  async function setStatus(id: number, status: string) {
    await api.patch(`/lgpd/requests/${id}`, { status });
    requests.reload();
  }

  return (
    <>
      <div className="grid cols-3">
        <div className="card">
          <h3>Controlador</h3>
          <p className="muted" style={{ marginBottom: 4 }}>{notice.data?.controlador}</p>
          <p className="muted" style={{ fontSize: 13 }}>
            DPO: {notice.data?.encarregado_dpo}
          </p>
          <p className="muted" style={{ fontSize: 13 }}>
            Retenção: {notice.data?.retencao_dias} dias
          </p>
        </div>
        <div className="card">
          <h3>Bases legais</h3>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
            {notice.data?.bases_legais.map((b) => (
              <span key={b} className="badge gray">
                {b}
              </span>
            ))}
          </div>
        </div>
        <div className="card">
          <h3>Direitos do titular</h3>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 6, marginTop: 8 }}>
            {notice.data?.direitos_do_titular.map((d) => (
              <span key={d} className="badge blue">
                {d}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="section-title">Requisições de titulares (art. 18)</div>
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Documento</th>
              <th>Tipo</th>
              <th>Status</th>
              <th>Ação</th>
            </tr>
          </thead>
          <tbody>
            {requests.data?.map((r) => (
              <tr key={r.id}>
                <td className="muted">{r.requester_document}</td>
                <td>
                  <Badge value={r.request_type} />
                </td>
                <td>
                  <Badge value={r.status} />
                </td>
                <td>
                  <select
                    className="input"
                    style={{ padding: "6px 8px" }}
                    value={r.status}
                    onChange={(e) => setStatus(r.id, e.target.value)}
                  >
                    {DSR_STATUSES.map((s) => (
                      <option key={s} value={s}>
                        {s}
                      </option>
                    ))}
                  </select>
                </td>
              </tr>
            ))}
            {!requests.data?.length && (
              <tr>
                <td colSpan={4} className="muted">
                  Nenhuma requisição registrada.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {hasMinRole("gerencia") && (
        <>
          <div className="section-title">Trilha de auditoria</div>
          <div className="card">
            <table>
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Ator</th>
                  <th>Ação</th>
                  <th>Entidade</th>
                </tr>
              </thead>
              <tbody>
                {logs.data?.map((l) => (
                  <tr key={l.id}>
                    <td className="muted">
                      {new Date(l.created_at).toLocaleString("pt-BR")}
                    </td>
                    <td>{l.actor_email ?? "—"}</td>
                    <td>
                      <span className="badge gray">{l.action}</span>
                    </td>
                    <td className="muted">
                      {l.entity}
                      {l.entity_id ? `#${l.entity_id}` : ""}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </>
  );
}
