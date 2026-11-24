// /simulacion — SIRAG-D results: conclusion, the finding that changed the product, CI per policy and
// scenario, tests, validation, contingency where it happens, and sensitivity (clearly separated).
// Tables become stacked cards per metric on a phone (md:hidden / hidden md:block).
import { Presentation, X } from "lucide-react";
import { useEffect, useState, type ReactNode } from "react";
import { api } from "../api/client";
import { ChartLegend } from "../charts/ChartLegend";
import { CIChart } from "../charts/CIChart";
import { chart } from "../charts/theme";
import { AppShell } from "../components/AppShell";
import { ChartCard } from "../components/ChartCard";
import { AlertTriangle, CheckCircle2, Icon } from "../components/icons";
import { XCircle } from "lucide-react";
import { Button, Card, Notice, PageHeader } from "../components/ui";
import { es } from "../i18n/es";
import { ciRows, conclusion, fill, fmt, HUMAN, pick, POLICIES, SCENARIOS, VELA, VELA_TIMEOUT, type Results } from "./simulation/data";

const t = es.sim;
// The model document lives in the public repository (docs/dev/sirag_d_modelo.md); the card names it in Spanish.
const MODEL_DOC_URL = "https://github.com/daviddzd/vela/blob/main/docs/dev/sirag_d_modelo.md";
const source = <>{t.source} <a href={MODEL_DOC_URL} target="_blank" rel="noreferrer" className="underline">{t.sourceDoc}</a></>;
const MAIN = ["high_wait_p90_min", "crisis_under_60_pct", "crisis_response_p90_min", "unattended_pct", "high_wait_mean_min",
  "crisis_response_mean_min", "travel_km", "utilization_pct", "overtime_hours"];
const COMPARED = [VELA_TIMEOUT, VELA];
const selectClass = "mt-1 block min-h-12 w-full rounded-field border-2 border-muted/60 bg-white px-3";
const fmtP = (p: number | null | undefined) => (p == null ? "—" : p < 0.001 ? "p < 0.001" : `p = ${p.toFixed(3)}`);

/** A table on wide screens; one card per row (label + value pairs) on a phone. */
function ResponsiveTable({ head, rows }: { head: string[]; rows: { key: string; cells: ReactNode[] }[] }) {
  return (<>
    <div className="hidden overflow-x-auto md:block">
      <table className="w-full text-left text-sm">
        <thead><tr className="border-b border-navy/20">{head.map((h) => <th key={h} className="py-1 pr-3 align-bottom">{h}</th>)}</tr></thead>
        <tbody>{rows.map((r) => <tr key={r.key} className="border-b border-navy/10 align-top">
          {r.cells.map((c, i) => <td key={i} className={`py-1 pr-3 ${i === 0 ? "font-bold" : ""}`}>{c}</td>)}</tr>)}</tbody>
      </table>
    </div>
    <ul className="space-y-3 md:hidden">
      {rows.map((r) => (
        <li key={r.key} className="rounded-field border border-navy/15 p-3">
          <p className="font-bold">{r.cells[0]}</p>
          <dl className="mt-1 space-y-1">{r.cells.slice(1).map((c, i) => (
            <div key={i}><dt className="text-sm text-muted">{head[i + 1]}</dt><dd>{c}</dd></div>))}</dl>
        </li>))}
    </ul>
  </>);
}

/** Significance + DIRECTION: a significant difference can be better or worse depending on the metric. */
function Verdict({ p, diff, metric }: { p: number | null | undefined; diff: number | null | undefined; metric: string }) {
  const m = t.metrics[metric];
  const sig = p != null && p < 0.05;
  const better = diff == null || m?.better === "neutral" ? null : m?.better === "lower" ? diff < 0 : diff > 0;
  const [icon, text, cls] = !sig ? [AlertTriangle, t.notSignificant, "text-muted"]
    : better === null ? [CheckCircle2, t.significant, "text-ink"]
    : better ? [CheckCircle2, t.better, "text-ok"] : [XCircle, t.worse, "text-danger"];
  return (<>
    <span className={`font-bold ${cls}`}><Icon as={icon} /> {text}</span>
    <span className="block">{t.diffCol}: {fmt(diff, 2)} {m?.unit} · {fmtP(p)}</span>
  </>);
}

