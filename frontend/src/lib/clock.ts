// Real-time clock: the server's wall clock (GET /api/time), shown in Mexico City time.
// Syncs on load and every 5 minutes, then advances locally every second.
import { useEffect, useState } from "react";

const RESYNC_MS = 5 * 60 * 1000;
const TZ = "America/Mexico_City";

export function useServerClock(): { now: Date; synced: boolean } {
  const [offset, setOffset] = useState(0);        // server time − device time, in ms
  const [synced, setSynced] = useState(false);
  const [tick, setTick] = useState(Date.now());

  useEffect(() => {
    const sync = async () => {
      try {
        const sent = Date.now();
        const res = await fetch("/api/time", { credentials: "include" });
        const body = await res.json();
        const received = Date.now();
        // assume the answer was produced halfway through the round trip
        setOffset(body.epoch_ms - (sent + received) / 2);
        setSynced(true);
      } catch {
        setSynced(false);
      }
    };
    sync();
    const resync = setInterval(sync, RESYNC_MS);
    const second = setInterval(() => setTick(Date.now()), 1000);
    return () => { clearInterval(resync); clearInterval(second); };
  }, []);

  return { now: new Date(tick + offset), synced };
}

export function formatClock(d: Date): string {
  return new Intl.DateTimeFormat("es-MX", { timeZone: TZ, hourCycle: "h23", hour: "2-digit", minute: "2-digit", second: "2-digit" }).format(d);
}

export function formatLongDate(d: Date): string {
  return new Intl.DateTimeFormat("es-MX", { timeZone: TZ, weekday: "long", day: "numeric", month: "long" }).format(d);
}
