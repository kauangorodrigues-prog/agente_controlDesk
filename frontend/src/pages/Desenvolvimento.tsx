import { api } from "../api/client";
import { useFetch } from "../api/hooks";
import { Badge } from "../components/ui";

interface Feature {
  id: number;
  title: string;
  status: string;
  priority: string;
  squad: string;
}
interface Deployment {
  id: number;
  version: string;
  environment: string;
  status: string;
  deployed_at: string;
}

const COLUMNS = ["backlog", "em_andamento", "review", "concluido"];
const NEXT: Record<string, string> = {
  backlog: "em_andamento",
  em_andamento: "review",
  review: "concluido",
};

export default function Desenvolvimento() {
  const features = useFetch<Feature[]>("/desenvolvimento/features");
  const deployments = useFetch<Deployment[]>("/desenvolvimento/deployments");

  async function advance(f: Feature) {
    const next = NEXT[f.status];
    if (!next) return;
    await api.patch(`/desenvolvimento/features/${f.id}/status?new_status=${next}`);
    features.reload();
  }

  return (
    <>
      <div className="section-title">Board de features</div>
      <div className="grid cols-4">
        {COLUMNS.map((col) => (
          <div className="card" key={col}>
            <h3 style={{ textTransform: "capitalize", fontSize: 14 }}>
              {col.replace("_", " ")}
            </h3>
            <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 10 }}>
              {features.data
                ?.filter((f) => f.status === col)
                .map((f) => (
                  <div
                    key={f.id}
                    className="card"
                    style={{ padding: 12, background: "var(--bg-soft)" }}
                  >
                    <div style={{ fontSize: 13, fontWeight: 600 }}>{f.title}</div>
                    <div className="row between" style={{ marginTop: 8 }}>
                      <Badge value={f.priority} />
                      {NEXT[f.status] && (
                        <button className="btn ghost" style={{ padding: "4px 8px" }} onClick={() => advance(f)}>
                          →
                        </button>
                      )}
                    </div>
                  </div>
                ))}
            </div>
          </div>
        ))}
      </div>

      <div className="section-title">Deploys recentes</div>
      <div className="card">
        <table>
          <thead>
            <tr>
              <th>Versão</th>
              <th>Ambiente</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {deployments.data?.map((d) => (
              <tr key={d.id}>
                <td>{d.version}</td>
                <td>{d.environment}</td>
                <td>
                  <Badge value={d.status} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
