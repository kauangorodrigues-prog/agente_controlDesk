import { useFetch } from "../api/hooks";
import { Badge, Metric, money } from "../components/ui";

interface Overview {
  total_debts: number;
  total_outstanding: number;
  total_recovered: number;
  debts_settled: number;
  settlement_rate_pct: number;
}
interface PortfolioRow {
  portfolio: string;
  count: number;
  outstanding: number;
  avg_risk_score: number;
}
interface StatusRow {
  status: string;
  count: number;
}

export default function MIS() {
  const ov = useFetch<Overview>("/mis/overview");
  const pf = useFetch<PortfolioRow[]>("/mis/by-portfolio");
  const st = useFetch<StatusRow[]>("/mis/by-status");

  return (
    <>
      <div className="grid cols-4">
        <Metric label="Total de dívidas" value={ov.data?.total_debts ?? "—"} />
        <Metric label="Em aberto" value={ov.data ? money(ov.data.total_outstanding) : "—"} />
        <Metric label="Recuperado" value={ov.data ? money(ov.data.total_recovered) : "—"} />
        <Metric label="Quitação" value={ov.data ? `${ov.data.settlement_rate_pct}%` : "—"} />
      </div>

      <div className="grid cols-2" style={{ marginTop: 20 }}>
        <div className="card">
          <h3>Distribuição por carteira</h3>
          <table style={{ marginTop: 12 }}>
            <thead>
              <tr>
                <th>Carteira</th>
                <th>Qtd</th>
                <th>Em aberto</th>
                <th>Score médio</th>
              </tr>
            </thead>
            <tbody>
              {pf.data?.map((r) => (
                <tr key={r.portfolio}>
                  <td style={{ textTransform: "capitalize" }}>{r.portfolio}</td>
                  <td>{r.count}</td>
                  <td>{money(r.outstanding)}</td>
                  <td>{r.avg_risk_score}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="card">
          <h3>Distribuição por status</h3>
          <table style={{ marginTop: 12 }}>
            <thead>
              <tr>
                <th>Status</th>
                <th>Quantidade</th>
              </tr>
            </thead>
            <tbody>
              {st.data?.map((r) => (
                <tr key={r.status}>
                  <td>
                    <Badge value={r.status} />
                  </td>
                  <td>{r.count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </>
  );
}
