// /familia — next visit, "Solicitar servicio" and visit confirmation, only for the family's own patient.
import { useCallback, useEffect, useState } from "react";
import { api, type FamilyOverview, type ServiceRequest } from "../api/client";
import { AppShell } from "../components/AppShell";
import { RequestForm } from "../components/RequestForm";
import { RequestResult } from "../components/RequestResult";
import { StatusBadge } from "../components/StatusBadge";
import { Button, Card, Notice } from "../components/ui";
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

  const next = data?.next_visit;
  return (
    <AppShell>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-teal">{data ? `${es.screens["/familia"]}: ${data.patient_name}` : es.screens["/familia"]}</h1>
        <Link to={data ? `/voz?paciente=${encodeURIComponent(data.patient_id)}` : "/voz"}
          className="inline-flex min-h-12 items-center gap-2 rounded-card bg-teal px-4 font-bold text-white hover:bg-teal-dark">
          <Icon as={Mic} /> {es.family.voiceAssistant}</Link>
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-2">
        {error && <div className="lg:col-span-2"><Notice kind="error">{error}</Notice></div>}
        {notice && <div className="lg:col-span-2"><Notice kind="ok">{notice}</Notice></div>}
        {data?.notices.map((n) => (
          <div key={n.created_at} className="lg:col-span-2"><Notice kind="info">{n.message}</Notice></div>))}

        <Card>
          <h2>{es.family.nextVisit}</h2>
          {!data ? <p>{es.common.loading}</p> : !next ? <p className="mt-2">{es.family.noNextVisit}</p> : (
            <div className="mt-2 space-y-1">
              <p className="text-xl font-bold">{formatDateTime(next.scheduled_for)}</p>
              <p>{next.service_name}</p>
              <p><StatusBadge status={next.status} /></p>
              <p>{es.family.caregiver}: <strong>{next.caregiver_name ?? es.family.pendingCaregiver}</strong>
                {next.relay_caregiver_name && ` · ${relayText(next.relay_caregiver_name, next.relay_at)}`}</p>
              {next.status_reason && <p className="text-muted">{es.statusReason[next.status_reason] ?? ""}</p>}
            </div>
          )}
          {data?.to_confirm.map((v) => (
            <div key={v.assignment_id} className="mt-4 border-t border-teal/15 pt-4">
              <p className="font-bold">{es.family.toConfirm}</p>
              <p>{v.service_name} · {formatDateTime(v.scheduled_for)} · {v.caregiver_name}</p>
              <Button icon={ThumbsUp} className="mt-2 w-full" onClick={() => confirm(v.assignment_id!)}>{es.family.confirm}</Button>
            </div>
          ))}
        </Card>

        <Card>
          <h2>{es.family.requestTitle}</h2>
          <div className="mt-3 space-y-3">
            {data && !data.home_care_consent && <Notice kind="error">{es.family.noConsent}</Notice>}
            {data && !data.can_request_services && <Notice kind="error">{es.family.cannotRequest}</Notice>}
            {data?.can_request_services && (
              <RequestForm onCreated={(r) => { setCreated(r); load(); }} />
            )}
            {created && <RequestResult r={created} />}
          </div>
        </Card>

        {data && data.recent_requests.length > 0 && (
          <Card className="lg:col-span-2">
            <h2>{es.family.recent}</h2>
            <ul className="mt-2 divide-y divide-teal/10">
              {data.recent_requests.map((r) => (
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
