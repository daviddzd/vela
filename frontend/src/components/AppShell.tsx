// Common frame for logged-in screens.
// Projector / desktop (>= 1280 px): logo, every screen of the role and the user, all in ONE line.
// Phone / tablet: logo, a "Menú" button (icon + word) that opens the list, and the user.
import { LogOut, Menu, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { NavLink, useLocation, useNavigate } from "react-router";
import { useAuth } from "../auth/AuthContext";
import { es } from "../i18n/es";
import { EscalatedAlerts } from "./EscalatedAlerts";
import { Icon } from "./icons";

// `bare`: presentation mode, only the page content (no navigation, no footer).
export function AppShell({ children, bare = false }: { children: ReactNode; bare?: boolean }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [location.pathname]);       // close the menu after choosing a screen
  if (!user) return null;
  if (bare) return <main className="mx-auto max-w-[1880px] px-6 py-6">{children}</main>;

  // "Médico · INS-A"; coordination shows only the institution (its accounts carry the role in their name)
  const roleLine = [es.roleInHeader[user.role] ?? es.roles[user.role], user.institution_id].filter(Boolean).join(" · ");

  const onLogout = async () => {
    await logout();
    navigate("/entrar", { replace: true });
  };
  const link = ({ isActive }: { isActive: boolean }) =>
    `inline-flex min-h-12 items-center whitespace-nowrap rounded-full px-2 font-bold 2xl:px-3 ${
      isActive ? "bg-navy text-white" : "text-navy hover:bg-sky"}`;

  return (
    <div className="min-h-screen">
      <header className="border-b border-navy/10 bg-white shadow-[0_2px_12px_rgba(27,51,73,0.06)]">
        <div className="mx-auto flex max-w-[1880px] items-center gap-3 px-4 py-2">
          <img src="/logo.svg" alt={`${es.app.name} · ${es.app.tagline}`} className="h-10 shrink-0 xl:h-9 2xl:h-10" />

          <nav aria-label={es.shell.menu} className="hidden shrink-0 xl:block">
            <ul className="flex items-center gap-0.5">
              {user.screens.map((path) => (
                <li key={path}><NavLink to={path} className={link}>{es.nav.short[path] ?? es.screens[path]}</NavLink></li>
              ))}
            </ul>
          </nav>

          <button type="button" onClick={() => setOpen((o) => !o)} aria-expanded={open} aria-controls="main-menu"
            className="ml-auto inline-flex min-h-12 items-center gap-2 rounded-full border-2 border-navy px-4 font-bold text-navy xl:hidden">
            <Icon as={open ? X : Menu} />{open ? es.nav.closeShort : es.nav.menu}
          </button>

          {/* Desktop / projector: logout always visible; the user's name only when there is room (>= 1536 px) */}
          <div className="hidden min-w-0 items-center gap-3 xl:ml-auto xl:flex">   {/* the name shrinks (ellipsis), never the menu */}
            {/* the name stays on ONE line inside a maximum width: a longer one ends in "…" and shows whole on hover
                (title), so the header never overflows and "Cerrar sesión" is never cut */}
            <p className="hidden min-w-0 max-w-64 pl-4 text-right leading-tight 2xl:block" title={user.display_name}>
              <span className="block truncate font-bold">{user.display_name}</span>
              <span className="block truncate text-sm text-muted">{roleLine}</span>
            </p>
            <LogoutButton onLogout={onLogout} />
          </div>
        </div>

        {open && (
          <nav id="main-menu" aria-label={es.shell.menu} className="border-t border-navy/15 px-4 pb-3 xl:hidden">
            <p className="py-2" title={user.display_name}><span className="block truncate font-bold">{user.display_name}</span>
              <span className="block truncate text-muted">{roleLine}</span></p>
            <ul className="grid gap-1 sm:grid-cols-2">
              {user.screens.map((path) => (
                <li key={path}><NavLink to={path} className={({ isActive }) => `${link({ isActive })} w-full`}>
                  {es.screens[path]}</NavLink></li>
              ))}
            </ul>
            <div className="mt-2 border-t border-navy/15 pt-3"><LogoutButton onLogout={onLogout} /></div>
          </nav>
        )}
      </header>
      <main className="mx-auto max-w-[1880px] px-4 py-6">{user.role === "owner" && <EscalatedAlerts />}{children}</main>
      <footer className="mx-auto max-w-[1880px] px-4 pb-6 text-muted">{es.app.syntheticData}</footer>
    </div>
  );
}

function LogoutButton({ onLogout }: { onLogout: () => void }) {
  return (
    <button type="button" onClick={onLogout}
      className="inline-flex min-h-12 items-center gap-2 whitespace-nowrap rounded-full border-2 border-navy px-4 font-bold text-navy hover:bg-navy hover:text-white">
      <Icon as={LogOut} />{es.shell.logout}
    </button>
  );
}
