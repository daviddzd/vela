// Legend drawn in HTML above the chart: it wraps on a phone and never overlaps the axes.
// The key mirrors the mark: a short line (solid or dashed) for lines, a rounded rectangle for bars.
export type LegendItem = { label: string; color: string; kind: "line" | "dashed" | "bar" | "tick" };

export function ChartLegend({ items }: { items: LegendItem[] }) {
  return (
    <ul className="mb-2 flex flex-wrap gap-x-5 gap-y-1 text-sm">
      {items.map((it) => (
        <li key={it.label} className="flex items-center gap-2">
          <svg aria-hidden="true" width="22" height="12" className="shrink-0">
            {it.kind === "bar" && <rect x="1" y="2" width="20" height="8" rx="3" fill={it.color} />}
            {it.kind === "line" && <line x1="1" y1="6" x2="21" y2="6" stroke={it.color} strokeWidth="2.5" strokeLinecap="round" />}
            {it.kind === "dashed" && <line x1="1" y1="6" x2="21" y2="6" stroke={it.color} strokeWidth="2.5" strokeDasharray="4 3" />}
            {it.kind === "tick" && <rect x="10" y="0" width="3" height="12" fill={it.color} />}
          </svg>
          {it.label}
        </li>
      ))}
    </ul>
  );
}
