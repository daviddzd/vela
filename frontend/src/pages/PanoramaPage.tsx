// /panorama — Panorama-AM (docs/spec/07): two views and one row of filters above them.
// Filters: alcaldía and dates for everyone; institution only for the owner (Dirección Vela).
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { AppShell } from "../components/AppShell";
import { inputClass, Notice } from "../components/ui";
import { DateField } from "../components/DateField";
import { es } from "../i18n/es";
import { OperationView } from "./panorama/OperationView";
import { PanoramaView } from "./panorama/PanoramaView";
import type { Filters } from "./panorama/types";

const t = es.panorama;

export function PanoramaPage() {
  const { user } = useAuth();
  const isOwner = user?.role === "owner";
  const [tab, setTab] = useState<"operation" | "panorama">(new URLSearchParams(location.search).get("vista") === "panorama" ? "panorama" : "operation");
  const [filters, setFilters] = useState<Filters>({});
  const [districts, setDistricts] = useState<{ district_id: string; district_name: string }[]>([]);
  const [institutions, setInstitutions] = useState<{ institution_id: string; name: string }[]>([]);

  useEffect(() => {
    api.panorama<{ districts: { district_id: string; district_name: string }[] }>("population").then((p) => setDistricts(p.districts));
    if (isOwner) api.panorama<{ institution_id: string; name: string }[]>("institutions").then(setInstitutions);
  }, [isOwner]);
  const set = (k: keyof Filters, v: string) => setFilters((f) => ({ ...f, [k]: v || undefined }));
  // Dates are applied only when both are valid and "Desde" is not after "Hasta"; until then the charts keep the
  // previous range and a notice says why.
  const [dates, setDates] = useState({ from: "", to: "", fromOk: true, toOk: true });
  const reversed = !!dates.from && !!dates.to && dates.from > dates.to;
  useEffect(() => {
    if (!dates.fromOk || !dates.toOk || reversed) return;
    setFilters((f) => ({ ...f, from: dates.from || undefined, to: dates.to || undefined }));
  }, [dates, reversed]);

  return (
    <AppShell>
      <h1 className="text-navy">{es.screens["/panorama"]}</h1>
      <p className="mt-1 max-w-4xl text-muted">{t.laborNote}</p>
      <div role="tablist" aria-label={es.screens["/panorama"]} className="mt-3 flex gap-2">
        {(["operation", "panorama"] as const).map((k) => (
          <button key={k} role="tab" aria-selected={tab === k} onClick={() => setTab(k)}
            className={`min-h-12 rounded-card px-4 font-bold ${tab === k ? "bg-navy text-white" : "border-2 border-navy bg-white text-navy"}`}>
            {t.tabs[k]}
          </button>
        ))}
      </div>

      <form className="mt-4 flex flex-wrap items-start gap-3" aria-label={t.filters} onSubmit={(e) => e.preventDefault()}>
        <label className="min-w-48 flex-1 sm:flex-none"><span className="font-bold">{t.district}</span>
          <select className={inputClass} value={filters.district ?? ""} onChange={(e) => set("district", e.target.value)}>
            <option value="">{t.allDistricts}</option>
            {districts.map((d) => <option key={d.district_id} value={d.district_id}>{d.district_name}</option>)}
          </select>
        </label>
        <DateField label={t.from} value={dates.from} onChange={(v, ok) => setDates((d) => ({ ...d, from: v, fromOk: ok }))}
          error={reversed ? t.datesReversed : undefined} />
        <DateField label={t.to} value={dates.to} onChange={(v, ok) => setDates((d) => ({ ...d, to: v, toOk: ok }))} />
        {isOwner && (
          <label className="min-w-48 flex-1 sm:flex-none"><span className="font-bold">{t.institution}</span>
            <select className={inputClass} value={filters.institution ?? ""} onChange={(e) => set("institution", e.target.value)}>
              <option value="">{t.allInstitutions}</option>
              {institutions.map((i) => <option key={i.institution_id} value={i.institution_id}>{i.name}</option>)}
            </select>
          </label>
        )}
      </form>
      <p className="mt-2 max-w-4xl text-sm text-muted">{t.datesScope}</p>
      {reversed && <div className="mt-2 max-w-4xl"><Notice kind="error">{t.datesReversedNotice}</Notice></div>}

      <div className="mt-4">
        {tab === "operation" ? <OperationView filters={filters} /> : <PanoramaView filters={filters} />}
      </div>
    </AppShell>
  );
}
