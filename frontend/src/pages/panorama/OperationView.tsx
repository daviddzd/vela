// Vista Operación (MIS, real time): counters, punctuality / unattended (baseline before Vela vs with Vela),
// staff load (visit + travel) and queue by priority. Re-reads on every /ws/board event (step 4).
import { Radio, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { api } from "../../api/client";
import { ChartLegend } from "../../charts/ChartLegend";
import { EChart, esc } from "../../charts/EChart";
import { axisCommon, baseOption, chart } from "../../charts/theme";
import { ChartCard } from "../../components/ChartCard";
import { COUNTER_ICON, Icon, PRIORITY_ICON } from "../../components/icons";
import { Card } from "../../components/ui";
import { es } from "../../i18n/es";
import { useBoardSocket } from "../../lib/useBoardSocket";
import { num, pct, shortDay } from "./format";
import type { Filters, Operation } from "./types";

const t = es.panorama;
const COUNTERS = ["queued", "on_the_way", "in_visit", "done_today"] as const;
const BASELINE = chart.muted;      // gray dashed = before Vela
const VELA = chart.series[0];      // teal solid = with Vela

export function OperationView({ filters }: { filters: Filters }) {
  const [data, setData] = useState<Operation | null>(null);
  const [mode, setMode] = useState<"today" | "history">("today");
  const timer = useRef<ReturnType<typeof setTimeout> | undefined>(undefined);

  const load = useCallback(() => {
    clearTimeout(timer.current);
    timer.current = setTimeout(() => api.panorama<Operation>("operation", filters).then(setData).catch(() => undefined), 300);
  }, [filters]);
  useEffect(load, [load]);
  const socket = useBoardSocket(load);
  // If nobody has hours today yet (early morning, or a day institution at night), start on the 30-day view.
  const autoMode = useRef(false);
  useEffect(() => {
    if (data && !autoMode.current) {
      autoMode.current = true;
      if (!data.staff_load.some((s) => s.hours_today > 0)) setMode("history");
    }
  }, [data]);

  // One small chart per measure (punctuality, unattended); each has the baseline and the "with Vela" line.
  const periodChart = useCallback((key: "on_time_pct" | "unattended_pct") => {
    if (!data) return null;
    const days = [...new Set(data.daily.map((d) => d.day))];
    const value = (day: string, period: string) => data.daily.find((d) => d.day === day && d.period === period)?.[key] ?? null;
    return {
      ...baseOption(), legend: { show: false },
      grid: { left: 8, right: 52, top: 12, bottom: 8, containLabel: true },
      tooltip: { ...baseOption().tooltip as object, trigger: "axis", axisPointer: { type: "line", lineStyle: { color: chart.muted } },
        valueFormatter: (v: number | null) => (v == null ? "—" : `${num(v, 1)} %`) },
      xAxis: { ...axisCommon, type: "category", data: days.map(shortDay), splitLine: { show: false },
        axisLabel: { ...axisCommon.axisLabel, hideOverlap: true } },
      yAxis: { ...axisCommon, type: "value", min: 0, max: key === "on_time_pct" ? 100 : (v: { max: number }) => Math.max(40, Math.ceil(v.max / 10) * 10),
        axisLabel: { ...axisCommon.axisLabel, formatter: "{value} %" } },
      series: [
        { name: t.baseline, type: "line", data: days.map((d) => value(d, "baseline")), showSymbol: false, connectNulls: false,
          lineStyle: { width: 2, type: [5, 4], color: BASELINE }, itemStyle: { color: BASELINE } },
        { name: t.withVela, type: "line", data: days.map((d) => value(d, "vela")), symbol: "circle", symbolSize: 8,
          showSymbol: true, connectNulls: true, lineStyle: { width: 2, color: VELA }, itemStyle: { color: VELA, borderColor: "#FFFFFF", borderWidth: 2 },
          endLabel: { show: true, formatter: "{c} %", color: chart.ink } },
      ],
    };
  }, [data]);
  const onTimeOption = useMemo(() => periodChart("on_time_pct"), [periodChart]);
  const unattendedOption = useMemo(() => periodChart("unattended_pct"), [periodChart]);

  const staff = data?.staff_load ?? [];
  const loadRows = mode === "today" ? staff.filter((s) => s.hours_today > 0) : staff.filter((s) => s.avg_hours_per_day > 0);
  const loadOption = useMemo(() => ({
    ...baseOption(), legend: { show: false },
    grid: { left: 8, right: 16, top: 8, bottom: 8, containLabel: true },
    tooltip: { ...baseOption().tooltip as object, trigger: "item",
      formatter: (p: any) => `<strong>${num(p.value, 1)} h</strong> ${esc(p.seriesName)}<br/>${esc(p.name)}` },
    xAxis: { ...axisCommon, type: "value", axisLabel: { ...axisCommon.axisLabel, formatter: "{value} h" } },
    yAxis: { ...axisCommon, type: "category", inverse: true, data: loadRows.map((s) => s.name), splitLine: { show: false } },
    series: [
      { name: t.loadHoursSeries, type: "bar", barMaxWidth: 16, itemStyle: { color: VELA, borderRadius: [0, 4, 4, 0] },
        data: loadRows.map((s) => (mode === "today" ? s.hours_today : s.avg_hours_per_day)) },
      { name: t.loadShift, type: "scatter", symbol: "rect", symbolSize: [3, 22], itemStyle: { color: chart.ink },
        data: loadRows.map((s) => s.shift_hours), z: 3 },
    ],
  }), [loadRows, mode]);

  if (!data) return <p>{es.common.loading}</p>;
  const queued = data.queue_by_priority.reduce((a, q) => a + q.waiting, 0);
  const withHoursToday = staff.filter((s) => s.hours_today > 0).length;
  const worked = staff.filter((s) => s.avg_hours_per_day > 0);
  const avgHistory = worked.length ? worked.reduce((a, s) => a + s.avg_hours_per_day, 0) / worked.length : 0;
  const { baseline, vela } = data.periods;
  const periodLegend = [{ label: t.baseline, color: BASELINE, kind: "dashed" as const }, { label: t.withVela, color: VELA, kind: "line" as const }];
  const compare = (label: string, before: number | null, after: number | null, empty: string) => (
    <li><strong>{label}:</strong> {pct(before)} {t.before} · {after == null ? <span className="text-muted">{empty}</span> : <strong>{pct(after)} {t.withVelaShort}</strong>}</li>
  );

  return (
    <div className="space-y-4">
      <p className="font-bold" aria-live="polite">
        {socket === "live" ? <span className="text-ok"><Icon as={Radio} /> {t.live}</span>
          : socket === "reconnecting" ? <span className="text-warn"><Icon as={RefreshCw} /> {es.board.reconnecting}</span>
          : <span className="text-muted">{es.board.connecting}</span>}
      </p>
      <ul className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        {COUNTERS.map((k) => (
          <li key={k}><Card className="text-center">
            <p className="figure text-4xl text-teal">{data.counters[k]}</p>
            <p className="font-bold"><Icon as={COUNTER_ICON[k]} /> {es.board.counters[k]}</p>
          </Card></li>
        ))}
      </ul>

      <div className="grid gap-4 xl:grid-cols-2">
        <ChartCard question={t.onTimeQ} keyValue={pct(vela.on_time_pct ?? baseline.on_time_pct)}
          keyLabel={vela.on_time_pct == null ? `${t.onTimeKey} · ${t.baseline}` : `${t.onTimeKey} · ${t.withVela}`}
          note={t.onTimeNote} source={t.onTimeSource}
          table={{ columns: ["Día", t.period, t.onTimeSeries, t.unattendedSeries, "Visitas"],
            rows: data.daily.map((d) => [shortDay(d.day), d.period === "baseline" ? t.baseline : t.withVela,
              pct(d.on_time_pct), pct(d.unattended_pct), d.visits]) }}>
          <ul className="mb-3 space-y-1">
            {compare(t.onTimeSeries, baseline.on_time_pct, vela.on_time_pct, t.noVelaYet)}
            {compare(t.unattendedSeries, baseline.unattended_pct, vela.unattended_pct, t.noVelaYet)}
          </ul>
          <ChartLegend items={periodLegend} />
          <h3 className="font-bold">{t.onTimeSeries}</h3>
          {onTimeOption && <EChart option={onTimeOption} height={200} label={`${t.onTimeSeries}: ${t.baseline} ${pct(baseline.on_time_pct)}`} />}
          <h3 className="mt-3 font-bold">{t.unattendedSeries}</h3>
          {unattendedOption && <EChart option={unattendedOption} height={170} label={`${t.unattendedSeries}: ${t.baseline} ${pct(baseline.unattended_pct)}`} />}
        </ChartCard>

        <ChartCard question={t.loadQ}
          keyValue={mode === "today" ? withHoursToday : num(avgHistory, 1)}
          keyLabel={mode === "today" ? t.loadKeyLabel : t.loadKeyHistory}
          note={t.loadNote} source={t.loadSource}
          table={{ columns: ["Persona", t.loadToday, t.loadHistory, t.loadShift],
            rows: staff.map((s) => [s.name, num(s.hours_today, 1), num(s.avg_hours_per_day, 1), num(s.shift_hours, 1)]) }}>
          <fieldset className="mb-2 flex flex-wrap gap-x-4">
            <legend className="sr-only">{t.loadQ}</legend>
            {(["today", "history"] as const).map((m) => (
              <label key={m} className="flex min-h-12 items-center gap-2">
                <input type="radio" name="load-mode" checked={mode === m} onChange={() => setMode(m)} className="size-6 accent-teal" />
                {m === "today" ? t.loadToday : t.loadHistory}
              </label>
            ))}
          </fieldset>
          {loadRows.length === 0 ? <p>{t.loadEmptyToday}</p> : <>
            <ChartLegend items={[{ label: t.loadHoursSeries, color: VELA, kind: "bar" }, { label: t.loadShift, color: chart.ink, kind: "tick" }]} />
            <EChart option={loadOption} height={Math.max(220, 30 * loadRows.length + 40)} label={t.loadQ} />
          </>}
        </ChartCard>
      </div>

      <ChartCard question={t.queueQ} keyValue={queued} keyLabel={t.queueKeyLabel} source={t.queueSource}>
        <ul className="grid gap-3 sm:grid-cols-3">
          {data.queue_by_priority.map((q) => (
            <li key={q.priority} className="rounded-card border-2 border-teal/20 p-3">
              <p className="font-bold"><Icon as={PRIORITY_ICON[q.priority]} /> {es.priority[q.priority]}</p>
              <p className="figure text-3xl">{q.waiting}</p>
              <p className="text-muted">{q.max_wait_min == null ? t.noWait : `${t.maxWait}: ${q.max_wait_min} ${es.common.minutes}`}</p>
            </li>
          ))}
        </ul>
      </ChartCard>
    </div>
  );
}
