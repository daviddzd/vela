// /voz — ORACLE-Voz for family and caregivers.
// The "Llamar al 911" button is ALWAYS on screen (sticky), whatever else fails.
// Consent is checked by the API before anything is recorded or processed.
// Emergency: full-screen "Esto puede ser una emergencia. Llama al 911 ahora." as soon as the level arrives
// (the physician's report is written afterwards and never delays this screen).
import { Languages, Mic, PhoneCall, Send, Square, X } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import { AppShell } from "../components/AppShell";
import { Button, Card, Highlight, Notice, inputClass } from "../components/ui";
import { AlertTriangle, Icon } from "../components/icons";
import { es } from "../i18n/es";

const t = es.voice;
const MAX_SECONDS = 60;
type Patient = { patient_id: string; name: string; voice_consent: boolean; voice_block?: "no_consent" | "no_assent" | null;
  language: string | null };
type SupportLine = { name: string; phone: string; tel: string };
type Result = { level: string; emergency_source?: "rule" | "classifier" | null; transcript: string; ask_repeat: boolean; needs_human_review: boolean; support_line?: SupportLine | null };

function Call911({ big = false }: { big?: boolean }) {
  return (
    <a href="tel:911" className={`inline-flex items-center justify-center gap-3 rounded-full bg-danger font-bold text-white
      ${big ? "min-h-20 px-8 text-3xl" : "min-h-12 px-5 text-lg"}`}>
      <Icon as={PhoneCall} /> {t.call911}
    </a>
  );
}

