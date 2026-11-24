// /familia — next visit, "Solicitar servicio" and visit confirmation, only for the family's own patient.
import { useCallback, useEffect, useState } from "react";
import { api, type FamilyOverview, type ServiceRequest } from "../api/client";
import { AppShell } from "../components/AppShell";
import { RequestForm } from "../components/RequestForm";
import { RequestResult } from "../components/RequestResult";
import { StatusBadge } from "../components/StatusBadge";
import { Button, Card, IconCircle, Notice, PageHeader } from "../components/ui";
import { CalendarClock, History, Plus } from "lucide-react";
import { Icon, Mic, ThumbsUp } from "../components/icons";
import { Link } from "react-router";
import { es } from "../i18n/es";
import { formatDateTime } from "../lib/format";
import { relayText } from "../lib/relay";

export function FamilyPage() {
  const [data, setData] = useState<FamilyOverview | null>(null);
  const [created, setCreated] = useState<ServiceRequest | null>(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const load = useCallback(() => {
    api.familyOverview().then(setData).catch(() => setError(es.common.error));
  }, []);
  useEffect(load, [load]);

  const confirm = async (id: string) => {
    try {
      await api.confirmVisit(id);
      setNotice(es.family.confirmed);
    } catch (err) {
      setError((err as Error).message || es.common.error);
    }
    load();
  };

  return (
    <AppShell>
      <PageHeader title={data ? es.pageTitles.family.replace("{name}", data.patient_name) : es.screens["/familia"]}
        actions={<Link to={data ? `/voz?paciente=${encodeURIComponent(data.patient_id)}` : "/voz"}
          className="inline-flex min-h-12 items-center gap-2 rounded-full bg-navy px-6 font-bold text-white shadow-sm hover:bg-navy-dark">
          <Icon as={Mic} /> {es.family.voiceAssistant}</Link>}>
        <p>{es.family.headerNote}</p>
      </PageHeader>
      <div className="items-start grid gap-4 lg:grid-cols-2">
        {error && <div className="lg:col-span-2"><Notice kind="error">{error}</Notice></div>}
        {notice && <div className="lg:col-span-2"><Notice kind="ok">{notice}</Notice></div>}
        {data?.notices.map((n) => (
          <div key={n.created_at} className="lg:col-span-2"><Notice kind="info">{n.message}</Notice></div>))}

        <Card>
          <h2 className="flex items-center gap-3"><IconCircle icon={CalendarClock} /> {es.family.upcomingTitle}</h2>
          <p className="text-sm text-muted">{es.family.upcomingNote}</p>
          {!data ? <p>{es.common.loading}</p> : data.upcoming.length === 0 ? <p className="mt-2">{es.family.upcomingNone}</p> : (
            <ul className="mt-2 divide-y divide-navy/10">{data.upcoming.map((v, i) => (
              <li key={v.request_id ?? `${v.scheduled_for}-${i}`} className="py-2">
                <p className={i === 0 ? "text-xl font-bold" : "font-bold"}>{formatDateTime(v.scheduled_for)}</p>
                <p>{v.service_name}</p>
                {v.status === "planned"
                  ? <p className="text-muted"><Icon as={CalendarClock} /> {es.family.plannedNote}</p>
                  : <p className="flex flex-wrap items-center gap-2"><StatusBadge status={v.status} />
                      <span>{es.family.caregiver}: <strong>{v.caregiver_name ?? es.family.pendingCaregiver}</strong>
                        {v.relay_caregiver_name && ` · ${relayText(v.relay_caregiver_name, v.relay_at)}`}</span></p>}
              </li>))}</ul>
          )}
          {data?.to_confirm.map((v) => (
            <div key={v.assignment_id} className="mt-4 border-t border-navy/15 pt-4">
              <p className="font-bold">{es.family.toConfirm}</p>
              <p>{v.service_name} · {formatDateTime(v.scheduled_for)} · {v.caregiver_name}</p>
              <Button icon={ThumbsUp} className="mt-2 w-full" onClick={() => confirm(v.assignment_id!)}>{es.family.confirm}</Button>
            </div>
          ))}
        </Card>

        <Card>
          <h2 className="flex items-center gap-3"><IconCircle icon={Plus} /> {es.family.requestTitle}</h2>
          <div className="mt-3 space-y-3">
            {data && !data.home_care_consent && <Notice kind="error">{es.family.noConsent}</Notice>}
            {data && !data.can_request_services && <Notice kind="error">{es.family.cannotRequest}</Notice>}
            {data?.can_request_services && (
              <RequestForm onCreated={(r) => { setCreated(r); load(); }} />
            )}
            {created && <RequestResult r={created} />}
          </div>
        </Card>

        {data && data.last_visits.length > 0 && (
          <Card className="lg:col-span-2">
            <h2 className="flex items-center gap-3"><IconCircle icon={History} /> {es.family.lastVisits}</h2>
            <ul className="mt-2 divide-y divide-navy/10">
              {data.last_visits.map((r) => (
                <li key={r.request_id} className="flex flex-wrap items-center justify-between gap-2 py-2">
                  <span>{formatDateTime(r.scheduled_for)} · {r.service_name}</span>
                  <StatusBadge status={r.status} />
                </li>
              ))}
            </ul>
          </Card>
        )}
      </div>
    </AppShell>
  );
}
