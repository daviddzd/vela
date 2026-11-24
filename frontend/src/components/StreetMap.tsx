// Real street base map (MapLibre GL + OpenFreeMap "positron" style: free, no API key, OpenStreetMap data) with the
// official district boundaries on top and the page's points as HTML markers (shape + optional label, details on
// hover / tap / keyboard focus). Same inputs as CityMap. If the browser has no WebGL, or the style or the tiles do not
// load in time (no internet at the venue), it falls back to CityMap, the district drawing that needs no internet.
// CityMap is ALSO drawn on top while the street map loads (and if the GPU drops the WebGL context): the first visit
// can take seconds to download the style and tiles, and the card must never be a blank box meanwhile.
// Privacy: the tile service only learns which part of the city is on screen; points are drawn in the browser.
import "maplibre-gl/dist/maplibre-gl.css";
import * as maplibregl from "maplibre-gl";
// MapLibre v6 draws tiles in an ES-module web worker. Vite bundles that worker (with its imports) as its own file
// and gives us its URL; without this the map stays blank ("Worker failed to load").
import workerUrl from "maplibre-gl/dist/maplibre-gl-worker.mjs?worker&url";
import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { CityMap, type MapPoint } from "../charts/CityMap";
import { chart } from "../charts/theme";
import { es } from "../i18n/es";

maplibregl.setWorkerUrl(workerUrl);
const STYLE_URL = "https://tiles.openfreemap.org/styles/positron";
const LOAD_TIMEOUT_MS = 8000;
const CDMX_BOUNDS: [[number, number], [number, number]] = [[-99.37, 19.04], [-98.94, 19.6]];

let boundaries: Promise<any> | null = null;            // fetched once per page load
function loadBoundaries() {
  boundaries ??= api.panorama<{ available: boolean; geojson?: any }>("boundaries").then((b) => (b.available ? b.geojson : null));
  return boundaries;
}

function webglAvailable(): boolean {
  try {
    const c = document.createElement("canvas");
    return !!(c.getContext("webgl2") || c.getContext("webgl"));
  } catch {
    return false;
  }
}

/** SVG for the point shapes CityMap uses (shape carries meaning together with the legend's word). */
function shapeSvg(symbol: string, color: string, size: number): string {
  const s = size, h = s / 2, stroke = `stroke="#FFFFFF" stroke-width="1.5"`;
  const shape = {
    triangle: `<polygon points="${h},1 ${s - 1},${s - 1} 1,${s - 1}" fill="${color}" ${stroke}/>`,
    diamond: `<polygon points="${h},1 ${s - 1},${h} ${h},${s - 1} 1,${h}" fill="${color}" ${stroke}/>`,
    rect: `<rect x="1" y="1" width="${s - 2}" height="${s - 2}" fill="${color}" ${stroke}/>`,
    roundRect: `<rect x="1" y="1" width="${s - 2}" height="${s - 2}" rx="${s / 4}" fill="${color}" ${stroke}/>`,
    pin: `<path d="M${h} ${s - 1} L2 ${h} A${h - 2} ${h - 2} 0 1 1 ${s - 2} ${h} Z" fill="${color}" ${stroke}/>`,
  }[symbol] ?? `<circle cx="${h}" cy="${h}" r="${h - 1}" fill="${color}" ${stroke}/>`;
  return `<svg width="${s}" height="${s}" viewBox="0 0 ${s} ${s}" aria-hidden="true">${shape}</svg>`;
}

