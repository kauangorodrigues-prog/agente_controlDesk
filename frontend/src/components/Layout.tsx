import { NavLink, Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

interface NavItem {
  to: string;
  label: string;
  icon: string;
  sector?: string;
  minRole?: "diretoria" | "gerencia" | "administracao";
}

const MAIN_NAV: NavItem[] = [
  { to: "/", label: "Visão Geral", icon: "▣" },
  { to: "/cobranca", label: "Cobrança", icon: "₵" },
];

const SECTOR_NAV: NavItem[] = [
  { to: "/control-desk", label: "Control Desk", icon: "◉", sector: "control_desk" },
  { to: "/planejamento", label: "Planejamento", icon: "◈", sector: "planejamento" },
  { to: "/mis", label: "MIS", icon: "▤", sector: "mis" },
  { to: "/desenvolvimento", label: "Desenvolvimento", icon: "⌘", sector: "desenvolvimento" },
  { to: "/infraestrutura", label: "Infraestrutura", icon: "⚙", sector: "infraestrutura" },
];

const ADMIN_NAV: NavItem[] = [
  { to: "/lgpd", label: "LGPD & Privacidade", icon: "⚖" },
  { to: "/usuarios", label: "Usuários", icon: "☖", minRole: "gerencia" },
];

function Section({ label, items }: { label: string; items: NavItem[] }) {
  const { hasSector, hasMinRole } = useAuth();
  const visible = items.filter(
    (i) => (!i.sector || hasSector(i.sector)) && (!i.minRole || hasMinRole(i.minRole))
  );
  if (visible.length === 0) return null;
  return (
    <>
      <div className="nav-group-label">{label}</div>
      {visible.map((i) => (
        <NavLink key={i.to} to={i.to} end={i.to === "/"} className="nav-link">
          <span className="ico">{i.icon}</span>
          {i.label}
        </NavLink>
      ))}
    </>
  );
}

const TITLES: Record<string, string> = {
  "/": "Visão Geral",
  "/cobranca": "Cobrança",
  "/control-desk": "Control Desk",
  "/planejamento": "Planejamento",
  "/mis": "MIS · Indicadores",
  "/desenvolvimento": "Desenvolvimento",
  "/infraestrutura": "Infraestrutura",
  "/lgpd": "LGPD & Privacidade",
  "/usuarios": "Gestão de Usuários",
};

export default function Layout() {
  const { user, logout } = useAuth();
  const { pathname } = useLocation();
  const initials = user?.full_name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="dot" />
          ControlDesk
        </div>
        <div className="muted" style={{ fontSize: 12, marginLeft: 40 }}>
          Cobranças SaaS
        </div>
        <nav style={{ marginTop: 10 }}>
          <Section label="Operação" items={MAIN_NAV} />
          <Section label="Setores" items={SECTOR_NAV} />
          <Section label="Governança" items={ADMIN_NAV} />
        </nav>
        <div className="spacer" />
        <button className="btn ghost" onClick={logout}>
          ⏻ Sair
        </button>
      </aside>

      <div>
        <header className="main topbar" style={{ paddingBottom: 0 }}>
          <h1>{TITLES[pathname] ?? "ControlDesk"}</h1>
          <div className="user-chip">
            <div style={{ textAlign: "right" }}>
              <div style={{ fontWeight: 600, fontSize: 14 }}>{user?.full_name}</div>
              <div className="muted" style={{ fontSize: 12 }}>
                {user?.role}
              </div>
            </div>
            <div className="avatar">{initials}</div>
          </div>
        </header>
        <main className="main" style={{ paddingTop: 18 }}>
          <Outlet />
        </main>
      </div>
    </div>
  );
}
