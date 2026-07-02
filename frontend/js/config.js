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
  // Intervalo padrão do auto-refresh (ms)
  refreshMs: 30_000,
  // Chaves de armazenamento
  tokenKey: "cd_token",
  userKey: "cd_user",
  demoKey: "cd_demo",
};

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
