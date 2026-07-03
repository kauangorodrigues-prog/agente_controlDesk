// ══════════════════════════════════════════════════════════════════
// Configuração global do frontend
// ══════════════════════════════════════════════════════════════════

// Base da API. Vazio ("") = mesma origem que serve o frontend (FastAPI
// montando os estáticos). Pode ser sobrescrito via localStorage:
//   localStorage.setItem('cd_api_base', 'http://localhost:8000')
export const API_BASE = localStorage.getItem("cd_api_base") ?? "";

export const CONFIG = {
  appName: "ATLAS",
  appFull: "Control Desk IA",
  version: "2.0.0",
  company: "Roveri · Cobrança",
  // Intervalo PADRÃO do auto-refresh (ms). 0 = desligado.
  // Confortável para operar/demonstrar sem interromper a interação.
  refreshMs: 60_000,
  // Chaves de armazenamento
  tokenKey: "cd_token",
  userKey: "cd_user",
  demoKey: "cd_demo",
  refreshKey: "cd_refresh_ms",
};

// Opções de intervalo oferecidas na barra superior
export const REFRESH_OPTIONS = [
  { ms: 0,        label: "Desligado" },
  { ms: 30_000,   label: "30 s" },
  { ms: 60_000,   label: "1 min" },
  { ms: 120_000,  label: "2 min" },
  { ms: 300_000,  label: "5 min" },
];

// Lê/persiste a preferência de intervalo do usuário
export function getRefreshMs() {
  const raw = localStorage.getItem(CONFIG.refreshKey);
  if (raw === null) return CONFIG.refreshMs;
  const v = parseInt(raw, 10);
  return Number.isFinite(v) && v >= 0 ? v : CONFIG.refreshMs;
}
export function setRefreshMs(ms) {
  localStorage.setItem(CONFIG.refreshKey, String(ms));
}

// Modo demo: usa dados simulados quando o backend não está acessível.
// Ativado automaticamente em caso de falha de rede, ou manualmente.
export const Demo = {
  get forced() {
    return localStorage.getItem(CONFIG.demoKey) === "1";
  },
  set forced(v) {
    if (v) localStorage.setItem(CONFIG.demoKey, "1");
    else localStorage.removeItem(CONFIG.demoKey);
  },
  // Flag em runtime: vira true quando um request real falha e caímos no mock
  active: false,
};

export const NIVEL_META = {
  CRITICO: { label: "Crítico", badge: "red", icon: "alert-octagon" },
  ATENCAO: { label: "Atenção", badge: "yellow", icon: "alert-triangle" },
  INFO:    { label: "Info", badge: "blue", icon: "info" },
};
