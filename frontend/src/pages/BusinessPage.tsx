// /negocio (dirección) — business model computed by the API from data/business/assumptions.csv.
// Every number shows its source (link) or the label "supuesto". Changing an assumption calls the API again
// (one place computes everything: backend/app/services/business_model.py).
import { RotateCcw } from "lucide-react";
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { api } from "../api/client";
import { ChartLegend } from "../charts/ChartLegend";
import { EChart, esc } from "../charts/EChart";
import { axisCommon, baseOption, chart } from "../charts/theme";
import { AppShell } from "../components/AppShell";
import { ChartCard } from "../components/ChartCard";
import { Button, Card, Notice, PageHeader, inputClass } from "../components/ui";
import { es } from "../i18n/es";

const t = es.business;
const mxn = (n: number | null | undefined, digits = 0) =>
  n == null ? "—" : n.toLocaleString("es-MX", { style: "currency", currency: "MXN", maximumFractionDigits: digits });
const num = (n: number | null | undefined, digits = 0) =>
  n == null ? "—" : n.toLocaleString("es-MX", { maximumFractionDigits: digits, minimumFractionDigits: digits });
const fill = (s: string, v: Record<string, string | number>) => s.replace(/\{(\w+)\}/g, (_, k) => String(v[k] ?? ""));

type Row = { key: string; value: number | string; unit: string; description_es: string; source: string; url: string; type: string };

/** "Fuente: X" as a link, or the label "supuesto" — never a bare number. */
function Src({ row }: { row?: Row }) {
  if (!row) return null;
  if (row.type === "assumption")
    return <span className="rounded border border-muted/60 bg-sky-soft px-1.5 text-sm font-bold text-ink">{t.assumption}</span>;
  return <a className="text-sm text-navy underline" href={row.url} target="_blank" rel="noreferrer">{row.source}</a>;
}

function Kpi({ label, value, src }: { label: string; value: ReactNode; src: ReactNode }) {
  return (
    <div className="rounded-card border border-navy/10 bg-white shadow-[var(--shadow-card)] p-4">
      <p className="text-muted">{label}</p>
      <p className="figure text-3xl">{value}</p>
      <p className="mt-1">{src}</p>
    </div>
  );
}

function NumberField({ label, value, onChange, step = 1, min = 0, src }:
  { label: string; value: number; onChange: (v: number) => void; step?: number; min?: number; src?: ReactNode }) {
  return (
    <label className="block">
      <span className="font-bold">{label}</span> {src}
      <input type="number" inputMode="decimal" className={inputClass} value={Number.isFinite(value) ? value : ""} step={step} min={min}
        onChange={(e) => onChange(e.target.value === "" ? 0 : Number(e.target.value))} />
    </label>
  );
}

