import { useFetch } from "../api/hooks";
import { Metric } from "../components/ui";

interface Monitor {
  campaigns_active: number;
  agents_online: number;
  mailing_total: number;
  mailing_penetration_pct: number;
  campaigns: {
    id: number;
    name: string;
    portfolio: string;
    pacing: number;
    agents_online: number;
  }[];
}

export default function ControlDesk() {
  const { data, error } = useFetch<Monitor>("/control-desk/monitor");

  if (error) return <div className="card error-text">{error}</div>;

  return (
    <>
      <div className="grid cols-4">
        <Metric label="Campanhas ativas" value={data?.campaigns_active ?? "—"} />
        <Metric label="Agentes online" value={data?.agents_online ?? "—"} />
        <Metric label="Mailing total" value={data?.mailing_total?.toLocaleString("pt-BR") ?? "—"} />
        <Metric
          label="Penetração mailing"
          value={data ? `${data.mailing_penetration_pct}%` : "—"}
        />
      </div>

      <div className="section-title">Campanhas em operação</div>
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Campanha</th>
              <th>Carteira</th>
              <th>Agentes</th>
              <th>Pacing</th>
            </tr>
          </thead>
          <tbody>
            {data?.campaigns.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td style={{ textTransform: "capitalize" }}>{c.portfolio}</td>
                <td>{c.agents_online}</td>
                <td>
                  <span className="badge blue">{c.pacing.toFixed(1)}x</span>
                </td>
              </tr>
            ))}
            {!data?.campaigns.length && (
              <tr>
                <td colSpan={4} className="muted">
                  Nenhuma campanha ativa.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
