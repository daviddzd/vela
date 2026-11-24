// /aprobaciones — high-priority requests: proposed caregiver + 2 alternatives; coordination approves.
import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, type Approval, type Option } from "../api/client";
import { AppShell } from "../components/AppShell";
import { Button, Card, Notice } from "../components/ui";
import { AlertTriangle, CheckCircle2, Icon, Star } from "../components/icons";
import { es } from "../i18n/es";
import { formatDateTime, formatTime } from "../lib/format";
import { relayText } from "../lib/relay";

export function ApprovalsPage() {
  const [items, setItems] = useState<Approval[] | null>(null);
  const [message, setMessage] = useState<{ kind: "ok" | "error" | "info"; text: string } | null>(null);
  const [busy, setBusy] = useState("");
  // opened from the board's "Revisar y aprobar": /aprobaciones?solicitud=REQ-… brings that proposal into view
  const wanted = new URLSearchParams(location.search).get("solicitud");
  const shown = useRef(false);
  useEffect(() => {
    if (!wanted || shown.current || !items) return;
    const card = document.getElementById(`aprobacion-${wanted}`);
    if (card) { card.scrollIntoView({ block: "start" }); card.querySelector("h2")?.focus(); shown.current = true; }
    else if (!items.some((i) => i.request_id === wanted)) setMessage({ kind: "info", text: es.approvals.alreadyDecided });
  }, [items, wanted]);

  const load = useCallback(() => {
    api.approvals().then(setItems).catch(() => setMessage({ kind: "error", text: es.common.error }));
  }, []);
  useEffect(() => {
    load();
    const t = setInterval(load, 15000);   // the live WebSocket board replaces this in step 4
    return () => clearInterval(t);
  }, [load]);

  const approve = async (item: Approval, option: Option) => {
    setBusy(item.request_id);
    setMessage(null);
    try {
      await api.approve(item.request_id, option.caregiver_id);
      setMessage({ kind: "ok", text: `${es.approvals.approved} ${item.request_id}: ${option.caregiver_name}` });
    } catch (err) {
      const recalculated = err instanceof ApiError && err.status === 409 && Array.isArray(err.body.options);
      setMessage({ kind: recalculated ? "info" : "error", text: recalculated ? es.approvals.recalculated : (err as Error).message || es.common.error });
    } finally {
      setBusy("");
      load();
    }
  };

  return (
    <AppShell>
      <h1 className="text-navy">{es.screens["/aprobaciones"]}</h1>
      <div className="mt-4 space-y-4">
        {message && <Notice kind={message.kind}>{message.text}</Notice>}
        {items === null && <p>{es.common.loading}</p>}
        {items?.length === 0 && <Card>{es.approvals.empty}</Card>}
        {items?.map((item) => (
          <div key={item.request_id} id={`aprobacion-${item.request_id}`}
            className={`scroll-mt-4 rounded-card ${item.request_id === wanted ? "ring-4 ring-navy" : ""}`}><Card>
            <div className="flex flex-wrap items-baseline justify-between gap-2">
              <h2 tabIndex={-1}>{item.patient_name}</h2>
              <span className="font-bold text-danger"><Icon as={AlertTriangle} /> {es.priority.high}</span>
            </div>
            <p>{item.service_name} · {es.approvals.scheduledFor}: <strong>{formatDateTime(item.scheduled_for)}</strong></p>
            <p className="text-muted">{item.request_id} · {es.approvals.waiting} {item.minutes_waiting} {es.common.minutes}</p>
            {item.options.length === 0 ? (
              <div className="mt-3"><Notice>{es.approvals.noOptions}</Notice></div>
            ) : (
              <ul className="mt-3 grid gap-3 md:grid-cols-3">
                {item.options.map((o) => (
                  <li key={o.caregiver_id} className={`rounded-card border-2 p-3 ${o.rank === 1 ? "border-navy" : "border-muted/40"}`}>
                    <p className="font-bold">{o.rank === 1 ? <><Icon as={Star} /> {es.approvals.proposed}</> : es.approvals.alternative}</p>
                    <p>{o.caregiver_name}</p>
                    {o.relay_caregiver_name && <p>{relayText(o.relay_caregiver_name, o.relay_at)}</p>}
                    <p className="text-muted">{es.common.travel}: {Math.round(o.travel_min)} {es.common.minutes} · {es.common.leaves} {formatTime(o.planned_start)}</p>
                    <Button className="mt-2 w-full" icon={CheckCircle2} variant={o.rank === 1 ? "primary" : "secondary"}
                      disabled={busy === item.request_id} onClick={() => approve(item, o)}>
                      {es.approvals.approve}
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </Card></div>
        ))}
      </div>
    </AppShell>
  );
}
