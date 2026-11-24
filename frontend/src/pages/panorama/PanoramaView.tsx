// Vista Panorama (DSS): where the 60+ population with more risk lives, which conditions weigh more,
// air quality vs contingency threshold, traffic by hour, and (step 6) SIRAG-D results.
import { useEffect, useMemo, useState } from "react";
import { api } from "../../api/client";
import { EChart, echarts, esc } from "../../charts/EChart";
import { axisCommon, baseOption, chart } from "../../charts/theme";
import { ChartCard } from "../../components/ChartCard";
import { ChartLegend } from "../../charts/ChartLegend";
import { AlertTriangle, Ban, CheckCircle2, FlaskConical, Icon } from "../../components/icons";
import { CIChart } from "../../charts/CIChart";
import { Link } from "react-router";
import { ciRows, conclusion, fmt, OPERATING, pick, type Results } from "../simulation/data";
import { Notice, inputClass } from "../../components/ui";
import { es } from "../../i18n/es";
import { dayHour, num, pct } from "./format";
import type { Air, Boundaries, Filters, Population, Traffic } from "./types";

const t = es.panorama;
const INDICATORS = ["multimorbidity_pct", "multimorbidity_broad_pct", "dependency_moderate_severe_pct", "pollution_sensitive_pct"] as const;
type Indicator = (typeof INDICATORS)[number];

/** Five equal-width classes between the min and max of the indicator (shown in the legend with units). */
function classes(values: number[]) {
  const lo = Math.floor(Math.min(...values)), hi = Math.ceil(Math.max(...values));
  const step = Math.max(0.5, (hi - lo) / 5);
  return chart.ramp.map((color, i) => ({
    min: lo + i * step, max: i === 4 ? hi + 0.01 : lo + (i + 1) * step, color,
    label: `${num(lo + i * step, 1)}–${num(i === 4 ? hi : lo + (i + 1) * step, 1)} %`,
  }));
}

function useNarrow(): boolean {
  const [narrow, setNarrow] = useState(window.innerWidth < 640);
  useEffect(() => {
    const on = () => setNarrow(window.innerWidth < 640);
    window.addEventListener("resize", on);
    return () => window.removeEventListener("resize", on);
  }, []);
  return narrow;
}

