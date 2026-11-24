// "Solicitar servicio" form. Family: only service + date (patient and priority come from the API).
// Coordination: also patient id and priority.
import { useEffect, useState, type FormEvent } from "react";
import { api, type Service, type ServiceRequest } from "../api/client";
import { es } from "../i18n/es";
import { localInputValue } from "../lib/format";
import { DateField } from "./DateField";
import { AlertTriangle, Icon, Plus } from "./icons";
import { Button, ChoiceList, inputClass } from "./ui";

/** "30 min", "1 h", "12 h": how long the visit lasts, under the service name. */
const duration = (min: number) => (min % 60 === 0 ? `${min / 60}\u00a0h` : `${min}\u00a0${es.common.minutes}`);

const TIMES = Array.from({ length: (22 - 7) * 4 }, (_, i) =>
  `${String(7 + Math.floor(i / 4)).padStart(2, "0")}:${String((i % 4) * 15).padStart(2, "0")}`);

export function RequestForm({ coordinator = false, onCreated, patient }:
  { coordinator?: boolean; onCreated: (r: ServiceRequest) => void; patient?: string }) {
  const [services, setServices] = useState<Service[]>([]);
  const [serviceId, setServiceId] = useState("");
  // Date (dd/mm/aaaa) + time in 15-min steps, both in Mexico City time. Default: tomorrow at 10:00.
  const [day, setDay] = useState(localInputValue(24).slice(0, 10));
  const [time, setTime] = useState("10:00");
  const when = `${day}T${time}`;
  const [patientId, setPatientId] = useState(patient ?? "");   // fixed when opened from a patient record
  const [priority, setPriority] = useState("medium");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.services().then((s) => { setServices(s); setServiceId(s[0]?.service_id ?? ""); }).catch(() => undefined);
  }, []);

  // a date or time that already passed is stopped here, before anything is sent (no "No procede" request)
  const past = !!day && when < localInputValue(0);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    if (past) return;
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
      {coordinator && !patient && (
        <label className="block"><span className="font-bold">{es.board.patientId}</span>
          <input required value={patientId} onChange={(e) => setPatientId(e.target.value)} className={inputClass} />
        </label>
      )}
      <ChoiceList legend={es.family.service} name="service" value={serviceId} onChange={setServiceId}
        options={services.map((s) => ({ value: s.service_id, title: s.name, detail: duration(s.duration_min) }))} />
      <fieldset className="flex flex-wrap items-start gap-3">
        <legend className="sr-only">{es.family.when}</legend>
        <DateField label={es.family.when} value={day} onChange={setDay} required error={past ? es.family.pastDate : undefined} />
        <label className="block"><span className="font-bold">{es.dates.time}</span>
          <select value={time} onChange={(e) => setTime(e.target.value)} className={`${inputClass} w-32`}>
            {TIMES.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>
      </fieldset>
      {coordinator && (
        <fieldset><legend className="font-bold">{es.board.priority}</legend>
          <div className="mt-1 flex flex-wrap gap-4">
            {["low", "medium", "high"].map((p) => (
              <label key={p} className="flex min-h-12 items-center gap-2">
                <input type="radio" name="priority" value={p} checked={priority === p}
                  onChange={() => setPriority(p)} className="size-6 accent-navy" />{es.priority[p]}
              </label>
            ))}
          </div>
        </fieldset>
      )}
      {error && <p role="alert" className="font-bold text-danger"><Icon as={AlertTriangle} /> {error}</p>}
      <Button type="submit" icon={Plus} disabled={busy || !serviceId} className="w-full">{es.family.submit}</Button>
    </form>
  );
}
