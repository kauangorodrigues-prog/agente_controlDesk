// ══════════════════════════════════════════════════════════════════
// ATLAS · Control Desk IA — bootstrap do SPA
// ══════════════════════════════════════════════════════════════════
import { CONFIG, Demo, REFRESH_OPTIONS, getRefreshMs, setRefreshMs } from "./config.js";
import { Api, login, getToken, getUser, clearSession } from "./api.js";
import { $, el, toast } from "./ui.js";
import { icon, logoMark } from "./icons.js";

import * as dashboard from "./pages/dashboard.js";
import * as campanhas from "./pages/campanhas.js";
import * as pacing from "./pages/pacing.js";
import * as mailing from "./pages/mailing.js";
import * as forecast from "./pages/forecast.js";
import * as feriados from "./pages/feriados.js";
import * as auditoria from "./pages/auditoria.js";
import * as alertas from "./pages/alertas.js";
import * as configuracoes from "./pages/configuracoes.js";

const PAGES = {
  dashboard, campanhas, pacing, mailing, forecast, feriados, auditoria, alertas, configuracoes,
};

const NAV = [
  { section: "Operação" },
  { id: "dashboard", ...dashboard.meta },
  { id: "campanhas", ...campanhas.meta },
  { id: "pacing", ...pacing.meta },
  { section: "Inteligência" },
  { id: "mailing", ...mailing.meta },
  { id: "forecast", ...forecast.meta },
  { section: "Governança" },
  { id: "feriados", ...feriados.meta },
  { id: "auditoria", ...auditoria.meta },
  { id: "alertas", ...alertas.meta },
  { section: "Sistema" },
  { id: "configuracoes", ...configuracoes.meta },
];

const app = document.getElementById("app");
let current = { onRefresh: null };
let refreshTimer = null;
let clockTimer = null;
let refreshMs = getRefreshMs();   // intervalo escolhido (0 = desligado)

// ══════════════════════════════════════════════════════════════════
// Login
// ══════════════════════════════════════════════════════════════════
function renderLogin(errMsg = "") {
  stopTimers();
  app.innerHTML = `
    <div class="login-screen">
      <form class="login-card" id="login-form">
        <div class="login-brand">
          ${logoMark(60)}
          <h1>ATLAS</h1>
          <div class="sub">Control Desk IA · Roveri Cobrança</div>
        </div>
        ${errMsg ? `<div class="login-error">${errMsg}</div>` : ""}
        <div class="field">
          <label>Usuário</label>
          <input class="input" id="lg-user" placeholder="seu.usuario" autocomplete="username" autofocus>
        </div>
        <div class="field">
          <label>Senha</label>
          <input class="input" id="lg-pass" type="password" placeholder="••••••••" autocomplete="current-password">
        </div>
        <button class="btn btn-primary btn-block" type="submit" id="lg-btn" style="margin-top:8px">Entrar</button>
        <div class="login-hint">
          Ambiente de demonstração disponível com<br>
          <code>admin</code> / <code>admin</code>
        </div>
      </form>
    </div>`;

  const form = $("#login-form");
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const btn = $("#lg-btn");
    const u = $("#lg-user").value.trim();
    const p = $("#lg-pass").value;
    if (!u || !p) { renderLogin("Preencha usuário e senha."); return; }
    btn.disabled = true; btn.innerHTML = `<span class="spinner dark"></span> Entrando…`;
    try {
      await login(u, p);
      renderApp();
      navigate("dashboard");
    } catch (err) {
      renderLogin(err.message || "Falha na autenticação.");
    }
  });
}

