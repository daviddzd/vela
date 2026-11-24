// CDMX map drawn from the official district boundaries (same GeoJSON as Panorama-AM), with ECharts:
// no internet tiles needed. Districts can be shaded by a state (legend with icon + word, given by the page);
// points are small symbols (shape differs by state, so color is never the only cue). Only points with
// `label` show text on the map; every point shows its details on hover / tap (tooltip).
import { useEffect, useMemo, useState } from "react";
import { api } from "../api/client";
import { EChart, echarts, esc } from "./EChart";
import { baseOption, chart } from "./theme";

export type MapPoint = { id: string; lat: number; lon: number; tooltip: string; symbol: string; color: string;
  size?: number; label?: string; labelPosition?: "left" | "right" };
type Boundaries = { available: boolean; geojson?: any };

let boundaries: Promise<Boundaries> | null = null;     // fetched once per page load, shared by every map
function loadBoundaries(): Promise<Boundaries> {
  boundaries ??= api.panorama<Boundaries>("boundaries").then((b) => {
    if (b.available) echarts.registerMap("cdmx", b.geojson);
    return b;
  });
  return boundaries;
}

export function CityMap({ points, districtFill = {}, height = 440, label, onSelect }:
  { points: MapPoint[]; districtFill?: Record<string, string>; height?: number; label: string; onSelect?: (id: string) => void }) {
  const [geo, setGeo] = useState<Boundaries | null>(null);
  useEffect(() => { loadBoundaries().then(setGeo).catch(() => setGeo({ available: false })); }, []);

  const option = useMemo(() => {
    if (!geo) return null;
    const scatter = {
      type: "scatter", data: points.map((p) => ({
        name: p.id, value: [p.lon, p.lat], symbol: p.symbol, symbolSize: p.size ?? 10, tip: p.tooltip,
        itemStyle: { color: p.color, borderColor: "#FFFFFF", borderWidth: 1.5 },
        label: p.label ? { show: true, formatter: p.label, position: p.labelPosition ?? "right", distance: 8, color: chart.ink,
          fontFamily: chart.font, fontSize: 13, fontWeight: "bold", backgroundColor: "#FFFFFF", borderColor: p.color,
          borderWidth: 1.5, borderRadius: 6, padding: [2, 5] } : { show: false },
      })),
      // labels never overlap: they move apart vertically (ECharts label layout)
      labelLayout: { moveOverlap: "shiftY", hideOverlap: false }, labelLine: { show: true, lineStyle: { color: chart.muted } }, z: 3,
    };
    const tooltip = { ...baseOption().tooltip as object, trigger: "item", triggerOn: "mousemove|click",
      formatter: (p: any) => (p.data?.tip ? esc(p.data.tip) : p.name ? esc(p.data?.label ?? p.name) : "") };
    if (!geo.available) {
      return { ...baseOption(), tooltip, xAxis: { type: "value", scale: true, show: false }, yAxis: { type: "value", scale: true, show: false },
        grid: { left: 8, right: 8, top: 8, bottom: 8 }, series: [scatter] };
    }
    return { ...baseOption(), tooltip,
      geo: { map: "cdmx", nameProperty: "district_id", roam: false, layoutCenter: ["50%", "50%"], layoutSize: "96%",
        silent: true, label: { show: false },
        itemStyle: { areaColor: "#EEF3F4", borderColor: "#FFFFFF", borderWidth: 1.5 },
        regions: Object.entries(districtFill).map(([id, color]) => ({ name: id, itemStyle: { areaColor: color } })) },
      series: [{ ...scatter, coordinateSystem: "geo" }] };
  }, [geo, points, districtFill]);

  return option ? <EChart option={option} height={height} label={label}
    onClick={onSelect && ((p) => p.seriesType === "scatter" && p.data?.name && onSelect(p.data.name))} /> : <div style={{ minHeight: height }} />;
}
