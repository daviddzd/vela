// Minimal ECharts wrapper (tree-shaken: only the chart types we use are bundled).
import { BarChart, HeatmapChart, LineChart, MapChart, ScatterChart } from "echarts/charts";
import {
  GeoComponent, GridComponent, LegendComponent, MarkLineComponent, TooltipComponent, VisualMapComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useRef } from "react";

echarts.use([BarChart, LineChart, HeatmapChart, MapChart, ScatterChart, GridComponent, TooltipComponent,
  LegendComponent, MarkLineComponent, VisualMapComponent, GeoComponent, CanvasRenderer]);

export { echarts };
/** Escape text before it goes into an HTML tooltip (names come from data). */
export const esc = (s: unknown) => echarts.format.encodeHTML(String(s ?? ""));

export function EChart({ option, height, label }: { option: Record<string, unknown>; height: number; label: string }) {
  const el = useRef<HTMLDivElement>(null);
  const inst = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!el.current) return;
    inst.current = echarts.init(el.current, undefined, { renderer: "canvas" });
    const ro = new ResizeObserver(() => inst.current?.resize());
    ro.observe(el.current);
    return () => { ro.disconnect(); inst.current?.dispose(); };
  }, []);

  useEffect(() => { inst.current?.setOption(option, { notMerge: true }); }, [option]);

  // The canvas is decorative for screen readers: every chart has a "Ver como tabla" with the same data.
  // `height` is the minimum; the chart grows to fill the card so cards in a row have no empty space.
  return <div ref={el} style={{ minHeight: height }} className="w-full flex-1" role="img" aria-label={label} />;
}
