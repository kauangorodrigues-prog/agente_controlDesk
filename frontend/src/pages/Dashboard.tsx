import { useFetch } from "../api/hooks";
import { Metric, money } from "../components/ui";
import { useAuth } from "../context/AuthContext";

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

export default function Dashboard() {
  const { hasSector, user } = useAuth();
  const canSeeMis = hasSector("mis");
  const { data: ov } = useFetch<Overview>(canSeeMis ? "/mis/overview" : null);
  const { data: pf } = useFetch<PortfolioRow[]>(canSeeMis ? "/mis/by-portfolio" : null);

  if (!canSeeMis)
    return (
      <div className="card">
        <h3>Bem-vindo, {user?.full_name}</h3>
        <p className="muted">
          Você não possui acesso ao setor MIS. Utilize o menu lateral para acessar
          os setores liberados para o seu perfil.
        </p>
      </div>
    );

  return (
    <>
      <div className="grid cols-4">
        <Metric label="Dívidas ativas" value={ov?.total_debts ?? "—"} />
        <Metric label="Saldo em aberto" value={ov ? money(ov.total_outstanding) : "—"} />
        <Metric label="Total recuperado" value={ov ? money(ov.total_recovered) : "—"} />
        <Metric
          label="Taxa de quitação"
          value={ov ? `${ov.settlement_rate_pct}%` : "—"}
        />
      </div>

      <div className="section-title">Carteiras por tipo</div>
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Carteira</th>
              <th>Contratos</th>
              <th>Saldo em aberto</th>
              <th>Score médio</th>
              <th>Recuperabilidade</th>
            </tr>
          </thead>
          <tbody>
            {pf?.map((r) => (
              <tr key={r.portfolio}>
                <td style={{ textTransform: "capitalize" }}>{r.portfolio}</td>
                <td>{r.count}</td>
                <td>{money(r.outstanding)}</td>
                <td>{r.avg_risk_score}</td>
                <td style={{ width: 160 }}>
                  <div className="pill-bar">
                    <span style={{ width: `${r.avg_risk_score}%` }} />
                  </div>
                </td>
              </tr>
            ))}
            {!pf?.length && (
              <tr>
                <td colSpan={5} className="muted">
                  Sem dados. Rode o seed do backend.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </>
  );
}
