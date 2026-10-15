import { useEffect, useState } from "react";
import { trpc } from "@/providers/trpc";
import { useAuth } from "@/hooks/useAuth";
import {
  Gauge,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Timer,
  Save,
} from "lucide-react";
import { Input } from "@/components/ui/input";

const PRIORITY_LABELS: Record<string, string> = {
  low: "Baixa",
  medium: "Média",
  high: "Alta",
  critical: "Crítica",
};

const PRIORITY_COLORS: Record<string, string> = {
  low: "text-green-400",
  medium: "text-yellow-400",
  high: "text-orange-400",
  critical: "text-red-400",
};

const SLA_BADGE: Record<string, string> = {
  ok: "bg-green-500/10 text-green-400",
  at_risk: "bg-yellow-500/10 text-yellow-400",
  breached: "bg-red-500/10 text-red-400",
};

const SLA_LABEL: Record<string, string> = {
  ok: "No prazo",
  at_risk: "Em risco",
  breached: "Violado",
};

function formatRemaining(hours: number) {
  if (hours <= 0) {
    const over = Math.abs(hours);
    if (over >= 24) return `Vencido há ${Math.round(over / 24)}d`;
    return `Vencido há ${Math.round(over)}h`;
  }
  if (hours >= 48) return `${Math.round(hours / 24)}d restantes`;
  if (hours >= 1) return `${Math.round(hours)}h restantes`;
  return `${Math.round(hours * 60)}min restantes`;
}

