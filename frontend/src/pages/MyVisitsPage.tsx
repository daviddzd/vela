// /mis-visitas — today's agenda for a caregiver, with big "Llegué" / "Terminé" buttons.
import { useCallback, useEffect, useState } from "react";
import { api, type Visit } from "../api/client";
import { AppShell } from "../components/AppShell";
import { StatusBadge } from "../components/StatusBadge";
import { Button, Card, Notice } from "../components/ui";
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

  const load = useCallback(() => {
    api.myVisits().then(setVisits).catch(() => setError(es.common.error));
  }, []);
  useEffect(load, [load]);

  const step = async (fn: (id: string) => Promise<unknown>, id: string) => {
    setError("");
    try {
      await fn(id);
    } catch (err) {
      setError((err as Error).message || es.common.error);
    }
    load();
  };

  return (
    <AppShell>
      <h1 className="text-teal">{es.screens["/mis-visitas"]}</h1>
      <div className="mt-4 space-y-4">
        {error && <Notice kind="error">{error}</Notice>}
        {visits === null && <p>{es.common.loading}</p>}
        {visits?.length === 0 && <Card>{es.visits.empty}</Card>}
        {visits?.map((v) => (
          <Card key={v.assignment_id}>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2>{formatTime(v.scheduled_for)} · {v.patient_name}</h2>
              <StatusBadge status={v.status} />
            </div>
            <p>{v.service_name}</p>
            <p className="text-muted">{es.visits.district}: {v.district_name} · {es.common.leaves} {formatTime(v.planned_start)} ({Math.round(v.travel_min)} {es.common.minutes})</p>
            <div className="mt-4 grid gap-3 sm:grid-cols-3">
              <Button icon={Navigation} className="min-h-16 text-xl" disabled={v.status !== "assigned"}
                onClick={() => step(api.arrive, v.assignment_id)}>{es.visits.arrived}</Button>
              <Button icon={CheckCircle2} className="min-h-16 text-xl" disabled={v.status !== "in_progress"}
                onClick={() => step(api.finish, v.assignment_id)}>{es.visits.finished}</Button>
              {/* only caregivers use the voice assistant (/voz); physicians record in their own notes */}
              {user?.role === "caregiver" && (
                <Link to={`/voz?paciente=${encodeURIComponent(v.patient_id)}`} aria-label={fill(es.visits.voiceNoteFor, { name: v.patient_name })}
                  className="inline-flex min-h-16 items-center justify-center gap-2 rounded-card border-2 border-teal bg-white px-4 font-bold text-teal hover:bg-teal/10">
                  <Icon as={Mic} /> {es.visits.voiceNote}</Link>)}
            </div>
          </Card>
        ))}
      </div>
    </AppShell>
  );
}
