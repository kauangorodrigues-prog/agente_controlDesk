// Cliente HTTP central. Injeta o token JWT e trata erros de forma uniforme.

const TOKEN_KEY = "controldesk_token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(
  method: string,
  path: string,
  body?: unknown,
  auth = true
): Promise<T> {
  const headers: Record<string, string> = { "Content-Type": "application/json" };
  const token = getToken();
  if (auth && token) headers["Authorization"] = `Bearer ${token}`;

  const resp = await fetch(`/api${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });

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
