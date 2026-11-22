// Types and helpers for the SIRAG-D results (GET /api/simulation/results).
import { es } from "../../i18n/es";
import type { CIRow } from "../../charts/CIChart";

export type Row = { scenario?: string; policy?: string; metric: string; mean: number | null; ci_low: number | null;
  ci_high: number | null; n: number; approval_delay?: string; risk_multiplier?: number; knob?: string };
export type TestRow = { scenario: string; metric: string; omnibus: string; omnibus_p: number | null; pairwise_test?: string } &
  Record<string, any>;
export type Results = {
  available: boolean;
  info: { elapsed_seconds: number; workers: number; replications: number; sensitivity_replications: number; seed: number;
    approval?: { auto_apply_after_minutes: number; urgent_within_minutes: number; hold_minutes: number };
    late_tolerance_minutes?: number };
  summary: Row[]; window: Row[]; tests: TestRow[]; sensitivity: (Row & { extra_staff?: string })[];
  sensitivity_tests: (TestRow & { knob: string; level: string })[];
  validation: Record<string, number>[];
  contingency_effect: { scenario: string; at_risk_entries: number; win_at_risk_entries: number; crises: number; win_crises: number }[];
};

export const POLICIES = ["vela_timeout", "risk_plus_live_traffic", "risk_priority", "nearest", "human_dispatcher"];
export const SCENARIOS = ["normal", "contingency_east", "contingency_east_roadblocks"];
export const VELA = "risk_plus_live_traffic";
export const VELA_TIMEOUT = "vela_timeout";
/** The policy the operation runs today (worker: time-limited approval + reservation). */
export const OPERATING = VELA_TIMEOUT;
export const HUMAN = "human_dispatcher";

export function pick(rows: Row[], scenario: string, policy: string, metric: string) {
  return rows.find((r) => r.scenario === scenario && r.policy === policy && r.metric === metric);
}

export function ciRows(rows: Row[], scenario: string, metric: string): CIRow[] {
  return POLICIES.map((p) => {
    const r = pick(rows, scenario, p, metric);
    return { label: es.sim.policies[p], mean: r?.mean ?? null, lo: r?.ci_low ?? null, hi: r?.ci_high ?? null,
      emphasis: p === VELA || p === VELA_TIMEOUT };
  });
}

export const fmt = (v: number | null | undefined, d = 1) => (v == null ? "—" : v.toLocaleString("es-MX", { maximumFractionDigits: d }));
export const fill = (tpl: string, vals: Record<string, string>) => tpl.replace(/\{(\w+)\}/g, (_, k) => vals[k] ?? "");

/** The Spanish conclusion, built from the numbers and the significance tests (never hard-coded). */
export function conclusion(r: Results): string[] {
  const c = es.sim.conclusion;
  const m = (metric: string, policy: string, scenario = "normal") => pick(r.summary, scenario, policy, metric)?.mean ?? null;
  const sig = (metric: string) => {
    const t = r.tests.find((x) => x.scenario === "normal" && x.metric === metric);
    return t ? (t[`${OPERATING}_p_holm`] ?? 1) < 0.05 : false;
  };
  // The summary describes the policy the operation actually runs (Vela with time-limited approval).
  const vals = (metric: string) => ({ vela: fmt(m(metric, OPERATING)), human: fmt(m(metric, HUMAN)) });
  const waitBetter = sig("high_wait_p90_min") && (m("high_wait_p90_min", OPERATING) ?? 0) < (m("high_wait_p90_min", HUMAN) ?? 0);
  return [
    fill(waitBetter ? c.waitBetter : c.waitSame, vals("high_wait_p90_min")),
    fill(sig("crisis_under_60_pct") ? c.crisisBetter : c.crisisSame, vals("crisis_under_60_pct")),
    fill(c.unattended, vals("unattended_pct")),
    fill(c.contingency, { normal: fmt(m("overtime_hours", OPERATING)), block: fmt(m("overtime_hours", OPERATING, "contingency_east_roadblocks")) }),
    fill(c.hiring, { before: fmt(staff(r, "current")), after: fmt(staff(r, "targeted")) }),
  ];
}

function staff(r: Results, level: string) {
  return r.sensitivity.find((x) => x.knob === "extra_staff" && x.extra_staff === level && x.policy === VELA_TIMEOUT
    && x.metric === "unattended_pct")?.mean ?? null;
}