export function PanoramaView({ filters }: { filters: Filters }) {
  const narrow = useNarrow();
  const [pop, setPop] = useState<Population | null>(null);
  const [geo, setGeo] = useState<Boundaries | null>(null);
  const [air, setAir] = useState<Air | null>(null);
  const [traffic, setTraffic] = useState<Traffic | null>(null);
  const [indicator, setIndicator] = useState<Indicator>("multimorbidity_pct");
  const [station, setStation] = useState<string | undefined>();

  useEffect(() => { api.panorama<Population>("population", { district: filters.district }).then(setPop); }, [filters.district]);
  useEffect(() => {
    api.panorama<Boundaries>("boundaries").then((b) => {
      if (b.available) echarts.registerMap("cdmx", b.geojson);
      setGeo(b);
    });
    api.panorama<Traffic>("traffic").then(setTraffic);
  }, []);
  useEffect(() => {
    api.panorama<Air>("air", { station, district: filters.district, from: filters.from, to: filters.to }).then(setAir);
  }, [station, filters.district, filters.from, filters.to]);

  // ---- choropleth ----
  const mapOption = useMemo(() => {
    if (!pop || !geo) return null;
    const rows = pop.districts;
    const pieces = classes(rows.map((r) => r[indicator]));
    const tooltip = { ...baseOption().tooltip as object, trigger: "item",
      formatter: (p: any) => p.data ? `<strong>${num(Array.isArray(p.data.value) ? p.data.value[2] : p.data.value, 1)} %</strong><br/>${esc(p.data.label)}<br/>${num(p.data.persons)} ${t.persons}` : "" };
    // The legend is drawn in HTML below the map (ranges + units, wraps on a phone); ECharts only maps colors.
    const visualMap = { type: "piecewise", pieces, show: false };
    const data = rows.map((r) => ({ name: r.district_id, label: r.district_name, value: r[indicator], persons: r.persons_60_plus,
      selected: r.district_id === filters.district }));
    if (geo.available) {
      return { ...baseOption(), tooltip, visualMap,
        series: [{ type: "map", map: "cdmx", nameProperty: "district_id", roam: false, layoutCenter: ["50%", "50%"],
          layoutSize: "96%", selectedMode: false, showLegendSymbol: false, data,
          itemStyle: { borderColor: "#FFFFFF", borderWidth: 2 },
          emphasis: { label: { show: false }, itemStyle: { areaColor: undefined, borderColor: chart.ink, borderWidth: 2 } },
          select: { disabled: true },
          // the district picked in the filter gets an ink outline (not a color change)
          regions: filters.district ? [{ name: filters.district, itemStyle: { borderColor: chart.ink, borderWidth: 3 } }] : [] }] };
    }
    const pts = new Map(geo.points.map((p) => [p.district_id, p]));
    return { ...baseOption(), tooltip, visualMap: { ...visualMap, dimension: 2 },
      xAxis: { ...axisCommon, type: "value", scale: true, show: false }, yAxis: { ...axisCommon, type: "value", scale: true, show: false },
      series: [{ type: "scatter", symbolSize: 28, itemStyle: { borderColor: "#FFFFFF", borderWidth: 2 },
        data: data.map((d) => ({ ...d, value: [pts.get(d.name)!.lon, pts.get(d.name)!.lat, d.value] })) }] };
  }, [pop, geo, indicator, filters.district]);

  // ---- prevalence (synthetic vs reference; adjusted references are a separate, labelled series) ----
  const prevOption = useMemo(() => {
    if (!pop) return null;
    const rows = pop.conditions;
    return { ...baseOption(),
      color: chart.series,
      grid: { left: 8, right: 24, top: 8, bottom: 8, containLabel: true },
      tooltip: { ...baseOption().tooltip as object, trigger: "axis", axisPointer: { type: "shadow", shadowStyle: { color: "rgba(0,0,0,0.04)" } },
        valueFormatter: (v: number | null) => (v == null ? "—" : `${num(v, 1)} %`) },
      legend: { show: false },
      xAxis: { ...axisCommon, type: "value", interval: narrow ? 25 : 10, max: narrow ? 50 : undefined,
        axisLabel: { ...axisCommon.axisLabel, formatter: "{value} %" } },
      yAxis: { ...axisCommon, type: "category", inverse: true, splitLine: { show: false },
        data: rows.map((r) => t.conditions[r.condition] ?? r.condition) },
      series: [
        { name: t.prevalenceSynthetic, type: "bar", barMaxWidth: 10, barGap: "20%", itemStyle: { borderRadius: [0, 4, 4, 0] },
          data: rows.map((r) => r.prevalence_pct) },
        { name: t.prevalenceReference, type: "bar", barMaxWidth: 10, itemStyle: { borderRadius: [0, 4, 4, 0] },
          data: rows.map((r) => (r.reference && !r.reference.adjusted ? r.reference.reference_pct : null)) },
        { name: t.prevalenceAdjusted, type: "bar", barMaxWidth: 10, itemStyle: { borderRadius: [0, 4, 4, 0] },
          data: rows.map((r) => (r.reference?.adjusted ? r.reference.reference_pct : null)) },
      ] };
  }, [pop, narrow]);

  // ---- air: two small multiples (different units → never a dual axis) ----
  const airOption = (key: "o3" | "pm25_24h", limit: number, _label: string) => air && ({
    ...baseOption(), color: [chart.series[0]],
    grid: { left: 8, right: 16, top: 24, bottom: 8, containLabel: true },
    tooltip: { ...baseOption().tooltip as object, trigger: "axis", axisPointer: { type: "line", lineStyle: { color: chart.muted } },
      formatter: (ps: any[]) => `<strong>${num(ps[0]?.value?.[1], 1)}</strong><br/>${esc(dayHour(ps[0]?.value?.[0]))}` },
    xAxis: { ...axisCommon, type: "time", splitLine: { show: false }, axisLabel: { ...axisCommon.axisLabel, hideOverlap: true,
      formatter: (v: number) => new Intl.DateTimeFormat("es-MX", { timeZone: "America/Mexico_City", day: "2-digit", month: "2-digit", year: "numeric" }).format(new Date(v)) } },
    yAxis: { ...axisCommon, type: "value", min: 0, max: Math.ceil((limit * 1.1) / 20) * 20 },
    series: [{ type: "line", showSymbol: false, lineStyle: { width: 2 }, data: air.series.map((p) => [p.t, p[key]]),
      // period of an ACTIVE demo scenario, labelled so nobody confuses it with real readings
      markArea: scenarioSpan(air.series) ? { silent: true, itemStyle: { color: "rgba(183,121,31,0.12)" },
        label: { show: true, position: "insideTop", color: chart.ink, fontFamily: chart.font, formatter: t.demoScenario },
        data: [[{ xAxis: scenarioSpan(air.series)![0] }, { xAxis: scenarioSpan(air.series)![1] }]] } : undefined,
      markLine: { silent: true, symbol: "none", lineStyle: { color: chart.threshold, width: 2, type: "solid" },
        label: { formatter: `${t.threshold}: ${limit}`, position: "insideEndTop", color: chart.ink, fontFamily: chart.font },
        data: [{ yAxis: limit }] } }],
  });

  // ---- traffic heatmap ----
  const trafficOption = useMemo(() => traffic && ({
    ...baseOption(),
    grid: { left: 8, right: 8, top: 8, bottom: 64, containLabel: true },
    tooltip: { ...baseOption().tooltip as object, trigger: "item",
      formatter: (p: any) => `<strong>${num(p.value[2], 1)} %</strong> ${esc(t.congestion)}<br/>${esc(p.value[1] === 0 ? t.weekday : t.weekend)} · ${p.value[0]}:00 h<br/>${esc(t.speed)}: ${num(p.data.speed, 1)} km/h` },
    xAxis: { ...axisCommon, type: "category", data: [...Array(24).keys()].map((h) => `${h}`), splitLine: { show: false },
      name: t.hour, nameLocation: "middle", nameGap: 26, nameTextStyle: { color: chart.muted },
      axisLabel: { ...axisCommon.axisLabel, interval: 2 } },
    yAxis: { ...axisCommon, type: "category", data: [t.weekday, t.weekend], splitLine: { show: false } },
    visualMap: { type: "continuous", min: 0, max: Math.ceil(traffic.peak.congestion_pct / 10) * 10, inRange: { color: chart.ramp },
      orient: "horizontal", left: "center", bottom: 0, itemHeight: 160, calculable: false,
      text: [`${Math.ceil(traffic.peak.congestion_pct / 10) * 10} %`, "0 %"], textStyle: { color: chart.ink } },
    series: [{ type: "heatmap", itemStyle: { borderColor: "#FFFFFF", borderWidth: 2, borderRadius: 4 },
      data: traffic.cells.map((c) => ({ value: [c.hour, c.day_type === "weekday" ? 0 : 1, c.congestion_pct], speed: c.avg_speed_kmh })) }],
  }), [traffic]);

  if (!pop) return <p>{es.common.loading}</p>;
  const ranked = [...pop.districts].sort((a, b) => b[indicator] - a[indicator]);
  const selected = filters.district ? pop.districts.find((d) => d.district_id === filters.district) : null;
  const top = pop.conditions[0];
  const st = air?.stations.find((s) => s.station_id === air.station);
  const airLevel = !air?.max_o3 ? null
    : air.max_o3 >= air.thresholds.o3_ppb_1h ? { icon: Ban, text: t.airPhase1, cls: "text-danger" }
    : air.max_o3 >= air.thresholds.o3_ppb_1h * air.thresholds.watch_fraction ? { icon: AlertTriangle, text: t.airWatch, cls: "text-warn" }
    : { icon: CheckCircle2, text: t.airOk, cls: "text-ok" };

  return (
    <div className="items-start grid gap-4 xl:grid-cols-2">
      <ChartCard className="xl:col-span-2" question={t.riskQ}
        keyValue={pct(selected ? selected[indicator] : pop.city[indicator])}
        keyLabel={selected ? `${selected.district_name}` : t.cityValue}
        source={indicator === "multimorbidity_broad_pct" ? `${t.riskSource}; ${t.broadRefSource}` : t.riskSource}
        note={<>{t.highest}: <strong className="text-ink">{ranked[0].district_name}</strong> ({pct(ranked[0][indicator])})
          {indicator === "multimorbidity_broad_pct" && pop.indicator_reference.multimorbidity_broad_pct && (
            <span className="mt-2 block rounded-card border-2 border-navy/30 p-2 text-ink">
              <strong>{t.broadCompare}: </strong>{pct(pop.city.multimorbidity_broad_pct)} {t.inVela} · {" "}
              <strong>{pct(pop.indicator_reference.multimorbidity_broad_pct.reference_pct)}</strong> ENSANUT 2018-19.{" "}
              <span className="text-muted">{t.broadCaveat}</span>
            </span>)}</>}
        table={{ columns: [t.district, t.indicators[indicator], t.persons],
          rows: ranked.map((r) => [r.district_name, pct(r[indicator]), num(r.persons_60_plus)]) }}>
        <fieldset className="mb-2 flex flex-wrap gap-x-6">
          <legend className="sr-only">{t.riskQ}</legend>
          {INDICATORS.map((k) => (
            <label key={k} className="flex min-h-12 items-center gap-2">
              <input type="radio" name="indicator" checked={indicator === k} onChange={() => setIndicator(k)} className="size-6 accent-navy" />
              {t.indicators[k]}
            </label>
          ))}
        </fieldset>
        {geo && !geo.available && <Notice>{t.noBoundaries}</Notice>}
        {mapOption && <EChart option={mapOption} height={narrow ? 340 : 460} label={`${t.riskQ} ${t.indicators[indicator]}`} />}
        <MapLegend title={t.indicators[indicator]} pieces={classes(pop.districts.map((r) => r[indicator]))} />
      </ChartCard>

      <ChartCard question={t.prevalenceQ} keyValue={pct(top?.prevalence_pct)}
        keyLabel={`${t.conditions[top?.condition] ?? ""} · ${t.prevalenceKeyLabel}`}
        note={<>{filters.district && <>{t.filterNotApplied} </>}{t.prevalenceNote}</>} source={t.prevalenceSource}
        table={{ columns: ["Condición", t.prevalenceSynthetic, "Referencia", "Encuesta"],
          rows: pop.conditions.map((c) => [t.conditions[c.condition] ?? c.condition, pct(c.prevalence_pct),
            c.reference ? `${pct(c.reference.reference_pct)}${c.reference.adjusted ? " (ajustada ×0.57, supuesto)" : ""}` : "—",
            c.reference?.survey ?? "—"]) }}>
        <ChartLegend items={[{ label: t.prevalenceSynthetic, color: chart.series[0], kind: "bar" },
          { label: t.prevalenceReference, color: chart.series[1], kind: "bar" },
          { label: t.prevalenceAdjusted, color: chart.series[2], kind: "bar" }]} />
        {prevOption && <EChart option={prevOption} height={520} label={t.prevalenceQ} />}
      </ChartCard>

      <ChartCard question={t.airQ} keyValue={num(air?.max_o3, 1)} keyLabel={t.airKeyLabel} source={t.airSource}
        note={<>{airLevel && <strong className={airLevel.cls}><Icon as={airLevel.icon} /> {airLevel.text}</strong>}
          {" "}{t.dataUntil} {air?.data_until}. {st?.location_source === "approximate" ? t.approximate : ""}</>}
        table={air ? { columns: ["Hora", "O₃ (ppb)", "PM2.5 24 h (µg/m³)"],
          rows: air.series.filter((_, i) => i % 6 === 0).map((p) => [dayHour(p.t), num(p.o3, 1), num(p.pm25_24h, 1)]) } : undefined}>
        <label className="block max-w-sm"><span className="font-bold">{t.station}</span>
          <select className={inputClass} value={air?.station ?? ""} onChange={(e) => setStation(e.target.value)}>
            {air?.stations.map((s) => <option key={s.station_id} value={s.station_id}>{s.station_id} · {s.name} ({s.district_name})</option>)}
          </select>
        </label>
        {air && <div className="mt-3 flex flex-1 flex-col gap-4">
          <ChartLegend items={[{ label: t.airSeries, color: chart.series[0], kind: "line" },
            { label: t.threshold, color: chart.threshold, kind: "line" }]} />
          <div className="flex flex-1 flex-col"><h3 className="font-bold">{t.o3Title}</h3>
            <EChart option={airOption("o3", air.thresholds.o3_ppb_1h, t.o3Title)!} height={220} label={t.o3Title} /></div>
          <div className="flex flex-1 flex-col"><h3 className="font-bold">{t.pm25Title}</h3>
            <EChart option={airOption("pm25_24h", air.thresholds.pm25_ugm3_24h, t.pm25Title)!} height={220} label={t.pm25Title} /></div>
        </div>}
      </ChartCard>

      <ChartCard question={t.trafficQ} keyValue={traffic ? pct(traffic.peak.congestion_pct) : "—"}
        keyLabel={traffic ? `${t.trafficKeyLabel}, ${t.trafficPeakAt.replace("{hour}", String(traffic.peak.hour))}` : ""}
        note={<>{filters.district && <>{t.filterNotApplied} </>}{t.trafficNote}</>} source={t.trafficSource}
        table={traffic ? { columns: [t.hour, `${t.weekday} (${t.congestion})`, `${t.weekend} (${t.congestion})`],
          rows: [...Array(24).keys()].map((h) => [`${h}:00`,
            pct(traffic.cells.find((c) => c.hour === h && c.day_type === "weekday")?.congestion_pct),
            pct(traffic.cells.find((c) => c.hour === h && c.day_type === "weekend")?.congestion_pct)]) } : undefined}>
        {trafficOption && <EChart option={trafficOption} height={220} label={t.trafficQ} />}
      </ChartCard>

      <SimulationCard />
    </div>
  );
}

