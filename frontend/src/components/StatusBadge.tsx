// Request status as icon + word (never color alone, docs/brand.md).
import { es } from "../i18n/es";

const TONE: Record<string, string> = {
  rejected: "border-danger text-danger", unattended: "border-danger text-danger",
  queued: "border-warn text-ink", completed: "border-ok text-ok", closed: "border-ok text-ok",
};

export function StatusBadge({ status }: { status: string }) {
  const s = es.requestStatus[status] ?? { icon: "•", label: status };
  return (
    <span className={`inline-flex items-center gap-1 rounded-card border-2 px-2 font-bold ${TONE[status] ?? "border-teal text-teal"}`}>
      <span aria-hidden="true">{s.icon}</span>
      {s.label}
    </span>
  );
}
