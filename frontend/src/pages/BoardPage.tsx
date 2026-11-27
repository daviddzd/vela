// /tablero — live board for coordination: clock, counters, queue, alerts, map, new request.
// Updates without reloading: every WebSocket event triggers a re-read of /api/board.
import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { api, type Board, type BoardAlert } from "../api/client";
import { classifierText } from "../lib/classifierText";
import { AppShell } from "../components/AppShell";
import { RequestForm } from "../components/RequestForm";
import { RequestResult } from "../components/RequestResult";
import { StatusBadge } from "../components/StatusBadge";
import { Button, Card, IconCircle, Notice, PageHeader } from "../components/ui";
import { AlertTriangle, CheckCircle2, COUNTER_ICON, Icon } from "../components/icons";
import { RefreshCw, Radio, Sparkles } from "lucide-react";
import { es } from "../i18n/es";
import { formatClock, formatLongDate, useServerClock } from "../lib/clock";
import { formatWhen } from "../lib/format";
import { useBoardSocket } from "../lib/useBoardSocket";
import type { ServiceRequest } from "../api/client";
import { relayText } from "../lib/relay";

// MapLibre is large: load it only when the board opens (phones on the family screen never download it).
const VisitsMap = lazy(() => import("../components/VisitsMap").then((m) => ({ default: m.VisitsMap })));

const COUNTERS = ["queued", "on_the_way", "in_visit", "done_today"] as const;

