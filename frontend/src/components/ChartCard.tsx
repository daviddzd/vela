// Card rules from docs/spec/07: the title is the question, a big key number, "Fuente: …" and
// "Datos sintéticos" in the footer, and a table view so nothing depends on color or hover.
import type { ReactNode } from "react";
import { es } from "../i18n/es";

export function ChartCard({ question, keyValue, keyLabel, children, source, table, note, className = "", synthetic = true }: {
  question: string; keyValue?: ReactNode; keyLabel?: ReactNode; children: ReactNode; source: ReactNode;
  table?: { columns: string[]; rows: (string | number | null)[][] }; note?: ReactNode; className?: string;
  synthetic?: boolean;   // false for numbers that come from real sources / assumptions (e.g. /negocio)
}) {
  return (
    <section className={`flex flex-1 flex-col rounded-card border border-teal/20 bg-white p-4 sm:p-5 ${className}`}>
      <h2 className="text-teal">{question}</h2>
      {keyValue !== undefined && (
        <p className="mt-1"><span className="figure text-4xl">{keyValue}</span>
          {keyLabel && <span className="ml-2 text-muted">{keyLabel}</span>}</p>
      )}
      <div className="mt-3 flex flex-1 flex-col">{children}</div>
      {note && <p className="mt-2 text-muted">{note}</p>}
      {table && (
        <details className="mt-3">
          <summary className="min-h-12 cursor-pointer font-bold text-teal flex items-center">{es.panorama.viewTable}</summary>
          <div className="max-h-72 overflow-auto">
            <table className="w-full text-left tabular-nums">
              <thead><tr>{table.columns.map((c) => <th key={c} className="border-b border-teal/20 py-1 pr-3">{c}</th>)}</tr></thead>
              <tbody>{table.rows.map((r, i) => (
                <tr key={i}>{r.map((v, j) => <td key={j} className="border-b border-teal/10 py-1 pr-3">{v ?? "—"}</td>)}</tr>
              ))}</tbody>
            </table>
          </div>
        </details>
      )}
      <p className="mt-3 border-t border-teal/10 pt-2 text-sm text-muted">
        {es.panorama.sourcePrefix} {source}{synthetic && <> · <strong>{es.panorama.synthetic}</strong></>}
      </p>
    </section>
  );
}
