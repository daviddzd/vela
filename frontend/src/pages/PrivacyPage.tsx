// /privacidad — privacy notice (everyone), consents with their validity (coordination registers / revokes),
// ARCO rights form, and for dirección the audit trail with filters and a summary of blocked attempts.
// The API decides who sees what; this page only shows the tabs that make sense for the role.
import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from "react";
import { api, ApiError } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { EChart, esc } from "../charts/EChart";
import { axisCommon, baseOption, chart } from "../charts/theme";
import { AppShell } from "../components/AppShell";
import { ChartCard } from "../components/ChartCard";
import { DateField } from "../components/DateField";
import { AlertTriangle, Ban, CheckCircle2, Icon } from "../components/icons";
import { Button, Card, inputClass, Notice } from "../components/ui";
import { es } from "../i18n/es";
import { auditDetail, auditEntity } from "../lib/auditText";
import { formatShortDateTime } from "../lib/format";
import { useBoardSocket } from "../lib/useBoardSocket";

const t = es.privacy;
const fill = (s: string, v: Record<string, string | number>) => s.replace(/\{(\w+)\}/g, (_, k) => String(v[k] ?? ""));
const dmy = (iso?: string | null) => (iso ? iso.slice(0, 10).split("-").reverse().join("/") : "—");
const when = formatShortDateTime;
const TYPES = ["health_data", "home_care", "voice_assistant"];

type Tab = "notice" | "consents" | "arco" | "audit";

export function PrivacyPage() {
  const { user } = useAuth();
  const role = user?.role ?? "";
  const tabs: Tab[] = ["notice", ...(["coordinator", "physician", "family"].includes(role) ? ["consents" as Tab] : []),
    "arco", ...(role === "owner" ? ["audit" as Tab] : [])];
  const [tab, setTab] = useState<Tab>(role === "owner" ? "audit" : "notice");

  return (
    <AppShell>
      <h1 className="text-teal">{es.screens["/privacidad"]}</h1>
      <div role="tablist" aria-label={es.screens["/privacidad"]} className="mt-3 flex flex-wrap gap-2">
        {tabs.map((k) => (
          <Button key={k} role="tab" aria-selected={tab === k} variant={tab === k ? "primary" : "secondary"} onClick={() => setTab(k)}>
            {t.tabs[k]}</Button>))}
      </div>
      <div className="mt-4" role="tabpanel">
        {tab === "notice" && <NoticeTab />}
        {tab === "consents" && <ConsentsTab />}
        {tab === "arco" && <ArcoTab role={role} />}
        {tab === "audit" && <AuditTab />}
      </div>
    </AppShell>
  );
}

// ---- notice ---------------------------------------------------------------------------------------------

/** Tiny Markdown subset of the notice file: headings, paragraphs, "- " lists, **bold** and > quotes. */
function inline(s: string): ReactNode[] {
  return s.split(/(\*\*[^*]+\*\*)/g).map((part, i) => part.startsWith("**") ? <strong key={i}>{part.slice(2, -2)}</strong> : part);
}
function Markdown({ text }: { text: string }) {
  const blocks = text.split(/\n\s*\n/).map((b) => b.trim()).filter(Boolean);
  return (<div className="max-w-3xl space-y-3">{blocks.map((b, i) => {
    if (b.startsWith("# ")) return <h2 key={i} className="text-teal">{b.slice(2)}</h2>;
    if (b.startsWith("> ")) return <p key={i} className="border-l-4 border-teal/40 pl-3 text-muted">{inline(b.slice(2))}</p>;
    if (b.split("\n").every((l) => l.startsWith("- ")))
      return <ul key={i} className="list-disc space-y-1 pl-6">{b.split("\n").map((l, j) => <li key={j}>{inline(l.slice(2))}</li>)}</ul>;
    return <p key={i}>{inline(b)}</p>;
  })}</div>);
}

function NoticeTab() {
  const [md, setMd] = useState<string | null>(null);
  useEffect(() => { api.privacyNotice().then((x) => setMd(x.markdown)); }, []);
  return <Card>{md === null ? <p>{es.common.loading}</p> : <Markdown text={md} />}</Card>;
}

