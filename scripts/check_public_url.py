# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx", "websockets"]
# ///
"""End-to-end check of the public address (named Cloudflare tunnel), from outside the laptop's network path.

    uv run scripts/check_public_url.py                                   # https://enlaza.zenthinks.com
    uv run scripts/check_public_url.py https://xxx.trycloudflare.com     # the quick tunnel (backup)
    uv run scripts/check_public_url.py --audio nota.wav                  # also sends a voice note

It checks: landing page, HTTPS certificate, login cookie (Secure, HttpOnly, SameSite=Lax), the live board WebSocket
(accepted with our Origin, refused with a foreign one), a family request that reaches the board live, and optionally a
voice note. It creates one service request (and one voice report): run scripts/reset_demo.py afterwards.
Output is in Spanish because the team reads it.
"""
from __future__ import annotations

import asyncio
import json
import socket
import ssl
import sys
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlsplit

import httpx
import websockets

PASSWORD = "Demo2026!"   # public demo password, synthetic users only
COORD = "coordinacion.a@ejemplo.test"
FAMILY = "fam-0002@ejemplo.test"   # medium priority: the request is assigned at once
results: list[tuple[bool, str]] = []


def check(ok: bool, text: str) -> bool:
    results.append((ok, text))
    print(("  OK    " if ok else "  FALLA ") + text, flush=True)
    return ok


def certificate(host: str) -> None:
    ctx = ssl.create_default_context()
    with socket.create_connection((host, 443), timeout=10) as raw, ctx.wrap_socket(raw, server_hostname=host) as s:
        cert = s.getpeercert()
    issuer = dict(x[0] for x in cert["issuer"]).get("organizationName", "?")
    until = datetime.strptime(cert["notAfter"], "%b %d %H:%M:%S %Y %Z")
    check(until > datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7),
          f"certificado HTTPS válido para {host} (emisor {issuer}, vence {until:%Y-%m-%d})")


def login(base: str, email: str) -> httpx.Client:
    c = httpx.Client(base_url=base, timeout=30)
    r = c.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    cookie = r.headers.get("set-cookie", "")
    flags = cookie.lower()
    need_secure = base.startswith("https://")   # over plain http (localhost) the browser would drop a Secure cookie
    check(r.status_code == 200 and ("secure" in flags or not need_secure) and "httponly" in flags and "samesite=lax" in flags,
          f"inicio de sesión {email}: HTTP {r.status_code}, cookie con Secure/HttpOnly/SameSite=Lax"
          f" = {'secure' in flags}/{'httponly' in flags}/{'samesite=lax' in flags}")
    return c


async def websocket_checks(base: str, coord: httpx.Client, family: httpx.Client) -> None:
    host = urlsplit(base).hostname
    ws_url = base.replace("https://", "wss://").replace("http://", "ws://") + "/ws/board"
    cookie = "; ".join(f"{k}={v}" for k, v in coord.cookies.items())
    # a foreign Origin must be refused (CSRF protection), with no code change for our own domain
    try:
        async with websockets.connect(ws_url, origin="https://otro-sitio.example", additional_headers={"Cookie": cookie}) as ws:
            await asyncio.wait_for(ws.recv(), 5)
            await asyncio.wait_for(ws.recv(), 5)
            refused = False
    except websockets.ConnectionClosed as e:
        refused = e.rcvd is not None and e.rcvd.code == 4403
    except Exception:  # noqa: BLE001
        refused = True
    check(refused, "WebSocket con un Origin ajeno: rechazado (4403)")

    async with websockets.connect(ws_url, origin=f"https://{host}", additional_headers={"Cookie": cookie}) as ws:
        first = json.loads(await asyncio.wait_for(ws.recv(), 10))
        check(first.get("type") == "ready", f"WebSocket del tablero con Origin https://{host}: aceptado ({first})")
        services = family.get("/api/services").json()
        when = (datetime.now() + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        t0 = time.monotonic()
        r = family.post("/api/requests", json={"service_id": services[0]["service_id"], "scheduled_for": when.isoformat()})
        check(r.status_code == 201, f"la familia solicita un servicio: HTTP {r.status_code}")
        got = None
        while time.monotonic() - t0 < 15:
            msg = json.loads(await asyncio.wait_for(ws.recv(), 15))
            if msg.get("type") not in ("ready", "ping"):
                got = msg
                break
        check(got is not None, f"el tablero recibe el evento en vivo en {time.monotonic() - t0:.1f} s ({(got or {}).get('type')})")


def voice_note(family: httpx.Client, audio: str) -> None:
    patients = [p for p in family.get("/api/voice/patients").json() if p["voice_consent"]]
    if not check(bool(patients), "la familia tiene un paciente con autorización de voz"):
        return
    with open(audio, "rb") as f:
        r = family.post("/api/voice/notes", data={"patient_id": patients[0]["patient_id"]},
                        files={"audio": ("nota.wav", f, "audio/wav")}, timeout=120)
    body = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
    check(r.status_code == 200, f"nota de voz: HTTP {r.status_code}, nivel «{body.get('level')}», "
                                f"transcripción «{(body.get('transcript') or '')[:70]}»")


def main() -> None:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    audio = sys.argv[sys.argv.index("--audio") + 1] if "--audio" in sys.argv else None
    if audio in args:
        args.remove(audio)
    base = (args[0] if args else "https://enlaza.zenthinks.com").rstrip("/")
    host = urlsplit(base).hostname
    print(f"Revisando {base}")
    r = httpx.get(base + "/", timeout=20, follow_redirects=False)
    check(r.status_code == 200 and 'id="root"' in r.text, f"portada: HTTP {r.status_code}")
    h = httpx.get(base + "/api/health", timeout=20)
    check(h.status_code == 200 and h.json().get("realtime") == "ok", f"/api/health: {h.text.strip()[:120]}")
    if base.startswith("https://"):
        certificate(host)
        plain = httpx.get(f"http://{host}/", timeout=20, follow_redirects=False)
        check(plain.status_code in (301, 302, 307, 308) or plain.status_code == 200,
              f"http:// (sin s) responde {plain.status_code} {plain.headers.get('location', '')}")
    coord = login(base, COORD)
    family = login(base, FAMILY)
    asyncio.run(websocket_checks(base, coord, family))
    if audio:
        voice_note(family, audio)
    bad = [t for ok, t in results if not ok]
    print(f"\n{len(results) - len(bad)} de {len(results)} revisiones bien." + ("" if not bad else " Fallaron: " + "; ".join(bad)))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
