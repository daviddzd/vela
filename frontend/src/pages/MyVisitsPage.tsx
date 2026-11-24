// /mis-visitas — today's agenda for a caregiver, with big "Llegué" / "Terminé" buttons.
import { useCallback, useEffect, useState } from "react";
import { api, ApiError, type Visit } from "../api/client";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { Button, Card, Notice, PageHeader } from "../components/ui";
import { CheckCircle2, Icon, Mic, Navigation } from "../components/icons";
import { Link } from "react-router";
import { useAuth } from "../auth/AuthContext";
import { es } from "../i18n/es";
import { formatTime } from "../lib/format";

const fill = (s: string, v: Record<string, string>) => s.replace(/\{(\w+)\}/g, (_, k) => v[k] ?? "");

export function MyVisitsPage() {
  const { user } = useAuth();
  const [visits, setVisits] = useState<Visit[] | null>(null);
  const [error, setError] = useState("");
  const [confirming, setConfirming] = useState<{ id: string; text: string } | null>(null);   // "¿Seguro? …"
  const [now, setNow] = useState(Date.now());
  useEffect(() => { const t = setInterval(() => setNow(Date.now()), 30_000); return () => clearInterval(t); }, []);

  const load = useCallback(() => {
    api.myVisits().then(setVisits).catch(() => setError(es.common.error));
  }, []);
  useEffect(load, [load]);

  const step = async (fn: (id: string) => Promise<unknown>, id: string) => {
    setError("");
    setConfirming(null);
    try {
      await fn(id);
    } catch (err) {
      // the API asks to confirm a "Terminé" before half of the visit: show the question, nothing was saved
      if (err instanceof ApiError && err.body?.needs_confirmation) setConfirming({ id, text: err.message });
      else setError((err as Error).message || es.common.error);
    }
    load();
  };
  // "Terminé" before half of the visit asks first (same rule as the API: operations.early_finish)
  const finish = (v: Visit) => {
    const onSite = v.arrived_at ? (now - new Date(v.arrived_at).getTime()) / 60000 : Infinity;
    if (v.expected_min && onSite < v.expected_min / 2) {
      setConfirming({ id: v.assignment_id, text: fill(es.visits.confirmFinish, { n: String(v.expected_min) }) });
    } else step((id) => api.finish(id), v.assignment_id);
  };

  const tooEarly = (v: Visit) => !!v.arrive_from && now < new Date(v.arrive_from).getTime();

  return (
    <AppShell>
      <PageHeader title={es.pageTitles["/mis-visitas"]} />
      <div className="mt-4 space-y-4">
        {error && <Notice kind="error">{error}</Notice>}
        {visits === null && <p>{es.common.loading}</p>}
        {visits?.length === 0 && <Card>{es.visits.empty}</Card>}
        {visits?.map((v) => (
          <Card key={v.assignment_id}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2>{formatTime(v.relay_role === "relay" ? v.relay_at : v.scheduled_for)} · {v.patient_name}</h2>
              <StatusBadge status={v.status} />
            </div>
            <p>{v.service_name}</p>
            {v.relay_role && v.relay_at && (
              <p className="font-bold">{fill(v.relay_role === "first" ? es.visits.relayFirst : es.visits.relayRelay,
                { name: v.relay_partner_name ?? "", time: formatTime(v.relay_at) })}</p>)}
            {v.step === "wait" && v.relay_role === "relay" && <p>{fill(es.visits.waitFirst, { name: v.relay_partner_name ?? "" })}</p>}
            <p className="text-muted">{es.visits.district}: {v.district_name} · {es.common.leaves} {formatTime(v.planned_start)} ({Math.round(v.travel_min)} {es.common.minutes})</p>
            {v.step === "arrive" && tooEarly(v) && v.arrive_from && (
              <p className="mt-2 font-bold">{fill(es.visits.arriveFrom, { time: formatTime(v.arrive_from) })}</p>)}
            {confirming?.id === v.assignment_id && (
              <div role="alertdialog" aria-labelledby={`confirm-${v.assignment_id}`} className="mt-3 rounded-card border-2 border-warn p-3">
                <p id={`confirm-${v.assignment_id}`} className="font-bold">{confirming.text}</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  <Button icon={CheckCircle2} onClick={() => step((id) => api.finish(id, true), v.assignment_id)}>{es.visits.confirmYes}</Button>
                  <Button variant="secondary" onClick={() => setConfirming(null)}>{es.visits.confirmNo}</Button>
                </div>
              </div>)}
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <Button icon={Navigation} className="min-h-16 text-xl" disabled={v.step !== "arrive" || tooEarly(v)}
                onClick={() => step(api.arrive, v.assignment_id)}>{es.visits.arrived}</Button>
              <Button icon={CheckCircle2} className="min-h-16 text-xl" disabled={v.step !== "finish"}
                onClick={() => finish(v)}>{es.visits.finished}</Button>
              {/* only caregivers use the voice assistant (/voz); physicians record in their own notes */}
              {user?.role === "caregiver" && (
                <Link to={`/voz?paciente=${encodeURIComponent(v.patient_id)}`} aria-label={fill(es.visits.voiceNoteFor, { name: v.patient_name })}
                  className="inline-flex min-h-16 items-center justify-center gap-2 rounded-full border-2 border-navy bg-white px-4 font-bold text-navy hover:bg-navy/10">
                  <Icon as={Mic} /> {es.visits.voiceNote}</Link>)}
            </div>
          </Card>
        ))}
      </div>
    </AppShell>
  );
}
