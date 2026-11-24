// Dirección: what coordination did not answer in time (voice review alerts, escalated by the worker after
// classifier_only.escalate_after_minutes) and emergencies confirmed by coordination. Shown on every screen of the
// owner, above the content, until someone records the family contact or Dirección presses "Enterado".
import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { es } from "../i18n/es";
import { formatWhen } from "../lib/format";
import { useBoardSocket } from "../lib/useBoardSocket";
import { AlertTriangle, CheckCircle2, Icon } from "./icons";
import { Button } from "./ui";

const t = es.escalated;

export function EscalatedAlerts() {
  const [items, setItems] = useState<any[]>([]);
  const [error, setError] = useState("");
  const load = useCallback(() => { api.escalatedAlerts().then(setItems).catch(() => undefined); }, []);
  useEffect(() => { load(); const id = setInterval(load, 30_000); return () => clearInterval(id); }, [load]);
  useBoardSocket(() => load());
  const act = async (fn: () => Promise<unknown>) => {
    setError("");
    try { await fn(); } catch (err) { setError((err as Error).message || es.common.error); }
    load();
  };
  if (!items.length) return null;
  return (
    <section role="alert" aria-label={t.title} className="mb-4 rounded-card border-4 border-danger bg-white p-4">
      <h2 className="text-danger"><Icon as={AlertTriangle} /> {t.title}</h2>
      <ul className="mt-2 space-y-3">{items.map((a) => (
        <li key={a.alert_id} className="rounded-card border-2 border-danger/40 p-3">
          <p className="font-bold">{a.institution_name ?? a.institution_id} · {a.type === "emergency_review" ? t.unanswered : t.confirmed}</p>
          <p>{a.message}</p>
          <p className="text-sm text-muted">{t.since} {formatWhen(a.escalated_at)}</p>
          <div className="mt-2 flex flex-wrap gap-2">
            {a.type === "emergency_review" ? (<>
              <Button icon={AlertTriangle} className="bg-danger! hover:bg-danger/90!" onClick={() => act(() => api.reviewAlert(a.alert_id, "emergency"))}>{es.board.reviewWasEmergency}</Button>
              <Button variant="secondary" onClick={() => act(() => api.reviewAlert(a.alert_id, "not_emergency"))}>{es.board.reviewNotEmergency}</Button>
            </>) : <Button variant="secondary" icon={CheckCircle2} onClick={() => act(() => api.acknowledgeAlert(a.alert_id))}>{t.acknowledge}</Button>}
          </div>
        </li>))}</ul>
      {error && <p className="mt-2 font-bold text-danger">{error}</p>}
    </section>
  );
}
