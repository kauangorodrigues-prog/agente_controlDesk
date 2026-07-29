import {
  createContext,
  useContext,
  useEffect,
  useState,
  ReactNode,
} from "react";
import { api, setToken, getToken } from "../api/client";

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

const ROLE_LEVEL: Record<string, number> = {
  administracao: 1,
  gerencia: 2,
  diretoria: 3,
};

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
    const res = await api.post<{ access_token: string }>(
      "/auth/login",
      { email, password },
      false
    );
    setToken(res.access_token);
    setUser(await api.get<CurrentUser>("/auth/me"));
  }

  function logout() {
    setToken(null);
    setUser(null);
  }

  const hasSector = (sector: string) =>
    !!user && (user.role === "diretoria" || user.sectors.includes(sector));

  const hasMinRole = (role: "diretoria" | "gerencia" | "administracao") =>
    !!user && ROLE_LEVEL[user.role] >= ROLE_LEVEL[role];

  return (
    <AuthContext.Provider
      value={{ user, loading, login, logout, hasSector, hasMinRole }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
