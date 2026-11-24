// Small shared UI pieces with the accessibility rules: >= 48 px targets, text + icon, AA contrast.
// Enlaza style (docs/brand.md): pill buttons, white cards with 22 px corners and a soft shadow, icons in soft circles.
import type { ButtonHTMLAttributes, ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Icon, NOTICE_ICON } from "./icons";

type Variant = "primary" | "secondary";

export function Button({ variant = "primary", icon, children, className = "", ...rest }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; icon?: LucideIcon; children: ReactNode }) {
  const look = variant === "primary"
    ? "bg-navy text-white shadow-sm hover:bg-navy-dark"
    : "border-2 border-navy text-navy bg-white hover:bg-sky";
  return (
    <button type="button" className={`inline-flex min-h-12 items-center justify-center gap-2 rounded-full px-6 font-bold
      disabled:cursor-not-allowed disabled:opacity-60 ${look} ${className}`} {...rest}>
      {icon && <Icon as={icon} />}
      {children}
    </button>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-card border border-navy/10 bg-white p-6 shadow-[var(--shadow-card)] ${className}`}>{children}</section>;
}

export function Notice({ kind = "info", children }: { kind?: "info" | "ok" | "error"; children: ReactNode }) {
  const look = { info: "border-navy/30 bg-sky text-ink", ok: "border-ok bg-ok-soft text-ok", error: "border-danger bg-danger-soft text-danger" }[kind];
  return (
    <p role={kind === "error" ? "alert" : "status"} className={`flex gap-2 rounded-field border-2 p-3 font-bold ${look}`}>
      <Icon as={NOTICE_ICON[kind]} className="mt-1" /><span>{children}</span>
    </p>
  );
}

export const inputClass =
  "mt-1 block w-full min-h-12 rounded-field border-2 border-muted/60 bg-white px-3 focus:border-navy";

/** A list of radio choices, each on two lines (title, then detail), so a long name is never cut the way it is inside
 *  a <select> on a phone. Two columns only when the card itself is wide enough (container query). */
export function ChoiceList({ legend, name, value, onChange, options }: {
  legend: ReactNode; name: string; value: string; onChange: (v: string) => void;
  options: { value: string; title: ReactNode; detail?: ReactNode }[];
}) {
  return (
    <fieldset className="@container">
      <legend className="font-bold">{legend}</legend>
      <div className="mt-1 grid gap-2 @xl:grid-cols-2">
        {options.map((o) => {
          const checked = o.value === value;
          return (
            <label key={o.value} className={`flex min-h-12 cursor-pointer items-start gap-3 rounded-field border-2 px-3 py-2
              ${checked ? "border-navy bg-sky" : "border-muted/40 bg-white hover:border-navy/60"}`}>
              <input type="radio" name={name} value={o.value} checked={checked} onChange={() => onChange(o.value)}
                className="mt-0.5 size-6 shrink-0 accent-navy" />
              <span className="leading-snug"><span className="block font-bold">{o.title}</span>
                {o.detail && <span className="block text-muted">{o.detail}</span>}</span>
            </label>);
        })}
      </div>
    </fieldset>
  );
}

/** An icon inside a soft teal circle (the icon itself in teal-text: 5.7:1). `tone` changes the circle for states. */
export function IconCircle({ icon, tone = "teal", size = "md" }: { icon: LucideIcon; tone?: "teal" | "navy" | "ok" | "warn" | "danger"; size?: "md" | "lg" }) {
  const look = { teal: "bg-teal-soft text-teal-text", navy: "bg-sky text-navy", ok: "bg-ok-soft text-ok", warn: "bg-warn-soft text-warn",
    danger: "bg-danger-soft text-danger" }[tone];
  return (
    <span aria-hidden="true" className={`inline-flex shrink-0 items-center justify-center rounded-full ${look} ${size === "lg" ? "size-16" : "size-12"}`}>
      <Icon as={icon} className={size === "lg" ? "size-8!" : "size-6!"} />
    </span>
  );
}

/** A title with one highlighted word: es.ts writes it between asterisks, "Tablero *en vivo*" (teal-text, AA). */
export function Highlight({ text }: { text: string }) {
  return <>{text.split(/(\*[^*]+\*)/).map((part, i) => part.startsWith("*") && part.endsWith("*")
    ? <span key={i} className="text-teal-text">{part.slice(1, -1)}</span> : <span key={i}>{part}</span>)}</>;
}

/** Section header: very light blue gradient, big title with a highlighted word, optional text and actions. */
export function PageHeader({ title, children, actions }: { title: string; children?: ReactNode; actions?: ReactNode }) {
  return (
    <div className="section-header -mx-4 -mt-6 mb-6 px-4 pt-8 pb-6 sm:rounded-b-[32px]">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <h1 className="text-3xl sm:text-4xl"><Highlight text={title} /></h1>
          {children && <div className="mt-2 text-muted">{children}</div>}
        </div>
        {actions && <div className="flex flex-wrap items-center gap-3">{actions}</div>}
      </div>
    </div>
  );
}
