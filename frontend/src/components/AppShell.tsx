// Common frame for logged-in screens.
// Projector / desktop (>= 1280 px): logo, every screen of the role and the user, all in ONE line.
// Phone / tablet: logo, a "Menú" button (icon + word) that opens the list, and the user.
import { LogOut, Menu, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useLocation, useNavigate } from "react-router";
import { useAuth } from "../auth/AuthContext";
import { es } from "../i18n/es";
import { Icon } from "./icons";

export function AppShell({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [location.pathname]);       // close the menu after choosing a screen
  if (!user) return null;

  const onLogout = async () => {
    await logout();
    navigate("/", { replace: true });
  };
  const link = ({ isActive }: { isActive: boolean }) =>
    `inline-flex min-h-12 items-center whitespace-nowrap rounded-card px-2 font-bold ${
      isActive ? "bg-teal text-white" : "text-teal hover:bg-teal/10"}`;

  return (
    <div className="min-h-screen">
      <header className="border-b border-teal/20 bg-white">
        <div className="mx-auto flex max-w-[1880px] items-center gap-3 px-4 py-2">
          <img src="/logo.svg" alt={`${es.app.name} · ${es.app.tagline}`} className="h-10 shrink-0" />

          <nav aria-label={es.shell.menu} className="hidden flex-1 xl:block">
            <ul className="flex items-center gap-0.5">
              {user.screens.map((path) => (
                <li key={path}><NavLink to={path} className={link}>{es.nav.short[path] ?? es.screens[path]}</NavLink></li>
              ))}
            </ul>
          </nav>

          <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-controls="main-menu"
            className="ml-auto inline-flex min-h-12 items-center gap-2 rounded-card border-2 border-teal px-3 font-bold text-teal xl:hidden">
            <Icon as={open ? X : Menu} />{open ? es.nav.closeShort : es.nav.menu}
          </button>

          {/* Desktop / projector: logout always visible; the user's name only when there is room (>= 1536 px) */}
          <div className="hidden shrink-0 items-center gap-3 xl:ml-auto xl:flex">
            <p className="hidden text-right leading-tight 2xl:block">
              <span className="block font-bold">{user.display_name}</span>
              <span className="text-sm text-muted">{es.roles[user.role]}{user.institution_id ? ` · ${user.institution_id}` : ""}</span>
            </p>
            <LogoutButton onLogout={onLogout} />
          </div>
        </div>

        {open && (
          <nav id="main-menu" aria-label={es.shell.menu} className="border-t border-teal/15 px-4 pb-3 xl:hidden">
            <p className="py-2"><span className="font-bold">{user.display_name}</span>
              <span className="text-muted"> · {es.roles[user.role]}{user.institution_id ? ` · ${user.institution_id}` : ""}</span></p>
            <ul className="grid gap-1 sm:grid-cols-2">
              {user.screens.map((path) => (
                <li key={path}><NavLink to={path} className={({ isActive }) => `${link({ isActive })} w-full`}>
                  {es.screens[path]}</NavLink></li>
              ))}
            </ul>
            <div className="mt-2 border-t border-teal/15 pt-3"><LogoutButton onLogout={onLogout} /></div>
          </nav>
        )}
      </header>
      <main className="mx-auto max-w-[1880px] px-4 py-6">{children}</main>
      <footer className="mx-auto max-w-[1880px] px-4 pb-6 text-muted">{es.app.syntheticData}</footer>
    </div>
  );
}

function LogoutButton({ onLogout }: { onLogout: () => void }) {
  return (
    <button type="button" onClick={onLogout}
      className="inline-flex min-h-12 items-center gap-2 whitespace-nowrap rounded-card border-2 border-teal px-3 font-bold text-teal hover:bg-teal hover:text-white">
      <Icon as={LogOut} />{es.shell.logout}
    </button>
  );
}