export function BusinessPage() {
  const [d, setD] = useState<any>(null);
  const [values, setValues] = useState<Record<string, any> | null>(null);
  const [m, setM] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const first = useRef(true);

  useEffect(() => {
    api.business().then((x) => { setD(x); setM(x.model); setValues(defaults(x)); });
  }, []);

  // The three plan shares must add up to 100 %; until they do, nothing is recalculated (a notice says why).
  const mixSum = values ? values.plan_mix_basic + values.plan_mix_professional + values.plan_mix_institutional : 100;
  const mixOk = Math.abs(mixSum - 100) < 0.01;

  // Live recalculation: wait 400 ms after the last change, then ask the API.
  useEffect(() => {
    if (!values) return;
    if (first.current) { first.current = false; return; }
    if (!mixOk) { setBusy(false); return; }
    setBusy(true);
    const id = setTimeout(() => api.businessModel(values).then(setM).finally(() => setBusy(false)), 400);
    return () => clearTimeout(id);
  }, [values, mixOk]);

  if (!d || !m || !values) return <AppShell><p>{es.common.loading}</p></AppShell>;
  const a: Record<string, Row> = d.assumptions;
  const set = (k: string, v: any) => setValues({ ...values, [k]: v });
  const growth: number[] = String(values.customer_growth_year2_5).split(",").map(Number);
  const targets = [values.customers_year1, ...growth];
  const setTarget = (i: number, v: number) => {
    if (i === 0) return set("customers_year1", v);
    const g = [...growth]; g[i - 1] = v; set("customer_growth_year2_5", g.join(","));
  };

  return (
    <AppShell>
      <PageHeader title={es.pageTitles["/negocio"]}>
        <p className="max-w-4xl">{t.intro}</p>
      </PageHeader>
      <p className="mt-1 text-muted">{t.nominal}</p>

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5" aria-live="polite">
        <Kpi label={t.kpiArpa} value={mxn(m.average_revenue_year1)} src={<span className="text-sm text-muted">{t.derived}: {t.mix.toLowerCase()} × {t.prices.toLowerCase()}</span>} />
        <Kpi label={t.kpiFixed} value={mxn(m.fixed_costs_year1)} src={<span className="text-sm text-muted">{t.derived}: {a.founders.value} × <Src row={a.salary_software_developer_cdmx} /> × {a.employer_cost_factor.value} + {mxn(Number(a.infra_monthly_year1.value))}</span>} />
        <Kpi label={t.kpiStatic} value={`${m.breakeven_institutions_static ?? "—"} ${t.kpiStaticUnit}`} src={<span className="text-sm text-muted">{t.derived}</span>} />
        <Kpi label={t.kpiBreakeven} value={m.breakeven_month ? fill(t.kpiBreakevenValue, { m: m.breakeven_month, y: m.breakeven_year }) : t.never} src={<span className="text-sm text-muted">{t.derived}</span>} />
        <Kpi label={t.kpiPayback} value={m.payback_month ? fill(t.kpiBreakevenValue, { m: m.payback_month, y: Math.ceil(m.payback_month / 12) }) : t.never} src={<span className="text-sm text-muted">{t.derived}</span>} />
      </div>

      <div className="items-start mt-4 grid gap-4 xl:grid-cols-[minmax(0,380px)_1fr]">
        <Card>
          <div className="flex items-center justify-between gap-2">
            <h2 className="text-navy">{t.controlsQ}</h2>
            {busy && <span className="text-muted" role="status">{t.recalculating}</span>}
          </div>
          <fieldset className="mt-3 space-y-2">
            <legend className="font-bold">{t.prices}</legend>
            {["plan_basic_price", "plan_professional_price", "plan_institutional_price"].map((k) => (
              <NumberField key={k} label={t.plans[k]} value={values[k]} step={100} onChange={(v) => set(k, v)} src={<Src row={a[k]} />} />))}
          </fieldset>
          <fieldset className="mt-4 space-y-2">
            <legend className="font-bold">{t.mix} <Src row={a.plan_mix_basic} /></legend>
            {["plan_mix_basic", "plan_mix_professional", "plan_mix_institutional"].map((k) => (
              <NumberField key={k} label={`${t.mixKeys[k]} (%)`} value={values[k]} step={5} onChange={(v) => set(k, v)} />))}
            {mixOk ? <p className="text-sm text-muted">{t.mixNote}</p>
              : <Notice kind="error">{fill(t.mixBad, { n: num(mixSum, 1) })}</Notice>}
          </fieldset>
          <fieldset className="mt-4">
            <legend className="font-bold">{t.customers} <Src row={a.customers_year1} /></legend>
            <div className="grid grid-cols-3 gap-2">
              {targets.map((v, i) => <NumberField key={i} label={fill(t.yearN, { n: i + 1 })} value={v} onChange={(x) => setTarget(i, x)} />)}
            </div>
          </fieldset>
          <div className="mt-4 space-y-2">
            <NumberField label={t.churn} value={values.monthly_churn} step={0.5} onChange={(v) => set("monthly_churn", v)} src={<Src row={a.monthly_churn} />} />
            <label className="flex min-h-12 items-center gap-3">
              <input type="checkbox" className="size-6 shrink-0 accent-navy" checked={values.price_inflation_adjustment >= 0.5}
                onChange={(e) => set("price_inflation_adjustment", e.target.checked ? 1 : 0)} />
              <span>{values.price_inflation_adjustment >= 0.5 ? fill(t.priceAdjust, { infl: num(Number(a.inflation_annual_oct_2026.value), 2) }) : t.priceAdjustOff}{" "}
                <Src row={a.inflation_annual_oct_2026} /></span>
            </label>
            <NumberField label={t.cac} value={values.cac_per_institution} step={1000} onChange={(v) => set("cac_per_institution", v)} src={<Src row={a.cac_per_institution} />} />
            <NumberField label={t.perSupport} value={values.institutions_per_support} min={1} onChange={(v) => set("institutions_per_support", v)} src={<Src row={a.institutions_per_support} />} />
            <NumberField label={t.perServer} value={values.institutions_per_server} min={1} onChange={(v) => set("institutions_per_server", v)} src={<Src row={a.institutions_per_server} />} />
          </div>
          <fieldset className="mt-4 space-y-2">
            <legend className="font-bold">{t.recommendedControls}</legend>
            <NumberField label={t.capLabel} value={values.recommended_private_cap} min={1} onChange={(v) => set("recommended_private_cap", v)} src={<Src row={a.recommended_private_cap} />} />
            <NumberField label={t.govPrice} value={values.plan_government_price} step={500} onChange={(v) => set("plan_government_price", v)} src={<Src row={a.plan_government_price} />} />
            <NumberField label={t.govCycle} value={values.government_sales_cycle_months} onChange={(v) => set("government_sales_cycle_months", v)} src={<Src row={a.government_sales_cycle_months} />} />
            <NumberField label={t.govCap} value={values.government_cap} onChange={(v) => set("government_cap", v)} src={<Src row={a.government_cap} />} />
            <NumberField label={t.founderPct} value={values.founder_salary_year1_recommended} step={10} onChange={(v) => set("founder_salary_year1_recommended", v)} src={<Src row={a.founder_salary_year1_recommended} />} />
          </fieldset>
          <Button className="mt-4" variant="secondary" icon={RotateCcw} onClick={() => setValues(defaults(d))}>{t.reset}</Button>
        </Card>

        <div className="space-y-4">
          <ChartCard synthetic={false} question={t.npvQ} source={`${a.tiie_28_days.source} (TIIE) · ${t.assumption}`} note={fill(t.npvNote, { tiie: num(Number(a.tiie_28_days.value), 4) })}>
            <ul className="grid gap-3 sm:grid-cols-3">
              {m.npv.map((n: any) => (
                <li key={n.rate_pct} className={`rounded-card border-2 p-3 ${n.rate_pct === Number(a.discount_rate_base.value) ? "border-navy" : "border-navy/20"}`}>
                  <p className="text-muted">{fill(t.npvRate, { r: n.rate_pct })}</p>
                  <p className={`figure text-2xl ${n.npv < 0 ? "text-danger" : ""}`}>{mxn(n.npv)}</p>
                </li>))}
            </ul>
          </ChartCard>
          <FlowChart m={m} />
          <CustomersChart m={m} />
        </div>
      </div>

      <Investment m={m} />
      <WhatIf m={m} />
      <Scenarios m={m} a={a} values={values} />
      <YearsTable m={m} a={a} values={values} />
      <Competition d={d} />
      <RealMarket a={a} m={m} />
      <Usage d={d} />
    </AppShell>
  );
}

