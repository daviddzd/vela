// Common frame for logged-in screens: logo, user, menu with the screens of the role, logout.
import type { ReactNode } from "react";
import { NavLink, useNavigate } from "react-router";
import { useAuth } from "../auth/AuthContext";
import { es } from "../i18n/es";

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  if (!user) return null;

  const onLogout = async () => {
    await logout();
    navigate("/", { replace: true });
  };

  return (
    <div className="min-h-screen">
      <header className="bg-white border-b border-teal/20">
        <div className="mx-auto max-w-6xl flex flex-wrap items-center gap-4 px-4 py-3">
          <img src="/logo.svg" alt={`${es.app.name} · ${es.app.tagline}`} className="h-12" />
          <div className="ml-auto text-right">
            <p className="font-bold">{user.display_name}</p>
            <p className="text-muted">
              {es.roles[user.role]}
              {user.institution_id ? ` · ${user.institution_id}` : ""}
            </p>
          </div>
          <button
            type="button"
            onClick={onLogout}
            className="min-h-12 rounded-card border-2 border-teal px-4 font-bold text-teal hover:bg-teal hover:text-white"
          >
            <span aria-hidden="true">⎋ </span>
            {es.shell.logout}
          </button>
        </div>
        <nav aria-label={es.shell.menu} className="mx-auto max-w-6xl px-4 pb-2">
          <ul className="flex flex-wrap gap-2">
            {user.screens.map((path) => (
              <li key={path}>
                <NavLink
                  to={path}
                  className={({ isActive }) =>
                    `inline-flex min-h-12 items-center rounded-card px-3 font-bold ${
                      isActive ? "bg-teal text-white" : "text-teal hover:bg-teal/10"
                    }`
                  }
                >
                  {es.screens[path]}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-8">{children}</main>
      <footer className="mx-auto max-w-6xl px-4 pb-6 text-muted">{es.app.syntheticData}</footer>
    </div>
  );
}
