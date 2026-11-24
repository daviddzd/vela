// Form validation messages in Spanish for every form of the app. The browser's own bubbles ("Please fill out this
// field.") follow the browser's language, so we cancel them (the `invalid` event) and write our message under the
// field instead, linked with aria-describedby. Installed once in main.tsx; forms keep their normal HTML attributes
// (required, minLength, min, max, type="email") and are still blocked from submitting while a field is invalid.
import { es } from "../i18n/es";

type Field = HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement;
const v = es.validation;

function message(el: Field): string {
  const s = el.validity;
  const attr = (name: string) => el.getAttribute(name) ?? "";
  if (s.customError) return el.validationMessage;            // already ours (set with setCustomValidity in Spanish)
  if (s.valueMissing) return el instanceof HTMLInputElement && el.type === "radio" ? v.choose : v.required;
  if (s.typeMismatch) return el instanceof HTMLInputElement && el.type === "email" ? v.email : v.format;
  if (s.tooShort) return v.tooShort.replace("{n}", attr("minlength"));
  if (s.tooLong) return v.tooLong.replace("{n}", attr("maxlength"));
  if (s.rangeUnderflow) return v.min.replace("{n}", attr("min"));
  if (s.rangeOverflow) return v.max.replace("{n}", attr("max"));
  if (s.stepMismatch) return v.step.replace("{n}", attr("step"));
  if (s.badInput) return v.number;
  return v.format;
}

let seq = 0;
function show(el: Field) {
  if (el.dataset.ownError !== undefined) return;             // the component shows its own message (DateField)
  el.dataset.errorId ??= `form-error-${++seq}`;
  const id = el.dataset.errorId;
  let note = document.getElementById(id);
  if (!note) {
    note = document.createElement("span");
    note.id = id;
    note.className = "block text-sm font-bold text-danger";
    (el.closest("label") ?? el.parentElement)?.appendChild(note);
  }
  note.textContent = message(el);
  el.setAttribute("aria-invalid", "true");
  el.setAttribute("aria-describedby", id);
}

function clear(el: Field) {
  const id = el.dataset.errorId;
  if (!id) return;
  document.getElementById(id)?.remove();
  el.removeAttribute("aria-invalid");
  el.removeAttribute("aria-describedby");
  delete el.dataset.errorId;
}

export function installFormErrors() {
  let first: Field | null = null;
  document.addEventListener("invalid", (e) => {
    const el = e.target as Field;
    e.preventDefault();                                      // no browser bubble
    show(el);
    if (!first) {                                            // focus the first wrong field of this attempt
      first = el;
      queueMicrotask(() => { first?.focus(); first = null; });
    }
  }, true);
  const recheck = (e: Event) => {
    const el = e.target as Field;
    if (el?.dataset?.errorId) { if (el.validity.valid) clear(el); else show(el); }
  };
  document.addEventListener("input", recheck, true);
  document.addEventListener("change", recheck, true);
}