function defaults(d: any): Record<string, any> {
  const a = d.assumptions;
  return Object.fromEntries(d.editable.map((k: string) => [k, a[k].value]));
}

function FlowChart({ m }: { m: any }) {
  const rows = m.months as any[];
  const option = useMemo(() => ({
    ...baseOption(), legend: { show: false },
    tooltip: { ...baseOption().tooltip as object, trigger: "axis",
      formatter: (ps: any[]) => `${esc(t.month)} ${ps[0].axisValue}<br/>` +
        ps.map((p) => `${esc(p.seriesName)}: <strong>${mxn(p.value)}</strong>`).join("<br/>") },
    xAxis: { ...axisCommon, type: "category", data: rows.map((r) => r.month), splitLine: { show: false },
      axisLabel: { ...axisCommon.axisLabel, interval: 11, formatter: (v: string) => `${t.year} ${Math.ceil(Number(v) / 12)}` } },
    yAxis: { ...axisCommon, type: "value", axisLabel: { ...axisCommon.axisLabel, formatter: (v: number) => `${num(v / 1000)} mil` } },
    series: [
      { name: t.revenue, type: "line", showSymbol: false, data: rows.map((r) => Math.round(r.revenue)), lineStyle: { width: 2, color: chart.series[0] }, itemStyle: { color: chart.series[0] } },
      { name: t.costs, type: "line", showSymbol: false, data: rows.map((r) => Math.round(r.costs)), lineStyle: { width: 2, color: chart.series[1] }, itemStyle: { color: chart.series[1] },
        markLine: m.breakeven_month ? { symbol: "none", silent: true, lineStyle: { color: chart.muted, type: "dashed" },
          label: { formatter: fill(t.kpiBreakevenValue, { m: m.breakeven_month, y: m.breakeven_year }), color: chart.ink },
          data: [{ xAxis: String(m.breakeven_month) }] } : undefined },
    ],
  }), [rows, m.breakeven_month, m.breakeven_year]);
  return (
    <ChartCard synthetic={false} question={t.flowQ} source={`${t.assumptionsSource} · ${t.derived}`}
      table={{ columns: [t.month, t.revenue, t.costs, t.profit, t.cash],
        rows: rows.map((r) => [r.month, mxn(r.revenue), mxn(r.costs), mxn(r.profit), mxn(r.cash)]) }}>
      <ChartLegend items={[{ label: t.revenue, color: chart.series[0], kind: "line" }, { label: t.costs, color: chart.series[1], kind: "line" }]} />
      <EChart option={option} height={260} label={t.flowQ} />
    </ChartCard>
  );
}