export function VoicePage() {
  const { user } = useAuth();
  const [patients, setPatients] = useState<Patient[]>([]);
  const [pid, setPid] = useState("");
  const [mode, setMode] = useState<"idle" | "recording" | "sending" | "write">("idle");
  const [seconds, setSeconds] = useState(0);
  const [text, setText] = useState("");
  const [notice, setNotice] = useState<{ kind: "info" | "error" | "ok"; text: string } | null>(null);
  const [result, setResult] = useState<Result | null>(null);
  // emergency screen: "red" = a rule fired (as always); "amber" = ONLY the classifier said so (CLAUDE.md rule 6)
  const [emergency, setEmergency] = useState<false | "red" | "amber">(false);
  const rec = useRef<MediaRecorder | null>(null);
  const chunks = useRef<Blob[]>([]);
  const timer = useRef<ReturnType<typeof setInterval> | undefined>(undefined);

  useEffect(() => {
    // "Nota de voz" from /mis-visitas opens this screen with the patient already chosen (?paciente=PAC-…)
    const asked = new URLSearchParams(window.location.search).get("paciente");
    api.voicePatients().then((p: Patient[]) => { setPatients(p); setPid((cur) => cur || p.find((x) => x.patient_id === asked)?.patient_id
      || p.find((x) => x.voice_consent)?.patient_id || p[0]?.patient_id || ""); })
      .catch(() => undefined);
    return () => clearInterval(timer.current);
  }, []);
  const patient = patients.find((p) => p.patient_id === pid);
  const staff = user?.role !== "family";

  const handle = (r: Result) => {
    setResult(r);
    setMode("idle");
    if (r.level === "emergency") setEmergency(r.emergency_source === "classifier" ? "amber" : "red");   // at once, before any report
    else setNotice({ kind: r.ask_repeat ? "info" : "ok", text: r.ask_repeat ? t.repeat : t.sent });
  };
  const fail = (status: number, msg: string) => {
    setMode(status === 503 ? "write" : "idle");
    setNotice({ kind: "error", text: status === 403 ? (msg || t.noConsent) : status === 503 ? t.voiceDown : msg || es.common.error });
  };

  const start = async () => {
    setNotice(null); setResult(null);
    if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
      setMode("write"); setNotice({ kind: "info", text: t.micInsecure }); return;
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mr = new MediaRecorder(stream, MediaRecorder.isTypeSupported("audio/webm;codecs=opus") ? { mimeType: "audio/webm;codecs=opus" } : undefined);
      chunks.current = [];
      mr.ondataavailable = (e) => chunks.current.push(e.data);
      mr.onstop = () => { stream.getTracks().forEach((tr) => tr.stop()); upload(); };
      rec.current = mr; mr.start(); setMode("recording"); setSeconds(0);
      timer.current = setInterval(() => setSeconds((s) => { if (s + 1 >= MAX_SECONDS) stop(); return s + 1; }), 1000);
    } catch {
      setMode("write"); setNotice({ kind: "info", text: t.micDenied });       // denied: offer typing
    }
  };
  const stop = () => { clearInterval(timer.current); if (rec.current?.state === "recording") rec.current.stop(); };
  const upload = async () => {
    setMode("sending");
    const form = new FormData();
    form.append("patient_id", pid);
    form.append("audio", new Blob(chunks.current, { type: "audio/webm" }), "nota.webm");
    try {
      const r = await fetch("/api/voice/notes", { method: "POST", body: form, credentials: "include" });
      const body = await r.json().catch(() => ({}));
      r.ok ? handle(body) : fail(r.status, body.detail);
    } catch { fail(503, ""); }
  };
  const sendText = async () => {
    setMode("sending"); setNotice(null);
    try { handle(await api.voiceText(pid, text)); setText(""); }
    catch (e: any) { fail(e.status ?? 0, e.message); }
  };
  const callMe = async () => {
    try { const r = await api.voiceCallMe(pid); setNotice({ kind: "ok", text: t.callMeDone.replace("{lang}", r.language) }); }
    catch (e: any) { setNotice({ kind: "error", text: e.message || es.common.error }); }
  };

  return (
    <AppShell>
      {/* always visible, sticky: even if everything else fails */}
      <div className="section-header sticky top-0 z-30 -mx-4 -mt-6 mb-6 flex flex-wrap items-center justify-between gap-3 px-4 py-4 shadow-[0_2px_12px_rgba(27,51,73,0.06)]">
        <h1 className="text-3xl sm:text-4xl"><Highlight text={es.pageTitles["/voz"]} /></h1>
        <Call911 />
      </div>

      {/* justify-center-safe: centered when it fits; on a small phone it starts at the top and scrolls, so the title
          and the close button are always reachable (plain justify-center pushed the title above the screen) */}
      {emergency === "amber" && (
        <div role="alertdialog" aria-modal="true" aria-labelledby="amber-title" aria-describedby="amber-signs"
          className="fixed inset-0 z-50 flex flex-col items-center justify-center-safe gap-5 overflow-y-auto border-[12px] border-warn bg-[#FFF4DC] p-6 text-center text-ink">
          <p id="amber-title" className="flex items-center gap-3 text-4xl font-bold"><Icon as={AlertTriangle} /> {t.amberTitle}</p>
          <div id="amber-signs" className="max-w-2xl text-left text-2xl">
            <p className="font-bold">{t.amberCallIf}</p>
            <ul className="mt-2 list-disc space-y-1 pl-8">{t.amberSigns.map((s) => <li key={s}>{s}</li>)}</ul>
          </div>
          <a href="tel:911" className="inline-flex min-h-24 items-center gap-4 rounded-full bg-danger px-10 text-4xl font-bold text-white">
            <Icon as={PhoneCall} /> {t.call911}</a>
          <p className="text-2xl font-bold">{t.amberCoordination}</p>
          <button type="button" onClick={() => setEmergency(false)} className="inline-flex min-h-12 items-center gap-2 rounded-full border-2 border-ink px-4 font-bold">
            <Icon as={X} /> {t.emergencyClose}</button>
        </div>
      )}

      {emergency === "red" && (
        <div role="alertdialog" aria-modal="true" aria-labelledby="em-title"
          className="fixed inset-0 z-50 flex flex-col items-center justify-center-safe gap-6 overflow-y-auto bg-danger p-6 text-center text-white">
          <p id="em-title" className="text-4xl font-bold">{t.emergencyTitle}</p>
          <p className="text-3xl font-bold">{t.emergencyCall}</p>
          <a href="tel:911" className="inline-flex min-h-24 items-center gap-4 rounded-full bg-white px-10 text-4xl font-bold text-danger">
            <Icon as={PhoneCall} /> {t.call911}</a>
          {result?.support_line && (   // self-harm: Línea de la Vida too (number from config, official source)
            <div className="flex flex-col items-center gap-3">
              <p className="text-2xl font-bold">{t.supportLine.replace("{name}", result.support_line.name)}</p>
              <a href={`tel:${result.support_line.tel}`} className="inline-flex min-h-16 flex-wrap items-center justify-center gap-x-3 rounded-full border-4 border-white px-6 py-2 text-2xl font-bold sm:text-3xl">
                <Icon as={PhoneCall} /> {t.supportCall.split("{phone}")[0]}
                <span className="whitespace-nowrap">{result.support_line.phone}</span></a>
            </div>)}
          <p className="text-xl">{t.emergencyNotified}</p>
          <button type="button" onClick={() => setEmergency(false)} className="inline-flex min-h-12 items-center gap-2 rounded-full border-2 border-white px-4 font-bold">
            <Icon as={X} /> {t.emergencyClose}</button>
        </div>
      )}

      <Card>
        <p>{t.intro}</p>
        <label className="mt-3 block max-w-md"><span className="font-bold">{t.patient}</span>
          <select className={inputClass} value={pid} onChange={(e) => { setPid(e.target.value); setNotice(null); setResult(null); }}>
            {patients.map((p) => <option key={p.patient_id} value={p.patient_id}>{p.name}</option>)}
          </select>
        </label>
        {patient && !patient.voice_consent && <div className="mt-3"><Notice kind="error">
          {patient.voice_block === "no_assent" ? t.noAssent : t.noConsent}</Notice></div>}
        {notice && <div className="mt-3"><Notice kind={notice.kind}>{notice.text}</Notice></div>}

        {patient?.voice_consent && (
          <div className="mt-4 space-y-4">
            {mode !== "write" && (
              <div className="flex flex-wrap items-center gap-3">
                {mode === "recording"
                  ? <Button icon={Square} className="min-h-16 text-xl" onClick={stop}>{t.stop}</Button>
                  : <Button icon={Mic} className="min-h-16 text-xl" disabled={mode === "sending" || !pid} onClick={start}>{t.record}</Button>}
                {mode === "recording" && <p className="figure text-2xl" aria-live="polite">{t.recording.replace("{s}", String(seconds))}</p>}
                {mode === "sending" && <p aria-live="polite">{t.processing}</p>}
                {mode === "idle" && <Button variant="secondary" onClick={() => setMode("write")}>{t.write}</Button>}
              </div>
            )}
            {mode === "write" && (
              <div>
                <label className="block"><span className="font-bold">{t.writeLabel}</span>
                  <textarea className={`${inputClass} min-h-32 py-2`} value={text} maxLength={2000} onChange={(e) => setText(e.target.value)} /></label>
                <Button className="mt-2" icon={Send} disabled={!text.trim()} onClick={sendText}>{t.send}</Button>
              </div>
            )}
            {mode === "sending" && <p aria-live="polite">{t.processing}</p>}
            {result && result.level !== "emergency" && (
              <div className="rounded-field border border-navy/15 p-3">
                <p className="font-bold">{t.heard}</p><p>«{result.transcript}»</p>
                {staff && <p className="mt-1 text-muted">{t.levelForStaff}: {t.levels[result.level]}</p>}
              </div>
            )}
          </div>
        )}
        <div className="mt-6 border-t border-navy/15 pt-4">
          <Button variant="secondary" icon={Languages} disabled={!pid} onClick={callMe}>{t.callMe}</Button>
        </div>
      </Card>
    </AppShell>
  );
}
