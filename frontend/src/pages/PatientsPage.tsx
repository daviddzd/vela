// /pacientes — coordination (whole institution) and physicians (only their patients; the API decides).
// Search + filters (borough, priority, dependency, pollution sensitivity) and a risk indicator in WORDS with an icon.
// Risk and health filters only exist for people with a valid health_data consent; otherwise "Falta consentimiento".
import { AlertTriangle, ChevronRight, Lock, Minus, ShieldCheck } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { AppShell } from "../components/AppShell";
import { Icon } from "../components/icons";
import { Button, Card, PageHeader, inputClass } from "../components/ui";
import { es } from "../i18n/es";

const t = es.patients;
const fill = (s: string, v: Record<string, string | number>) => s.replace(/\{(\w+)\}/g, (_, k) => String(v[k] ?? ""));
export const RISK_LOOK = { low: [ShieldCheck, "text-ok"], medium: [Minus, "text-warn"], high: [AlertTriangle, "text-danger"] } as const;

export function RiskBadge({ level }: { level: string | null }) {
  if (!level) return <span className="text-muted"><Icon as={Lock} /> {t.noConsent}</span>;
  const [icon, cls] = RISK_LOOK[level as keyof typeof RISK_LOOK];
  return <span className={`font-bold ${cls}`}><Icon as={icon} /> {t.risk} {t.riskLevels[level].toLowerCase()}</span>;
}

type Row = { patient_id: string; full_name: string; base_priority: string; district_id: string; district_name: string;
  age: number; health_consent: boolean; dependency_level: string | null; pollution_sensitive: boolean | null;
  risk: number | null; risk_level: string | null };

export function PatientsPage() {
  const { user } = useAuth();
  const [all, setAll] = useState<Row[] | null>(null);
  const [f, setF] = useState({ q: "", district: "", priority: "", dependency: "", sensitive: "" });
  const [limit, setLimit] = useState(30);
  useEffect(() => { api.patients().then(setAll); }, []);

  // Filtering happens here (the list is one institution); the API applies the same rules for direct calls.
  const rows = useMemo(() => (all ?? []).filter((p) =>
    (!f.q || `${p.full_name} ${p.patient_id}`.toLowerCase().includes(f.q.toLowerCase()))
    && (!f.district || p.district_id === f.district) && (!f.priority || p.base_priority === f.priority)
    && (!f.dependency || p.dependency_level === f.dependency)
    && (!f.sensitive || String(p.pollution_sensitive) === f.sensitive)), [all, f]);
  const districts = useMemo(() => [...new Map((all ?? []).map((p) => [p.district_id, p.district_name])).entries()]
    .sort((a, b) => a[1].localeCompare(b[1])), [all]);
  const set = (k: string, v: string) => { setF({ ...f, [k]: v }); setLimit(30); };
  const select = (label: string, k: string, options: [string, string][]) => (
    <label className="block"><span className="font-bold">{label}</span>
      <select className={inputClass} value={(f as any)[k]} onChange={(e) => set(k, e.target.value)}>
        <option value="">{t.all}</option>{options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>);

  return (
    <AppShell>
      <PageHeader title={es.pageTitles["/pacientes"]}>
        <p className="max-w-4xl">{t.intro} {user?.role === "physician" && t.introPhysician}</p>
      </PageHeader>
      <Card className="mt-4">
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
          <label className="block"><span className="font-bold">{t.search}</span>
            <input className={inputClass} value={f.q} onChange={(e) => set("q", e.target.value)} /></label>
          {select(t.district, "district", districts)}
          {select(t.priority, "priority", ["high", "medium", "low"].map((p) => [p, es.priority[p]]))}
          {select(t.dependency, "dependency", Object.entries(t.dependencyLevels))}
          {select(t.sensitive, "sensitive", [["true", t.yes], ["false", t.no]])}
        </div>
        <p className="mt-2 text-sm text-muted">{t.riskNote}</p>
      </Card>
      {!all ? <p className="mt-4">{es.common.loading}</p> : (<>
        <p className="mt-4 font-bold" aria-live="polite">{fill(t.count, { n: rows.length })}</p>
        {rows.length === 0 && <p className="mt-2">{t.empty}</p>}
        <ul className="mt-2 grid gap-2 lg:grid-cols-2">
          {rows.slice(0, limit).map((p) => (
            <li key={p.patient_id}>
              <Link to={`/pacientes/${p.patient_id}`} className="flex min-h-12 items-center justify-between gap-3 rounded-card border border-navy/10 bg-white shadow-[var(--shadow-card)] p-3 hover:border-navy">
                <span>
                  <span className="block font-bold text-navy">{p.full_name} <span className="font-normal text-muted">· {p.patient_id}</span></span>
                  <span className="block text-sm">{fill(t.age, { n: p.age })} · {p.district_name} · {t.priority} {es.priority[p.base_priority].toLowerCase()}
                    {p.dependency_level && ` · ${t.dependency} ${t.dependencyLevels[p.dependency_level].toLowerCase()}`}
                    {p.pollution_sensitive && ` · ${t.sensitive.toLowerCase()}`}</span>
                  <span className="block text-sm"><RiskBadge level={p.risk_level} /></span>
                </span>
                <span className="text-navy"><Icon as={ChevronRight} /><span className="sr-only">{t.open}</span></span>
              </Link>
            </li>))}
        </ul>
        {rows.length > limit && <Button className="mt-3" variant="secondary" onClick={() => setLimit(limit + 30)}>{t.showMore}</Button>}
      </>)}
    </AppShell>
  );
}
