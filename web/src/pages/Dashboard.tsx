import { trpc } from "@/providers/trpc";
import {
  Ticket,
  AlertCircle,
  CheckCircle2,
  ShieldAlert,
  Activity,
  Database,
  Mail,
  Globe,
  HardDrive,
  Shield,
  ArrowUpRight,
  ArrowDownRight,
  TrendingUp,
  TrendingDown,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
} from "recharts";
import { useNavigate } from "react-router";

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

const STATUS_COLORS: Record<string, string> = {
  operational: "#22C55E",
  degraded: "#EAB308",
  down: "#EF4444",
};

const STATUS_LABELS: Record<string, string> = {
  open: "Aberto",
  in_progress: "Em Andamento",
  pending: "Pendente",
  resolved: "Resolvido",
  closed: "Fechado",
};

const CATEGORY_LABELS: Record<string, string> = {
  hardware: "Hardware",
  software: "Software",
  network: "Rede",
  security: "Seguranca",
  access: "Acesso",
  other: "Outro",
};

export default function Dashboard() {
  const navigate = useNavigate();
  const { data: stats } = trpc.dashboard.stats.useQuery();
  const { data: trendData } = trpc.dashboard.ticketTrend.useQuery();
  const { data: categoryData } = trpc.dashboard.ticketsByCategory.useQuery();
  const { data: recentTickets } = trpc.dashboard.recentTickets.useQuery();
  const { data: systemStatus } = trpc.dashboard.systemStatus.useQuery();

  const kpis = [
    {
      title: "Total de Tickets",
      value: stats?.totalTickets ?? 0,
      icon: Ticket,
      trend: stats?.trends.totalTickets.trend ?? "—",
      trendUp: stats?.trends.totalTickets.trendUp ?? true,
      color: COLORS.orange,
    },
    {
      title: "Tickets Abertos",
      value: stats?.openTickets ?? 0,
      icon: AlertCircle,
      trend: stats?.trends.openTickets.trend ?? "—",
      trendUp: stats?.trends.openTickets.trendUp ?? true,
      color: COLORS.yellow,
    },
    {
      title: "Resolvidos Hoje",
      value: stats?.resolvedToday ?? 0,
      icon: CheckCircle2,
      trend: stats?.trends.resolvedToday.trend ?? "—",
      trendUp: stats?.trends.resolvedToday.trendUp ?? true,
      color: COLORS.green,
    },
    {
      title: "Incidentes Críticos",
      value: stats?.criticalIncidents ?? 0,
      icon: ShieldAlert,
      trend: stats?.trends.criticalIncidents.trend ?? "—",
      trendUp: stats?.trends.criticalIncidents.trendUp ?? true,
      color: COLORS.red,
    },
  ];

  const pieData = (categoryData ?? []).map((item) => ({
    name: CATEGORY_LABELS[item.category] ?? item.category,
    value: item.count,
  }));

  const PIE_COLORS = [COLORS.orange, COLORS.orangeLight, COLORS.orangeDark, COLORS.gray, "#A1A1AA", "#52525B"];

  const formatDate = (dateStr: string) => {
    const d = new Date(dateStr);
    return d.toLocaleDateString("pt-BR", { day: "2-digit", month: "2-digit" });
  };

  const getStatusBadge = (status: string) => {
    const colors: Record<string, string> = {
      open: "bg-orange-500/10 text-orange-400 border-orange-500/20",
      in_progress: "bg-blue-500/10 text-blue-400 border-blue-500/20",
      pending: "bg-yellow-500/10 text-yellow-400 border-yellow-500/20",
      resolved: "bg-green-500/10 text-green-400 border-green-500/20",
      closed: "bg-gray-500/10 text-gray-400 border-gray-500/20",
    };
    return colors[status] ?? colors.open;
  };

  const getPriorityBadge = (priority: string) => {
    const colors: Record<string, string> = {
      low: "bg-green-500/10 text-green-400",
      medium: "bg-yellow-500/10 text-yellow-400",
      high: "bg-orange-500/10 text-orange-400",
      critical: "bg-red-500/10 text-red-400",
    };
    return colors[priority] ?? colors.medium;
  };

  return (
    <div className="space-y-6">
      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <div
              key={kpi.title}
              className="bg-[#111111] border border-[#27272A] rounded-lg p-5 card-hover cursor-pointer"
              onClick={() => kpi.title === "Total de Tickets" && navigate("/tickets")}
            >
              <div className="flex items-center justify-between mb-4">
                <div
                  className="w-10 h-10 rounded-lg flex items-center justify-center"
                  style={{ backgroundColor: `${kpi.color}15` }}
                >
                  <Icon className="w-5 h-5" style={{ color: kpi.color }} />
                </div>
                <span
                  className={`flex items-center gap-1 text-xs font-medium ${
                    kpi.trendUp ? "text-green-400" : "text-red-400"
                  }`}
                >
                  {kpi.trendUp ? (
                    <ArrowUpRight className="w-3.5 h-3.5" />
                  ) : (
                    <ArrowDownRight className="w-3.5 h-3.5" />
                  )}
                  {kpi.trend}
                </span>
              </div>
              <div className="text-2xl font-semibold font-mono text-[#F8FAFC] mb-1">
                {kpi.value}
              </div>
              <div className="text-xs text-[#94A3B8]">{kpi.title}</div>
            </div>
          );
        })}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Area Chart */}
        <div className="lg:col-span-2 bg-[#111111] border border-[#27272A] rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-[#F8FAFC]">
                Volume de Tickets
              </h3>
              <p className="text-xs text-[#64748B]">Últimos 7 dias</p>
            </div>
            <div className="flex items-center gap-2">
              {stats?.trends.totalTickets.trendUp === false ? (
                <TrendingDown className="w-4 h-4 text-[#EF4444]" />
              ) : (
                <TrendingUp className="w-4 h-4 text-[#22C55E]" />
              )}
              <span className={stats?.trends.totalTickets.trendUp === false ? "text-xs text-[#EF4444]" : "text-xs text-[#22C55E]"}>
                {stats?.trends.totalTickets.trend ?? "—"}
              </span>
            </div>
          </div>
          <div className="h-[260px]">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={trendData ?? []}>
                <defs>
                  <linearGradient id="colorTickets" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor={COLORS.orange} stopOpacity={0.3} />
                    <stop offset="95%" stopColor={COLORS.orange} stopOpacity={0} />
                  </linearGradient>
                </defs>
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
                  formatter={(value: number) => [`${value} tickets`, "Quantidade"]}
                  labelFormatter={(label: string) => formatDate(label)}
                />
                <Area
                  type="monotone"
                  dataKey="count"
                  stroke={COLORS.orange}
                  strokeWidth={2}
                  fillOpacity={1}
                  fill="url(#colorTickets)"
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Pie Chart */}
        <div className="bg-[#111111] border border-[#27272A] rounded-lg p-5">
          <h3 className="text-sm font-semibold text-[#F8FAFC] mb-1">
            Por Categoria
          </h3>
          <p className="text-xs text-[#64748B] mb-4">Distribuição atual</p>
          <div className="h-[200px]">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {pieData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
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
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="space-y-2 mt-2">
            {pieData.slice(0, 4).map((item, i) => (
              <div key={item.name} className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <div
                    className="w-2.5 h-2.5 rounded-full"
                    style={{ backgroundColor: PIE_COLORS[i] }}
                  />
                  <span className="text-[#94A3B8]">{item.name}</span>
                </div>
                <span className="text-[#F8FAFC] font-medium">{item.value}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Recent Tickets */}
        <div className="bg-[#111111] border border-[#27272A] rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-[#F8FAFC]">
                Tickets Recentes
              </h3>
              <p className="text-xs text-[#64748B]">Últimos 5 chamados</p>
            </div>
            <button
              onClick={() => navigate("/tickets")}
              className="text-xs text-[#F97316] hover:text-[#FB923C] flex items-center gap-1 transition-colors"
            >
              Ver todos
              <ArrowUpRight className="w-3 h-3" />
            </button>
          </div>
          <div className="space-y-2">
            {(recentTickets ?? []).map((ticket) => (
              <div
                key={ticket.id}
                className="flex items-center gap-3 p-3 rounded-lg bg-[#0A0A0A] hover:bg-[#1A1A1A] transition-colors cursor-pointer"
                onClick={() => navigate("/tickets")}
              >
                <div className="w-8 h-8 rounded-full bg-[#F97316]/10 flex items-center justify-center shrink-0">
                  <Ticket className="w-4 h-4 text-[#F97316]" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm text-[#F8FAFC] truncate">{ticket.title}</p>
                  <p className="text-xs text-[#64748B]">
                    #{ticket.id} · {CATEGORY_LABELS[ticket.category] ?? ticket.category}
                  </p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <span
                    className={`px-2 py-0.5 text-[10px] font-medium rounded-full border ${getStatusBadge(
                      ticket.status
                    )}`}
                  >
                    {STATUS_LABELS[ticket.status] ?? ticket.status}
                  </span>
                  <span
                    className={`px-2 py-0.5 text-[10px] font-medium rounded-full ${getPriorityBadge(
                      ticket.priority
                    )}`}
                  >
                    {ticket.priority}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* System Status */}
        <div className="bg-[#111111] border border-[#27272A] rounded-lg p-5">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h3 className="text-sm font-semibold text-[#F8FAFC]">
                Status dos Sistemas
              </h3>
              <p className="text-xs text-[#64748B]">Monitoramento em tempo real</p>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-2 h-2 rounded-full bg-green-500 status-dot" />
              <span className="text-xs text-[#22C55E]">Operacional</span>
            </div>
          </div>
          <div className="space-y-3">
            {(systemStatus ?? []).map((service) => {
              const iconMap: Record<string, React.ReactNode> = {
                "API Gateway": <Activity className="w-4 h-4" />,
                "Banco de Dados": <Database className="w-4 h-4" />,
                "Servidor de Email": <Mail className="w-4 h-4" />,
                "Portal de Clientes": <Globe className="w-4 h-4" />,
                "Servidor de Arquivos": <HardDrive className="w-4 h-4" />,
                Firewall: <Shield className="w-4 h-4" />,
              };
              return (
                <div
                  key={service.name}
                  className="flex items-center justify-between py-2 px-3 rounded-lg bg-[#0A0A0A]"
                >
                  <div className="flex items-center gap-3">
                    <div
                      className="w-8 h-8 rounded-lg flex items-center justify-center"
                      style={{
                        backgroundColor: `${STATUS_COLORS[service.status]}15`,
                        color: STATUS_COLORS[service.status],
                      }}
                    >
                      {iconMap[service.name]}
                    </div>
                    <div>
                      <p className="text-sm text-[#F8FAFC]">{service.name}</p>
                      <p className="text-xs text-[#64748B]">
                        {service.status === "operational"
                          ? "Operacional"
                          : service.status === "degraded"
                          ? "Degradado"
                          : "Fora do ar"}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-mono text-[#F8FAFC]">{service.uptime}</p>
                    <p className="text-xs text-[#64748B]">uptime</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