// ---- consents ---------------------------------------------------------------------------------------------

function consentState(c: any | undefined, today: string): "valid" | "expired" | "revoked" | "missing" {
  if (!c) return "missing";
  if (c.revoked_at) return "revoked";
  if (!c.granted) return "missing";
  return c.expires_on >= today ? "valid" : "expired";
}
const STATE_LOOK = { valid: [CheckCircle2, "text-ok"], expired: [AlertTriangle, "text-warn"], revoked: [Ban, "text-danger"],
  missing: [Ban, "text-muted"] } as const;

function ConsentsTab() {
  const [d, setD] = useState<any>(null);
  const [q, setQ] = useState("");
  const [limit, setLimit] = useState(12);
  const [msg, setMsg] = useState<{ kind: "ok" | "error" | "info"; text: string } | null>(null);
  const [dialog, setDialog] = useState<{ kind: "revoke" | "record"; patient: any; type?: string } | null>(null);
  const load = useCallback(() => { api.consents(q).then(setD); }, [q]);
  useEffect(() => { const id = setTimeout(load, 250); return () => clearTimeout(id); }, [load]);
  useBoardSocket((e) => { if (e.type === "consent.changed") load(); });   // coordination: another screen changed one

  if (!d) return <p>{es.common.loading}</p>;
  const shown = d.patients.slice(0, limit);
  return (
    <div className="space-y-3">
      <p>{t.consentsIntro}</p>
      {msg && <Notice kind={msg.kind}>{msg.text}</Notice>}
      {d.can_edit && (
        <label className="block max-w-md"><span className="font-bold">{t.search}</span>
          <input className={inputClass} value={q} onChange={(e) => { setQ(e.target.value); setLimit(12); }} /></label>)}
      {d.patients.length === 0 && <p>{t.noPatients}</p>}
      <p className="text-muted">{fill(t.showing, { n: shown.length, total: d.patients.length })}</p>
      <ul className="grid gap-3 lg:grid-cols-2">
        {shown.map((p: any) => (
          <li key={p.patient_id}><Card>
            <h2 className="text-teal">{p.name} <span className="text-base text-muted">· {p.patient_id}</span></h2>
            <ul className="mt-2 space-y-3">{TYPES.map((k) => {
              const c = p.consents[k];
              const st = consentState(c, d.today);
              const [icon, cls] = STATE_LOOK[st];
              return (
                <li key={k} className="border-t border-teal/10 pt-2">
                  <p><span className="font-bold">{t.types[k]}:</span> <span className={`font-bold ${cls}`}><Icon as={icon} /> {t.state[st]}</span></p>
                  {c && <p className="text-sm">
                    {t.validity} {fill(t.fromTo, { from: dmy(c.signed_on), to: dmy(c.expires_on) })} · {t.signedBy}: {t.grantedBy[c.granted_by]}
                    {c.signer_name ? ` (${c.signer_name})` : ""} · {t.assentLabel}: {t.assent[c.patient_assent]}</p>}
                  {c?.revoked_at && <p className="text-sm text-danger">{fill(t.revokedOn, { d: dmy(c.revoked_at), reason: c.revoke_reason })}</p>}
                  {d.can_edit && (
                    <div className="mt-1 flex flex-wrap gap-2">
                      {st === "valid" && <Button variant="secondary" onClick={() => setDialog({ kind: "revoke", patient: p, type: k })}>{t.revoke}</Button>}
                      <Button variant="secondary" onClick={() => setDialog({ kind: "record", patient: p, type: k })}>{t.record}</Button>
                    </div>)}
                </li>);
            })}</ul>
          </Card></li>))}
      </ul>
      {shown.length < d.patients.length && <Button variant="secondary" onClick={() => setLimit(limit + 12)}>{t.showMore}</Button>}
      {dialog?.kind === "revoke" && <RevokeDialog patient={dialog.patient} type={dialog.type!} onClose={(m) => { setDialog(null); if (m) { setMsg(m); load(); } }} />}
      {dialog?.kind === "record" && <RecordDialog patient={dialog.patient} type={dialog.type!} onClose={(m) => { setDialog(null); if (m) { setMsg(m); load(); } }} />}
    </div>
  );
}

