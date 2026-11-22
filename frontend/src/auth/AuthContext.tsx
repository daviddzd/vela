// Keeps the logged-in user (from /api/auth/me) available to every page.
import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api, type Me } from "../api/client";

type AuthState = {
  user: Me | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<Me>;
  logout: () => Promise<void>;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<Me | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // On page load, ask the API whether the cookie still holds a valid session.
    api.me().then(setUser).catch(() => setUser(null)).finally(() => setLoading(false));
  }, []);

  const login = async (email: string, password: string) => {
    const me = await api.login(email, password);
    setUser(me);
    return me;
  };

  const logout = async () => {
    await api.logout().catch(() => undefined);
    setUser(null);
  };

  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used inside <AuthProvider>");
  return ctx;
}