function scenarioSpan(series: { t: string; scenario?: boolean }[]): [string, string] | null {
  const s = series.filter((p) => p.scenario);
  return s.length ? [s[0].t, s[s.length - 1].t] : null;
}

function MapLegend({ title, pieces }: { title: string; pieces: { color: string; label: string }[] }) {
  return (
    <div className="mt-2">
      <p className="text-sm font-bold">{title}</p>
      <ul className="mt-1 flex flex-wrap gap-x-4 gap-y-1">
        {pieces.map((p) => (
          <li key={p.label} className="flex items-center gap-2 text-sm tabular-nums">
            <span aria-hidden="true" className="inline-block h-3 w-5 rounded-sm" style={{ background: p.color }} />{p.label}
          </li>
        ))}
      </ul>
    </div>
  );
}

// "¿Qué política conviene?": SIRAG-D results (step 6), compact. Full detail in /simulacion.
function SimulationCard() {
  const [r, setR] = useState<Results | null>(null);
  useEffect(() => { api.simulation().then((x) => setR(x as Results)).catch(() => undefined); }, []);
  const available = r?.available;
  return (
    <ChartCard question={t.simQ} source={es.sim.source}
      keyValue={available ? fmt(pick(r!.summary, "normal", OPERATING, "high_wait_p90_min")?.mean) : undefined}
      keyLabel={available ? es.sim.panoramaKey : undefined}>
      {!available ? (
        <div className="flex min-h-40 items-center justify-center rounded-card border-2 border-dashed border-navy/30 p-6 text-center text-muted">
          <p><Icon as={FlaskConical} /> {t.simPending}</p>
        </div>
      ) : (<>
        <p className="font-bold">{es.sim.metrics.high_wait_p90_min.label} · {es.sim.scenarios.normal}</p>
        <CIChart rows={ciRows(r!.summary, "normal", "high_wait_p90_min")} unit="min" title={es.sim.metrics.high_wait_p90_min.label} />
        <p className="mt-2">{conclusion(r!)[0]}</p>
        <Link to="/simulacion" className="mt-2 inline-flex min-h-12 items-center font-bold text-navy underline">{es.sim.panoramaLink}</Link>
      </>)}
    </ChartCard>
  );
}