export function BoardPage() {
  const [board, setBoard] = useState<Board | null>(null);
  const [created, setCreated] = useState<ServiceRequest | null>(null);
  const { now, synced } = useServerClock();
  const pending = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const refresh = useCallback(() => {
    // several events often arrive together: wait 300 ms and read once
    clearTimeout(pending.current);
    pending.current = setTimeout(() => api.board().then(setBoard).catch(() => undefined), 300);
  }, []);
  useEffect(() => { refresh(); }, [refresh]);
  const socket = useBoardSocket(refresh);

  return (
    <AppShell>
      <PageHeader title={es.pageTitles.board}
        actions={<div className="text-right">
          <p className="figure text-4xl tabular-nums text-navy" aria-live="off">{formatClock(now)}</p>
          {!synced && <p className="text-muted">{es.board.clockUnsynced}</p>}
          <p className="font-bold" aria-live="polite">
            {socket === "live" && <span className="inline-flex items-center gap-1 rounded-full bg-ok-soft px-3 py-0.5 text-ok"><Icon as={Radio} /> {es.board.live}</span>}
            {socket === "connecting" && <span className="text-muted">{es.board.connecting}</span>}
            {socket === "reconnecting" && <span className="text-warn"><Icon as={RefreshCw} /> {es.board.reconnecting}</span>}
          </p>
        </div>}>
        <p className="first-letter:uppercase">{formatLongDate(now)}</p>
      </PageHeader>

      {socket === "reconnecting" && <div className="mt-3"><Notice kind="error">{es.board.reconnecting}</Notice></div>}
      {socket === "denied" && <div className="mt-3"><Notice kind="error">{es.board.denied}</Notice></div>}

      {/* figures strip: one white card, a big number per state, icon in a soft circle */}
      <ul className="grid grid-cols-2 gap-y-4 rounded-card border border-navy/10 bg-white p-5 shadow-[var(--shadow-card)] md:grid-cols-4 md:divide-x md:divide-navy/10">
        {COUNTERS.map((k) => (
          <li key={k} className="flex flex-col items-center gap-2 px-2 text-center lg:flex-row lg:gap-4 lg:px-3 lg:text-left">
            <IconCircle icon={COUNTER_ICON[k]} />
            <span><span className="figure block text-4xl leading-none text-navy">{board?.counters[k] ?? "—"}</span>
              <span className="font-bold">{es.board.counters[k]}</span></span>
          </li>
        ))}
      </ul>

      {/* two independent columns: no gaps when the queue is long and the alerts short (or the other way) */}
      {/* phone: alerts right after the figures (order, below lg only); projector: the two columns as before */}
      <div className="mt-4 grid items-start gap-4 lg:grid-cols-3">
        <div className="contents lg:col-span-2 lg:block lg:space-y-4">
        <Card className="max-lg:order-2">
          <h2>{es.board.queueTitle}</h2>
          {board && board.queue.length === 0 && <AllClear board={board} />}
          {board && board.queue.length > 0 && <NewOnes board={board} />}
          <ol className="mt-2 divide-y divide-navy/10">
            {board?.queue.map((q) => (
              <li key={q.request_id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span>
                  <strong className={q.priority === "high" ? "text-danger" : ""}>
                    {q.priority === "high" && <><Icon as={AlertTriangle} /> </>}{es.priority[q.priority]}
                  </strong>{" · "}<Link to={`/pacientes/${q.patient_id}`} className="underline decoration-navy/40 hover:text-navy">{q.patient_name}</Link> · {q.service_name} · {formatWhen(q.scheduled_for, board ? new Date(board.now) : undefined)}
                  <span className="block text-muted">
                    {es.board.origin[q.origin] ?? q.origin} · {q.status_reason ? es.statusReason[q.status_reason] : ""}
                  </span>
                </span>
                <span className="flex flex-wrap items-center gap-3">
                  <span className="font-bold tabular-nums">{q.minutes_waiting} {es.common.minutes} {es.board.waiting}</span>
                  {q.status_reason === "awaiting_approval" && (
                    <Link to={`/aprobaciones?solicitud=${encodeURIComponent(q.request_id)}`}
                      className="inline-flex min-h-12 items-center gap-2 rounded-full bg-navy px-5 font-bold text-white hover:bg-navy-dark">
                      <Icon as={CheckCircle2} /> {es.board.reviewApprove}</Link>)}
                </span>
              </li>
            ))}
          </ol>
        </Card>
        <Card className="max-lg:order-3">
          <h2>{es.board.mapTitle}</h2>
          <div className="mt-2">
            <Suspense fallback={<p>{es.common.loading}</p>}>
              <VisitsMap visits={board?.visits ?? []} staff={board?.staff ?? []} />
            </Suspense>
          </div>
          {board && board.visits.length === 0 && <p className="mt-2">{es.board.visitsEmpty}</p>}
          <ul className="mt-3 max-h-60 divide-y divide-navy/10 overflow-y-auto">
            {board?.visits.map((v) => (
              <li key={v.request_id} className="flex flex-wrap items-center justify-between gap-2 py-1">
                <span>{formatWhen(v.scheduled_for, board ? new Date(board.now) : undefined)} · <Link to={`/pacientes/${v.patient_id}`} className="underline decoration-navy/40 hover:text-navy">{v.patient_name}</Link> · {v.caregiver_name ?? es.family.pendingCaregiver}{v.relay_caregiver_name && ` (${relayText(v.relay_caregiver_name, v.relay_at)})`}</span>
                <StatusBadge status={v.status} />
              </li>
            ))}
          </ul>
          <p className="mt-2 text-muted">{es.board.syntheticNote}</p>
        </Card>
        </div>
        <div className="contents lg:block lg:space-y-4">
        <Card className="max-lg:order-1">
          <h2>{es.board.alertsTitle}</h2>
          {board && board.alerts.length === 0 && <p className="mt-2">{es.board.alertsEmpty}</p>}
          <ul className="mt-2 space-y-2">
            {board && groupAlerts(board.alerts).map((g) => g.critical
              ? (g.items[0].type === "emergency_review"
                ? <ReviewAlert key={g.key} a={g.items[0]} now={now} onDone={refresh} />
                : <li key={g.key} className="rounded-field border-4 border-danger bg-danger-soft p-3 font-bold" role="alert">
                    <Icon as={AlertTriangle} /> {g.items[0].message}
                    <span className="block font-normal text-muted">{formatWhen(g.items[0].created_at, new Date(board.now))}</span></li>)
              : g.items.length === 1
                ? <li key={g.key} className="rounded-field border-2 border-danger/60 bg-white p-3">
                    <Icon as={AlertTriangle} /> {g.items[0].message}
                    <span className="block text-muted">{formatWhen(g.items[0].created_at, new Date(board.now))}</span></li>
                : <li key={g.key} className="rounded-field border-2 border-danger/60 bg-white p-3">
                    <p className="font-bold"><Icon as={AlertTriangle} /> {(es.board.alertGroups[g.items[0].type] ?? es.board.alertGroups.other).replace("{n}", String(g.items.length))}</p>
                    <details className="mt-1">
                      <summary className="min-h-12 cursor-pointer font-bold text-navy flex items-center">{es.board.alertGroupShow.replace("{n}", String(g.items.length))}</summary>
                      <ul className="mt-1 space-y-2">{g.items.map((a) => (
                        <li key={a.alert_id} className="border-t border-danger/20 pt-2">{a.message}
                          <span className="block text-muted">{formatWhen(a.created_at, new Date(board.now))}</span></li>))}</ul>
                    </details>
                  </li>)}
          </ul>
        </Card>
        <Card className="max-lg:order-4">
          <h2>{es.board.newRequest}</h2>
          <div className="mt-3 space-y-3">
            <RequestForm coordinator onCreated={(r) => { setCreated(r); refresh(); }} />
            {created && <RequestResult r={created} />}
          </div>
        </Card>
        </div>
      </div>
    </AppShell>
  );
}

/** Voice note rated "emergency" ONLY by the classifier (alerts_followup.py): coordination must contact the family
 *  before the deadline, or the alert escalates to Dirección. Both answers are audited. */
function ReviewAlert({ a, now, onDone }: { a: BoardAlert; now: Date; onDone: () => void }) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const left = a.escalate_at ? Math.max(0, new Date(a.escalate_at).getTime() - now.getTime()) : 0;
  const mmss = `${Math.floor(left / 60000)}:${String(Math.floor((left % 60000) / 1000)).padStart(2, "0")}`;
  const answer = async (outcome: "emergency" | "not_emergency") => {
    setBusy(true); setError("");
    try { await api.reviewAlert(a.alert_id, outcome); onDone(); }
    catch (err) { setError((err as Error).message || es.common.error); }
    finally { setBusy(false); }
  };
  return (
    <li className="rounded-field border-4 border-danger bg-danger-soft p-3" role="alert">
      <p className="font-bold text-danger"><Icon as={AlertTriangle} /> {es.board.reviewTitle}</p>
      <p className="mt-1">{a.message}</p>
      {classifierText(a.classifier_probs) && <p className="mt-1"><strong>{es.classifierConfidence.label}:</strong>{" "}
        {classifierText(a.classifier_probs)}<br /><span className="text-sm text-muted">{es.classifierConfidence.note}</span></p>}
      <p className="mt-2 text-lg font-bold" aria-live="off">{a.escalated_at || left === 0
        ? es.board.reviewEscalated : es.board.reviewCountdown.replace("{t}", mmss)}</p>
      <div className="mt-2 grid gap-2">
        <Button icon={AlertTriangle} disabled={busy} onClick={() => answer("emergency")} className="bg-danger! hover:bg-danger/90!">{es.board.reviewWasEmergency}</Button>
        <Button variant="secondary" disabled={busy} onClick={() => answer("not_emergency")}>{es.board.reviewNotEmergency}</Button>
      </div>
      {error && <p className="mt-1 font-bold text-danger">{error}</p>}
    </li>
  );
}