function CustomersChart({ m }: { m: any }) {
  const rows = m.months as any[];
  const option = useMemo(() => ({
    ...baseOption(), legend: { show: false },
    tooltip: { ...baseOption().tooltip as object, trigger: "axis",
      formatter: (ps: any[]) => `${esc(t.month)} ${ps[0].axisValue}: <strong>${num(ps[0].value, 1)}</strong>` },
    xAxis: { ...axisCommon, type: "category", data: rows.map((r) => r.month), splitLine: { show: false },
      axisLabel: { ...axisCommon.axisLabel, interval: 11, formatter: (v: string) => `${t.year} ${Math.ceil(Number(v) / 12)}` } },
    yAxis: { ...axisCommon, type: "value", minInterval: 1 },
    series: [{ name: t.customersLine, type: "line", showSymbol: false, data: rows.map((r) => Number(r.customers.toFixed(1))),
      lineStyle: { width: 2, color: chart.series[0] }, itemStyle: { color: chart.series[0] } }],
  }), [rows]);
  return (
    <ChartCard synthetic={false} question={t.customersQ} source={`${t.assumptionsSource} · ${t.derived}`}
      table={{ columns: [t.month, t.customersLine], rows: rows.map((r) => [r.month, num(r.customers, 1)]) }}>
      <EChart option={option} height={200} label={t.customersQ} />
    </ChartCard>
  );
}

