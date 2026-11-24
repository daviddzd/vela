// Chart palette, derived from the Enlaza logo (23 Nov 2026), validated with the dataviz validator against white:
//   categorical  #0094A6 (deep teal) · #3159B8 (blue, from the logo navy) · #B23E89 (magenta, the third hue)
//                lightness band, chroma floor, contrast >= 3:1 on white: PASS; worst adjacent CVD ΔE 8.2 (protan),
//                normal-vision ΔE 17.6. Non-adjacent teal↔magenta is 5.3 (deutan): every chart has a legend and/or
//                direct labels (secondary encoding).
//                Against the status colours (ok #1D7447, warn #8A5A00, danger #B42318): normal ΔE >= 15.0 for every
//                series; CVD >= 9.0 except tritan (blue↔ok 4.2, magenta↔danger 7.4): status always comes with an
//                icon and a word, never colour alone.
//   sequential   5 teal steps light → dark: monotone lightness, gaps >= 0.06, light end 2.05:1, one hue.
// The logo teal #2AAEAE itself is 2.7:1 on white: decoration only, never a data mark.
// Text never wears a series color: labels and values use ink / muted.
export const chart = {
  series: ["#0094A6", "#3159B8", "#B23E89"],
  ramp: ["#6FBFC8", "#3FA5B1", "#1B8A99", "#0D6D7C", "#0A4F5C"],
  ink: "#1B2B38",
  muted: "#4F5F6B",
  grid: "#E3E9ED",          // hairline gridlines, one step off the surface
  surface: "#FFFFFF",
  threshold: "#B42318",     // contingency threshold line (status "danger", always with a text label)
  font: '"Enlaza Digits", "Atkinson Hyperlegible", Arial, sans-serif',   // digits with a plain zero (index.css)
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
