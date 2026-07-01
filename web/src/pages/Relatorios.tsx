import { useState } from "react";
import { trpc } from "@/providers/trpc";
import {
  BarChart3,
  TrendingUp,
  CheckCircle2,
  AlertTriangle,
  Download,
} from "lucide-react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

const COLORS = {
  orange: "#F97316",
  orangeLight: "#FB923C",
  orangeDark: "#EA580C",
  green: "#22C55E",
  yellow: "#EAB308",
  red: "#EF4444",
  blue: "#3B82F6",
  gray: "#64748B",
};

const PRIORITY_COLORS: Record<string, string> = {
  low: "#22C55E",
  medium: "#EAB308",
  high: "#F97316",
  critical: "#EF4444",
};

const PRIORITY_LABELS: Record<string, string> = {
  low: "Baixa",
  medium: "Média",
  high: "Alta",
  critical: "Crítica",
};

const datePresets = [
  { label: "7 dias", value: 7 },
  { label: "30 dias", value: 30 },
  { label: "90 dias", value: 90 },
];

export default function Relatorios() {
  const [days, setDays] = useState(7);

  const { data: ticketVolume } = trpc.report.ticketVolume.useQuery({ days });
  const { data: resolutionTime } = trpc.report.resolutionTime.useQuery();
  const { data: priorityDistribution } = trpc.report.priorityDistribution.useQuery();
  const { data: summary } = trpc.report.summary.useQuery({ days });

  const pieData = (priorityDistribution ?? []).map((item) => ({
    name: PRIORITY_LABELS[item.priority] ?? item.priority,
    value: item.count,
    color: PRIORITY_COLORS[item.priority] ?? COLORS.gray,
  }));

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
  };

  return (
    <div className="space-y-6">
      {/* Date Filter & Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          {datePresets.map((preset) => (
            <button
              key={preset.value}
              onClick={() => setDays(preset.value)}
              className={`px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                days === preset.value
                  ? "bg-[#F97316] text-white"
                  : "bg-[#111111] border border-[#27272A] text-[#94A3B8] hover:text-[#F8FAFC] hover:border-[#F97316]/30"
              }`}
            >
              {preset.label}
            </button>
          ))}
        </div>
        <button className="flex items-center gap-2 px-4 py-2 bg-[#111111] border border-[#27272A] text-[#94A3B8] hover:text-[#F8FAFC] hover:border-[#F97316]/30 text-sm rounded-md transition-colors">
          <Download className="w-4 h-4" />
          Exportar
        </button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {[
          {
            title: "Total de Tickets",
            value: summary?.totalTickets ?? 0,
            icon: BarChart3,
            color: COLORS.orange,
          },
          {
            title: "Taxa de Resolução",
            value: `${summary?.resolutionRate ?? 0}%`,
            icon: CheckCircle2,
            color: COLORS.green,
          },
          {
            title: "Tickets Abertos",
            value: summary?.openTickets ?? 0,
            icon: TrendingUp,
            color: COLORS.yellow,
          },
          {
            title: "Incidentes",
            value: summary?.totalIncidents ?? 0,
            icon: AlertTriangle,
            color: COLORS.red,
          },
        ].map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.title} className="bg-[#111111] border border-[#27272A] rounded-lg p-5 card-hover">
              <div className="flex items-center gap-3 mb-3">
                <div
                  className="w-10 h-10 rounded-lg flex items-center justify-center"
                  style={{ backgroundColor: `${item.color}15` }}
                >
                  <Icon className="w-5 h-5" style={{ color: item.color }} />
                </div>
                <span className="text-xs text-[#94A3B8]">{item.title}</span>
              </div>
              <div className="text-2xl font-semibold font-mono text-[#F8FAFC]">{item.value}</div>
            </div>
          );
        })}
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Ticket Volume */}
        <div className="bg-[#111111] border border-[#27272A] rounded-lg p-5">
          <h3 className="text-sm font-semibold text-[#F8FAFC] mb-1">Volume de Tickets</h3>
          <p className="text-xs text-[#64748B] mb-4">Criados vs Resolvidos</p>
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={ticketVolume ?? []}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272A" vertical={false} />
                <XAxis
                  dataKey="date"
                  tickFormatter={formatDate}
                  stroke="#64748B"
                  tick={{ fontSize: 11 }}
                  axisLine={{ stroke: "#27272A" }}
                />
                <YAxis
                  stroke="#64748B"
                  tick={{ fontSize: 11 }}
                  axisLine={{ stroke: "#27272A" }}
                  allowDecimals={false}
                />
                <Tooltip
                  contentStyle={{
                    background: "#1A1A1A",
                    border: "1px solid #27272A",
                    borderRadius: "6px",
                    fontSize: "12px",
                    color: "#F8FAFC",
                  }}
                  labelFormatter={(label: string) => formatDate(label)}
                />
                <Legend
                  wrapperStyle={{ fontSize: "11px", color: "#94A3B8" }}
                />
                <Bar dataKey="created" name="Criados" fill={COLORS.orange} radius={[4, 4, 0, 0]} />
                <Bar dataKey="resolved" name="Resolvidos" fill={COLORS.green} radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Resolution Time */}
        <div className="bg-[#111111] border border-[#27272A] rounded-lg p-5">
          <h3 className="text-sm font-semibold text-[#F8FAFC] mb-1">Tempo Médio de Resolução</h3>
          <p className="text-xs text-[#64748B] mb-4">Por categoria (horas)</p>
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={resolutionTime ?? []} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#27272A" horizontal={false} />
                <XAxis
                  type="number"
                  stroke="#64748B"
                  tick={{ fontSize: 11 }}
                  axisLine={{ stroke: "#27272A" }}
                  unit="h"
                />
                <YAxis
                  dataKey="category"
                  type="category"
                  stroke="#94A3B8"
                  tick={{ fontSize: 11 }}
                  axisLine={{ stroke: "#27272A" }}
                  width={100}
                />
                <Tooltip
                  contentStyle={{
                    background: "#1A1A1A",
                    border: "1px solid #27272A",
                    borderRadius: "6px",
                    fontSize: "12px",
                    color: "#F8FAFC",
                  }}
                  formatter={(value: number) => [`${value} horas`, "Tempo Médio"]}
                />
                <Bar dataKey="hours" fill={COLORS.orange} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Priority Distribution */}
        <div className="bg-[#111111] border border-[#27272A] rounded-lg p-5">
          <h3 className="text-sm font-semibold text-[#F8FAFC] mb-1">Distribuição de Prioridade</h3>
          <p className="text-xs text-[#64748B] mb-4">Todos os tickets</p>
          <div className="h-[280px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={90}
                  paddingAngle={4}
                  dataKey="value"
                >
                  {pieData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.color} />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    background: "#1A1A1A",
                    border: "1px solid #27272A",
                    borderRadius: "6px",
                    fontSize: "12px",
                    color: "#F8FAFC",
                  }}
                />
                <Legend
                  verticalAlign="bottom"
                  wrapperStyle={{ fontSize: "11px", color: "#94A3B8" }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Stats Overview */}
        <div className="bg-[#111111] border border-[#27272A] rounded-lg p-5">
          <h3 className="text-sm font-semibold text-[#F8FAFC] mb-1">Visão Geral</h3>
          <p className="text-xs text-[#64748B] mb-4">Métricas do período</p>
          <div className="space-y-4">
            {[
              { label: "Taxa de Resolução", value: summary?.resolutionRate ?? 0, total: 100, color: COLORS.green, suffix: "%" },
              { label: "Tickets no Período", value: summary?.totalTickets ?? 0, total: 100, color: COLORS.orange, suffix: "" },
              { label: "Incidentes", value: summary?.totalIncidents ?? 0, total: 50, color: COLORS.red, suffix: "" },
              { label: "Abertos", value: summary?.openTickets ?? 0, total: 30, color: COLORS.yellow, suffix: "" },
            ].map((stat) => (
              <div key={stat.label}>
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs text-[#94A3B8]">{stat.label}</span>
                  <span className="text-sm font-mono font-medium text-[#F8FAFC]">
                    {stat.value}{stat.suffix}
                  </span>
                </div>
                <div className="h-2 bg-[#0A0A0A] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.min(100, (stat.value / stat.total) * 100)}%`,
                      backgroundColor: stat.color,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