function YearsTable({ m, a, values }: { m: any; a: Record<string, Row>; values: Record<string, any> }) {
  const head = [t.year, t.colCustomers, t.colNew, t.colLost, t.revenue, t.colFixed, t.colSupport, t.colHosting, t.colCac, t.profit, t.cash];
  return (
    <Card className="mt-4">
      <h2 className="text-navy">{t.yearsQ}</h2>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full text-left tabular-nums">
          <thead><tr className="border-b border-navy/20">{head.map((h) => <th key={h} className="py-1 pr-3 align-bottom">{h}</th>)}</tr></thead>
          <tbody>{m.years.map((y: any) => (
            <tr key={y.year} className="border-b border-navy/10">
              <td className="py-1 pr-3 font-bold">{y.year}</td><td className="pr-3">{num(y.customers_end)}</td>
              <td className="pr-3">{num(y.new)}</td><td className="pr-3">{num(y.lost)}</td>
              <td className="pr-3">{mxn(y.revenue)}</td><td className="pr-3">{mxn(y.cost_fixed)}</td><td className="pr-3">{mxn(y.cost_support)}</td>
              <td className="pr-3">{mxn(y.cost_hosting)}</td><td className="pr-3">{mxn(y.cost_acquisition)}</td>
              <td className={`pr-3 font-bold ${y.profit < 0 ? "text-danger" : ""}`}>{mxn(y.profit)}</td>
              <td className={`pr-3 ${y.cash_end < 0 ? "text-danger" : ""}`}>{mxn(y.cash_end)}</td>
            </tr>))}</tbody>
        </table>
      </div>
      <p className="mt-2 text-muted">{t.roundedNote}</p>
      <p className="mt-2 text-muted">
        {fill(t.costRules, { sup: values.institutions_per_support, sal: num(Number(a.support_salary_reference.value)),
          hy: Number(a.hosting_start_year.value), srv: values.institutions_per_server,
          usd: num(Number(a.hosting_server_usd.value) + Number(a.hosting_database_usd.value), 2),
          fx: num(Number(a.usd_mxn_fix.value), 4), cac: num(values.cac_per_institution) })}{" "}
        <Src row={a.support_salary_reference} /> · <Src row={a.hosting_server_usd} /> · <Src row={a.hosting_database_usd} /> · <Src row={a.usd_mxn_fix} /> · <Src row={a.cac_per_institution} />
      </p>
    </Card>
  );
}

function SourceTable({ rows }: { rows: Row[] }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left">
        <thead><tr className="border-b border-navy/20"><th className="py-1 pr-3">{t.colConcept}</th><th className="pr-3">{t.colValue}</th><th>{t.source}</th></tr></thead>
        <tbody>{rows.map((r) => (
          <tr key={r.key} className="border-b border-navy/10 align-top">
            <td className="py-1 pr-3">{r.description_es}</td>
            <td className="whitespace-nowrap pr-3 font-bold tabular-nums">{typeof r.value === "number" ? `${num(r.value, r.value % 1 ? 2 : 0)} ${t.units[r.unit] ?? r.unit}` : r.value}</td>
            <td><Src row={r} /></td>
          </tr>))}</tbody>
      </table>
    </div>
  );
}

function Competition({ d }: { d: any }) {
  return (
    <Card className="mt-4">
      <h2 className="text-navy">{t.competitionQ}</h2>
      <p className="mt-1 text-muted">{t.competitionNote}</p>
      <div className="mt-2"><SourceTable rows={[...d.plans, ...d.competitors]} /></div>
    </Card>
  );
}

