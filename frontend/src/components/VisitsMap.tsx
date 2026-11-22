// Map of today's visits and staff bases. MapLibre + OpenFreeMap tiles (free, no key, © OpenStreetMap).
// Without internet the markers still show on a plain background. Each marker has an icon AND a word;
// the list next to the map carries the same information for people who do not use the map.
import * as maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef } from "react";
import { es } from "../i18n/es";

export type MapVisit = { request_id: string; status: string; lat: number; lon: number; patient_name: string;
  service_name: string; caregiver_name: string | null; scheduled_for: string };
export type MapStaff = { caregiver_id: string; name: string; lat: number; lon: number };

const STYLE = "https://tiles.openfreemap.org/styles/positron";
const OFFLINE_STYLE: maplibregl.StyleSpecification = {
  version: 8, sources: {}, layers: [{ id: "bg", type: "background", paint: { "background-color": "#FAF7F2" } }],
};
const CDMX: [number, number] = [-99.13, 19.40];

function markerElement(icon: string, label: string, tone: string): HTMLElement {
  const el = document.createElement("div");
  el.className = `rounded-card border-2 bg-white px-1 text-sm font-bold shadow ${tone}`;
  el.textContent = `${icon} ${label}`;
  return el;
}

export function VisitsMap({ visits, staff }: { visits: MapVisit[]; staff: MapStaff[] }) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markers = useRef<maplibregl.Marker[]>([]);

  useEffect(() => {
    if (!container.current) return;
    const m = new maplibregl.Map({ container: container.current, style: STYLE, center: CDMX, zoom: 10,
      attributionControl: { compact: false } });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }));
    // If the tiles cannot load (no internet at the venue), fall back to a plain background.
    m.on("error", () => { if (!m.isStyleLoaded()) m.setStyle(OFFLINE_STYLE); });
    map.current = m;
    return () => m.remove();
  }, []);

  useEffect(() => {
    const m = map.current;
    if (!m) return;
    markers.current.forEach((mk) => mk.remove());
    markers.current = [
      ...staff.map((s) => new maplibregl.Marker({ element: markerElement("🏥", "", "border-muted text-muted") })
        .setLngLat([s.lon, s.lat]).setPopup(new maplibregl.Popup().setText(`${es.board.staffBase}: ${s.name}`)).addTo(m)),
      ...visits.map((v) => {
        const st = es.requestStatus[v.status] ?? { icon: "•", label: v.status };
        const tone = v.status === "queued" ? "border-warn text-ink" : v.status === "in_progress" ? "border-coral text-ink" : "border-teal text-teal";
        return new maplibregl.Marker({ element: markerElement(st.icon, st.label, tone) })
          .setLngLat([v.lon, v.lat])
          .setPopup(new maplibregl.Popup().setText(`${v.patient_name} · ${v.service_name} · ${v.caregiver_name ?? es.family.pendingCaregiver}`))
          .addTo(m);
      }),
    ];
  }, [visits, staff]);

  return <div ref={container} className="h-96 w-full overflow-hidden rounded-card border border-teal/20"
    role="region" aria-label={es.board.mapLabel} />;
}
