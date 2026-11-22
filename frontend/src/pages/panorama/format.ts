const TZ = "America/Mexico_City";
export const pct = (v: number | null | undefined) => (v == null ? "—" : `${v.toLocaleString("es-MX", { maximumFractionDigits: 1 })} %`);
export const num = (v: number | null | undefined, digits = 0) =>
  v == null ? "—" : v.toLocaleString("es-MX", { maximumFractionDigits: digits });
export const shortDay = (iso: string) =>
  new Intl.DateTimeFormat("es-MX", { timeZone: "UTC", day: "numeric", month: "short" }).format(new Date(`${iso}T12:00:00Z`));
export const dayHour = (iso: string) =>
  new Intl.DateTimeFormat("es-MX", { timeZone: TZ, day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }).format(new Date(iso));