type Done = (m: { kind: "ok" | "error" | "info"; text: string } | null) => void;

function Dialog({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="fixed inset-0 z-40 flex items-center justify-center bg-ink/50 p-4" role="dialog" aria-modal="true" aria-label={title}>
      <div className="max-h-[90vh] w-full max-w-lg overflow-auto rounded-card bg-white p-5">
        <h2 className="text-teal">{title}</h2>{children}
      </div>
    </div>
  );
}

function RevokeDialog({ patient, type, onClose }: { patient: any; type: string; onClose: Done }) {
  const [reason, setReason] = useState("");
  const [error, setError] = useState("");
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      const r = await api.revokeConsent(patient.consents[type].consent_id, reason);
      const text = fill(t.revoked, { n: r.cancelled.length }) + (r.in_progress.length ? ` ${fill(t.inProgress, { ids: r.in_progress.join(", ") })}` : "");
      onClose({ kind: r.in_progress.length ? "info" : "ok", text });
    } catch (err) { setError(err instanceof ApiError ? err.message : es.common.error); }
  };
  return (
    <Dialog title={fill(t.revokeTitle, { kind: t.types[type].toLowerCase(), name: patient.name })}>
      <form onSubmit={submit} className="mt-3 space-y-3">
        <Notice kind="error">{t.revokeWarn[type]}</Notice>
        <label className="block"><span className="font-bold">{t.reason}</span>
          <input className={inputClass} required minLength={3} maxLength={300} value={reason} onChange={(e) => setReason(e.target.value)} /></label>
        {error && <Notice kind="error">{error}</Notice>}
        <div className="flex flex-wrap gap-2">
          <Button type="submit">{t.confirmRevoke}</Button>
          <Button variant="secondary" onClick={() => onClose(null)}>{t.cancel}</Button>
        </div>
      </form>
    </Dialog>
  );
}

