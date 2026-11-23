// /personal (coordination) — caregivers with type, skills, shift and whether they are on shift now; the day's
// timeline per person (trip + visit on one time scale); the week's load; out of service / back in service
// (the same re-dispatch logic as the demo panel); and a street map with their bases.
import { CalendarClock, Car, CheckCircle2, Home, PowerOff, RotateCcw } from "lucide-react";
import { lazy, Suspense, useCallback, useEffect, useMemo, useState, type FormEvent } from "react";
import { api, ApiError } from "../api/client";
import type { MapPoint } from "../charts/CityMap";
import { chart } from "../charts/theme";
import { AppShell } from "../components/AppShell";
import { AlertTriangle, Ban, Icon } from "../components/icons";
import { StatusBadge } from "../components/StatusBadge";
import { Button, Card, inputClass, Notice } from "../components/ui";
import { es } from "../i18n/es";
import { useBoardSocket } from "../lib/useBoardSocket";

const StreetMap = lazy(() => import("../components/StreetMap").then((m) => ({ default: m.StreetMap })));
const t = es.staff;
const fill = (s: string, v: Record<string, string | number>) => s.replace(/\{(\w+)\}/g, (_, k) => String(v[k] ?? ""));
const hm = (iso: string) => new Date(iso).toLocaleTimeString("es-MX", { timeZone: "America/Mexico_City", hour: "2-digit", minute: "2-digit" });
const minutesOfDay = (iso: string) => {
  const [h, m] = new Date(iso).toLocaleTimeString("en-GB", { timeZone: "America/Mexico_City", hour: "2-digit", minute: "2-digit" }).split(":").map(Number);
  return h * 60 + m;
};

export function StaffPage() {
  const [d, setD] = useState<any>(null);
  const [sel, setSel] = useState<string | null>(null);
  const [msg, setMsg] = useState<{ kind: "ok" | "error" | "info"; text: string } | null>(null);
  const load = useCallback(() => api.staff().then((x) => { setD(x); setSel((cur) => cur ?? x.staff[0]?.caregiver_id ?? null); }), []);
  useEffect(() => { load(); }, [load]);
  useBoardSocket(() => load());           // assignments change live (worker, approvals, other screens)

  const points: MapPoint[] = useMemo(() => (d?.staff ?? []).map((c: any) => ({
    id: c.caregiver_id, lat: c.lat, lon: c.lon, symbol: c.out_of_service ? "triangle" : "roundRect",
    color: c.out_of_service ? "#C0392B" : c.on_shift_now ? chart.series[0] : "#9AA5AB", size: 11,
    label: c.caregiver_id === sel ? c.name.split(" ").slice(0, 2).join(" ") : undefined,
    tooltip: `${fill(t.base, { name: c.name })} · ${t.type[c.type]} · ${c.out_of_service ? t.outOfService : c.on_shift_now ? t.onShift : t.offShift}`,
  })), [d, sel]);

  if (!d) return <AppShell><p>{es.common.loading}</p></AppShell>;
  const person = d.staff.find((c: any) => c.caregiver_id === sel);
  return (
    <AppShell>
      <h1 className="text-teal">{es.screens["/personal"]}</h1>
      <p className="mt-1">{t.intro}</p>
      {msg && <div className="mt-3"><Notice kind={msg.kind}>{msg.text}</Notice></div>}
      <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1fr)_minmax(0,1.2fr)]">
        <Card>
          <ul className="divide-y divide-teal/10">{d.staff.map((c: any) => (
            <li key={c.caregiver_id}>
              <button type="button" onClick={() => setSel(c.caregiver_id)} aria-pressed={sel === c.caregiver_id}
                className={`w-full rounded-card p-2 text-left ${sel === c.caregiver_id ? "bg-teal/10" : "hover:bg-teal/5"}`}>
                <span className="flex flex-wrap items-center justify-between gap-2">
                  <strong className="text-teal">{c.name}</strong>
                  <StateWord c={c} />
                </span>
                <span className="block text-sm">{t.type[c.type]} · {c.skills.map((s: string) => t.skills[s]).join(", ")} · {c.shift_start}–{c.shift_end} ({t.legalType[c.legal_type]})
                  {" · "}{c.rests_today ? <strong>{t.restsToday}</strong> : fill(t.restDay, { day: t.weekdays[c.rest_day] })}</span>
                {c.exceeds_legal && <span className="mt-1 block text-sm font-bold text-danger"><Icon as={AlertTriangle} /> {t.exceeds}</span>}
                <LoadBar c={c} />
              </button>
            </li>))}</ul>
          <p className="mt-2 text-sm text-muted">{fill(t.weekNote, { d: d.workdays_per_week })}</p>
        </Card>
        <div className="space-y-4">
          {person && <Agenda person={person} onMsg={(m) => { setMsg(m); load(); }} />}
          <Card>
            <h2 className="text-teal">{t.mapTitle}</h2>
            <div className="mt-2"><Suspense fallback={<div style={{ minHeight: 380 }} />}>
              <StreetMap points={points} height={380} label={t.mapLabel} /></Suspense></div>
            <ul className="mt-2 flex flex-wrap gap-x-5 text-sm">
              <li><span style={{ color: chart.series[0] }}>■</span> {t.onShift}</li>
              <li><span style={{ color: "#9AA5AB" }}>■</span> {t.offShift}</li>
              <li><span style={{ color: "#C0392B" }}>▲</span> {t.outOfService}</li>
            </ul>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}

