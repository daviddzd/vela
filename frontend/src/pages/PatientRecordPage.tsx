// /pacientes/:id — the record. Same scope and consent rules as the API (which also writes the read to audit_log):
// health conditions and risk only with a valid health_data consent; voice content only for the physician.
// Physician: adjusts the care plan (service and frequency). Coordination: creates a request for this person.
import { ArrowLeft, Pencil, Plus, Square } from "lucide-react";
import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Link, useParams } from "react-router";
import { api, ApiError } from "../api/client";
import { AppShell } from "../components/AppShell";
import { Icon } from "../components/icons";
import { RequestForm } from "../components/RequestForm";
import { StatusBadge } from "../components/StatusBadge";
import { Button, Card, inputClass, Notice } from "../components/ui";
import { es } from "../i18n/es";
import { RiskBadge } from "./PatientsPage";

const t = es.record;
const fill = (s: string, v: Record<string, string | number>) => s.replace(/\{(\w+)\}/g, (_, k) => String(v[k] ?? ""));
const dmy = (iso?: string | null) => (iso ? iso.slice(0, 10).split("-").reverse().join("/") : "—");
const when = (iso: string) => new Date(iso).toLocaleString("es-MX", { timeZone: "America/Mexico_City", dateStyle: "short", timeStyle: "short" });

