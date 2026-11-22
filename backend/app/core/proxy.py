"""What the browser really used, behind Cloudflare → cloudflared → Caddy → uvicorn.

cloudflared talks plain http to Caddy, so the scheme seen inside Docker is "http" even when the
visitor uses https. Cloudflare adds `Cf-Visitor: {"scheme":"https"}` and `X-Forwarded-Proto: https`;
Caddy keeps X-Forwarded-* only from trusted proxies (infra/Caddyfile → trusted_proxies).
"""
from starlette.requests import HTTPConnection
from urllib.parse import urlsplit


def is_https(conn: HTTPConnection) -> bool:
    visitor = conn.headers.get("cf-visitor", "")
    if '"https"' in visitor.replace(" ", ""):
        return True
    if conn.headers.get("x-forwarded-proto", "").split(",")[0].strip() == "https":
        return True
    return conn.url.scheme in ("https", "wss")


def public_host(conn: HTTPConnection) -> str:
    """Host the browser typed (X-Forwarded-Host if a proxy set it, else Host). Lower-case, no port."""
    host = conn.headers.get("x-forwarded-host") or conn.headers.get("host", "")
    return host.split(",")[0].strip().lower().rsplit(":", 1)[0] if host else ""


def same_origin(conn: HTTPConnection) -> bool:
    """WebSocket CSRF protection: a browser always sends Origin; it must name the same HOST we serve
    (the scheme is ignored on purpose: inside Docker everything looks like http). Clients without
    Origin (scripts, tests) are allowed: the cookie is still required."""
    origin = conn.headers.get("origin")
    if not origin:
        return True
    origin_host = (urlsplit(origin).hostname or "").lower()
    return origin_host == public_host(conn)