function StateWord({ c }: { c: any }) {
  if (c.out_of_service) return <span className="font-bold text-danger"><Icon as={Ban} /> {t.outOfService}</span>;
  return c.on_shift_now ? <span className="font-bold text-ok"><Icon as={CheckCircle2} /> {t.onShift}</span>
    : <span className="text-muted"><Icon as={CalendarClock} /> {t.offShift}</span>;
}

function LoadBar({ c }: { c: any }) {
  const pct = Math.min(100, c.week_load_pct ?? 0);
  return (
    <span className="mt-1 block text-sm">
      {t.weekLoad}: {fill(t.weekLoadValue, { h: c.week_hours.toLocaleString("es-MX"), cap: c.week_capacity_hours, pct: (c.week_load_pct ?? 0).toLocaleString("es-MX") })}
      · {c.visits_today === 1 ? t.visitsTodayOne : fill(t.visitsToday, { n: c.visits_today })}
      <span aria-hidden="true" className="mt-1 block h-2 w-full overflow-hidden rounded bg-teal/10">
        <span className="block h-2 rounded bg-teal" style={{ width: `${pct}%` }} /></span>
    </span>
  );
}

function Agenda({ person, onMsg }: { person: any; onMsg: (m: { kind: "ok" | "error" | "info"; text: string }) => void }) {
  const [day, setDay] = useState<any>(null);
  const [asking, setAsking] = useState(false);
  const [reason, setReason] = useState("");
  useEffect(() => { setDay(null); api.staffDay(person.caregiver_id).then(setDay); }, [person.caregiver_id, person.out_of_service]);
  const markOut = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const r = await api.staffOut(person.caregiver_id, reason);
      setAsking(false); setReason("");
      onMsg({ kind: "ok", text: fill(t.outDone, { name: person.name, n: r.pending }) });
    } catch (err) { onMsg({ kind: "error", text: err instanceof ApiError ? err.message : es.common.error }); }
  };
  const back = async () => {
    try { await api.staffBack(person.caregiver_id); onMsg({ kind: "ok", text: fill(t.backDone, { name: person.name }) }); }
    catch (err) { onMsg({ kind: "error", text: err instanceof ApiError ? err.message : es.common.error }); }
  };
  return (
    <Card>
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-teal">{fill(t.agendaOf, { name: person.name })}</h2>
        {person.out_of_service
          ? <Button icon={RotateCcw} onClick={back}>{t.markBack}</Button>
          : !asking && <Button icon={PowerOff} variant="secondary" onClick={() => setAsking(true)}>{t.markOut}</Button>}
      </div>
      {asking && (
        <form onSubmit={markOut} className="mt-3 space-y-2 rounded-card border border-teal/20 p-3">
          <p className="text-sm">{t.outHelp}</p>
          <label className="block"><span className="font-bold">{t.reason}</span>
            <input className={inputClass} required minLength={3} maxLength={200} value={reason} onChange={(e) => setReason(e.target.value)} /></label>
          <div className="flex gap-2"><Button type="submit">{t.markOut}</Button>
            <Button variant="secondary" onClick={() => setAsking(false)}>{es.record.cancel}</Button></div>
        </form>)}
      {person.exceeds_legal && (
        <Notice kind="error">{t.exceeds}: {fill(t.exceedsDetail, { hours: person.shift_hours, kind: t.legalType[person.legal_type],
          max: person.legal_max_hours })}</Notice>)}
      <label className="mt-3 block max-w-xs"><span className="font-bold">{t.restDayLabel}</span>
        <select className={inputClass} value={person.rest_day} onChange={async (e) => {
          const d = Number(e.target.value);
          try {
            const r = await api.staffRestDay(person.caregiver_id, d);
            onMsg({ kind: "ok", text: fill(t.restDaySaved, { name: person.name, day: t.weekdays[d], n: r.redispatched.length }) });
          } catch (err) { onMsg({ kind: "error", text: err instanceof ApiError ? err.message : es.common.error }); }
        }}>{[1, 2, 3, 4, 5, 6, 7].map((d) => <option key={d} value={d}>{t.weekdays[d]}</option>)}</select></label>
      <p className="mt-1 text-sm text-muted">{t.restNote}</p>
      {!day ? <p className="mt-2">{es.common.loading}</p> : <Timeline day={day} />}
    </Card>
  );
}

