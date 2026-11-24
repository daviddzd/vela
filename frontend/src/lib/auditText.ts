// The audit trail in plain words: "Origen: plan de cuidado · Prioridad: baja" instead of the stored JSON.
// The JSON itself stays available (folded, "Ver detalle técnico") for whoever needs the exact record.
import { es } from "../i18n/es";

const t = es.privacy;
const lower = (s: string | undefined) => (s ? s.charAt(0).toLowerCase() + s.slice(1) : s);

/** "Solicitud REQ-08950", "Paciente PAC-0001": the record type in Spanish plus its id. */
export function auditEntity(entity: string, id?: string | null): string {
  return `${t.entities[entity] ?? entity}${id ? ` ${id}` : ""}`;
}

/** One field of the detail in words; undefined = nothing worth showing (empty or unknown). */
function value(key: string, v: any): string | undefined {
  if (v === null || v === undefined || v === "") return undefined;
  switch (key) {
    case "origin": return t.origins[v] ?? v;
    case "priority": return lower(es.priority[v]) ?? v;
    case "policy": return t.policies[v] ?? v;
    case "level": return lower(es.voice.levels[v]) ?? v;
    case "rule_hits": return v.length ? v.map((r: string) => t.rules[r] ?? r).join(", ") : t.noRules;
    case "input_mode": return t.inputModes[v] ?? v;
    case "reason": return es.statusReason[v] ?? v;
    case "travel_min": return `${Math.round(v)} ${es.common.minutes}`;
    case "result": return v.queued ? String(v.queued) : undefined;
    case "decision": return lower(es.contingency.decisions[v]) ?? v;
    case "kind": return es.contingency.kinds[v] ?? v;
    case "phase": return es.contingency.levels[v] ?? v;
    case "right": return lower(t.rights[v]) ?? v;
    case "script": return String(v).split("/").pop();
    case "emergency_source": return v === "rule" ? t.sourceRule : t.sourceClassifier;
    case "was_escalated": return v ? t.yes : t.no;
    default:
      if (!(key in t.fields)) return undefined;              // unknown field: only in the technical detail
      return Array.isArray(v) ? v.join(", ") : typeof v === "object" ? undefined : String(v);
  }
}

/** The whole detail as one sentence, fields in a fixed, readable order. */
export function auditDetail(detail: Record<string, any> | null | undefined): string {
  if (!detail || typeof detail !== "object") return "";
  const order = Object.keys(t.fields);
  return Object.keys(detail).sort((a, b) => order.indexOf(a) - order.indexOf(b))
    .map((k) => [k, value(k, detail[k])] as const)
    .filter(([, v]) => v !== undefined)
    .map(([k, v]) => `${t.fields[k]}: ${v}`).join(" · ");
}
