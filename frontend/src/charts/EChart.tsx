// Minimal ECharts wrapper (tree-shaken: only the chart types we use are bundled).
import { BarChart, CustomChart, HeatmapChart, LineChart, MapChart, ScatterChart } from "echarts/charts";
import {
  GeoComponent, GridComponent, LegendComponent, MarkLineComponent, TooltipComponent, VisualMapComponent,
} from "echarts/components";
import * as echarts from "echarts/core";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useRef } from "react";

echarts.use([BarChart, CustomChart, LineChart, HeatmapChart, MapChart, ScatterChart, GridComponent, TooltipComponent,
  LegendComponent, MarkLineComponent, VisualMapComponent, GeoComponent, CanvasRenderer]);

export { echarts };
/** Escape text before it goes into an HTML tooltip (names come from data). */
export const esc = (s: unknown) => echarts.format.encodeHTML(String(s ?? ""));

export function EChart({ option, height, label, onClick }:
  { option: Record<string, unknown>; height: number; label: string; onClick?: (params: any) => void }) {
  const click = useRef(onClick);
  click.current = onClick;
  const box = useRef<HTMLDivElement>(null);       // takes its size from the card (flex), never from the chart
  const el = useRef<HTMLDivElement>(null);        // ECharts draws here, positioned over the box
  const inst = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!el.current || !box.current) return;
    const node = box.current;
    inst.current = echarts.init(el.current, undefined, { renderer: "canvas" });
    inst.current.on("click", (p) => click.current?.(p));
    // React removes the node before this effect's cleanup runs, so the observer can still fire once with a 0×0 box;
    // resizing a map to 0×0 throws inside ECharts ("Cannot read properties of null"). Only follow real sizes.
    const ro = new ResizeObserver(() => { if (node.isConnected && node.clientWidth && node.clientHeight) inst.current?.resize(); });
    ro.observe(node);
    return () => { ro.disconnect(); inst.current?.dispose(); };
  }, []);

  useEffect(() => { inst.current?.setOption(option, { notMerge: true }); }, [option]);

  // The canvas is decorative for screen readers: every chart has a "Ver como tabla" with the same data.
  // `height` is the minimum; the chart grows to fill the card so cards in a row have no empty space.
  // The chart is ABSOLUTELY positioned inside the box: if it were in the flow, its canvas (rounded to whole device
  // pixels, e.g. at 125 % Windows scaling) would make the card a fraction taller, the observer would resize it
  // again, and the card would grow without end (~60 px/s, seen in Chrome on Windows).
  return (
    <div ref={box} style={{ minHeight: height }} className="relative w-full flex-1">
      <div ref={el} className="absolute inset-0" role="img" aria-label={label} />
    </div>
  );
}
