// Air-quality stations on the CDMX district map. Affected districts are shaded by their level; stations are
// small points (shape by level); only stations in watch / Phase I carry a label. Legend: icon + word.
import { AlertTriangle, Ban, CheckCircle2, type LucideIcon } from "lucide-react";
import { useMemo } from "react";
import { type MapPoint } from "../charts/CityMap";
import { StreetMap } from "./StreetMap";
import { chart } from "../charts/theme";
import { es } from "../i18n/es";
import { Icon } from "./icons";

export type StationLevel = { station_id: string; name: string; district_id: string; lat: number; lon: number;
  phase: string; o3: number; pm25_24h: number };
export const LEVEL_ICON: Record<string, LucideIcon> = { normal: CheckCircle2, watch: AlertTriangle, phase1: Ban };
const PHASES = ["normal", "watch", "phase1"];
const POINT = { normal: { symbol: "circle", color: chart.muted }, watch: { symbol: "triangle", color: "#8A5A00" },
  phase1: { symbol: "diamond", color: "#B42318" } } as Record<string, { symbol: string; color: string }>;
const FILL: Record<string, string> = { watch: "rgba(138,90,0,0.28)", phase1: "rgba(180,35,24,0.30)" };
const TEXT: Record<string, string> = { normal: "text-ok", watch: "text-warn", phase1: "text-danger" };

export function StationsMap({ stations }: { stations: StationLevel[] }) {
  // labelled stations alternate left / right (north to south) so close neighbours never share a side
  const side = useMemo(() => {
    const labelled = stations.filter((s) => s.phase !== "normal").sort((a, b) => b.lat - a.lat);
    return Object.fromEntries(labelled.map((s, i) => [s.station_id, i % 2 === 0 ? "left" : "right"])) as Record<string, "left" | "right">;
  }, [stations]);
  const points: MapPoint[] = useMemo(() => stations.map((s) => ({
    id: s.station_id, lat: s.lat, lon: s.lon, symbol: POINT[s.phase].symbol, color: POINT[s.phase].color,
    size: s.phase === "normal" ? 9 : 14,
    label: s.phase === "normal" ? undefined : `${s.station_id} · ${es.contingency.levels[s.phase]}`, labelPosition: side[s.station_id],
    tooltip: `${s.station_id} · ${s.name}: ${es.contingency.levels[s.phase]} — O₃ ${s.o3} ppb, PM2.5 24 h ${s.pm25_24h} µg/m³`,
  })), [stations, side]);
  // a district takes the worst level of its stations
  const fill = useMemo(() => {
    const worst: Record<string, string> = {};
    for (const s of stations) {
      if (PHASES.indexOf(s.phase) > PHASES.indexOf(worst[s.district_id] ?? "normal")) worst[s.district_id] = s.phase;
    }
    return Object.fromEntries(Object.entries(worst).map(([d, p]) => [d, FILL[p]]));
  }, [stations]);
  return (<>
    <StreetMap points={points} districtFill={fill} label={es.contingency.mapLabel} height={520} />
    <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm" aria-label={es.contingency.level}>
      {PHASES.map((k) => (
        <li key={k} className={`font-bold ${TEXT[k]}`}><Icon as={LEVEL_ICON[k]} /> {es.contingency.levels[k]}
          <span className="font-normal text-muted"> · {es.contingency.legend[k]}</span></li>))}
    </ul>
  </>);
}