function RecordDialog({ patient, type, onClose }: { patient: any; type: string; onClose: Done }) {
  const reps = patient.representatives as any[];
  const today = new Date().toLocaleDateString("en-CA", { timeZone: "America/Mexico_City" });
  const [f, setF] = useState({ type, granted_by: reps.length ? "legal_representative" : "patient",
    family_member_id: reps[0]?.family_member_id ?? "", patient_assent: reps.length ? "unable_to_express" : "not_applicable",
    signed_on: today, expires_on: "" });
  const [error, setError] = useState("");
  const set = (k: string, v: string) => setF({ ...f, [k]: v });
  const submit = async (e: FormEvent) => {
    e.preventDefault();
    try {
      await api.recordConsent({ ...f, patient_id: patient.patient_id, family_member_id: f.granted_by === "patient" ? null : f.family_member_id });
      onClose({ kind: "ok", text: t.saved });
    } catch (err) { setError(err instanceof ApiError ? err.message : es.common.error); }
  };
  const select = (label: string, k: string, options: [string, string][]) => (
    <label className="block"><span className="font-bold">{label}</span>
      <select className={inputClass} value={(f as any)[k]} onChange={(e) => set(k, e.target.value)}>
        {options.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>);
  return (
    <Dialog title={fill(t.recordTitle, { name: patient.name })}>
      <form onSubmit={submit} className="mt-3 space-y-3">
        {select(t.type, "type", TYPES.map((k) => [k, t.types[k]]))}
        {select(t.whoSigns, "granted_by", Object.entries(t.grantedBy))}
        {f.granted_by === "legal_representative" && (reps.length
          ? select(t.representative, "family_member_id", reps.map((r) => [r.family_member_id, r.name]))
          : <Notice kind="error">{t.noRepresentative}</Notice>)}
        {select(t.assentLabel, "patient_assent", Object.entries(t.assent))}
        <DateField label={t.signedOn} value={f.signed_on} onChange={(v) => set("signed_on", v)} required />
        <DateField label={t.expiresOn} value={f.expires_on} onChange={(v) => set("expires_on", v)} required />
        {error && <Notice kind="error">{error}</Notice>}
        <div className="flex flex-wrap gap-2">
          <Button type="submit" disabled={!f.expires_on || (f.granted_by === "legal_representative" && !reps.length)}>{t.save}</Button>
          <Button variant="secondary" onClick={() => onClose(null)}>{t.cancel}</Button>
        </div>
      </form>
    </Dialog>
  );
}

// ---- ARCO -------------------------------------------------------------------------------------------------

function ArcoTab({ role }: { role: string }) {
  const [days, setDays] = useState(20);
  const [list, setList] = useState<any[] | null>(null);
  const [f, setF] = useState({ right_type: "access", description: "", contact: "" });
  const [done, setDone] = useState<any>(null);
  const [error, setError] = useState("");
  const load = () => api.arcoList().then(setList);
  useEffect(() => { api.privacyNotice().then((x) => setDays(x.arco_days)); load(); }, []);
  const submit = async (e: FormEvent) => {
    e.preventDefault(); setError("");
    try { setDone(await api.arcoCreate(f)); setF({ ...f, description: "" }); load(); }
    catch (err) { setError(err instanceof ApiError ? err.message : es.common.error); }
  };
  return (
    <div className="items-start grid gap-4 lg:grid-cols-2">
      <Card>
        <p>{t.arcoIntro}</p>
        <p className="mt-2 font-bold">{fill(t.arcoDeadline, { days })}</p>
        {role === "owner" ? <p className="mt-3">{t.ownerNoArco}</p> : (
          <form onSubmit={submit} className="mt-3 space-y-3">
            <fieldset><legend className="font-bold">{t.whichRight}</legend>
              {Object.keys(t.rights).map((k) => (
                <label key={k} className="flex min-h-12 items-start gap-3 py-1">
                  <input type="radio" name="right" className="mt-1 size-6 shrink-0 accent-teal" checked={f.right_type === k} onChange={() => setF({ ...f, right_type: k })} />
                  <span><strong>{t.rights[k]}</strong> — {t.rightHelp[k]}</span>
                </label>))}
            </fieldset>
            <label className="block"><span className="font-bold">{t.description}</span>
              <textarea className={`${inputClass} min-h-28 py-2`} required minLength={10} maxLength={2000} value={f.description}
                onChange={(e) => setF({ ...f, description: e.target.value })} /></label>
            <label className="block"><span className="font-bold">{t.contact}</span>
              <input className={inputClass} required minLength={3} maxLength={200} value={f.contact} onChange={(e) => setF({ ...f, contact: e.target.value })} /></label>
            {error && <Notice kind="error">{error}</Notice>}
            {done && <><Notice kind="ok">{fill(t.sent, { id: done.arco_id, received: dmy(done.received_on), due: dmy(done.due_on) })}</Notice>
              <p className="text-sm text-muted">{t.dueNote}</p></>}
            <Button type="submit">{t.send}</Button>
          </form>)}
      </Card>
      <Card>
        <h2 className="text-teal">{t.arcoList}</h2>
        {list === null ? <p>{es.common.loading}</p> : list.length === 0 ? <p className="mt-2">{t.arcoEmpty}</p> : (
          <ul className="mt-2 space-y-3">{list.map((a) => (
            <li key={a.arco_id} className="border-t border-teal/10 pt-2">
              <p><strong>{a.arco_id}</strong> · {t.rights[a.right_type]} · {t.arcoStatus[a.status]}</p>
              <p className="text-sm">{a.requested_by} · {when(a.received_at)} · <strong>{fill(t.dueOn, { d: dmy(a.due_on) })}</strong></p>
              <p className="text-sm text-muted">{a.description}</p>
            </li>))}</ul>)}
        <p className="mt-2 text-sm text-muted">{t.dueNote}</p>
      </Card>
    </div>
  );
}

// ---- audit trail (dirección) ---------------------------------------------------------------------------

const label = (action: string) => t.actions[action] ?? action;

function AuditTab() {
  const empty = { action: "", user_id: "", allowed: "", start: "", end: "" };
  const [filters, setFilters] = useState(empty);
  const [applied, setApplied] = useState(empty);
  const [page, setPage] = useState(1);
  const [d, setD] = useState<any>(null);
  const [s, setS] = useState<any>(null);
  useEffect(() => { api.auditSummary().then(setS); }, []);
  useEffect(() => { api.audit({ ...applied, page: String(page) }).then(setD); }, [applied, page]);
  const set = (k: string, v: string) => setFilters({ ...filters, [k]: v });
  const pages = d ? Math.max(1, Math.ceil(d.total / d.page_size)) : 1;

  return (
    <div className="space-y-4">
      <p>{t.auditIntro}</p>
      {s && <BlockedSummary s={s} />}
      <Card>
        <form className="grid gap-3 sm:grid-cols-2 xl:grid-cols-6" onSubmit={(e) => { e.preventDefault(); setPage(1); setApplied(filters); }}>
          <label className="block xl:col-span-2"><span className="font-bold">{t.action}</span>
            <select className={inputClass} value={filters.action} onChange={(e) => set("action", e.target.value)}>
              <option value="">{t.all}</option>
              {(d?.options.actions ?? []).map((a: string) => <option key={a} value={a}>{label(a)}</option>)}</select></label>
          <label className="block xl:col-span-2"><span className="font-bold">{t.user}</span>
            <select className={inputClass} value={filters.user_id} onChange={(e) => set("user_id", e.target.value)}>
              <option value="">{t.all}</option>
              {(d?.options.users ?? []).map((u: any) => <option key={u.user_id} value={u.user_id}>{u.display_name}</option>)}</select></label>
          <label className="block xl:col-span-2"><span className="font-bold">{t.allowedFilter}</span>
            <select className={inputClass} value={filters.allowed} onChange={(e) => set("allowed", e.target.value)}>
              <option value="">{t.all}</option><option value="true">{t.allowed}</option><option value="false">{t.blocked}</option></select></label>
          <div className="xl:col-span-2"><DateField label={t.from} value={filters.start} onChange={(v) => set("start", v)} /></div>
          <div className="xl:col-span-2"><DateField label={t.to} value={filters.end} onChange={(v) => set("end", v)} /></div>
          <div className="flex items-end gap-2 xl:col-span-2">
            <Button type="submit">{t.apply}</Button>
            <Button variant="secondary" onClick={() => { setFilters(empty); setApplied(empty); setPage(1); }}>{t.clear}</Button>
          </div>
        </form>
      </Card>
      <Card>
        {!d ? <p>{es.common.loading}</p> : (<>
          <p className="font-bold">{fill(t.total, { n: d.total.toLocaleString("es-MX") })}</p>
          <p className="text-sm text-muted">{t.auditNote}</p>
          <div className="mt-2 overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead><tr className="border-b border-teal/20">{[t.when, t.user, t.action, t.entity, t.institution, t.allowedFilter, t.detail].map((h) =>
                <th key={h} className="py-1 pr-3">{h}</th>)}</tr></thead>
              <tbody>{d.rows.map((r: any) => (
                <tr key={r.audit_id} className="border-b border-teal/10 align-top">
                  <td className="whitespace-nowrap py-1 pr-3">{when(r.occurred_at)}</td>
                  <td className="pr-3">{r.display_name ?? (r.action === "login_failed" ? t.noUser : t.systemUser)}{r.role ? ` (${es.roles[r.role]})` : ""}</td>
                  <td className="pr-3">{label(r.action)}</td>
                  <td className="pr-3">{auditEntity(r.entity)}{r.entity_id && <> <span className="whitespace-nowrap">{r.entity_id}</span></>}</td>
                  <td className="pr-3">{r.institution_id ?? "—"}</td>
                  <td className="whitespace-nowrap pr-3 font-bold">{r.allowed
                    ? <span className="text-ok"><Icon as={CheckCircle2} /> {t.allowed}</span>
                    : <span className="text-danger"><Icon as={Ban} /> {t.blocked}</span>}</td>
                  <td className="min-w-48 max-w-sm break-words pr-3">{auditDetail(r.detail)}
                    {r.detail && Object.keys(r.detail).length > 0 && (
                      <details className="mt-1 text-muted"><summary className="cursor-pointer text-teal">{t.technicalDetail}</summary>
                        <code className="block break-all text-xs">{JSON.stringify(r.detail)}</code></details>)}</td>
                </tr>))}</tbody>
            </table>
          </div>
          <div className="mt-3 flex flex-wrap items-center gap-3">
            <Button variant="secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>{t.prev}</Button>
            <span>{fill(t.page, { p: page, n: pages })}</span>
            <Button variant="secondary" disabled={page >= pages} onClick={() => setPage(page + 1)}>{t.next}</Button>
          </div>
        </>)}
      </Card>
    </div>
  );
}

