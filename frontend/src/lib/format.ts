// Dates and times always shown in Mexico City time (CLAUDE.md rule 2), whatever the device's zone.
const TZ = "America/Mexico_City";

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("es-MX", {
    timeZone: TZ, weekday: "short", day: "numeric", month: "short", hour: "2-digit", minute: "2-digit",
  }).format(new Date(iso));
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Intl.DateTimeFormat("es-MX", { timeZone: TZ, hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
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
