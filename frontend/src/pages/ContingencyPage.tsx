// /contingencia — live: stations and their level, current event(s), my institution's proposal and decision.
// Real and demo events are shown apart. Nothing changes without the coordinator's approval.
import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { AppShell } from "../components/AppShell";
import { ChartCard } from "../components/ChartCard";
import { AlertTriangle, CheckCircle2, Icon } from "../components/icons";
import { Button, Card, Notice } from "../components/ui";
import { es } from "../i18n/es";
import { formatDateTime } from "../lib/format";
import { useBoardSocket } from "../lib/useBoardSocket";
import { LEVEL_ICON } from "../components/StationsMap";

const StationsMap = lazy(() => import("../components/StationsMap").then((m) => ({ default: m.StationsMap })));
const t = es.contingency;
type Proposal = { proposal_id: number; institution_id: string; kind: string; reason: string; status: string };
type Event = { event_id: string; origin: string; scenario: string | null; phase: string; pollutant: string; district_names: string[];
  started_at: string; ended_at: string | null; proposals: Proposal[]; traffic_active: boolean;
  decisions: { institution_id: string; decision: string; notes: string }[] };
type Current = { thresholds: { o3: number; pm25: number }; scenario: { scenario: string } | null; can_decide: boolean;
  stations: { station_id: string; name: string; district_id: string; district_name: string; lat: number; lon: number; phase: string; o3: number; pm25_24h: number; scenario: boolean }[];
  events: Event[] };
const TONE: Record<string, string> = { normal: "text-ok", watch: "text-warn", phase1: "text-danger" };