export default function SLA() {
  const { user } = useAuth();
  const isAdmin = user?.role === "admin";
  const utils = trpc.useUtils();

  const { data: overview, isLoading } = trpc.sla.overview.useQuery();
  const { data: policies } = trpc.sla.policies.useQuery();

  const cards = [
    {
      label: "Conformidade",
      value: `${overview?.compliance ?? 100}%`,
      icon: Gauge,
      color: "#F97316",
    },
    {
      label: "No prazo",
      value: overview?.summary.ok ?? 0,
      icon: CheckCircle2,
      color: "#22C55E",
    },
    {
      label: "Em risco",
      value: overview?.summary.atRisk ?? 0,
      icon: AlertTriangle,
      color: "#EAB308",
    },
    {
      label: "Violado",
      value: overview?.summary.breached ?? 0,
      icon: XCircle,
      color: "#EF4444",
    },
  ];

  return (
    <div className="space-y-4">
      {/* Summary */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {cards.map((c) => (
          <div
            key={c.label}
            className="bg-[#111111] border border-[#27272A] rounded-lg p-4 flex items-center gap-4"
          >
            <div
              className="w-10 h-10 rounded-lg flex items-center justify-center shrink-0"
              style={{ backgroundColor: `${c.color}1A` }}
            >
              <c.icon className="w-5 h-5" style={{ color: c.color }} />
            </div>
            <div className="min-w-0">
              <p className="text-2xl font-semibold text-[#F8FAFC]">{c.value}</p>
              <p className="text-xs text-[#64748B]">{c.label}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Active tickets vs SLA */}
      <div className="bg-[#111111] border border-[#27272A] rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-[#27272A] flex items-center gap-2">
          <Timer className="w-4 h-4 text-[#F97316]" />
          <h3 className="text-sm font-medium text-[#F8FAFC]">
            Tickets ativos x SLA
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-[#1A1A1A] border-b border-[#27272A]">
                <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase">
                  Ticket
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase hidden sm:table-cell">
                  Prioridade
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase">
                  SLA
                </th>
                <th className="text-left px-4 py-3 text-xs font-medium text-[#94A3B8] uppercase">
                  Prazo
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#27272A]/50">
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>
                    <td colSpan={4} className="px-4 py-4">
                      <div className="h-8 bg-[#1A1A1A] rounded animate-pulse" />
                    </td>
                  </tr>
                ))
              ) : overview && overview.tickets.length > 0 ? (
                overview.tickets.map((t) => (
                  <tr
                    key={t.id}
                    className="hover:bg-[#1A1A1A]/50 transition-colors"
                  >
                    <td className="px-4 py-3">
                      <p className="text-sm text-[#F8FAFC] truncate max-w-[280px]">
                        {t.title}
                      </p>
                      <p className="text-xs text-[#64748B] font-mono">#{t.id}</p>
                    </td>
                    <td className="px-4 py-3 hidden sm:table-cell">
                      <span
                        className={`text-xs font-medium ${PRIORITY_COLORS[t.priority]}`}
                      >
                        {PRIORITY_LABELS[t.priority]}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-block px-2 py-0.5 text-[10px] font-medium rounded-full ${SLA_BADGE[t.slaStatus]}`}
                      >
                        {SLA_LABEL[t.slaStatus]}
                      </span>
                    </td>
                    <td
                      className={`px-4 py-3 text-xs ${
                        t.slaStatus === "breached"
                          ? "text-[#EF4444]"
                          : t.slaStatus === "at_risk"
                            ? "text-[#EAB308]"
                            : "text-[#94A3B8]"
                      }`}
                    >
                      {formatRemaining(t.hoursRemaining)}
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan={4} className="px-4 py-12 text-center text-[#64748B]">
                    <CheckCircle2 className="w-10 h-10 mx-auto mb-3 text-[#27272A]" />
                    <p className="text-sm">Nenhum ticket ativo no momento</p>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Policies */}
      <div className="bg-[#111111] border border-[#27272A] rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-[#27272A]">
          <h3 className="text-sm font-medium text-[#F8FAFC]">
            Metas de SLA por prioridade
          </h3>
          <p className="text-xs text-[#64748B] mt-0.5">
            Tempo de resposta e de resolução (em horas).
            {isAdmin
              ? " Edite e salve para atualizar."
              : " Somente administradores podem editar."}
          </p>
        </div>
        <div className="divide-y divide-[#27272A]/50">
          {policies?.map((p) => (
            <PolicyRow
              key={p.priority}
              priority={p.priority}
              responseHours={p.responseHours}
              resolutionHours={p.resolutionHours}
              editable={isAdmin}
              onSaved={() => {
                utils.sla.policies.invalidate();
                utils.sla.overview.invalidate();
              }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

function PolicyRow({
  priority,
  responseHours,
  resolutionHours,
  editable,
  onSaved,
}: {
  priority: string;
  responseHours: number;
  resolutionHours: number;
  editable: boolean;
  onSaved: () => void;
}) {
  const [resp, setResp] = useState(responseHours);
  const [reso, setReso] = useState(resolutionHours);

  useEffect(() => {
    setResp(responseHours);
    setReso(resolutionHours);
  }, [responseHours, resolutionHours]);

  const mutation = trpc.sla.updatePolicy.useMutation({ onSuccess: onSaved });
  const dirty = resp !== responseHours || reso !== resolutionHours;

  return (
    <div className="px-4 py-3 flex flex-col sm:flex-row sm:items-center gap-3">
      <div className="sm:w-32">
        <span className={`text-sm font-medium ${PRIORITY_COLORS[priority]}`}>
          {PRIORITY_LABELS[priority]}
        </span>
      </div>
      <div className="flex items-center gap-4 flex-1">
        <label className="flex items-center gap-2">
          <span className="text-xs text-[#64748B]">Resposta</span>
          <Input
            type="number"
            min={1}
            value={resp}
            disabled={!editable}
            onChange={(e) => setResp(Number(e.target.value))}
            className="h-8 w-20 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] text-sm disabled:opacity-70"
          />
          <span className="text-xs text-[#64748B]">h</span>
        </label>
        <label className="flex items-center gap-2">
          <span className="text-xs text-[#64748B]">Resolução</span>
          <Input
            type="number"
            min={1}
            value={reso}
            disabled={!editable}
            onChange={(e) => setReso(Number(e.target.value))}
            className="h-8 w-20 bg-[#1A1A1A] border-[#27272A] text-[#F8FAFC] text-sm disabled:opacity-70"
          />
          <span className="text-xs text-[#64748B]">h</span>
        </label>
      </div>
      {editable && (
        <button
          onClick={() =>
            mutation.mutate({
              priority: priority as "low" | "medium" | "high" | "critical",
              responseHours: resp,
              resolutionHours: reso,
            })
          }
          disabled={!dirty || mutation.isPending}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-[#F97316] hover:bg-[#EA580C] text-white text-xs font-medium rounded-md transition-colors disabled:opacity-40"
        >
          <Save className="w-3.5 h-3.5" />
          {mutation.isPending ? "Salvando..." : "Salvar"}
        </button>
      )}
    </div>
  );
}
