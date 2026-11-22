// /tablero — live board for coordination: clock, counters, queue, alerts, map, new request.
// Updates without reloading: every WebSocket event triggers a re-read of /api/board.
import { lazy, Suspense, useCallback, useEffect, useRef, useState } from "react";
import { api, type Board } from "../api/client";
import { AppShell } from "../components/AppShell";
import { RequestForm } from "../components/RequestForm";
import { RequestResult } from "../components/RequestResult";
import { StatusBadge } from "../components/StatusBadge";
import { Card, Notice } from "../components/ui";
import { es } from "../i18n/es";
import { formatClock, formatLongDate, useServerClock } from "../lib/clock";
import { formatTime } from "../lib/format";
import { useBoardSocket } from "../lib/useBoardSocket";
import type { ServiceRequest } from "../api/client";

// MapLibre is large: load it only when the board opens (phones on the family screen never download it).
const VisitsMap = lazy(() => import("../components/VisitsMap").then((m) => ({ default: m.VisitsMap })));

const COUNTERS = ["queued", "on_the_way", "in_visit", "done_today"] as const;
const COUNTER_ICON = { queued: "⏳", on_the_way: "🚗", in_visit: "🏠", done_today: "✅" };

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
          <p className="text-4xl font-bold tabular-nums" aria-live="off">{formatClock(now)}</p>
          {!synced && <p className="text-muted">{es.board.clockUnsynced}</p>}
          <p className="font-bold" aria-live="polite">
            {socket === "live" && <span className="text-ok"><span aria-hidden="true">● </span>{es.board.live}</span>}
            {socket === "connecting" && <span className="text-muted">{es.board.connecting}</span>}
            {socket === "reconnecting" && <span className="text-warn"><span aria-hidden="true">⟳ </span>{es.board.reconnecting}</span>}
          </p>
        </div>
      </div>

      {socket === "reconnecting" && <div className="mt-3"><Notice kind="error">{es.board.reconnecting}</Notice></div>}
      {socket === "denied" && <div className="mt-3"><Notice kind="error">{es.board.denied}</Notice></div>}

      <ul className="mt-4 grid grid-cols-2 gap-3 md:grid-cols-4">
        {COUNTERS.map((k) => (
          <li key={k}><Card className="text-center">
            <p className="text-4xl font-bold text-teal tabular-nums">{board?.counters[k] ?? "—"}</p>
            <p className="font-bold"><span aria-hidden="true">{COUNTER_ICON[k]} </span>{es.board.counters[k]}</p>
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
                    {q.priority === "high" && <span aria-hidden="true">❗ </span>}{es.priority[q.priority]}
                  </strong>{" · "}{q.patient_name} · {q.service_name} · {formatTime(q.scheduled_for)}
                  <span className="block text-muted">
                    {es.board.origin[q.origin] ?? q.origin} · {q.status_reason ? es.statusReason[q.status_reason] : ""}
                  </span>
                </span>
                <span className="font-bold tabular-nums">{q.minutes_waiting} {es.common.minutes} {es.board.waiting}</span>
              </li>
            ))}
          </ol>
        </Card>
        <Card>
          <h2>{es.board.alertsTitle}</h2>
          {board && board.alerts.length === 0 && <p className="mt-2">{es.board.alertsEmpty}</p>}
          <ul className="mt-2 space-y-2">
            {board?.alerts.map((a) => (
              <li key={a.alert_id} className="rounded-card border-2 border-danger p-2">
                <span aria-hidden="true">⚠ </span>{a.message}
                <span className="block text-muted">{formatTime(a.created_at)}</span>
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
                <span>{formatTime(v.scheduled_for)} · {v.patient_name} · {v.caregiver_name ?? es.family.pendingCaregiver}</span>
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
