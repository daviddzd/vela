// Small shared UI pieces with the accessibility rules: >= 48 px targets, text + icon, AA contrast.
import type { ButtonHTMLAttributes, ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Icon, NOTICE_ICON } from "./icons";

type Variant = "primary" | "secondary";

export function Button({ variant = "primary", icon, children, className = "", ...rest }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; icon?: LucideIcon; children: ReactNode }) {
  const look = variant === "primary"
    ? "bg-teal text-white hover:bg-teal-dark"
    : "border-2 border-teal text-teal bg-white hover:bg-teal/10";
  return (
    <button type="button" className={`inline-flex min-h-12 items-center justify-center gap-2 rounded-card px-4 font-bold
      disabled:cursor-not-allowed disabled:opacity-60 ${look} ${className}`} {...rest}>
      {icon && <Icon as={icon} />}
      {children}
    </button>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-card border border-teal/20 bg-white p-5 ${className}`}>{children}</section>;
}

export function Notice({ kind = "info", children }: { kind?: "info" | "ok" | "error"; children: ReactNode }) {
  const look = { info: "border-teal text-ink", ok: "border-ok text-ok", error: "border-danger text-danger" }[kind];
  return (
    <p role={kind === "error" ? "alert" : "status"} className={`flex gap-2 rounded-card border-2 bg-white p-3 font-bold ${look}`}>
      <Icon as={NOTICE_ICON[kind]} className="mt-1" /><span>{children}</span>
    </p>
  );
}

export const inputClass =
  "mt-1 block w-full min-h-12 rounded-card border-2 border-muted/60 bg-white px-3 focus:border-teal";

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
            <label key={o.value} className={`flex min-h-12 cursor-pointer items-start gap-3 rounded-card border-2 px-3 py-2
              ${checked ? "border-teal bg-teal/5" : "border-muted/40 bg-white hover:border-teal/60"}`}>
              <input type="radio" name={name} value={o.value} checked={checked} onChange={() => onChange(o.value)}
                className="mt-0.5 size-6 shrink-0 accent-teal" />
              <span className="leading-snug"><span className="block font-bold">{o.title}</span>
                {o.detail && <span className="block text-muted">{o.detail}</span>}</span>
            </label>);
        })}
      </div>
    </fieldset>
  );
}