export function ContingencyPage() {
  const { user } = useAuth();
  const [d, setD] = useState<Current | null>(null);
  const [picked, setPicked] = useState<Record<string, Set<number>>>({});
  const [msg, setMsg] = useState("");
  const load = useCallback(() => { api.contingency().then((x) => setD(x as Current)).catch(() => undefined); }, []);
  useEffect(load, [load]);
  useBoardSocket(load);

  const decide = async (ev: Event, mode: "all" | "selected" | "none") => {
    const ids = [...(picked[ev.event_id] ?? [])];
    try {
      const r = await api.decideContingency(ev.event_id, mode, ids) as { approved: number; total: number };
      setMsg(t.decided.replace("{approved}", String(r.approved)).replace("{total}", String(r.total)));
    } catch (e) { setMsg((e as Error).message); }
    load();
  };
  const toggle = (ev: string, ids: number[]) => setPicked((p) => {
    const s = new Set(p[ev] ?? []);
    const on = ids.every((id) => s.has(id));
    ids.forEach((id) => (on ? s.delete(id) : s.add(id)));
    return { ...p, [ev]: s };
  });

  if (!d) return <AppShell><p>{es.common.loading}</p></AppShell>;
  const open = d.events.filter((e) => !e.ended_at);
  const ended = d.events.filter((e) => e.ended_at);
  const worst = d.stations.reduce((w, s) => (["normal", "watch", "phase1"].indexOf(s.phase) > ["normal", "watch", "phase1"].indexOf(w) ? s.phase : w), "normal");
  const line = (e: Event) => t.eventLine.replace("{phase}", t.levels[e.phase]).replace("{pollutant}", t.pollutant[e.pollutant])
    .replace("{districts}", e.district_names.join(", ")).replace("{since}", formatDateTime(e.started_at));
  const badge = (e: Event) => (
    <span className={`mr-2 rounded-card px-2 ${e.origin === "demo_scenario" ? "bg-warn/15" : "bg-danger/10"}`}>
      {e.origin === "demo_scenario" ? t.demo : t.real}</span>);

  return (
    <AppShell>
      <h1 className="text-teal">{es.screens["/contingencia"]}</h1>
      {d.scenario && <div className="mt-2"><Notice>{t.demoRunning.replace("{scenario}", es.demo.scenarios[d.scenario.scenario] ?? d.scenario.scenario)}</Notice></div>}
      {msg && <div className="mt-2"><Notice kind="ok">{msg}</Notice></div>}

      <div className="mt-4 grid gap-4 xl:grid-cols-5">
        <div className="space-y-4 xl:col-span-3">
          <ChartCard question={t.statusQ} keyValue={<span className={TONE[worst]}><Icon as={LEVEL_ICON[worst]} /> {t.levels[worst]}</span>}
            source={t.source}>
            {open.length === 0 && <p>{t.none}</p>}
            <ul className="space-y-2">
              {open.map((e) => <li key={e.event_id} className="rounded-card border-2 border-danger/60 p-3 font-bold">{badge(e)}{line(e)}</li>)}
            </ul>
            {ended.length > 0 && (
              <details className="mt-3">
                <summary className="flex min-h-12 cursor-pointer items-center font-bold text-teal">
                  {t.historyTitle.replace("{n}", String(ended.length))}</summary>
                <ul className="space-y-2 text-muted">
                  {ended.map((e) => <li key={e.event_id} className="rounded-card border border-muted/30 p-2">{badge(e)}{line(e)}
                    <span className="block">{t.ended.replace("{at}", formatDateTime(e.ended_at!))}</span></li>)}
                </ul>
              </details>)}
          </ChartCard>

          <ChartCard question={t.stationsQ} source={t.source}
            note={t.stationsNote.replace("{o3}", String(d.thresholds.o3)).replace("{pm}", String(d.thresholds.pm25))}
            table={{ columns: [t.station, t.o3, t.pm25, t.level], rows: d.stations.map((s) => [`${s.station_id} · ${s.name}`, s.o3, s.pm25_24h, t.levels[s.phase]]) }}>
            <Suspense fallback={<p>{es.common.loading}</p>}><StationsMap stations={d.stations} /></Suspense>
            <ul className="mt-3 grid gap-x-4 gap-y-1 sm:grid-cols-2 xl:grid-cols-3">
              {d.stations.filter((s) => s.phase !== "normal").map((s) => (
                <li key={s.station_id} className={`font-bold ${TONE[s.phase]}`}><Icon as={LEVEL_ICON[s.phase]} /> {s.station_id} ({s.district_name}): {t.levels[s.phase]}
                  <span className="block font-normal text-ink">PM2.5 24 h {s.pm25_24h} µg/m³ · O₃ {s.o3} ppb</span></li>))}
            </ul>
          </ChartCard>
        </div>

        <div className="space-y-4 xl:col-span-2">
          {open.length === 0 && <Card><h2 className="text-teal">{t.proposalQ}</h2><p className="mt-2">{t.noProposal}</p></Card>}
          {open.map((e) => {
            const mine = e.proposals;
            const pending = mine.filter((p) => p.status === "proposed");
            const sel = picked[e.event_id] ?? new Set<number>();
            return (
              <ChartCard key={e.event_id} question={`${t.proposalQ}${e.origin === "demo_scenario" ? ` (${t.demo})` : ""}`} source={t.source}
                note={user?.role === "owner" ? t.ownerView : t.nothingChanges}>
                {user?.role === "owner" ? (
                  <ul className="space-y-1">{[...new Set(mine.map((p) => p.institution_id))].map((inst) => {
                    const dec = e.decisions.find((x) => x.institution_id === inst);
                    return <li key={inst}>{t.institutionSummary.replace("{inst}", inst).replace("{n}", String(mine.filter((p) => p.institution_id === inst).length))
                      .replace("{decision}", dec ? t.decisions[dec.decision] : t.pending)}</li>; })}</ul>
                ) : (<>
                  {(t.order as string[]).map((k) => {
                    const items = mine.filter((p) => p.kind === k);
                    if (items.length === 0) {     // the system checked this category: say why there is nothing
                      const why = k === "recalculate_routes" && !e.traffic_active ? t.emptyReason.recalculate_routes_no_traffic : t.emptyReason[k];
                      return <p key={k} className="mt-3 text-muted"><Icon as={CheckCircle2} /> {why}</p>;
                    }
                    if (k === "notify_family") {  // one checkbox for all the families, list on demand
                      const open = items.filter((p) => p.status === "proposed").map((p) => p.proposal_id);
                      return (
                        <fieldset key={k} className="mt-3">
                          <legend className="font-bold">{t.kinds[k]} ({items.length})</legend>
                          <label className="flex min-h-12 items-center gap-3">
                            <input type="checkbox" className="size-6 shrink-0 accent-teal" disabled={open.length === 0}
                              checked={open.length > 0 && open.every((id) => sel.has(id))} onChange={() => toggle(e.event_id, open)} />
                            <span>{t.notifyAll.replace("{n}", String(items.length))}
                              {open.length === 0 && <span className="ml-1 font-bold text-teal"><Icon as={CheckCircle2} /> {t.proposalStatus[items[0].status]}</span>}</span>
                          </label>
                          <details><summary className="flex min-h-12 cursor-pointer items-center font-bold text-teal">{t.showList}</summary>
                            <ul className="ml-9 list-disc space-y-1">{items.map((p) => <li key={p.proposal_id}>{p.reason}</li>)}</ul>
                          </details>
                        </fieldset>);
                    }
                    return (
                      <fieldset key={k} className="mt-3">
                        <legend className="font-bold">{t.kinds[k]} ({items.length})</legend>
                        <ul className="mt-1 space-y-1 sm:max-h-72 sm:overflow-y-auto">
                          {items.map((p) => (
                            <li key={p.proposal_id}>
                              <label className="flex min-h-12 items-start gap-3">
                                <input type="checkbox" className="mt-1 size-6 shrink-0 accent-teal" disabled={p.status !== "proposed"}
                                  checked={sel.has(p.proposal_id)} onChange={() => toggle(e.event_id, [p.proposal_id])} />
                                <span>{p.reason}
                                  {p.status !== "proposed" && <span className="ml-1 font-bold text-teal"><Icon as={CheckCircle2} /> {t.proposalStatus[p.status]}</span>}</span>
                              </label>
                            </li>))}
                        </ul>
                      </fieldset>);
                  })}
                  {d.can_decide && pending.length > 0 && (   /* in the normal flow, after the list: never covers it */
                    <div className="mt-5 flex flex-wrap gap-2 border-t border-teal/15 pt-4">
                      <Button icon={CheckCircle2} onClick={() => decide(e, "all")}>{t.approveAll}</Button>
                      <Button variant="secondary" icon={CheckCircle2} disabled={!sel.size} onClick={() => decide(e, "selected")}>{t.approveSelected}</Button>
                      <Button variant="secondary" icon={AlertTriangle} onClick={() => decide(e, "none")}>{t.rejectAll}</Button>
                    </div>)}
                </>)}
              </ChartCard>);
          })}
        </div>
      </div>
    </AppShell>
  );
}