export function PatientRecordPage() {
  const { id = "" } = useParams();
  const [r, setR] = useState<any>(null);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");
  const load = useCallback(() => {
    api.patientRecord(id).then(setR).catch((e) => setError(e instanceof ApiError ? e.message : es.common.error));
  }, [id]);
  useEffect(load, [load]);

  if (error) return <AppShell><BackLink /><Notice kind="error">{error}</Notice></AppShell>;
  if (!r) return <AppShell><p>{es.common.loading}</p></AppShell>;
  const h = r.health;
  return (
    <AppShell>
      <BackLink />
      <h1 className="mt-2 text-teal">{r.full_name} <span className="text-xl text-muted">· {r.patient_id}</span></h1>
      <p className="mt-1"><RiskBadge level={r.risk_level} /></p>
      {msg && <div className="mt-3"><Notice kind="ok">{msg}</Notice></div>}

      <div className="mt-4 grid gap-4 xl:grid-cols-3">
        <Card>
          <h2 className="text-teal">{t.general}</h2>
          <dl className="mt-2 grid grid-cols-[auto_1fr] gap-x-4 gap-y-1">
            <dt className="text-muted">{t.ageLabel}</dt><dd>{fill(es.patients.age, { n: r.age })} · {t.sex[r.sex]}</dd>
            <dt className="text-muted">{es.patients.district}</dt><dd>{r.district_name}</dd>
            <dt className="text-muted">{t.institution}</dt><dd>{r.institution_name}</dd>
            <dt className="text-muted">{t.admission}</dt><dd>{dmy(r.admission_date)}</dd>
            <dt className="text-muted">{es.patients.priority}</dt><dd>{es.priority[r.base_priority]}</dd>
          </dl>
        </Card>
        <Card>
          <h2 className="text-teal">{t.health}</h2>
          {!h ? <p className="mt-2 font-bold text-muted">{r.health_notice}</p> : (<>
            <p className="mt-2">{h.conditions.length ? h.conditions.map((c: string) => t.conditionNames[c] ?? c).join(", ") : t.noConditions}</p>
            <p className="mt-1 text-sm">{fill(t.chronic, { n: h.chronic_disease_count })}{h.multimorbidity ? ` · ${t.multimorbidity}` : ""}</p>
            <p className="mt-1 text-sm">{t.dependencyLabel}: {es.patients.dependencyLevels[h.dependency_level]} · {t.cognitiveLabel}: {es.patients.cognitive[h.cognitive_status]}</p>
            {h.pollution_sensitive && <p className="mt-1 text-sm font-bold">{t.sensitiveYes}</p>}
            <p className="mt-2 text-sm text-muted">{es.patients.riskNote}</p>
          </>)}
        </Card>
        <Card>
          <h2 className="text-teal">{t.consents}</h2>
          <ul className="mt-2 space-y-1">{r.consents.map((c: any) => {
            const st = c.revoked_at ? "revoked" : !c.granted ? "missing" : c.is_valid ? "valid" : "expired";
            return <li key={c.type}><strong>{es.privacy.types[c.type]}:</strong> {es.privacy.state[st]} · {fill(es.privacy.fromTo, { from: dmy(c.signed_on), to: dmy(c.expires_on) })}</li>;
          })}</ul>
          {r.can_request && <Link to="/privacidad" className="mt-2 inline-block font-bold text-teal underline">{t.manageConsents}</Link>}
        </Card>
      </div>

      <Plans r={r} onChange={(text) => { setMsg(text); load(); }} />

      <div className="mt-4 grid gap-4 xl:grid-cols-[2fr_1fr]">
        <Card>
          <h2 className="text-teal">{t.history}</h2>
          {r.history.length === 0 ? <p className="mt-2">{t.noHistory}</p> : (
            <ul className="mt-2 divide-y divide-teal/10">{r.history.map((x: any) => (
              <li key={x.request_id} className="flex flex-wrap items-start justify-between gap-2 py-2">
                <span><strong>{when(x.scheduled_for)}</strong> · {x.service_name}
                  <span className="block text-sm text-muted">{x.request_id} · {t.origin[x.origin] ?? x.origin}
                    {x.caregiver_name && ` · ${x.caregiver_name}`}{x.approval && ` (${t.approval[x.approval]})`}
                    {x.status_reason && ` · ${es.statusReason[x.status_reason] ?? x.status_reason}`}</span></span>
                <StatusBadge status={x.status} />
              </li>))}</ul>)}
        </Card>
        <div className="space-y-4">
          {r.can_request && (
            <Card>
              <h2 className="text-teal">{t.request}</h2>
              <div className="mt-2"><RequestForm coordinator patient={r.patient_id}
                onCreated={(x) => { setMsg(fill(t.requestCreated, { id: x.request_id, status: es.requestStatus[x.status] ?? x.status })); load(); }} /></div>
            </Card>)}
          <Card>
            <h2 className="text-teal">{t.voice}</h2>
            {r.voice_reports.length === 0 ? <p className="mt-2">{t.noVoice}</p> : (
              <ul className="mt-2 space-y-2">{r.voice_reports.map((v: any) => (
                <li key={v.report_id} className="border-t border-teal/10 pt-2">
                  <strong>{es.voice.levels[v.triage_label]}</strong> · {when(v.created_at)} · {v.reviewed_at ? t.reviewed : t.unreviewed}
                  {v.transcript ? <p className="text-sm">«{v.transcript}»</p> : <p className="text-sm text-muted">{t.voiceHidden}</p>}
                </li>))}</ul>)}
          </Card>
          <Card>
            <h2 className="text-teal">{t.family}</h2>
            <ul className="mt-2 space-y-1">{r.family.map((f: any) => (
              <li key={f.family_member_id}><strong>{f.name}</strong> · {t.relationship[f.relationship] ?? f.relationship}
                {f.is_legal_representative && ` · ${t.legalRep}`}{f.can_request_services && ` · ${t.canRequest}`}
                {f.email && <span className="block text-sm text-muted">{f.email}</span>}</li>))}</ul>
          </Card>
        </div>
      </div>
    </AppShell>
  );
}

function BackLink() {
  return <Link to="/pacientes" className="inline-flex min-h-12 items-center gap-2 font-bold text-teal"><Icon as={ArrowLeft} /> {t.back}</Link>;
}

