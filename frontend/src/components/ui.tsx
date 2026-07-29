import { ReactNode } from "react";

export function Metric({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="card metric">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
    </div>
  );
}

const STATUS_COLORS: Record<string, string> = {
  quitada: "green",
  concluida: "green",
  resolvido: "green",
  sucesso: "green",
  up: "green",
  pendente: "gray",
  backlog: "gray",
  recebida: "blue",
  negociacao: "blue",
  em_andamento: "blue",
  em_analise: "amber",
  acordo: "amber",
  review: "amber",
  investigando: "amber",
  degraded: "amber",
  aberto: "red",
  recusada: "red",
  down: "red",
  critica: "red",
  alta: "red",
  media: "amber",
  baixa: "gray",
};

export function Badge({ value }: { value: string }) {
  const color = STATUS_COLORS[value] ?? "gray";
  return <span className={`badge ${color}`}>{value}</span>;
}

export function Modal({
  title,
  children,
  onClose,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
}) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="card modal" onClick={(e) => e.stopPropagation()}>
        <div className="row between" style={{ marginBottom: 16 }}>
          <h3>{title}</h3>
          <button className="btn ghost" onClick={onClose}>
            ✕
          </button>
        </div>
        {children}
      </div>
    </div>
  );
}

export function money(v: number): string {
  return v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
}
