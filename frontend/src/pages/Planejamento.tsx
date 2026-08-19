import { useFetch } from "../api/hooks";
import { money } from "../components/ui";

interface Forecast {
  id: number;
  reference_month: string;
  portfolio: string;
  expected_recovery: number;
  expected_volume: number;
}
interface Goal {
  id: number;
  reference_month: string;
  portfolio: string;
  target_amount: number;
  achieved_amount: number;
  attainment_pct: number;
}

export default function Planejamento() {
  const forecasts = useFetch<Forecast[]>("/planejamento/forecasts");
  const goals = useFetch<Goal[]>("/planejamento/goals");

  return (
    <div className="grid cols-2">
      <div className="card">
        <h3>Forecast por carteira</h3>
        <table style={{ marginTop: 12 }}>
          <thead>
            <tr>
              <th>Mês</th>
              <th>Carteira</th>
              <th>Recuperação prevista</th>
              <th>Volume</th>
            </tr>
          </thead>
          <tbody>
            {forecasts.data?.map((f) => (
              <tr key={f.id}>
                <td>{f.reference_month}</td>
                <td style={{ textTransform: "capitalize" }}>{f.portfolio}</td>
                <td>{money(f.expected_recovery)}</td>
                <td>{f.expected_volume.toLocaleString("pt-BR")}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3>Metas x Realizado</h3>
        <table style={{ marginTop: 12 }}>
          <thead>
            <tr>
              <th>Carteira</th>
              <th>Meta</th>
              <th>Atingimento</th>
            </tr>
          </thead>
          <tbody>
            {goals.data?.map((g) => (
              <tr key={g.id}>
                <td style={{ textTransform: "capitalize" }}>{g.portfolio}</td>
                <td>{money(g.target_amount)}</td>
                <td style={{ width: 200 }}>
                  <div className="row">
                    <div className="pill-bar" style={{ flex: 1 }}>
                      <span style={{ width: `${Math.min(g.attainment_pct, 100)}%` }} />
                    </div>
                    <span className="muted" style={{ fontSize: 12 }}>
                      {g.attainment_pct}%
                    </span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