function BlockedSummary({ s }: { s: any }) {
  const total = s.by_action.reduce((n: number, r: any) => n + r.n, 0);
  const bars = useMemo(() => ({
    ...baseOption(), legend: { show: false },
    grid: { left: 8, right: 48, top: 8, bottom: 8, containLabel: true },
    tooltip: { ...baseOption().tooltip as object, trigger: "item", formatter: (p: any) => `${esc(p.name)}: <strong>${p.value}</strong>` },
    xAxis: { ...axisCommon, type: "value", minInterval: 1, axisLabel: { show: false }, splitLine: { show: false } },   // each bar carries its value
    yAxis: { ...axisCommon, type: "category", inverse: true, splitLine: { show: false },
      data: s.by_action.map((r: any) => label(r.action)), axisLabel: { ...axisCommon.axisLabel, color: chart.ink, width: 180, overflow: "break" } },
    series: [{ type: "bar", barMaxWidth: 22, data: s.by_action.map((r: any) => r.n),
      itemStyle: { color: chart.series[0], borderRadius: [0, 4, 4, 0] }, label: { show: true, position: "right", color: chart.ink } }],
  }), [s]);
  const days = useMemo(() => ({
    ...baseOption(), legend: { show: false },
    tooltip: { ...baseOption().tooltip as object, trigger: "axis", formatter: (ps: any[]) => `${esc(ps[0].name)}: <strong>${ps[0].value}</strong>` },
    xAxis: { ...axisCommon, type: "category", data: s.by_day.map((r: any) => dmy(r.day)), splitLine: { show: false } },
    yAxis: { ...axisCommon, type: "value", minInterval: 1 },
    series: [{ type: "bar", barMaxWidth: 28, data: s.by_day.map((r: any) => r.n), itemStyle: { color: chart.series[0], borderRadius: [4, 4, 0, 0] } }],
  }), [s]);
  return (
    <div className="items-start grid gap-4 xl:grid-cols-3">
      <ChartCard synthetic={false} question={fill(t.summaryQ, { from: dmy(s.start), to: dmy(s.end) })} keyValue={total.toLocaleString("es-MX")}
        keyLabel={t.blockedTotal} source={t.auditSource} note={fill(t.allowedTotal, { n: s.allowed.toLocaleString("es-MX") })}
        table={{ columns: [t.byUser, t.blockedCount], rows: s.by_user.map((u: any) => [u.display_name ?? t.noUser, u.n]) }}>
        <h3 className="font-bold">{t.byUser}</h3>
        <ol className="mt-1 list-decimal pl-6">{s.by_user.map((u: any) => (
          <li key={u.user_id ?? "none"}>{u.display_name ?? t.noUser}{u.role ? ` (${es.roles[u.role]})` : ""}: <strong>{u.n}</strong></li>))}</ol>
      </ChartCard>
      <ChartCard synthetic={false} question={t.byAction} source={t.auditSource}
        table={{ columns: [t.action, t.blockedCount], rows: s.by_action.map((r: any) => [label(r.action), r.n]) }}>
        <EChart option={bars} height={Math.max(160, 40 * s.by_action.length)} label={t.byAction} />
      </ChartCard>
      <ChartCard synthetic={false} question={t.byDay} source={t.auditSource}
        table={{ columns: [t.when, t.blockedCount], rows: s.by_day.map((r: any) => [dmy(r.day), r.n]) }}>
        <EChart option={days} height={200} label={t.byDay} />
      </ChartCard>
    </div>
  );
}
