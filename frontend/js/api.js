// ══════════════════════════════════════════════════════════════════
// Cliente HTTP da API — autenticação JWT + fallback para modo DEMO
// ══════════════════════════════════════════════════════════════════
import { API_BASE, CONFIG, Demo } from "./config.js";
import { mockResponse, DEMO_CREDS } from "./mock.js";

export function getToken() {
  return localStorage.getItem(CONFIG.tokenKey);
}
export function getUser() {
  try { return JSON.parse(localStorage.getItem(CONFIG.userKey) || "null"); }
  catch { return null; }
}
export function setSession(token, user) {
  localStorage.setItem(CONFIG.tokenKey, token);
  localStorage.setItem(CONFIG.userKey, JSON.stringify(user));
}
export function clearSession() {
  localStorage.removeItem(CONFIG.tokenKey);
  localStorage.removeItem(CONFIG.userKey);
}

// Pequena espera para simular latência do backend em modo demo
const delay = (ms) => new Promise((res) => setTimeout(res, ms));

// ---------- Requisição base ----------
async function request(method, path, { body, form, auth = true } = {}) {
  // Modo demo forçado → não toca a rede
  if (Demo.forced) {
    await delay(180 + Math.random() * 220);
    Demo.active = true;
    return mockResponse(method, path);
  }

  const headers = {};
  if (auth) {
    const t = getToken();
    if (t) headers["Authorization"] = `Bearer ${t}`;
  }

  let payload;
  if (form) {
    headers["Content-Type"] = "application/x-www-form-urlencoded";
    payload = new URLSearchParams(form).toString();
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    payload = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: payload,
      // aborta requests longos
      signal: AbortSignal.timeout ? AbortSignal.timeout(12000) : undefined,
    });
  } catch (err) {
    // Falha de rede / backend offline → cai no modo demo automaticamente
    Demo.active = true;
    await delay(120);
    return mockResponse(method, path);
  }

  if (res.status === 401) {
    clearSession();
    throw new ApiError("Sessão expirada. Faça login novamente.", 401);
  }

  // Rota inexistente / método não implementado (backend ausente ou servidor
  // estático) → modo demo. 501 = servidor não implementa o método (ex.: POST).
  if (res.status === 404 || res.status === 405 || res.status === 501) {
    Demo.active = true;
    await delay(80);
    return mockResponse(method, path);
  }

  const ct = res.headers.get("content-type") || "";
  const data = ct.includes("application/json") ? await res.json().catch(() => null) : await res.text();

  if (!res.ok) {
    const detail = (data && data.detail) || (typeof data === "string" ? data : "Erro na requisição");
    throw new ApiError(detail, res.status);
  }
  Demo.active = false;
  return data;
}

export class ApiError extends Error {
  constructor(message, status) { super(message); this.status = status; this.name = "ApiError"; }
}

// ---------- Autenticação ----------
export async function login(username, password) {
  // Demo forçado: valida contra credenciais locais
  if (Demo.forced) {
    await delay(300);
    return _demoLogin(username, password);
  }
  try {
    const data = await request("POST", "/auth/token", {
      form: { username, password, grant_type: "password" },
      auth: false,
    });
    // Se a rota /auth/token não existir (404/405) ou rede caiu → modo demo
    if (Demo.active) return _demoLogin(username, password, true);
    if (!data || !data.access_token) throw new ApiError("Resposta inválida do servidor", 500);
    // decodifica payload do JWT p/ extrair role/sub (sem verificar assinatura)
    const claims = decodeJwt(data.access_token);
    setSession(data.access_token, { username: claims.sub || username, role: claims.role || "user" });
    Demo.active = false;
    return getUser();
  } catch (err) {
    // Backend inacessível ou com falha → permite login demo com admin/admin
    if (username === DEMO_CREDS.username && password === DEMO_CREDS.password) {
      return _demoLogin(username, password, true);
    }
    if (err instanceof ApiError) throw err;
    return _demoLogin(username, password, true);
  }
}

function _demoLogin(username, password, autoDemo = false) {
  if (username === DEMO_CREDS.username && password === DEMO_CREDS.password) {
    Demo.forced = true;
    Demo.active = true;
    setSession("demo-token", { username: DEMO_CREDS.username, role: DEMO_CREDS.role, demo: true });
    return getUser();
  }
  throw new ApiError(
    autoDemo
      ? "Backend indisponível. Use admin / admin para o modo demonstração."
      : "Usuário ou senha incorretos.",
    401
  );
}

function decodeJwt(token) {
  try {
    const b = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    return JSON.parse(decodeURIComponent(escape(atob(b))));
  } catch { return {}; }
}

// ---------- Endpoints tipados ----------
export const Api = {
  health:            () => request("GET", "/", { auth: false }),

  ocupacao:          () => request("GET", "/ocupacao"),
  ocupacaoCampanhas: () => request("GET", "/ocupacao/campanhas"),

  pacingHistorico:   (horas = 24, campanhaId) =>
    request("GET", `/pacing/historico?horas=${horas}${campanhaId ? `&campanha_id=${campanhaId}` : ""}`),
  pacingAjustar:     () => request("POST", "/pacing/ajustar"),

  mailingTop:        (n = 100, campanhaId) =>
    request("GET", `/mailing/top?n=${n}${campanhaId ? `&campanha_id=${campanhaId}` : ""}`),
  mailingProcessar:  () => request("POST", "/mailing/processar"),

  forecast:          () => request("GET", "/forecast"),
  forecastGerar:     (periodos = 24, tma = 5.0) =>
    request("POST", `/forecast/gerar?periodos=${periodos}&tma_min=${tma}`),

  feriados:          (ano) => request("GET", `/feriados${ano ? `?ano=${ano}` : ""}`),
  feriadosProximos:  (dias = 30) => request("GET", `/feriados/proximos?dias=${dias}`),
  feriadoAdd:        (body) => request("POST", "/feriados", { body }),
  feriadoDel:        (id) => request("DELETE", `/feriados/${id}`),
  feriadosSync:      (ano) => request("POST", `/feriados/sincronizar${ano ? `?ano=${ano}` : ""}`),

  auditoria:         () => request("POST", "/auditoria/executar"),
  alertas:           (limite = 50, nivel) =>
    request("GET", `/alertas?limite=${limite}${nivel ? `&nivel=${nivel}` : ""}`),

  campanhasConfig:   () => request("GET", "/campanhas/config"),
  etlRun:            () => request("POST", "/etl/run"),

  // Endpoints "extra" atendidos pelo mock (o backend real usa /ocupacao/campanhas
  // e campaign_snapshot). Tenta o real e cai no mock se indisponível.
  campanhasDesempenho: () => request("GET", "/campanhas/desempenho"),
  agentesImprodutivos: () => request("GET", "/auditoria/improdutivos"),
};
