// /reportes-voz — the physician's inbox: only their patients; health content only with health_data consent.
// The report is a summary of what was said; it never diagnoses.
import { AlertTriangle, Ban, CheckCircle2, ClipboardCheck, Minus } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { AppShell } from "../components/AppShell";
import { Icon } from "../components/icons";
import { Button, Card, Notice, PageHeader } from "../components/ui";
import { es } from "../i18n/es";
import { formatDateTime } from "../lib/format";

const t = es.reports;
const LEVEL = { emergency: { icon: Ban, cls: "border-danger text-danger" }, urgent: { icon: AlertTriangle, cls: "border-warn text-ink" },
  routine: { icon: Minus, cls: "border-navy text-navy" } } as const;

function List({ label, items }: { label: string; items?: string[] }) {
  if (!items?.length) return null;
  return <div><dt className="font-bold">{label}</dt><dd><ul className="ml-5 list-disc">{items.map((x) => <li key={x}>{x}</li>)}</ul></dd></div>;
}

export function VoiceReportsPage() {
  const [rows, setRows] = useState<any[] | null>(null);
  const [onlyUnreviewed, setOnlyUnreviewed] = useState(true);   // the server already sorts: unreviewed, most serious, newest
  const pending = rows?.filter((r) => !r.reviewed_at).length ?? 0;
  const shown = onlyUnreviewed ? rows?.filter((r) => !r.reviewed_at) : rows;
  const load = useCallback(() => { api.voiceReports().then(setRows).catch(() => setRows([])); }, []);
  useEffect(() => { load(); const id = setInterval(load, 10000); return () => clearInterval(id); }, [load]);
  const review = async (id: string) => { await api.voiceReview(id); load(); };

  return (
    <AppShell>
      <PageHeader title={es.pageTitles["/reportes-voz"]}>
        <p className="">{t.notDiagnosis}</p>
      </PageHeader>
      <div className="mt-3 flex flex-wrap items-center gap-2" role="group">
        <Button variant={onlyUnreviewed ? "primary" : "secondary"} aria-pressed={onlyUnreviewed} onClick={() => setOnlyUnreviewed(true)}>
          {t.filterUnreviewed}</Button>
        <Button variant={onlyUnreviewed ? "secondary" : "primary"} aria-pressed={!onlyUnreviewed} onClick={() => setOnlyUnreviewed(false)}>
          {t.filterAll}</Button>
        <span className="font-bold">{t.unreviewedCount.replace("{n}", String(pending))}</span>
      </div>
      <div className="items-start mt-4 grid gap-4 xl:grid-cols-2">
        {shown?.length === 0 && <Card>{t.empty}</Card>}
        {shown?.map((r) => {
          const lv = LEVEL[r.triage_label as keyof typeof LEVEL];
          const rep = r.report;
          return (
            <Card key={r.report_id} className={r.reviewed_at ? "opacity-80" : ""}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <h2>{r.patient_name}</h2>
                <span className={`inline-flex items-center gap-1 rounded-card border-2 px-2 font-bold ${lv.cls}`}>
                  <Icon as={lv.icon} /> {es.voice.levels[r.triage_label]}</span>
              </div>
              <p className="text-muted">{formatDateTime(r.created_at)} · {t.mode[r.input_mode]}
                {r.confidence != null && ` · ${t.confidence}: ${Math.round(r.confidence * 100)} %`}</p>
              {r.needs_human_review && <p className="mt-1 font-bold text-warn"><Icon as={AlertTriangle} /> {t.needsReview}</p>}
              {r.health_notice ? <div className="mt-3"><Notice kind="error">{t.noConsent}</Notice></div> : (
                <dl className="mt-3 space-y-2">
                  <div><dt className="font-bold">{t.transcript}</dt><dd>«{r.transcript}»</dd></div>
                  {r.rule_labels?.length > 0 && <div><dt className="font-bold">{t.rules}</dt><dd>{r.rule_labels.join(", ")}</dd></div>}
                  {r.report_status === "pending" && <p className="text-muted">{t.pending}</p>}
                  {(r.report_status === "invalid" || r.report_status === "failed") && <p className="text-muted">{t.invalid}</p>}
                  {rep && (<>
                    <div><dt className="font-bold">{t.summary}</dt><dd>{rep.resumen}</dd></div>
                    <List label={t.symptoms} items={rep.sintomas_mencionados} />
                    {rep.inicio && <div><dt className="font-bold">{t.onset}</dt><dd>{rep.inicio}</dd></div>}
                    <List label={t.alarm} items={rep.signos_de_alarma} />
                    <List label={t.meds} items={rep.medicamentos_mencionados} />
                    <List label={t.quotes} items={rep.frases_textuales} />
                    <div><dt className="font-bold">{t.limits}</dt><dd className="text-muted">{rep.limitaciones}</dd></div>
                  </>)}
                </dl>)}
              <div className="mt-4 border-t border-navy/15 pt-3">
                {r.reviewed_at ? <p className="font-bold text-ok"><Icon as={CheckCircle2} /> {t.reviewed} · {formatDateTime(r.reviewed_at)}</p>
                  : <Button icon={ClipboardCheck} onClick={() => review(r.report_id)}>{t.review}</Button>}
              </div>
            </Card>);
        })}
      </div>
    </AppShell>
  );
}