// ══════════════════════════════════════════════════════════════════
// Shell da aplicação
// ══════════════════════════════════════════════════════════════════
function renderApp() {
  const user = getUser();
  const initials = (user?.username || "US").slice(0, 2).toUpperCase();

  app.innerHTML = `
    <div class="app">
      <aside class="sidebar" id="sidebar">
        <div class="sidebar-brand">
          ${logoMark(34)}
          <div class="titles"><b>ATLAS</b><span>Control Desk IA</span></div>
        </div>
        <nav class="nav" id="nav">${renderNav()}</nav>
        <div class="sidebar-footer">
          <div class="db-status" id="db-status"><span class="dot off"></span> Verificando…</div>
        </div>
      </aside>
      <div class="main">
        <header class="topbar">
          <button class="btn btn-ghost btn-icon menu-toggle" id="menu-toggle">${icon("menu")}</button>
          <div>
            <h2 id="page-title">Tempo Real</h2>
            <div class="page-sub" id="page-sub"></div>
          </div>
          <span class="spacer"></span>
          <span class="clock hide-sm" id="clock"></span>
          <label class="refresh-select hide-sm" title="Intervalo de atualização automática">
            ${icon("clock")}
            <select id="refresh-interval">
              ${REFRESH_OPTIONS.map((o) => `<option value="${o.ms}" ${o.ms === refreshMs ? "selected" : ""}>${o.label}</option>`).join("")}
            </select>
          </label>
          <button class="btn btn-ghost btn-icon" id="refresh-btn" title="Atualizar agora">${icon("refresh")}</button>
          <div class="avatar" id="avatar" title="${user?.username || ""} (${user?.role || ""})">${initials}</div>
          <button class="btn btn-ghost btn-icon" id="logout-btn" title="Sair">${icon("logout")}</button>
        </header>
        <main class="content wide" id="content"></main>
      </div>
    </div>`;

  // eventos
  $("#nav").addEventListener("click", (e) => {
    const item = e.target.closest("[data-page]");
    if (item) { navigate(item.dataset.page); closeSidebar(); }
  });
  $("#logout-btn").addEventListener("click", doLogout);
  $("#refresh-btn").addEventListener("click", () => { doRefresh(true); });
  $("#menu-toggle").addEventListener("click", toggleSidebar);
  $("#refresh-interval").addEventListener("change", (e) => {
    refreshMs = parseInt(e.target.value, 10) || 0;
    setRefreshMs(refreshMs);
    setupRefreshTimer();
    const opt = REFRESH_OPTIONS.find((o) => o.ms === refreshMs);
    toast(refreshMs === 0 ? "Atualização automática desligada" : `Atualização automática: ${opt ? opt.label : refreshMs / 1000 + "s"}`, "info", 2000);
  });

  // Pausa/retoma o timer quando a aba perde/ganha foco
  document.addEventListener("visibilitychange", () => {
    if (document.hidden) { if (refreshTimer) clearInterval(refreshTimer); refreshTimer = null; }
    else setupRefreshTimer();
  });

  startClock();
  refreshDbStatus();
}

function renderNav(activeId = "dashboard") {
  return NAV.map((n) => {
    if (n.section) return `<div class="nav-section">${n.section}</div>`;
    return `<a class="nav-item ${n.id === activeId ? "active" : ""}" data-page="${n.id}">
      ${icon(n.icon)} <span>${n.title}</span>
      ${n.id === "alertas" ? `<span class="badge-count hidden" id="nav-alert-count">0</span>` : ""}
    </a>`;
  }).join("");
}

// ══════════════════════════════════════════════════════════════════
// Navegação entre páginas
// ══════════════════════════════════════════════════════════════════
async function navigate(pageId) {
  const page = PAGES[pageId];
  if (!page) return;
  current = { onRefresh: null };

  // marca ativo
  document.querySelectorAll(".nav-item").forEach((a) => a.classList.toggle("active", a.dataset.page === pageId));
  $("#page-title").textContent = page.meta.title;
  $("#page-sub").textContent = page.meta.subtitle || "";

  const content = $("#content");
  content.className = "content wide page-enter";
  content.innerHTML = "";
  // força reflow p/ reanimar
  void content.offsetWidth;
  content.classList.add("page-enter");

  try {
    const res = await page.mount(content);
    current = res || {};
  } catch (err) {
    if (err && err.status === 401) { doLogout(); return; }
    content.innerHTML = `<div class="empty">${icon("alert-triangle")}<p>Erro ao carregar a página</p><div class="hint">${err?.message || ""}</div></div>`;
  }
  setupRefreshTimer();
  refreshDbStatus();
}

// ══════════════════════════════════════════════════════════════════
// Auto-refresh / relógio / status
// ══════════════════════════════════════════════════════════════════
function setupRefreshTimer() {
  if (refreshTimer) { clearInterval(refreshTimer); refreshTimer = null; }
  if (refreshMs > 0 && !document.hidden) {
    refreshTimer = setInterval(() => doRefresh(false), refreshMs);
  }
}