function Plans({ r, onChange }: { r: any; onChange: (msg: string) => void }) {
  const [editing, setEditing] = useState<string | null>(null);      // plan id, "new" or null
  const done = (x: any) => { setEditing(null); onChange(fill(t.planSaved, { c: x.cancelled.length, a: x.assigned.length })); };
  return (
    <Card className="mt-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-teal">{t.plan}</h2>
        {r.can_edit_plan && editing === null && <Button icon={Plus} variant="secondary" onClick={() => setEditing("new")}>{t.addPlan}</Button>}
      </div>
      {r.can_edit_plan && <p className="mt-1 text-sm text-muted">{t.planNote}</p>}
      {editing === "new" && <PlanForm r={r} onDone={done} onCancel={() => setEditing(null)} />}
      <ul className="mt-2 divide-y divide-teal/10">{r.care_plans.map((p: any) => (
        <li key={p.care_plan_id} className={`py-2 ${p.active ? "" : "text-muted"}`}>
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span><strong>{p.service_name}</strong> · {p.times_per_week === 1 ? t.perWeekOne : fill(t.perWeek, { n: p.times_per_week.toLocaleString("es-MX", { maximumFractionDigits: 2 }) })}
              <span className="block text-sm">{p.reason} · {p.active ? t.planActive : `${t.planEnded} ${dmy(p.ended_at)}`}
                {p.replaces && ` · ${fill(t.planReplaces, { id: p.replaces })}`}</span></span>
            {r.can_edit_plan && p.active && editing === null && (
              <span className="flex gap-2">
                <Button variant="secondary" icon={Pencil} onClick={() => setEditing(p.care_plan_id)}>{t.changePlan}</Button>
                <Button variant="secondary" icon={Square} onClick={async () => {
                  if (window.confirm(t.confirmEnd)) done(await api.endPlan(r.patient_id, p.care_plan_id));
                }}>{t.endPlan}</Button>
              </span>)}
          </div>
          {editing === p.care_plan_id && <PlanForm r={r} plan={p} onDone={done} onCancel={() => setEditing(null)} />}
        </li>))}</ul>
    </Card>
  );
}

function PlanForm({ r, plan, onDone, onCancel }: { r: any; plan?: any; onDone: (x: any) => void; onCancel: () => void }) {
  const [f, setF] = useState({ service_id: plan?.service_id ?? r.services[0]?.service_id ?? "", times_per_week: plan?.times_per_week ?? 1, reason: "" });
  const [error, setError] = useState("");
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      onDone(plan ? await api.changePlan(r.patient_id, plan.care_plan_id, f) : await api.addPlan(r.patient_id, f));
    } catch (err) { setError(err instanceof ApiError ? err.message : es.common.error); }
  };
  return (
    <form onSubmit={submit} className="mt-3 grid gap-3 rounded-card border border-teal/20 p-3 md:grid-cols-4">
      <label className="block md:col-span-2"><span className="font-bold">{t.service}</span>
        <select className={inputClass} value={f.service_id} onChange={(e) => setF({ ...f, service_id: e.target.value })}>
          {r.services.map((s: any) => <option key={s.service_id} value={s.service_id}>{s.name}</option>)}</select></label>
      <label className="block"><span className="font-bold">{t.timesPerWeek}</span>
        <input type="number" min={0.25} max={14} step={0.25} required className={inputClass} value={f.times_per_week}
          onChange={(e) => setF({ ...f, times_per_week: Number(e.target.value) })} /></label>
      <label className="block md:col-span-4"><span className="font-bold">{t.reason}</span>
        <input className={inputClass} required minLength={3} maxLength={200} value={f.reason} onChange={(e) => setF({ ...f, reason: e.target.value })} /></label>
      {error && <div className="md:col-span-4"><Notice kind="error">{error}</Notice></div>}
      <div className="flex gap-2 md:col-span-4">
        <Button type="submit">{t.save}</Button>
        <Button variant="secondary" onClick={onCancel}>{t.cancel}</Button>
      </div>
    </form>
  );
}
