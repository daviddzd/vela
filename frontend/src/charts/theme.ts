// Chart palette (validated with the dataviz validator against the white card surface, 21 Nov 2026):
//   categorical  #00879C (chart teal) · #E8704A (brand coral) · #6250D6 (violet)  → all checks pass,
//                worst CVD ΔE 12.6, normal-vision ΔE 19.3 (also with --pairs all)
//   sequential   5 teal steps, light → dark (ordinal checks pass; light end ≥ 2:1 on white)
// Enlaza (23 Nov 2026): series kept (validated); UI chrome uses the navy / teal of the logo (index.css).
// Text never wears a series color: labels and values use ink / muted.
export const chart = {
  series: ["#00879C", "#E8704A", "#6250D6"],
  ramp: ["#86BFCB", "#5DA6B6", "#3A8CA0", "#1E7187", "#0F5C6E"],
  ink: "#1B2B38",
  muted: "#4F5F6B",
  grid: "#E3E7E9",          // hairline gridlines, one step off the surface
  surface: "#FFFFFF",
  threshold: "#C0392B",     // contingency threshold line (status "danger", always with a text label)
  font: '"Atkinson Hyperlegible", Arial, sans-serif',
};

/** Shared ECharts defaults: recessive axes, solid hairline grid, brand font. */
export function baseOption(): Record<string, unknown> {
  return {
    textStyle: { fontFamily: chart.font, color: chart.ink, fontSize: 14 },
    animationDuration: 300,
    grid: { left: 8, right: 16, top: 32, bottom: 8, containLabel: true },
    tooltip: {
      confine: true, backgroundColor: "#FFFFFF", borderColor: chart.grid,
      textStyle: { color: chart.ink, fontFamily: chart.font, fontSize: 14 },
    },
    legend: { top: 0, left: 0, icon: "roundRect", itemWidth: 14, itemHeight: 8,
      textStyle: { color: chart.ink, fontSize: 14 } },
  };
}

export const axisCommon = {
  axisLine: { lineStyle: { color: chart.grid } },
  axisTick: { show: false },
  axisLabel: { color: chart.muted, fontSize: 13 },
  splitLine: { lineStyle: { color: chart.grid, width: 1, type: "solid" } },
};
