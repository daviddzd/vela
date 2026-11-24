// Today's visits and staff bases on a street map of CDMX (falls back to the district drawing without internet). Visit points change shape with
// their state and the legend names each shape with icon + word; details on hover / tap. The list next to the
// map carries the same information for people who do not use the map.
import { useMemo } from "react";
import { type MapPoint } from "../charts/CityMap";
import { StreetMap } from "./StreetMap";
import { chart } from "../charts/theme";
import { es } from "../i18n/es";
import { CircleDot, Icon, STATUS_ICON } from "./icons";

export type MapVisit = { request_id: string; status: string; lat: number; lon: number; patient_name: string;
  service_name: string; caregiver_name: string | null; scheduled_for: string };
export type MapStaff = { caregiver_id: string; name: string; lat: number; lon: number };

const STYLE: Record<string, { symbol: string; color: string }> = {
  queued: { symbol: "triangle", color: "#8A5A00" }, assigned: { symbol: "circle", color: chart.series[0] },
  in_progress: { symbol: "diamond", color: chart.series[1] }, completed: { symbol: "rect", color: "#1D7447" },
  closed: { symbol: "rect", color: "#1D7447" }, unattended: { symbol: "pin", color: "#B42318" },
  not_closed: { symbol: "pin", color: "#8A5A00" },
};
const BASE = { symbol: "roundRect", color: "#9AA5AB" };

export function VisitsMap({ visits, staff }: { visits: MapVisit[]; staff: MapStaff[] }) {
  const points: MapPoint[] = useMemo(() => [
    ...staff.map((s) => ({ id: s.caregiver_id, lat: s.lat, lon: s.lon, ...BASE, size: 7,
      tooltip: `${es.board.staffBase}: ${s.name}` })),
    ...visits.map((v) => ({ id: v.request_id, lat: v.lat, lon: v.lon, ...(STYLE[v.status] ?? STYLE.assigned), size: 12,
      tooltip: `${es.requestStatus[v.status] ?? v.status}: ${v.patient_name} · ${v.service_name} · ${v.caregiver_name ?? es.family.pendingCaregiver}` })),
  ], [visits, staff]);
  const present = [...new Set(visits.map((v) => v.status))];
  return (<>
    <StreetMap points={points} label={es.board.mapLabel} height={400} />
    <ul className="mt-2 flex flex-wrap gap-x-5 gap-y-1 text-sm">
      {present.map((st) => <li key={st} className="font-bold"><Icon as={STATUS_ICON[st] ?? CircleDot} /> {es.requestStatus[st] ?? st}
        <span className="font-normal text-muted"> · {es.board.shapes[STYLE[st]?.symbol ?? "circle"]}</span></li>)}
      <li className="text-muted">▢ {es.board.staffBase}</li>
    </ul>
  </>);
}
