import { api } from "../api/client";
import { useFetch } from "../api/hooks";
import { Badge } from "../components/ui";

interface Incident {
  id: number;
  title: string;
  severity: string;
  status: string;
  service: string;
}
interface Health {
  has_open_incidents: boolean;
  checks: {
    service: string;
    status: string;
    latency_ms: number;
    cpu_pct: number;
    mem_pct: number;
  }[];
}

export default function Infraestrutura() {
  const incidents = useFetch<Incident[]>("/infraestrutura/incidents");
  const health = useFetch<Health>("/infraestrutura/health");

  async function resolve(id: number) {
    await api.post(`/infraestrutura/incidents/${id}/resolve`);
    incidents.reload();
  }

  return (
    <div className="grid cols-2">
      <div className="card">
        <h3>Incidentes</h3>
        <table style={{ marginTop: 12 }}>
          <thead>
            <tr>
              <th>Título</th>
              <th>Severidade</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {incidents.data?.map((i) => (
              <tr key={i.id}>
                <td>{i.title}</td>
                <td>
                  <Badge value={i.severity} />
                </td>
                <td>
                  <Badge value={i.status} />
                </td>
                <td>
                  {i.status !== "resolvido" && (
                    <button className="btn ghost" onClick={() => resolve(i.id)}>
                      Resolver
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {!incidents.data?.length && (
              <tr>
                <td colSpan={4} className="muted">
                  Nenhum incidente aberto. 🎉
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <div className="card">
        <h3>Saúde dos sistemas</h3>
        <table style={{ marginTop: 12 }}>
          <thead>
            <tr>
              <th>Serviço</th>
              <th>Status</th>
              <th>Latência</th>
              <th>CPU</th>
              <th>Mem</th>
            </tr>
          </thead>
          <tbody>
            {health.data?.checks.map((c, idx) => (
              <tr key={idx}>
                <td>{c.service}</td>
                <td>
                  <Badge value={c.status} />
                </td>
                <td>{c.latency_ms} ms</td>
                <td>{c.cpu_pct}%</td>
                <td>{c.mem_pct}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