/** Alerts of the same type go in one card ("2 turnos nocturnos exceden la jornada legal"); critical ones (emergencies
 *  and amber voice reviews) are never grouped and always go first. */
function groupAlerts(alerts: BoardAlert[]): { key: string; critical: boolean; items: BoardAlert[] }[] {
  const isCritical = (a: BoardAlert) => a.level === "critical" || a.type === "emergency" || a.type === "emergency_review";
  const critical = alerts.filter(isCritical).map((a) => ({ key: a.alert_id, critical: true, items: [a] }));
  const groups = new Map<string, BoardAlert[]>();
  for (const a of alerts.filter((x) => !isCritical(x))) groups.set(a.type, [...(groups.get(a.type) ?? []), a]);
  return [...critical, ...[...groups.entries()].map(([type, items]) => ({ key: `group-${type}`, critical: false, items }))];
}

/** Nobody is waiting: say so, and show what comes next (today and tomorrow), including the care-plan visits the
 *  worker will create on the day (care_plans.forecast). */
function AllClear({ board }: { board: Board }) {
  const now = new Date(board.now);
  const shown = board.upcoming.slice(0, 12);
  return (<>
    <p className="mt-2 text-xl font-bold text-ok">{es.board.allClear} <Icon as={CheckCircle2} /></p>
    <h3 className="mt-3 font-bold">{es.board.upcomingTitle}</h3>
    {board.upcoming.length === 0 ? <p className="mt-1">{es.board.upcomingNone}</p> : (
      <UpcomingList items={shown} now={now} />)}
    {board.upcoming.length > shown.length && <p className="mt-1 text-muted">{es.board.upcomingMore.replace("{n}", String(board.upcoming.length - shown.length))}</p>}
  </>);
}

/** Someone is waiting (the queue is shown instead of "Próximas visitas"): still show what was just created or
 *  assigned, so a new request never arrives unseen. */
function NewOnes({ board }: { board: Board }) {
  const fresh = board.upcoming.filter((v) => v.is_new);
  if (!fresh.length) return null;
  return (<div className="mt-3 border-t border-navy/10 pt-2">
    <h3 className="font-bold">{es.board.newTitle}</h3>
    <UpcomingList items={fresh} now={new Date(board.now)} />
  </div>);
}

/** One line per visit; a new one (created or assigned in the last minutes, sent first by the API) is marked with
 *  an icon, a border and the word «Nueva»: never by colour alone. */
function UpcomingList({ items, now }: { items: Board["upcoming"]; now: Date }) {
  return (
    <ul className="mt-1 divide-y divide-navy/10">{items.map((v, i) => (
      <li key={v.request_id ?? `${v.patient_id}-${i}`}
        className={v.is_new ? "my-1 rounded-xl border-2 border-teal-text bg-teal-soft px-3 py-1.5" : "py-1.5"}>
        {v.is_new && <><span className="inline-flex items-center gap-1 rounded-full border-2 border-teal-text bg-white px-2 font-bold text-teal-text">
          <Icon as={Sparkles} /> {es.board.newBadge}</span>{" "}</>}
        <strong className="tabular-nums">{formatWhen(v.scheduled_for, now)}</strong>{" · "}
        <Link to={`/pacientes/${v.patient_id}`} className="underline decoration-navy/40 hover:text-navy">{v.patient_name}</Link>
        {" · "}{v.service_name}{" · "}
        {v.caregiver_name ? <strong>{v.caregiver_name}</strong>
          : <span className="text-muted">{v.status === "planned" ? es.family.plannedNote : es.family.pendingCaregiver}</span>}
      </li>))}</ul>
  );
}
