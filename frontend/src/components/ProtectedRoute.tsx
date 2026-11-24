// Lets a page render only if the user is logged in AND their role may open that screen.
// The list of allowed screens comes from the API (/api/auth/me → screens). The API checks roles
// again on every request; this only avoids showing pages that would fail anyway.
import type { ReactNode } from "react";
import { Navigate } from "react-router";
import { useAuth } from "../auth/AuthContext";
import { es } from "../i18n/es";

export function ProtectedRoute({ path, children }: { path: string; children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return <p className="p-8">{es.shell.loading}</p>;
  if (!user) return <Navigate to="/entrar" replace />;
  if (!user.screens.includes(path)) return <Navigate to={user.home} replace />;
  return <>{children}</>;
}
