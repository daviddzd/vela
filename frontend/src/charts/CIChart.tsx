// Mean with its 95 % confidence interval, one row per policy (dot + whisker). The policy that matters
// (Vela) is emphasized in chart teal; the others stay gray (emphasis, not 4 categorical hues).
import { useMemo } from "react";
import { EChart, esc } from "./EChart";
import { axisCommon, baseOption, chart } from "./theme";

export type CIRow = { label: string; mean: number | null; lo: number | null; hi: number | null; emphasis?: boolean };

export function CIChart({ rows, unit, title, height = 190, large = false }:
  { rows: CIRow[]; unit: string; title: string; height?: number; large?: boolean }) {
  const size = large ? 20 : 13;   // canvas text does not follow the page's rem scaling
  const option = useMemo(() => {
    const data = rows.map((r, i) => [i, r.mean, r.lo, r.hi, r.emphasis ? 1 : 0]);
    const max = Math.max(...rows.map((r) => r.hi ?? r.mean ?? 0), 1);
    return {
      ...baseOption(), legend: { show: false },
      grid: { left: 8, right: 56, top: 8, bottom: 8, containLabel: true },
      tooltip: { ...baseOption().tooltip as object, trigger: "item",
        formatter: (p: any) => { const r = rows[p.value[0]];
          return `<strong>${fmt(r.mean)} ${esc(unit)}</strong><br/>IC 95 %: ${fmt(r.lo)} – ${fmt(r.hi)}<br/>${esc(r.label)}`; } },
      xAxis: { ...axisCommon, type: "value", min: 0, max: niceMax(max), splitNumber: 3,
        axisLabel: { ...axisCommon.axisLabel, formatter: `{value}`, hideOverlap: true, fontSize: size } },
      yAxis: { ...axisCommon, type: "category", inverse: true, data: rows.map((r) => r.label), splitLine: { show: false },
        axisLabel: { ...axisCommon.axisLabel, width: large ? 220 : 150, overflow: "break", color: chart.ink, fontSize: size } },
      series: [{
        type: "custom", data, encode: { x: [1, 2, 3], y: 0 },
        renderItem: (_: unknown, api: any) => {
          const y = api.coord([0, api.value(0)])[1];
          const [xm, xl, xh] = [1, 2, 3].map((d) => api.coord([api.value(d), 0])[0]);
          const color = api.value(4) ? chart.series[0] : chart.muted;
          return { type: "group", children: [
            { type: "line", shape: { x1: xl, y1: y, x2: xh, y2: y }, style: { stroke: color, lineWidth: 2 } },
            { type: "line", shape: { x1: xl, y1: y - 6, x2: xl, y2: y + 6 }, style: { stroke: color, lineWidth: 2 } },
            { type: "line", shape: { x1: xh, y1: y - 6, x2: xh, y2: y + 6 }, style: { stroke: color, lineWidth: 2 } },
            { type: "circle", shape: { cx: xm, cy: y, r: large ? 8 : 6 }, style: { fill: color, stroke: "#FFFFFF", lineWidth: 2 } },
            { type: "text", style: { text: fmt(api.value(1)), x: xh + 8, y, verticalAlign: "middle", fill: chart.ink,
              font: `${size}px ${chart.font}` } },
          ] };
        },
      }],
    };
  }, [rows, unit, size, large]);
  return <EChart option={option} height={height} label={`${title}: ${rows.map((r) => `${r.label} ${fmt(r.mean)} ${unit}`).join("; ")}`} />;
}

const fmt = (v: number | null | undefined) => (v == null ? "—" : v.toLocaleString("es-MX", { maximumFractionDigits: 1 }));
function niceMax(v: number) {
  const step = v > 100 ? 100 : v > 20 ? 10 : 5;
  return Math.ceil((v * 1.05) / step) * step;
}