export function StreetMap({ points, districtFill = {}, height = 440, label, onSelect }:
  { points: MapPoint[]; districtFill?: Record<string, string>; height?: number; label: string;
    onSelect?: (id: string) => void }) {      // a click (or Enter) on a point selects it in the page
  const el = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markers = useRef<maplibregl.Marker[]>([]);
  const [failed, setFailed] = useState(() => !webglAvailable());
  const [ready, setReady] = useState(false);
  const [glLost, setGlLost] = useState(false);
  const select = useRef(onSelect);
  select.current = onSelect;       // GPU reset / sleep on Windows: MapLibre redraws when it is restored

  // create the map once; fall back if it cannot load the style or the first tiles in time
  useEffect(() => {
    if (failed || !el.current) return;
    let done = false;
    const m = new maplibregl.Map({
      container: el.current, style: STYLE_URL, bounds: CDMX_BOUNDS, fitBoundsOptions: { padding: 8 },
      attributionControl: { compact: true, customAttribution: "© OpenStreetMap" }, dragRotate: false,
      cooperativeGestures: true,    // a phone can scroll the page without moving the map by accident
      locale: es.map.locale,
    });
    map.current = m;
    // the card may still be growing when the map is created (lazy loading, grid layout): follow its size
    const resize = new ResizeObserver(() => m.resize());
    resize.observe(el.current);
    // The OpenStreetMap credit is required by its licence and stays; only its English joining words are translated.
    const credit = new MutationObserver(() => {
      el.current?.querySelectorAll(".maplibregl-ctrl-attrib-inner").forEach((box) => {
        box.childNodes.forEach((n) => {
          if (n.nodeType === Node.TEXT_NODE && /Data from/.test(n.textContent ?? "")) n.textContent = (n.textContent ?? "").replace("Data from", es.map.dataFrom);
        });
      });
    });
    credit.observe(el.current, { childList: true, subtree: true });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    const timer = setTimeout(() => { if (!done) setFailed(true); }, LOAD_TIMEOUT_MS);
    m.on("error", (e: any) => { if (!done && /style|Failed to fetch|NetworkError|tile/i.test(String(e?.error?.message ?? e))) setFailed(true); });
    m.on("webglcontextlost", () => setGlLost(true));
    m.on("webglcontextrestored", () => setGlLost(false));
    m.on("load", async () => {
      // place names in Spanish when OpenStreetMap has them (the style shows English names by default)
      for (const layer of m.getStyle().layers ?? []) {
        const field = layer.type === "symbol" ? JSON.stringify(m.getLayoutProperty(layer.id, "text-field") ?? "") : "";
        if (field.includes("name") && !field.includes("ref")) {           // place / street names, not road numbers
          m.setLayoutProperty(layer.id, "text-field", ["coalesce", ["get", "name:es"], ["get", "name"]]);
        }
      }
      const geo = await loadBoundaries().catch(() => null);
      if (geo && !m.getSource("districts")) {
        m.addSource("districts", { type: "geojson", data: geo });
        m.addLayer({ id: "district-fill", type: "fill", source: "districts", paint: { "fill-color": "#000000", "fill-opacity": 0 } });
        m.addLayer({ id: "district-line", type: "line", source: "districts",
          paint: { "line-color": "#3A5B76", "line-width": 1.5, "line-opacity": 0.8 } });
      }
      m.once("idle", () => { done = true; clearTimeout(timer); setReady(true); });   // style + first tiles drawn
    });
    return () => { clearTimeout(timer); resize.disconnect(); credit.disconnect(); markers.current.forEach((mk) => mk.remove()); m.remove(); map.current = null; };
  }, [failed]);

  // district shading (contingency levels): a match expression on district_id
  useEffect(() => {
    const m = map.current;
    if (!ready || !m?.getLayer("district-fill")) return;
    const entries = Object.entries(districtFill);
    m.setPaintProperty("district-fill", "fill-color", entries.length
      ? ["match", ["get", "district_id"], ...entries.flat(), "rgba(0,0,0,0)"] as any : "rgba(0,0,0,0)");
    m.setPaintProperty("district-fill", "fill-opacity", entries.length ? 1 : 0);
  }, [ready, districtFill]);

  // points as HTML markers: keyboard focusable, tooltip on hover / focus / tap
  useEffect(() => {
    const m = map.current;
    if (!ready || !m) return;
    if (points.length) {         // zoom to where the points are (never closer than a neighbourhood)
      const b = new maplibregl.LngLatBounds();
      points.forEach((p) => b.extend([p.lon, p.lat]));
      m.fitBounds(b, { padding: 48, maxZoom: 14, duration: 0 });
    }
    markers.current.forEach((mk) => mk.remove());
    markers.current = points.map((p) => {
      const node = document.createElement("button");
      node.type = "button";
      node.className = "flex items-center gap-1 bg-transparent p-0";
      node.setAttribute("aria-label", p.tooltip);
      node.innerHTML = shapeSvg(p.symbol, p.color, (p.size ?? 10) + 4) + (p.label
        ? `<span style="font:bold 13px ${chart.font};color:${chart.ink};background:#fff;border:1.5px solid ${p.color};border-radius:6px;padding:1px 5px;white-space:nowrap">${p.label.replace(/</g, "&lt;")}</span>` : "");
      const popup = new maplibregl.Popup({ closeButton: false, offset: 10, maxWidth: "280px" }).setText(p.tooltip);
      const show = () => popup.setLngLat([p.lon, p.lat]).addTo(m);
      node.addEventListener("mouseenter", show);
      node.addEventListener("focus", show);
      node.addEventListener("click", () => { show(); select.current?.(p.id); });
      node.addEventListener("mouseleave", () => popup.remove());
      node.addEventListener("blur", () => popup.remove());
      return new maplibregl.Marker({ element: node, anchor: p.label && p.labelPosition === "left" ? "right" : "center" })
        .setLngLat([p.lon, p.lat]).addTo(m);
    });
  }, [ready, points]);

  if (failed) {
    return (<>
      <CityMap points={points} districtFill={districtFill} height={height} label={label} onSelect={onSelect} />
      <p className="mt-1 text-sm text-muted">{es.map.fallback}</p>
    </>);
  }
  const cover = !ready || glLost;     // the street map is not drawn (yet): show the district drawing over it
  return (<>
    <div className="relative w-full" style={{ height }}>
      <div ref={el} style={{ height }} className="w-full overflow-hidden rounded-card" role="region" aria-label={label} aria-hidden={cover} />
      {cover && <div className="absolute inset-0 z-10 bg-white"><CityMap points={points} districtFill={districtFill} height={height} label={label} onSelect={onSelect} /></div>}
    </div>
    {cover && <p className="mt-1 text-sm text-muted" role="status">{es.map.loading}</p>}
  </>);
}
