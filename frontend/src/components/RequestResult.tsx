// Shows what happened to a new request: assigned, waiting for approval, or why it was rejected.
import type { ServiceRequest } from "../api/client";
import { es } from "../i18n/es";
import { formatDateTime } from "../lib/format";
import { StatusBadge } from "./StatusBadge";

export function RequestResult({ r }: { r: ServiceRequest }) {
  return (
    <div role="status" className="rounded-card border-2 border-teal bg-white p-3">
      <p className="flex flex-wrap items-center gap-2 font-bold">{r.request_id} <StatusBadge status={r.status} /></p>
      <p>{r.service_name} · {formatDateTime(r.scheduled_for)}</p>
      {r.caregiver_name && <p>{es.family.caregiver}: <strong>{r.caregiver_name}</strong></p>}
      {r.status_reason && <p className="text-muted">{es.statusReason[r.status_reason] ?? r.status_reason}</p>}
    </div>
  );
}
