// "93 % emergencia · 5 % rutina · 2 % urgente": the classifier's probabilities, highest first.
// Shown to the physician and to coordination only, never to the family (team decision 25 Nov 2026).
import { es } from "../i18n/es";

export type ClassifierProbs = Record<string, number> | null | undefined;

export function classifierText(probs: ClassifierProbs): string | null {
  if (!probs) return null;
  const entries = Object.entries(probs).filter(([, v]) => typeof v === "number");
  if (!entries.length) return null;
  return entries.sort((a, b) => b[1] - a[1])
    .map(([k, v]) => `${Math.round(v * 100)}\u00a0%\u00a0${es.classifierConfidence.levels[k] ?? k}`).join(" · ");
}
