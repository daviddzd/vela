// Small shared UI pieces with the accessibility rules: ≥ 48 px targets, text + icon, AA contrast.
import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary";

export function Button({ variant = "primary", icon, children, className = "", ...rest }:
  ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; icon?: string; children: ReactNode }) {
  const look = variant === "primary"
    ? "bg-teal text-white hover:bg-teal-dark"
    : "border-2 border-teal text-teal bg-white hover:bg-teal/10";
  return (
    <button type="button" className={`inline-flex min-h-12 items-center justify-center gap-2 rounded-card px-4 font-bold
      disabled:cursor-not-allowed disabled:opacity-60 ${look} ${className}`} {...rest}>
      {icon && <span aria-hidden="true">{icon}</span>}
      {children}
    </button>
  );
}

export function Card({ children, className = "" }: { children: ReactNode; className?: string }) {
  return <section className={`rounded-card border border-teal/20 bg-white p-5 ${className}`}>{children}</section>;
}

export function Notice({ kind = "info", children }: { kind?: "info" | "ok" | "error"; children: ReactNode }) {
  const look = { info: "border-teal text-ink", ok: "border-ok text-ok", error: "border-danger text-danger" }[kind];
  const icon = { info: "ℹ", ok: "✅", error: "⚠" }[kind];
  return (
    <p role={kind === "error" ? "alert" : "status"} className={`rounded-card border-2 bg-white p-3 font-bold ${look}`}>
      <span aria-hidden="true">{icon} </span>{children}
    </p>
  );
}

export const inputClass =
  "mt-1 block w-full min-h-12 rounded-card border-2 border-muted/60 bg-white px-3 focus:border-teal";
