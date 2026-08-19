// Cliente HTTP central. Injeta o token JWT e trata erros de forma uniforme.

const TOKEN_KEY = "controldesk_token";
const REFRESH_KEY = "controldesk_refresh";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function setRefreshToken(token: string | null) {
  if (token) localStorage.setItem(REFRESH_KEY, token);
  else localStorage.removeItem(REFRESH_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

// Base da API. Em dev fica vazio (proxy do Vite trata /api). Em produção,
// defina VITE_API_URL com a origem do backend (ex.: https://api.exemplo.com).
const API_BASE = (import.meta.env.VITE_API_URL ?? "").replace(/\/$/, "");

function apiUrl(path: string): string {
  return `${API_BASE}/api${path}`;
}

async function rawFetch(
  method: string,
  path: string,
  body: unknown,
  auth: boolean
): Promise<Response> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (auth && token) headers["Authorization"] = `Bearer ${token}`;
  return fetch(apiUrl(path), {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

// Tenta renovar o access token usando o refresh token. Retorna true se OK.
let refreshing: Promise<boolean> | null = null;
async function tryRefresh(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  if (!refreshing) {
    refreshing = (async () => {
      try {
        const resp = await fetch(apiUrl("/auth/refresh"), {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refresh }),
        });
        if (!resp.ok) return false;
        const data = await resp.json();
        setToken(data.access_token);
        if (data.refresh_token) setRefreshToken(data.refresh_token);
        return true;
      } catch {
        return false;
      } finally {
        refreshing = null;
      }
    })();
  }
  return refreshing;
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  auth = true
): Promise<T> {
  let resp = await rawFetch(method, path, body, auth);

  // Access token expirado: tenta renovar uma vez de forma transparente.
  if (resp.status === 401 && auth && !path.startsWith("/auth/")) {
    if (await tryRefresh()) {
      resp = await rawFetch(method, path, body, auth);
    }
  }

  if (resp.status === 204) return undefined as T;

  const data = await resp.json().catch(() => ({}));
  if (!resp.ok) {
    const detail =
      (data && (data.detail || data.message)) || `Erro ${resp.status}`;
    const message = Array.isArray(detail)
      ? detail.map((d: any) => d.msg).join("; ")
      : String(detail);
    throw new ApiError(resp.status, message);
  }
  return data as T;
}

export const api = {
  get: <T>(path: string, auth = true) => request<T>("GET", path, undefined, auth),
  post: <T>(path: string, body?: unknown, auth = true) =>
    request<T>("POST", path, body, auth),
  patch: <T>(path: string, body?: unknown) => request<T>("PATCH", path, body),
  del: <T>(path: string) => request<T>("DELETE", path),
};
