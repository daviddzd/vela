"""Simple in-memory limit of failed login attempts per IP (5 per minute).

Only FAILED attempts count: during the defense many people log in from the same venue Wi-Fi
(same public IP) and a correct login must never be blocked. In memory is enough for a single
API process; it resets when the container restarts.
"""
import time
from collections import defaultdict, deque

from fastapi import Request

WINDOW_SECONDS = 60
_failures: dict[str, deque[float]] = defaultdict(deque)


def client_ip(request: Request) -> str:
    """Real client IP: Cloudflare sends Cf-Connecting-Ip; Caddy sets X-Forwarded-For
    (uvicorn --proxy-headers already applies it to request.client)."""
    return request.headers.get("cf-connecting-ip") or (request.client.host if request.client else "unknown")


def _recent(ip: str) -> deque[float]:
    attempts = _failures[ip]
    cutoff = time.monotonic() - WINDOW_SECONDS
    while attempts and attempts[0] < cutoff:
        attempts.popleft()
    return attempts


def is_blocked(ip: str, limit: int) -> bool:
    return len(_recent(ip)) >= limit


def record_failure(ip: str) -> None:
    _recent(ip).append(time.monotonic())


def reset() -> None:
    """Forget every attempt (used by the tests)."""
    _failures.clear()