function Usage({ d }: { d: any }) {
  const u = d.usage;
  const a = d.assumptions;
  return (
    <Card className="mt-4">
      <h2 className="text-navy">{t.usageQ}</h2>
      <p className="mt-1 text-muted">{t.usageNote} {u.first_activity && fill(t.since, { d: u.first_activity.split("-").reverse().join("/") })}</p>
      <div className="mt-3 grid gap-3 sm:grid-cols-3">
        <Kpi label={t.colCoordinated} value={num(u.totals.coordinated)} src={<span className="text-sm">{fill(t.autoPct, { pct: num(u.auto_pct, 1) })}</span>} />
        <Kpi label={t.hoursSaved} value={`${num(u.hours_saved, 1)} h`} src={<span className="text-sm">{fill(t.hoursNote, { min: a.minutes_per_manual_assignment.value })} <Src row={a.minutes_per_manual_assignment} /></span>} />
        <Kpi label={t.mrr} value={mxn(u.mrr)} src={<span className="text-sm text-muted">{t.mrrNote}</span>} />
      </div>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-left tabular-nums">
          <thead><tr className="border-b border-navy/20">{[t.colInstitution, t.colPlan, t.colCoordinated, t.colAuto, t.colManual, t.colTimeout].map((h) =>
            <th key={h} className="py-1 pr-3 align-bottom">{h}</th>)}</tr></thead>
          <tbody>{u.institutions.map((i: any) => (
            <tr key={i.institution_id} className="border-b border-navy/10">
              <td className="py-1 pr-3 font-bold">{i.name}</td><td className="pr-3">{i.plan} · {mxn(i.price)}</td>
              <td className="pr-3">{num(i.coordinated)}</td><td className="pr-3">{num(i.auto)}</td>
              <td className="pr-3">{num(i.manual)}</td><td className="pr-3">{num(i.timeout)}</td>
            </tr>))}</tbody>
        </table>
      </div>
    </Card>
  );
}

function Investment({ m }: { m: any }) {
  const u = m.unit, inv = m.investment;
  return (
    <section className="mt-4" aria-labelledby="inv-title">
      <h2 id="inv-title" className="text-navy">{t.investmentQ}</h2>
      <div className="mt-2 grid gap-3 md:grid-cols-3">
        <Kpi label={t.kpiInvestment} value={inv.month ? mxn(inv.amount) : t.noInvestment}
          src={inv.month && <span className="text-sm">{fill(t.kpiInvestmentWhen, { m: inv.month, y: Math.ceil(inv.month / 12) })} · <span className="text-muted">{t.derived}</span></span>} />
        <Kpi label={t.kpiLtvCac} value={u.ltv_cac == null ? "—" : `${num(u.ltv_cac, 1)} : 1`}
          src={<span className="text-sm">{fill(t.kpiLtvCacNote, { ltv: mxn(u.ltv), margin: mxn(u.margin_month), life: num(u.lifetime_months, 0),
            churn: num(m.inputs.monthly_churn, 1), cac: mxn(u.cac) })}</span>} />
        <Kpi label={t.kpiCacPayback} value={u.cac_payback_months == null ? "—" : fill(t.monthsValue, { n: num(u.cac_payback_months, 1) })}
          src={<span className="text-sm">{fill(t.kpiCacPaybackNote, { var: mxn(u.variable_cost_month) })}</span>} />
      </div>
      <p className="mt-2 text-muted">{t.unitNote}</p>
    </section>
  );
}

function WhatIf({ m }: { m: any }) {
  const w = m.what_if;
  const row = (label: string, value: number | null, now: number, fmt: (x: number) => string) => (
    <li className="rounded-card border border-navy/10 bg-white shadow-[var(--shadow-card)] p-4">
      <p className="text-muted">{label}</p>
      <p className="figure text-2xl">{value == null ? t.whatIfNone : fmt(value)}</p>
      <p className="text-sm">{fill(t.whatIfNow, { v: fmt(now) })}</p>
    </li>);
  return (
    <Card className="mt-4">
      <h2 className="text-navy">{fill(t.whatIfQ, { r: num(w.rate_pct) })}</h2>
      {w.npv_now >= 0 ? <p className="mt-1">{fill(t.whatIfAlready, { r: num(w.rate_pct), npv: mxn(w.npv_now) })}</p> : (<>
        <p className="mt-1 text-muted">{t.whatIfIntro}</p>
        <ul className="mt-3 grid gap-3 md:grid-cols-3">
          {row(t.whatIfPrice, w.plan_professional_price, w.current_professional_price, (x) => mxn(Math.ceil(x)))}
          {row(t.whatIfCustomers, w.customers_year5, w.current_customers_year5, (x) => num(Math.ceil(x)))}
          {row(t.whatIfCac, w.cac, w.current_cac, (x) => mxn(Math.floor(x)))}
        </ul></>)}
    </Card>
  );
}

