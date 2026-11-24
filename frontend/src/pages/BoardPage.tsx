// /tablero — live board for coordination: clock, counters, queue, alerts, map, new request.
// Updates without reloading: every WebSocket event triggers a re-read of /api/board.
import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router";
import { api, type Board, type BoardAlert } from "../api/client";
import { AppShell } from "../components/AppShell";
import { RequestForm } from "../components/RequestForm";
import { RequestResult } from "../components/RequestResult";
import { StatusBadge } from "../components/StatusBadge";
import { Button, Card, Notice } from "../components/ui";
import { AlertTriangle, CheckCircle2, COUNTER_ICON, Icon } from "../components/icons";
import { RefreshCw, Radio } from "lucide-react";
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
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-teal">{es.screens["/tablero"]}</h1>
          <p className="text-muted first-letter:uppercase">{formatLongDate(now)}</p>
        </div>
        <div className="text-right">
          <p className="figure text-4xl tabular-nums" aria-live="off">{formatClock(now)}</p>
          {!synced && <p className="text-muted">{es.board.clockUnsynced}</p>}
          <p className="font-bold" aria-live="polite">
            {socket === "live" && <span className="text-ok"><Icon as={Radio} /> {es.board.live}</span>}
            {socket === "connecting" && <span className="text-muted">{es.board.connecting}</span>}
            {socket === "reconnecting" && <span className="text-warn"><Icon as={RefreshCw} /> {es.board.reconnecting}</span>}
          </p>
        </div>
      </div>

      {socket === "reconnecting" && <div className="mt-3"><Notice kind="error">{es.board.reconnecting}</Notice></div>}
      {socket === "denied" && <div className="mt-3"><Notice kind="error">{es.board.denied}</Notice></div>}

      <ul className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        {COUNTERS.map((k) => (
          <li key={k}><Card className="text-center">
            <p className="figure text-4xl text-teal">{board?.counters[k] ?? "—"}</p>
            <p className="font-bold"><Icon as={COUNTER_ICON[k]} /> {es.board.counters[k]}</p>
          </Card></li>
        ))}
      </ul>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <h2>{es.board.queueTitle}</h2>
          {board && board.queue.length === 0 && <p className="mt-2">{es.board.queueEmpty}</p>}
          <ol className="mt-2 divide-y divide-teal/10">
            {board?.queue.map((q) => (
              <li key={q.request_id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                <span>
                  <strong className={q.priority === "high" ? "text-danger" : ""}>
                    {q.priority === "high" && <><Icon as={AlertTriangle} /> </>}{es.priority[q.priority]}
                  </strong>{" · "}<Link to={`/pacientes/${q.patient_id}`} className="underline decoration-teal/40 hover:text-teal">{q.patient_name}</Link> · {q.service_name} · {formatWhen(q.scheduled_for, board ? new Date(board.now) : undefined)}
                  <span className="block text-muted">
                    {es.board.origin[q.origin] ?? q.origin} · {q.status_reason ? es.statusReason[q.status_reason] : ""}
                  </span>
                </span>
                <span className="flex flex-wrap items-center gap-3">
                  <span className="font-bold tabular-nums">{q.minutes_waiting} {es.common.minutes} {es.board.waiting}</span>
                  {q.status_reason === "awaiting_approval" && (
                    <Link to={`/aprobaciones?solicitud=${encodeURIComponent(q.request_id)}`}
                      className="inline-flex min-h-12 items-center gap-2 rounded-card bg-teal px-4 font-bold text-white hover:bg-teal-dark">
                      <Icon as={CheckCircle2} /> {es.board.reviewApprove}</Link>)}
                </span>
              </li>
            ))}
          </ol>
        </Card>
        <Card>
          <h2>{es.board.alertsTitle}</h2>
          {board && board.alerts.length === 0 && <p className="mt-2">{es.board.alertsEmpty}</p>}
          <ul className="mt-2 space-y-2">
            {board?.alerts.map((a) => a.type === "emergency_review" ? <ReviewAlert key={a.alert_id} a={a} now={now} onDone={refresh} /> : (
              <li key={a.alert_id} className="rounded-card border-2 border-danger p-2">
                <Icon as={AlertTriangle} /> {a.message}
                <span className="block text-muted">{formatWhen(a.created_at, board ? new Date(board.now) : undefined)}</span>
              </li>
            ))}
          </ul>
        </Card>
      </div>

      <div className="mt-4 grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <h2>{es.board.mapTitle}</h2>
          <div className="mt-2">
            <Suspense fallback={<p>{es.common.loading}</p>}>
              <VisitsMap visits={board?.visits ?? []} staff={board?.staff ?? []} />
            </Suspense>
          </div>
          {board && board.visits.length === 0 && <p className="mt-2">{es.board.visitsEmpty}</p>}
          <ul className="mt-3 max-h-60 divide-y divide-teal/10 overflow-y-auto">
            {board?.visits.map((v) => (
              <li key={v.request_id} className="flex flex-wrap items-center justify-between gap-2 py-1">
                <span>{formatWhen(v.scheduled_for, board ? new Date(board.now) : undefined)} · <Link to={`/pacientes/${v.patient_id}`} className="underline decoration-teal/40 hover:text-teal">{v.patient_name}</Link> · {v.caregiver_name ?? es.family.pendingCaregiver}{v.relay_caregiver_name && ` (${relayText(v.relay_caregiver_name, v.relay_at)})`}</span>
                <StatusBadge status={v.status} />
              </li>
            ))}
          </ul>
          <p className="mt-2 text-muted">{es.board.syntheticNote}</p>
        </Card>
        <Card>
          <h2>{es.board.newRequest}</h2>
          <div className="mt-3 space-y-3">
            <RequestForm coordinator onCreated={(r) => { setCreated(r); refresh(); }} />
            {created && <RequestResult r={created} />}
          </div>
        </Card>
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
    <li className="rounded-card border-4 border-danger bg-danger/5 p-3" role="alert">
      <p className="font-bold text-danger"><Icon as={AlertTriangle} /> {es.board.reviewTitle}</p>
      <p className="mt-1">{a.message}</p>
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
