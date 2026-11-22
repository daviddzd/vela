// Live events from /ws/board. The browser sends the httpOnly session cookie automatically.
// On any event we call onEvent (the page re-reads /api/board). If the socket drops we show
// "Reconectando…" and retry every 3 s; after reconnecting the page re-reads everything.
import { useEffect, useRef, useState } from "react";

export type SocketState = "connecting" | "live" | "reconnecting" | "denied";
const RETRY_MS = 3000;

export function useBoardSocket(onEvent: (e: { type: string }) => void): SocketState {
  const [state, setState] = useState<SocketState>("connecting");
  const handler = useRef(onEvent);
  handler.current = onEvent;

  useEffect(() => {
    let socket: WebSocket | null = null;
    let retry: ReturnType<typeof setTimeout> | undefined;
    let stopped = false;

    const connect = () => {
      const scheme = location.protocol === "https:" ? "wss" : "ws";
      socket = new WebSocket(`${scheme}://${location.host}/ws/board`);
      socket.onmessage = (msg) => {
        const event = JSON.parse(msg.data);
        if (event.type === "ping") return;
        if (event.type === "ready") setState("live");
        handler.current(event);           // "ready" and "board.resync" also trigger a full refresh
      };
      socket.onclose = (e) => {
        if (stopped) return;
        if (e.code === 4401 || e.code === 4403) { setState("denied"); return; }   // not logged in / no access
        setState("reconnecting");
        retry = setTimeout(connect, RETRY_MS);
      };
    };
    connect();
    return () => { stopped = true; clearTimeout(retry); socket?.close(); };
  }, []);

  return state;
}
