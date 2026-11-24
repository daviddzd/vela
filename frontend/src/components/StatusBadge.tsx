// Request status as SVG icon + word (never color alone, docs/brand.md).
import { es } from "../i18n/es";
import { CircleDot, Icon, STATUS_ICON } from "./icons";

const TONE: Record<string, string> = {
  rejected: "border-danger text-danger", unattended: "border-danger text-danger", not_closed: "border-warn text-warn",
  queued: "border-warn text-ink", completed: "border-ok text-ok", closed: "border-ok text-ok",
};

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`inline-flex items-center gap-1 rounded-card border-2 px-2 font-bold ${TONE[status] ?? "border-teal text-teal"}`}>
      <Icon as={STATUS_ICON[status] ?? CircleDot} />
      {es.requestStatus[status] ?? status}
    </span>
  );
}