function RealMarket({ a, m }: { a: Record<string, Row>; m: any }) {
  const mk = m.market;
  const cell = (k: string) => (a[k] ? num(Number(a[k].value)) : "—");
  const rows = [
    ["residences", "denue_residences_private_cdmx", "denue_residences_public_cdmx", "denue_residences_private_edomex", "denue_residences_public_edomex"],
    ["day_centers", "denue_day_centers_private_cdmx", "denue_day_centers_public_cdmx", "denue_day_centers_private_edomex", "denue_day_centers_public_edomex"],
    ["home_nursing", "denue_home_nursing_cdmx", "", "denue_home_nursing_edomex", ""],
  ];
  const pct = (x: number | null) => (x == null ? "—" : `${num(x, 1)} %`);
  return (
    <Card className="mt-4">
      <h2 className="text-navy">{t.marketRealQ}</h2>
      <p className="mt-1 text-muted">{t.marketRealIntro} <Src row={a.denue_residences_private_cdmx} /> · <Src row={a.target_market_private_only} /></p>
      <div className="mt-2 overflow-x-auto">
        <table className="w-full text-left tabular-nums">
          <thead><tr className="border-b border-navy/20">{[t.segment, t.privateCdmx, t.publicCdmx, t.privateEdomex, t.publicEdomex].map((h) =>
            <th key={h} className="py-1 pr-3">{h}</th>)}</tr></thead>
          <tbody>
            {rows.map(([seg, ...keys]) => (
              <tr key={seg} className="border-b border-navy/10">
                <td className="py-1 pr-3">{t.segments[seg]}</td>{keys.map((k, i) => <td key={i} className="pr-3">{k ? cell(k) : "—"}</td>)}
              </tr>))}
            <tr className="border-b border-navy/10"><td className="py-1 pr-3">{t.segments.geriatric}</td><td colSpan={4} className="text-muted">{t.noClass}</td></tr>
          </tbody>
        </table>
      </div>
      <ul className="mt-3 space-y-1">
        {["cdmx", "edomex"].map((r) => (
          <li key={r} className="text-lg">{fill(t.shareLine, { region: t.region[r], n: num(mk[r].customers_year5), base: num(mk[r].target_establishments),
            pct: pct(mk[r].share_pct) })}</li>))}
      </ul>
      <p className="mt-1 text-muted">{fill(t.expansionNote, { y: Number(a.edomex_start_year.value), s: Number(a.edomex_share_of_new.value) })} <Src row={a.edomex_start_year} /> <span className="text-sm text-muted">({t.derived})</span></p>
      <p className={`mt-2 font-bold ${mk.too_high ? "text-danger" : "text-ok"}`}>
        {fill(mk.too_high ? t.shareHigh : t.shareOk, { a: num(mk.alert_pct) })} <Src row={a.market_share_alert} /></p>
    </Card>
  );
}

