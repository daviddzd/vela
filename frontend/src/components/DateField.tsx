// Date input in Spanish format dd/mm/aaaa. Native <input type="date"> follows the browser's language
// (it showed mm/dd/yyyy), so we use a plain text field with validation. Value out: "YYYY-MM-DD" or "".
import { useEffect, useId, useState } from "react";
import { es } from "../i18n/es";
import { inputClass } from "./ui";

const toDisplay = (iso?: string) => (iso ? iso.split("-").reverse().join("/") : "");

function parse(text: string): string | null {
  const m = text.trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (!m) return null;
  const [d, mo, y] = [Number(m[1]), Number(m[2]), Number(m[3])];
  const date = new Date(Date.UTC(y, mo - 1, d));
  if (date.getUTCFullYear() !== y || date.getUTCMonth() !== mo - 1 || date.getUTCDate() !== d) return null;
  return `${y}-${String(mo).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

export function DateField({ label, value, onChange, required = false }:
  { label: string; value?: string; onChange: (iso: string) => void; required?: boolean }) {
  const [text, setText] = useState(toDisplay(value));
  const [invalid, setInvalid] = useState(false);
  const errorId = useId();
  useEffect(() => setText(toDisplay(value)), [value]);

  const commit = () => {
    if (!text.trim() && !required) { setInvalid(false); onChange(""); return; }
    const iso = parse(text);
    setInvalid(iso === null);
    if (iso) onChange(iso);
  };

  return (
    <label className="block"><span className="font-bold">{label}</span>
      <input type="text" inputMode="numeric" autoComplete="off" placeholder={es.dates.placeholder} value={text}
        onChange={(e) => setText(e.target.value)} onBlur={commit} onKeyDown={(e) => e.key === "Enter" && commit()}
        aria-invalid={invalid} aria-describedby={invalid ? errorId : undefined} className={`${inputClass} w-40`} />
      {invalid && <span id={errorId} className="block text-sm font-bold text-danger">{es.dates.invalid}</span>}
    </label>
  );
}
