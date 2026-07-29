import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import {
  api,
  setToken,
  getToken,
  setRefreshToken,
  getRefreshToken,
} from "../api/client";
import { canAccessSector, hasMinRole as hasMinRoleFn, Role } from "../lib/roles";

export interface CurrentUser {
  id: number;
  email: string;
  full_name: string;
  role: "diretoria" | "gerencia" | "administracao";
  sectors: string[];
}

interface AuthState {
  user: CurrentUser | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  hasSector: (sector: string) => boolean;
  hasMinRole: (role: "diretoria" | "gerencia" | "administracao") => boolean;
}

const AuthContext = createContext<AuthState>({} as AuthState);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      if (getToken()) {
        try {
          setUser(await api.get<CurrentUser>("/auth/me"));
        } catch {
          setToken(null);
        }
      }
      setLoading(false);
    })();
  }, []);

  async function login(email: string, password: string) {
    const res = await api.post<{ access_token: string; refresh_token?: string }>(
      "/auth/login",
      { email, password },
      false
    );
    setToken(res.access_token);
    if (res.refresh_token) setRefreshToken(res.refresh_token);
    setUser(await api.get<CurrentUser>("/auth/me"));
  }

  async function logout() {
    const refresh = getRefreshToken();
    if (refresh) {
      // Revoga a sessão no servidor (best-effort).
      try {
        await api.post("/auth/logout", { refresh_token: refresh }, false);
      } catch {
        /* ignora falhas de rede no logout */
      }
    }
    setToken(null);
    setRefreshToken(null);
    setUser(null);
  }

  const hasSector = (sector: string) =>
    canAccessSector(user?.role, user?.sectors ?? [], sector);

  const hasMinRole = (role: Role) => hasMinRoleFn(user?.role, role);

  return (
    <AuthContext.Provider
      value={{ user, loading, login, logout, hasSector, hasMinRole }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
