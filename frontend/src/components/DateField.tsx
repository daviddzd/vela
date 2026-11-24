// Date input in Spanish format dd/mm/aaaa. Native <input type="date"> follows the browser's language
// (it showed mm/dd/yyyy), so we use a plain text field with validation.
// What the parent receives is ALWAYS what the field shows: onChange runs on every keystroke with "YYYY-MM-DD"
// (valid), "" (empty) and `valid = false` while the text is not a date. An invalid text also blocks the form's
// submission (setCustomValidity), so a form can never send an older date than the one on screen.
import { useEffect, useId, useRef, useState } from "react";
import { es } from "../i18n/es";
import { inputClass } from "./ui";

const toDisplay = (iso?: string) => (iso ? iso.split("-").reverse().join("/") : "");

export function parseDate(text: string): string | null {
  const m = text.trim().match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (!m) return null;
  const [d, mo, y] = [Number(m[1]), Number(m[2]), Number(m[3])];
  const date = new Date(Date.UTC(y, mo - 1, d));
  if (date.getUTCFullYear() !== y || date.getUTCMonth() !== mo - 1 || date.getUTCDate() !== d) return null;
  return `${y}-${String(mo).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
}

export function DateField({ label, value, onChange, required = false, error }: {
  label: string; value?: string; onChange: (iso: string, valid: boolean) => void; required?: boolean;
  error?: string;            // a message from the parent (e.g. "la fecha ya pasó"), shown like our own
}) {
  const [text, setText] = useState(toDisplay(value));
  const [touched, setTouched] = useState(false);
  const input = useRef<HTMLInputElement>(null);
  const emitted = useRef(value ?? "");
  const errorId = useId();
  // a new value from the parent (e.g. "Quitar filtros") replaces the text; our own echo does not
  useEffect(() => { if ((value ?? "") !== emitted.current) { emitted.current = value ?? ""; setText(toDisplay(value)); } }, [value]);

  const iso = parseDate(text);
  const empty = !text.trim();
  const bad = !empty && iso === null;
  const message = bad ? es.dates.invalid : empty && required ? es.validation.required : error ?? "";
  useEffect(() => { input.current?.setCustomValidity(message); }, [message]);

  const change = (t: string) => {
    setText(t);
    const v = parseDate(t);
    const out = v ?? "";
    emitted.current = out;
    onChange(out, v !== null || (!t.trim() && !required));
  };
  const show = (touched && !!message) || (!!error && !bad);

  return (
    <label className="block"><span className="font-bold">{label}</span>
      <input ref={input} type="text" inputMode="numeric" autoComplete="off" placeholder={es.dates.placeholder} value={text}
        maxLength={10} data-own-error="" required={required}
        // writing over a date that is already there replaces it instead of appending ("24/11/202624/11/2026")
        onFocus={(e) => { const el = e.currentTarget; setTimeout(() => el.select(), 0); }}   // after the click places the caret
        onChange={(e) => change(e.target.value)} onBlur={() => setTouched(true)}
        onInvalid={() => setTouched(true)}
        aria-invalid={show} aria-describedby={show ? errorId : undefined} className={`${inputClass} w-40`} />
      {show && <span id={errorId} className="block text-sm font-bold text-danger">{message}</span>}
    </label>
  );
}