/** One time axis (the shift, widened to include every visit): trip and visit bars, each also written as text. */
function Timeline({ day }: { day: any }) {
  const [sh, sm] = day.shift_start.split(":").map(Number);
  const [eh, em] = day.shift_end.split(":").map(Number);
  let from = sh * 60 + sm, to = eh * 60 + em;
  if (to <= from) to += 24 * 60;
  for (const v of day.visits) {
    if (v.planned_start) from = Math.min(from, minutesOfDay(v.planned_start));
    if (v.planned_end) to = Math.max(to, minutesOfDay(v.planned_end));
  }
  from = Math.floor(from / 60) * 60; to = Math.ceil(to / 60) * 60;
  const pos = (m: number) => `${(100 * (m - from)) / (to - from)}%`;
  const hours = Array.from({ length: (to - from) / 60 + 1 }, (_, i) => from + i * 60);
  return (<>
    <p className="mt-1 text-sm text-muted">{fill(t.shiftWindow, { from: day.shift_start, to: day.shift_end })}</p>
    {day.visits.length === 0 ? <p className="mt-2">{t.noVisits}</p> : (<>
      <div className="relative mt-3 h-16 rounded bg-cream" aria-hidden="true">
        {hours.map((m) => (
          <span key={m} className="absolute top-0 h-full border-l border-teal/15 text-[11px] text-muted" style={{ left: pos(m) }}>
            <span className="ml-0.5">{String(Math.floor(m / 60) % 24).padStart(2, "0")}</span></span>))}
        {day.visits.map((v: any) => {
          const start = v.planned_start ? minutesOfDay(v.planned_start) : null;
          const arrive = v.arrive_at ? minutesOfDay(v.arrive_at) : start;
          const end = v.planned_end ? minutesOfDay(v.planned_end) : arrive;
          return (<span key={v.assignment_id}>
            {start !== null && arrive !== null && arrive > start && (
              <span className="absolute top-5 h-6 rounded-l border border-teal/40 bg-[repeating-linear-gradient(45deg,#ffffff,#ffffff_3px,#cfe3e7_3px,#cfe3e7_6px)]"
                style={{ left: pos(start), width: `calc(${pos(arrive)} - ${pos(start)})` }} />)}
            {arrive !== null && end !== null && (
              <span className="absolute top-5 h-6 rounded-r bg-teal" style={{ left: pos(arrive), width: `max(4px, calc(${pos(end)} - ${pos(arrive)}))` }} />)}
          </span>);
        })}
      </div>
      <ul className="mt-2 flex gap-4 text-sm"><li><Icon as={Car} /> {t.tripLegend}</li><li><Icon as={Home} /> {t.visitLegend}</li></ul>
      <ol className="mt-2 divide-y divide-teal/10">{day.visits.map((v: any) => (
        <li key={v.assignment_id} className="flex flex-wrap items-center justify-between gap-2 py-1.5">
          <span>{v.planned_start && <>{t.trip} {hm(v.planned_start)}–{hm(v.arrive_at)} · </>}
            <strong>{t.visit} {v.arrive_at ? hm(v.arrive_at) : "—"}–{v.planned_end ? hm(v.planned_end) : "—"}</strong> · {v.patient_name} · {v.service_name}</span>
          <StatusBadge status={v.status} />
        </li>))}</ol>
    </>)}
  </>);
}