function Scenarios({ m, a, values }: { m: any; a: Record<string, Row>; values: Record<string, any> }) {
  const s = m.scenarios;
  const keys = ["base", "conservative", "recommended"];
  const r = s.rate_pct;
  const month = (x: number | null) => (x ? fill(t.monthAt, { m: x }) + ` (${t.year.toLowerCase()} ${Math.ceil(x / 12)})` : t.never);
  const share = (k: string, region: string) => {
    const x = s[k].shares[region];
    return x.customers < 0.05 ? t.notOpen : `${num(x.share_pct, 1)} % (${num(x.customers)} de ${num(x.establishments)})`;
  };
  const rows: [string, (k: string) => ReactNode][] = [
    [t.rowInvestment, (k) => <>{mxn(s[k].investment.amount)}{s[k].investment.month && <span className="block text-sm text-muted">{fill(t.monthAt, { m: s[k].investment.month })}</span>}</>],
    [t.rowBreakeven, (k) => month(s[k].breakeven_month)],
    [t.rowPayback, (k) => month(s[k].payback_month)],
    [fill(t.rowNpv, { r: num(r) }), (k) => <span className={`font-bold ${s[k].npv[1].npv < 0 ? "text-danger" : "text-ok"}`}>{mxn(s[k].npv[1].npv)}</span>],
    [t.rowCustomers, (k) => fill(t.rowCustomersValue, { total: num(s[k].customers_year5), priv: num(s[k].private_year5), gov: num(s[k].government_year5) })],
    ...["cdmx", "edomex", "jalisco", "nuevoleon"].map((reg) => [fill(t.rowShare, { region: t.region4[reg] }), (k: string) => share(k, reg)] as [string, (k: string) => ReactNode]),
    [t.rowGovShare, (k) => (s[k].government_year5 < 0.05 ? "—" : `${num(s[k].government_share_pct, 1)} % (${num(s[k].government_year5)} de ${num(s[k].public_day_centers)})`)],
  ];
  const help = (k: string) => fill(t.scenHelp[k], { cap: num(values.recommended_private_cap), y: Number(a.recommended_new_states_year.value),
    price: mxn(values.plan_government_price), cycle: num(values.government_sales_cycle_months), gcap: num(values.government_cap),
    fpct: num(values.founder_salary_year1_recommended) });
  const miss = s.recommended_missing;
  const opt = (x: number | null, f: (n: number) => string) => (x == null ? t.whatIfNone : f(x));
  return (
    <Card className="mt-4">
      <h2 className="text-navy">{t.scenariosQ}</h2>
      <p className="mt-1 text-muted">{t.scenariosIntro}</p>
      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-left tabular-nums">
          <thead><tr className="border-b border-navy/20 align-bottom">
            <th className="py-1 pr-3" />
            {keys.map((k) => (
              <th key={k} className={`py-2 pr-3 ${k === "recommended" ? "rounded-t-card bg-navy/10" : ""}`}>
                {k === "recommended" ? <span className="rounded bg-navy px-2 py-0.5 text-white">{t.recommendedBadge}</span> : t.scen[k]}
                <span className="block text-sm font-normal text-muted">{help(k)}</span>
              </th>))}
          </tr></thead>
          <tbody>{rows.map(([label, f]) => (
            <tr key={label} className="border-b border-navy/10 align-top">
              <th scope="row" className="py-1.5 pr-3 font-bold">{label}</th>
              {keys.map((k) => <td key={k} className={`py-1.5 pr-3 ${k === "recommended" ? "bg-navy/10" : ""}`}>{f(k)}</td>)}
            </tr>))}</tbody>
        </table>
      </div>
      {s.recommended_positive ? (
        <p className="mt-3">{fill(t.recommendedOk, { r: num(r), npv: mxn(s.recommended.npv[1].npv), noGov: mxn(s.recommended_without.government),
          noCut: mxn(s.recommended_without.founder_cut), both: mxn(s.recommended_without.both) })}</p>
      ) : (<>
        <p className="mt-3 font-bold text-danger">{fill(t.recommendedNo, { r: num(r), npv: mxn(s.recommended.npv[1].npv) })}</p>
        <ul className="mt-1 list-disc pl-6">
          <li>{fill(t.missingPrice, { v: opt(miss.plan_professional_price, (x) => mxn(Math.ceil(x))), now: mxn(miss.current_professional_price) })}</li>
          <li>{fill(t.missingGov, { v: opt(miss.plan_government_price, (x) => mxn(Math.ceil(x))), now: mxn(miss.current_government_price) })}</li>
          <li>{fill(t.missingCac, { v: opt(miss.cac, (x) => mxn(Math.floor(x))), now: mxn(miss.current_cac) })}</li>
          <li>{fill(t.missingCap, { v: opt(miss.recommended_private_cap, (x) => `${num(x, 1)} %`), now: `${num(miss.current_private_cap)} %` })}</li>
        </ul></>)}
      <p className="mt-2 text-sm text-muted"><Src row={a.plan_government_price} /> {a.plan_government_price.description_es}</p>
    </Card>
  );
}
