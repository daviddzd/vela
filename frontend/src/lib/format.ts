// Dates and times always shown in Mexico City time (CLAUDE.md rule 2), whatever the device's zone.
// One clock format in the whole system: 24 h ("15:57"), never a.m./p.m.; and one date format: dd/mm/aaaa.
import { es } from "../i18n/es";

const TZ = "America/Mexico_City";
const H24 = { timeZone: TZ, hourCycle: "h23" } as const;

/** "24/11/2026" */
export function formatDate(iso: string | Date | null | undefined): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("es-MX", { timeZone: TZ, day: "2-digit", month: "2-digit", year: "numeric" }).format(new Date(iso));
}

/** "mar 24/11/2026, 10:00" (the weekday helps families and caregivers) */
export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const weekday = new Intl.DateTimeFormat("es-MX", { timeZone: TZ, weekday: "short" }).format(new Date(iso)).replace(".", "");
  return `${weekday} ${formatDate(iso)}, ${formatTime(iso)}`;
}

/** "15:57" */
export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("es-MX", { ...H24, hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
}

/** "21/11/2026 15:57" (tables: audit trail, patient record). */
export function formatShortDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("es-MX", { ...H24, day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" })
    .format(new Date(iso)).replace(",", "");
}

/** Calendar day in Mexico City as YYYY-MM-DD, to compare days whatever the device's zone. */
export function dayKey(d: Date): string {
  return new Intl.DateTimeFormat("en-CA", { timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit" }).format(d);
}

/** A moment on the board (alerts, queue, visits): "15:57" today, "ayer, 21:22" yesterday, "24/11/2026, 11:00" any other day. */
export function formatWhen(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return "—";
  const d = new Date(iso);
  const time = formatTime(iso);
  if (dayKey(d) === dayKey(now)) return time;
  if (dayKey(d) === dayKey(new Date(now.getTime() - 86_400_000))) return `${es.dates.yesterday}, ${time}`;
  return `${formatDate(d)}, ${time}`;
}

/** Value for <input type="datetime-local"> = now + hours, in Mexico City time. */
export function localInputValue(hoursAhead = 2): string {
  const d = new Date(Date.now() + hoursAhead * 3600_000);
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: TZ, year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit", hour12: false,
  }).formatToParts(d);
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "00";
  return `${get("year")}-${get("month")}-${get("day")}T${get("hour") === "24" ? "00" : get("hour")}:${get("minute")}`;
}
