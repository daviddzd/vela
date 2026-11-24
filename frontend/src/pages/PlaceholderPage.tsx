// Empty screen used until each module is built (steps 3–9 of the work order).
import { AppShell } from "../components/AppShell";
import { es } from "../i18n/es";

export function PlaceholderPage({ path }: { path: string }) {
  return (
    <AppShell>
      <h1>{es.screens[path]}</h1>
      <section className="mt-6 rounded-card border border-navy/10 bg-white shadow-[var(--shadow-card)] p-6">
        <h2>{es.shell.comingSoon}</h2>
        <p className="mt-2 text-muted">{es.shell.comingSoonBody}</p>
      </section>
    </AppShell>
  );
}