export function SimulationPage() {
  const [r, setR] = useState<Results | null>(null);
  const [metric, setMetric] = useState("high_wait_p90_min");
  const [scenario, setScenario] = useState("normal");
  // Presentation mode: only summary + finding + comparison, with large type for the projector.
  // Like "modo sencillo", it scales the root font size (every size is in rem) and restores it on exit.
  const [present, setPresent] = useState(false);
  useEffect(() => {
    const html = document.documentElement;
    const before = html.style.fontSize;
    if (present) { html.style.fontSize = "26px"; window.scrollTo(0, 0); }
    return () => { html.style.fontSize = before; };
  }, [present]);
  useEffect(() => { api.simulation().then((x) => setR(x as Results)).catch(() => setR({ available: false } as Results)); }, []);

  if (!r) return <AppShell><p>{es.common.loading}</p></AppShell>;
  if (!r.available) return <AppShell><PageHeader title={es.pageTitles["/simulacion"]} /><Notice>{t.notRun}</Notice></AppShell>;

  const meta = t.metrics[metric];
  const v = r.validation[0];
  const legend = [{ label: t.legendEnlaza, color: chart.series[0], kind: "line" as const },
    { label: t.legendOthers, color: chart.muted, kind: "line" as const }];
  const sensTest = (level: string, m: string) => r.sensitivity_tests.find((x) => x.knob === "approval_delay" && x.level === level && x.metric === m);
  const cfg = { urgent: String(r.info.approval?.urgent_within_minutes ?? "—"), after: String(r.info.approval?.auto_apply_after_minutes ?? "—"),
    hold: String(r.info.approval?.hold_minutes ?? "—") };

  return (
    <AppShell bare={present}>
      <PageHeader title={es.pageTitles["/simulacion"]}
        actions={<Button icon={present ? X : Presentation} variant={present ? "secondary" : "primary"} onClick={() => setPresent(!present)}
          aria-pressed={present}>{present ? t.presentOff : t.presentOn}</Button>}>
        {!present && <p>{t.presentHint}</p>}
      </PageHeader>
      <p className="mt-1 max-w-4xl">{t.intro}</p>
      <p className="mt-1 max-w-4xl text-muted">{t.laborNote}</p>
      <p className="mt-1 text-muted">{fill(t.runInfo, { reps: String(r.info.replications), seed: String(r.info.seed),
        secs: fmt(r.info.elapsed_seconds, 0), workers: String(r.info.workers) })}</p>

      <div className="mt-4 space-y-4">
        <ChartCard question={t.conclusionQ} source={source}>
          <ul className="space-y-2 text-lg">
            {conclusion(r).map((line) => <li key={line} className="flex gap-2"><Icon as={CheckCircle2} className="mt-1 text-navy" /><span>{line}</span></li>)}
          </ul>
        </ChartCard>

        <ChartCard question={t.findingQ} source={source}>
          <p>{fill(t.findingIntro, cfg)}</p>
          <p className="mt-2 font-bold">{t.findingTable}</p>
          <ResponsiveTable head={[t.metric, t.policies[VELA], t.policies[VELA_TIMEOUT]]}
            rows={["crisis_response_p90_min", "high_wait_p90_min"].map((m) => {
              const x = sensTest("5-15", m);
              return { key: m, cells: [`${t.metrics[m].label} · ${t.approvalDelay} 5–15 · ${t.vsHumanShort}`,
                <Verdict p={x?.[`${VELA}_p_holm`]} diff={x?.[`${VELA}_diff_mean`]} metric={m} />,
                <Verdict p={x?.[`${VELA_TIMEOUT}_p_holm`]} diff={x?.[`${VELA_TIMEOUT}_diff_mean`]} metric={m} />] };
            })} />
        </ChartCard>

        <ChartCard question={t.metricQ} keyValue={`${fmt(pick(r.summary, "normal", VELA_TIMEOUT, metric)?.mean)} ${meta.unit}`}
          keyLabel={`${meta.label} · ${t.policies[VELA_TIMEOUT]} · ${t.scenarios.normal}`} note={t.ciNote} source={source}
          table={{ columns: [t.scenario, ...POLICIES.map((p) => t.policies[p])],
            rows: SCENARIOS.map((s) => [t.scenarios[s], ...POLICIES.map((p) => {
              const x = pick(r.summary, s, p, metric);
              return x ? `${fmt(x.mean)} [${fmt(x.ci_low)}–${fmt(x.ci_high)}]` : "—"; })]) }}>
          <label className="block max-w-md"><span className="font-bold">{t.metric}</span>
            <select className={selectClass} value={metric} onChange={(e) => setMetric(e.target.value)}>
              {MAIN.map((k) => <option key={k} value={k}>{t.metrics[k].short} ({t.metrics[k].unit})</option>)}
            </select>
          </label>
          <div className="mt-3"><ChartLegend items={legend} /></div>
          {/* media queries do not follow the root font size: one column, full width, when presenting */}
          <div className={`grid gap-4 ${present ? "" : "lg:grid-cols-3"}`}>
            {SCENARIOS.map((s) => (
              <div key={s} className="flex flex-col">
                <h3 className="font-bold">{t.scenarios[s]}</h3>
                <CIChart rows={ciRows(r.summary, s, metric)} unit={meta.unit} title={`${meta.label}, ${t.scenarios[s]}`}
                  height={present ? 320 : 230} large={present} />
              </div>
            ))}
          </div>
        </ChartCard>

        {!present && <>
        <ChartCard question={t.testsQ} note={t.testsNote} source={source}>
          <label className="block max-w-sm"><span className="font-bold">{t.scenario}</span>
            <select className={selectClass} value={scenario} onChange={(e) => setScenario(e.target.value)}>
              {SCENARIOS.map((s) => <option key={s} value={s}>{t.scenarios[s]}</option>)}
            </select>
          </label>
          <div className="mt-3">
            <ResponsiveTable head={[t.metric, t.omnibus, ...COMPARED.map((p) => `${t.policies[p]} ${t.vsHumanShort}`)]}
              rows={r.tests.filter((x) => x.scenario === scenario && MAIN.includes(x.metric)).map((x) => ({
                key: x.metric,
                cells: [t.metrics[x.metric]?.label,
                  x.omnibus === "sin variación" ? t.noVariation : `${x.omnibus}, ${fmtP(x.omnibus_p)}`,
                  ...COMPARED.map((p) => x.omnibus === "sin variación" ? "—"
                    : <Verdict p={x[`${p}_p_holm`]} diff={x[`${p}_diff_mean`]} metric={x.metric} />)],
              }))} />
          </div>
        </ChartCard>

        <div className="items-start grid gap-4 xl:grid-cols-2">
          <ChartCard question={t.validationQ} keyValue={`${fmt(v.sim_mean)} %`} keyLabel={t.validationKeyLabel}
            note={fill(t.validationNote, { noStaff: fmt(v.no_staff, 0), total: fmt(v.total, 0), cancelled: fmt(v.cancelled, 0),
              obsShort: `${fmt(v.pct_short_services)} %`, simShort: `${fmt(v.sim_short_mean)} %` })} source={source}>
            <dl className="grid grid-cols-[1fr_auto] gap-x-4 gap-y-2">
              {[[t.observedAll, `${fmt(v.pct_all)} %`], [t.observedNoCancel, `${fmt(v.pct_without_cancelled)} %`],
                [t.simulatedAll, `${fmt(v.sim_mean)} % [${fmt(v.sim_ci_low)}–${fmt(v.sim_ci_high)}]`],
                [t.observedShort, `${fmt(v.pct_short_services)} %`],
                [t.simulatedShort, `${fmt(v.sim_short_mean)} % [${fmt(v.sim_short_ci_low)}–${fmt(v.sim_short_ci_high)}]`]].map(([k, val]) => (
                <div key={k} className="contents"><dt>{k}</dt><dd className="figure text-right text-xl">{val}</dd></div>))}
            </dl>
          </ChartCard>

          <ChartCard question={t.contingencyQ} note={t.contingencyNote} source={source}>
            <ResponsiveTable head={["", ...SCENARIOS.map((s) => t.scenarios[s])]}
              rows={[
                { key: "risk", cells: [t.atRisk, ...SCENARIOS.map((s) => fmt(r.contingency_effect.find((x) => x.scenario === s)?.win_at_risk_entries, 0))] },
                { key: "crises", cells: [t.crisesWin, ...SCENARIOS.map((s) => fmt(r.contingency_effect.find((x) => x.scenario === s)?.win_crises, 0))] },
                ...([["win_crisis_under_60_pct", t.winCrisis60, "%"], ["win_high_wait_mean_min", t.winWait, "min"],
                  ["win_unattended_pct", t.winUnattended, "%"]] as const).map(([k, label, u]) => ({
                  key: k, cells: [`${label} · ${t.policies[VELA_TIMEOUT]}`, ...SCENARIOS.map((s) => {
                    const x = pick(r.window, s, VELA_TIMEOUT, k);
                    return x ? `${fmt(x.mean)} ${u} [${fmt(x.ci_low)}–${fmt(x.ci_high)}]` : "—"; })] })),
              ]} />
          </ChartCard>
        </div>

        <Card className="border-2 border-dashed border-warn/60">
          <h2 className="text-navy"><Icon as={AlertTriangle} className="text-warn" /> {t.sensitivityQ}</h2>
          <p className="mt-2 text-muted">{t.sensitivityNote}</p>
          <div className="mt-2 grid gap-6 xl:grid-cols-2">
            {(["approval_delay", "risk_multiplier"] as const).map((knob) => {
              const rows = r.sensitivity.filter((x) => x.knob === knob);
              const levels = [...new Set(rows.map((x) => String(x[knob])))];
              const label = (l: string) => knob === "risk_multiplier" ? `×${fmt(Number(l))}` : (t.approvalLevels[l] ?? l);
              return (
                <div key={knob}>
                  <h3 className="font-bold">{knob === "approval_delay" ? t.approvalDelay : t.riskMultiplier}</h3>
                  <ResponsiveTable head={[t.metric, ...levels.map(label)]}
                    rows={["high_wait_p90_min", "crisis_response_p90_min", "crisis_under_60_pct"].flatMap((m) => [VELA_TIMEOUT, VELA, HUMAN].map((p) => ({
                      key: m + p, cells: [`${t.metrics[m].label} · ${t.policies[p]}`, ...levels.map((l) => {
                        const x = rows.find((y) => y.metric === m && y.policy === p && String(y[knob]) === l);
                        return `${fmt(x?.mean)} ${t.metrics[m].unit}`; })] })))} />
                </div>);
            })}
          </div>

          <h3 className="mt-6 text-xl font-bold text-navy">{t.hiringQ}</h3>
          <p className="mt-1 text-muted">{t.hiringNote}</p>
          <div className="mt-2">
            <ResponsiveTable head={[t.metric, ...["current", "requested", "targeted"].map((l) => t.staffLevels[l])]}
              rows={["unattended_pct", "crisis_under_60_pct"].flatMap((m) => [VELA_TIMEOUT, HUMAN].map((p) => ({
                key: m + p, cells: [`${t.metrics[m].label} · ${t.policies[p]}`, ...["current", "requested", "targeted"].map((l) => {
                  const x = r.sensitivity.find((y) => y.knob === "extra_staff" && y.extra_staff === l && y.policy === p && y.metric === m);
                  return x ? `${fmt(x.mean)} % [${fmt(x.ci_low)}–${fmt(x.ci_high)}]` : "—"; })] })))} />
          </div>
          <h3 className="mt-6 text-xl font-bold text-navy">{t.nightQ}</h3>
          <p className="mt-1 text-muted">{t.nightNote}</p>
          <div className="mt-2">
            <ResponsiveTable head={[t.metric, ...["current", "night_legal"].map((l) => t.nightLevels[l])]}
              rows={[{ key: "staff", cells: [t.nightStaff, ...["current", "night_legal"].map((l) => {
                const x = r.sensitivity.find((y) => y.knob === "extra_staff" && y.extra_staff === l && y.policy === VELA_TIMEOUT && y.metric === "staff");
                return x ? fmt(x.mean, 0) : "—"; })] },
              { key: "relays", cells: [t.nightRelays, ...["current", "night_legal"].map((l) => {
                const x = r.sensitivity.find((y) => y.knob === "extra_staff" && y.extra_staff === l && y.policy === VELA_TIMEOUT && y.metric === "relays");
                return x ? fmt(x.mean) : "—"; })] },
              ...["unattended_pct", "crisis_under_60_pct", "night_crisis_under_60_pct"].flatMap((m) => [VELA_TIMEOUT, HUMAN].map((p) => ({
                key: m + p, cells: [`${t.metrics[m].label} · ${t.policies[p]}`, ...["current", "night_legal"].map((l) => {
                  const x = r.sensitivity.find((y) => y.knob === "extra_staff" && y.extra_staff === l && y.policy === p && y.metric === m);
                  return x ? `${fmt(x.mean)} % [${fmt(x.ci_low)}–${fmt(x.ci_high)}]` : "—"; })] })))]} />
          </div>
        </Card>
        </>}
      </div>
    </AppShell>
  );
}