// Enquanto o usuário está interagindo, adiar o refresh automático evita
// que o conteúdo seja recriado sob os pés dele (rolagem, filtros, modais).
function usuarioInteragindo() {
  if (document.querySelector(".modal-backdrop")) return true;       // modal aberto
  const ae = document.activeElement;
  if (ae && /^(INPUT|SELECT|TEXTAREA)$/.test(ae.tagName)) return true; // digitando/escolhendo
  const tt = document.querySelector(".chart-tooltip");
  if (tt && tt.style.opacity === "1") return true;                   // tooltip de gráfico visível
  return false;
}

async function doRefresh(manual) {
  if (!manual && (document.hidden || usuarioInteragindo())) return;  // não interrompe o usuário
  if (typeof current.onRefresh === "function") {
    const btn = $("#refresh-btn");
    if (manual && btn) btn.querySelector("svg")?.style.setProperty("animation", "spin .7s linear");
    try { await current.onRefresh(); } catch (e) { if (e?.status === 401) doLogout(); }
    if (manual) { toast("Dados atualizados", "success", 1500); if (btn) btn.querySelector("svg")?.style.removeProperty("animation"); }
  }
  refreshDbStatus();
  refreshAlertCount();
}

function startClock() {
  if (clockTimer) clearInterval(clockTimer);
  // Mostra HH:MM (sem segundos) e atualiza a cada 30s — sem "piscar" a cada segundo.
  const tick = () => {
    const c = $("#clock");
    if (c) c.textContent = new Date().toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
  };
  tick(); clockTimer = setInterval(tick, 30_000);
}
function stopTimers() {
  if (refreshTimer) clearInterval(refreshTimer);
  if (clockTimer) clearInterval(clockTimer);
  refreshTimer = clockTimer = null;
}

async function refreshDbStatus() {
  const box = $("#db-status");
  if (!box) return;
  try {
    const h = await Api.health();
    if (Demo.active || Demo.forced) {
      box.innerHTML = `<span class="dot demo"></span> Modo Demonstração`;
    } else if (h && h.banco) {
      box.innerHTML = `<span class="dot on"></span> Banco conectado · v${h.versao || CONFIG.version}`;
    } else {
      box.innerHTML = `<span class="dot off"></span> Banco offline · API v${h?.versao || CONFIG.version}`;
    }
  } catch {
    box.innerHTML = `<span class="dot demo"></span> Modo Demonstração`;
  }
}

async function refreshAlertCount() {
  try {
    const rows = await Api.alertas(100, "CRITICO");
    const badge = $("#nav-alert-count");
    if (!badge) return;
    const n = Array.isArray(rows) ? rows.length : 0;
    if (n > 0) { badge.textContent = n > 99 ? "99+" : n; badge.classList.remove("hidden"); }
    else badge.classList.add("hidden");
  } catch { /* silencioso */ }
}

// ══════════════════════════════════════════════════════════════════
// Sidebar mobile
// ══════════════════════════════════════════════════════════════════
function toggleSidebar() {
  const sb = $("#sidebar");
  sb.classList.toggle("open");
  if (sb.classList.contains("open")) {
    const bd = el(`<div class="sidebar-backdrop" id="sb-backdrop"></div>`);
    bd.addEventListener("click", closeSidebar);
    document.body.appendChild(bd);
  } else closeSidebar();
}
function closeSidebar() {
  $("#sidebar")?.classList.remove("open");
  document.getElementById("sb-backdrop")?.remove();
}

// ══════════════════════════════════════════════════════════════════
// Logout
// ══════════════════════════════════════════════════════════════════
function doLogout() {
  clearSession();
  Demo.forced = false; Demo.active = false;
  stopTimers();
  renderLogin();
}

// ══════════════════════════════════════════════════════════════════
// Boot
// ══════════════════════════════════════════════════════════════════
function boot() {
  if (getToken()) {
    renderApp();
    navigate("dashboard");
    refreshAlertCount();
  } else {
    renderLogin();
  }
}
boot();
