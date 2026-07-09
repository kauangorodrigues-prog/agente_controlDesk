import { Outlet, useLocation, useNavigate } from "react-router";
import { useState } from "react";
import {
  LayoutDashboard,
  Ticket,
  MessageSquare,
  AlertTriangle,
  BookOpen,
  Users,
  BarChart3,
  Settings,
  LogOut,
  Menu,
  X,
  Bot,
  ChevronDown,
  Bell,
  Search,
  User,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";

const navItems = [
  { path: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { path: "/tickets", label: "Tickets", icon: Ticket },
  { path: "/chat", label: "Chat IA", icon: MessageSquare },
  { path: "/incidentes", label: "Incidentes", icon: AlertTriangle },
  { path: "/base-conhecimento", label: "Base de Conhecimento", icon: BookOpen },
  { path: "/equipe", label: "Equipe", icon: Users },
  { path: "/relatorios", label: "Relatórios", icon: BarChart3 },
  { path: "/configuracoes", label: "Configurações", icon: Settings },
];

export default function MainLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout, isLoading } = useAuth({
    redirectOnUnauthenticated: true,
  });
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  const isActive = (path: string) => location.pathname === path;

  const pageTitle = navItems.find((item) => isActive(item.path))?.label ?? "NexusAI";

  if (isLoading || !user) {
    return (
      <div className="flex h-screen items-center justify-center bg-[#0A0A0A] text-[#94A3B8]">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-[#F97316] flex items-center justify-center animate-pulse">
            <Bot className="w-5 h-5 text-white" />
          </div>
          <p className="text-sm">Carregando...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-[#0A0A0A] text-[#F8FAFC] overflow-hidden">
      {/* Mobile Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/60 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed lg:static inset-y-0 left-0 z-50 w-[260px] bg-[#0D0D0D] border-r border-[#27272A] flex flex-col transition-transform duration-300 ${
          sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
        }`}
      >
        {/* Logo */}
        <div className="h-16 flex items-center px-6 border-b border-[#27272A]">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-[#F97316] flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-sm font-semibold tracking-tight">NexusAI</h1>
              <p className="text-[10px] text-[#64748B] -mt-0.5">Control Desk</p>
            </div>
          </div>
          <button
            className="ml-auto lg:hidden text-[#94A3B8] hover:text-white"
            onClick={() => setSidebarOpen(false)}
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Nav Items */}
        <nav className="flex-1 py-4 px-3 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            return (
              <button
                key={item.path}
                onClick={() => {
                  navigate(item.path);
                  setSidebarOpen(false);
                }}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                  active
                    ? "bg-[#1A1A1A] text-[#F97316] border-l-[3px] border-[#F97316]"
                    : "text-[#94A3B8] hover:bg-[#1A1A1A] hover:text-[#F8FAFC] border-l-[3px] border-transparent"
                }`}
              >
                <Icon className={`w-[18px] h-[18px] ${active ? "text-[#F97316]" : ""}`} />
                {item.label}
              </button>
            );
          })}
        </nav>

        {/* Bottom - User */}
        <div className="p-3 border-t border-[#27272A]">
          <div className="relative">
            <button
              onClick={() => setUserMenuOpen(!userMenuOpen)}
              className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-[#1A1A1A] transition-colors"
            >
              <div className="w-8 h-8 rounded-full bg-[#F97316]/20 flex items-center justify-center">
                <User className="w-4 h-4 text-[#F97316]" />
              </div>
              <div className="flex-1 text-left">
                <p className="text-sm font-medium text-[#F8FAFC] truncate">
                  {user?.name ?? "Usuário"}
                </p>
                <p className="text-xs text-[#64748B] truncate">
                  {user?.email ?? "usuario@empresa.com"}
                </p>
              </div>
              <ChevronDown className={`w-4 h-4 text-[#64748B] transition-transform ${userMenuOpen ? "rotate-180" : ""}`} />
            </button>

            {userMenuOpen && (
              <div className="absolute bottom-full left-0 right-0 mb-1 bg-[#1A1A1A] border border-[#27272A] rounded-lg shadow-lg overflow-hidden">
                <button
                  onClick={() => {
                    navigate("/configuracoes");
                    setUserMenuOpen(false);
                  }}
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-[#94A3B8] hover:bg-[#27272A] hover:text-[#F8FAFC] transition-colors"
                >
                  <Settings className="w-4 h-4" />
                  Configurações
                </button>
                <button
                  onClick={() => {
                    logout();
                    setUserMenuOpen(false);
                  }}
                  className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-[#EF4444] hover:bg-[#27272A] transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  Sair
                </button>
              </div>
            )}
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top Bar */}
        <header className="h-16 bg-[#0A0A0A] border-b border-[#27272A] flex items-center justify-between px-4 lg:px-6 shrink-0">
          <div className="flex items-center gap-4">
            <button
              className="lg:hidden text-[#94A3B8] hover:text-white p-1"
              onClick={() => setSidebarOpen(true)}
            >
              <Menu className="w-5 h-5" />
            </button>
            <div>
              <h2 className="text-base font-semibold">{pageTitle}</h2>
              <p className="text-xs text-[#64748B] hidden sm:block">
                {new Date().toLocaleDateString("pt-BR", {
                  weekday: "long",
                  year: "numeric",
                  month: "long",
                  day: "numeric",
                })}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            <button className="p-2 text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#1A1A1A] rounded-lg transition-colors">
              <Search className="w-[18px] h-[18px]" />
            </button>
            <button className="p-2 text-[#94A3B8] hover:text-[#F8FAFC] hover:bg-[#1A1A1A] rounded-lg transition-colors relative">
              <Bell className="w-[18px] h-[18px]" />
              <span className="absolute top-1.5 right-1.5 w-2 h-2 bg-[#F97316] rounded-full" />
            </button>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-4 lg:p-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
