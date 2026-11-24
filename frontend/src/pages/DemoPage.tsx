// /demo — owner only. Changes INPUT data (readings, traffic, availability); the system then detects and
// proposes by itself, exactly as in the real operation. Everything is marked as demonstration.
import { CloudFog, Construction, Mic, RotateCcw, Siren, UserX } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { api } from "../api/client";
import { AppShell } from "../components/AppShell";
import { CheckCircle2, Icon } from "../components/icons";
import { Button, Card, ChoiceList, Notice } from "../components/ui";
import { es } from "../i18n/es";

const t = es.demo;
const ICONS = { normal: RotateCcw, contingency_east: CloudFog, contingency_east_roadblocks: Construction } as const;
type State = { scenario: { scenario: string } | null; default_institution: string;
  institutions: { institution_id: string; name: string; on_shift: number; pending: number }[];
  staff: { caregiver_id: string; institution_id: string; name: string; pending: number; unavailable: boolean; on_shift: boolean }[] };

export function DemoPage() {
  const [s, setS] = useState<State | null>(null);
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [inst, setInst] = useState("");
  const [voiceMsg, setVoiceMsg] = useState("");
  const load = useCallback(() => { api.demoState().then((x) => {
    const st = x as State; setS(st); setInst((cur) => cur || st.default_institution); }).catch(() => undefined); }, []);
  useEffect(load, [load]);
  const run = async (fn: () => Promise<unknown>) => {
    setBusy(true); setMsg("");
    try { await fn(); setMsg(t.done); } catch (e) { setMsg((e as Error).message || es.common.error); }
    setBusy(false); load();
  };
  const active = s?.scenario?.scenario ?? "normal";

  return (
    <AppShell>
      <h1 className="text-navy">{es.screens["/demo"]}</h1>
      <p className="mt-1 max-w-4xl">{t.intro}</p>
      {msg && <div className="mt-3"><Notice kind="ok">{msg}</Notice></div>}
      <div className="items-start mt-4 grid gap-4 xl:grid-cols-2">
        <Card>
          <h2 className="text-navy">{t.worldQ}</h2>
          <ul className="mt-3 space-y-3">
            {(["contingency_east", "contingency_east_roadblocks", "normal"] as const).map((k) => (
              <li key={k} className={`rounded-card border-2 p-3 ${active === k ? "border-navy" : "border-navy/20"}`}>
                <Button className="w-full sm:w-auto" icon={ICONS[k]} variant={active === k ? "primary" : "secondary"} disabled={busy}
                  onClick={() => run(() => api.demoScenario(k))}>{t.scenarios[k]}</Button>
                {active === k && <span className="ml-3 font-bold text-navy"><Icon as={CheckCircle2} /> {t.active}</span>}
                <p className="mt-1 text-muted">{t.scenarioHelp[k]}</p>
              </li>))}
          </ul>
        </Card>
        <Card>
          <h2 className="text-navy">{t.actionsQ}</h2>
          <div className="mt-3">
            <ChoiceList legend={t.institution} name="institution" value={inst} onChange={setInst}
              options={(s?.institutions ?? []).map((i) => ({ value: i.institution_id, title: i.name,
                detail: `${t.onShiftShort.replace("{n}", String(i.on_shift))} · ${i.pending === 1 ? t.pendingShortOne : t.pendingShort.replace("{n}", String(i.pending))}` }))} />
            <p className="mt-1 text-sm text-muted">{t.institutionHelp}</p>
          </div>
          <div className="mt-3 space-y-4">
            <div><Button icon={Siren} disabled={busy || !inst} onClick={() => run(() => api.demoUrgent(inst))}>{t.urgent}</Button>
              <p className="mt-1 text-muted">{t.urgentHelp}</p></div>
            <div>
              <p className="font-bold">{t.caregiverOut}</p>
              <p className="text-muted">{t.caregiverHelp}</p>
              <ul className="mt-2 space-y-2">
                {s?.staff.filter((c) => c.institution_id === inst).slice(0, 5).map((c) => (
                  <li key={c.caregiver_id} className="flex flex-wrap items-center justify-between gap-2 rounded-card border border-navy/20 p-2">
                    <span>{c.name} · {t.pendingVisits.replace("{n}", String(c.pending))}{c.on_shift ? ` · ${t.onShift.replace("{n}", "").trim()}` : ""}</span>
                    {c.unavailable ? <span className="font-bold text-warn"><Icon as={UserX} /> {t.unavailable}</span>
                      : <Button variant="secondary" icon={UserX} disabled={busy} onClick={() => run(() => api.demoCaregiverOut(c.caregiver_id))}>{t.caregiverOut}</Button>}
                  </li>))}
              </ul>
            </div>
            <div>
              <p className="font-bold"><Icon as={Mic} /> {t.voice}</p>
              <p className="text-muted">{t.voiceHelp}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                {(["routine", "urgent", "emergency"] as const).map((k) => (
                  <Button key={k} variant={k === "emergency" ? "primary" : "secondary"} disabled={busy || !inst}
                    onClick={() => run(async () => { const r = await api.demoVoice(inst, k);
                      setVoiceMsg(t.voiceResult.replace("{phrase}", r.phrase_id).replace("{text}", r.transcript).replace("{level}", es.voice.levels[r.level])); })}>
                    {t.voiceKinds[k]}</Button>))}
              </div>
              {voiceMsg && <p className="mt-2" aria-live="polite">{voiceMsg}</p>}
            </div>
          </div>
        </Card>
      </div>
    </AppShell>
  );
}
