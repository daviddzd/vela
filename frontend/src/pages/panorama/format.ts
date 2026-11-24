const TZ = "America/Mexico_City";
export const pct = (v: number | null | undefined) => (v == null ? "—" : `${v.toLocaleString("es-MX", { maximumFractionDigits: 1 })} %`);
export const num = (v: number | null | undefined, digits = 0) =>
  v == null ? "—" : v.toLocaleString("es-MX", { maximumFractionDigits: digits });
// dates always dd/mm/aaaa, times in 24 h
export const shortDay = (iso: string) => iso.slice(0, 10).split("-").reverse().join("/");
export const dayHour = (iso: string) =>
  new Intl.DateTimeFormat("es-MX", { timeZone: TZ, hourCycle: "h23", day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" })
    .format(new Date(iso)).replace(",", "");
