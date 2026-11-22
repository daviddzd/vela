// "Solicitar servicio" form. Family: only service + date (patient and priority come from the API).
// Coordination: also patient id and priority.
import { useEffect, useState, type FormEvent } from "react";
import { api, type Service, type ServiceRequest } from "../api/client";
import { es } from "../i18n/es";
import { localInputValue } from "../lib/format";
import { Button, inputClass } from "./ui";

export function RequestForm({ coordinator = false, onCreated }:
  { coordinator?: boolean; onCreated: (r: ServiceRequest) => void }) {
  const [services, setServices] = useState<Service[]>([]);
  const [serviceId, setServiceId] = useState("");
  const [when, setWhen] = useState(localInputValue(24));
  const [patientId, setPatientId] = useState("");
  const [priority, setPriority] = useState("medium");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.services().then((s) => { setServices(s); setServiceId(s[0]?.service_id ?? ""); }).catch(() => undefined);
  }, []);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      onCreated(await api.createRequest({ service_id: serviceId, scheduled_for: when,
        ...(coordinator ? { patient_id: patientId.trim().toUpperCase(), priority } : {}) }));
    } catch (err) {
      setError((err as Error).message || es.common.error);
    } finally {
      setBusy(false);
    }
  };

  return (
    <form onSubmit={submit} className="space-y-3">
      {coordinator && (
        <label className="block"><span className="font-bold">{es.board.patientId}</span>
          <input required value={patientId} onChange={(e) => setPatientId(e.target.value)} className={inputClass} />
        </label>
      )}
      <label className="block"><span className="font-bold">{es.family.service}</span>
        <select value={serviceId} onChange={(e) => setServiceId(e.target.value)} className={inputClass}>
          {services.map((s) => <option key={s.service_id} value={s.service_id}>{s.name} ({s.duration_min} {es.common.minutes})</option>)}
        </select>
      </label>
      <label className="block"><span className="font-bold">{es.family.when}</span>
        <input type="datetime-local" required value={when} onChange={(e) => setWhen(e.target.value)} className={inputClass} />
      </label>
      {coordinator && (
        <fieldset><legend className="font-bold">{es.board.priority}</legend>
          <div className="mt-1 flex flex-wrap gap-4">
            {["low", "medium", "high"].map((p) => (
              <label key={p} className="flex min-h-12 items-center gap-2">
                <input type="radio" name="priority" value={p} checked={priority === p}
                  onChange={() => setPriority(p)} className="size-6 accent-teal" />{es.priority[p]}
              </label>
            ))}
          </div>
        </fieldset>
      )}
      {error && <p role="alert" className="font-bold text-danger"><span aria-hidden="true">⚠ </span>{error}</p>}
      <Button type="submit" icon="➕" disabled={busy || !serviceId} className="w-full">{es.family.submit}</Button>
    </form>
  );
}
