"""Realtime events: PostgreSQL LISTEN/NOTIFY → WebSocket (/ws/board).

Publishing (sync, from the API and the worker):
    publish(db, "request.created", institution_id, request_id="REQ-…")
runs pg_notify() INSIDE the caller's transaction. PostgreSQL delivers it only when that transaction
commits: a rolled-back change never produces an event.

Events carry NO personal data (type, institution, ids). The board re-reads /api/board, which applies
row-level security and role scope, so the WebSocket is never a second door to the data.

Receiving (async, inside the API process): `listen_forever()` keeps one LISTEN connection and hands
each event to the Hub, which forwards it only to sockets of the same institution (owner gets all).
If PostgreSQL restarts, the loop reconnects by itself and tells every client to resync.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime

import psycopg
from fastapi import WebSocket
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import MEXICO_CITY, get_settings
from app.core.roles import OWNER

CHANNEL = "vela_events"
EVENT_TYPES = ("request.created", "request.updated", "assignment.proposed", "assignment.approved",
               "visit.arrived", "visit.finished", "alert.created")
HEALTH_CHECK_SECONDS = 15      # how often the listener checks its connection is alive
RECONNECT_SECONDS = 2
log = logging.getLogger("vela.events")


def publish(db: Session, event_type: str, institution_id: str | None, **ids: str | None) -> None:
    """Queue an event; it is sent when the caller's transaction commits."""
    assert event_type in EVENT_TYPES, event_type
    payload = {"type": event_type, "institution_id": institution_id,
               "at": datetime.now(MEXICO_CITY).isoformat(), **ids}
    db.execute(text("SELECT pg_notify(:ch, :p)"), {"ch": CHANNEL, "p": json.dumps(payload)})


@dataclass(eq=False)
class Client:
    websocket: WebSocket
    role: str
    institution_id: str | None

    def wants(self, event: dict) -> bool:
        return self.role == OWNER or event.get("institution_id") == self.institution_id


class Hub:
    """Connected board sockets and the state of the LISTEN connection."""

    def __init__(self) -> None:
        self.clients: set[Client] = set()
        self.listening = False               # True while LISTEN is active (tests and /api/health read it)
        self.reconnects = 0

    def add(self, client: Client) -> None:
        self.clients.add(client)

    def remove(self, client: Client) -> None:
        self.clients.discard(client)

    async def broadcast(self, event: dict) -> None:
        for client in list(self.clients):
            if event.get("type") == "board.resync" or client.wants(event):
                try:
                    await client.websocket.send_json(event)
                except Exception:  # noqa: BLE001 - a dead socket must not stop the others
                    self.remove(client)


hub = Hub()


def listener_dsn() -> str:
    """psycopg DSN from the SQLAlchemy URL (postgresql+psycopg://… → postgresql://…)."""
    return get_settings().database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def listener_name() -> str:
    """application_name of the LISTEN connection (includes the process id, so tests can find theirs)."""
    return f"vela-listener-{os.getpid()}"


async def listen_forever() -> None:
    """Keep one LISTEN connection open forever; reconnect if PostgreSQL restarts or the link dies."""
    hub.listening = False
    while True:
        try:
            async with await psycopg.AsyncConnection.connect(
                    listener_dsn(), autocommit=True, application_name=listener_name(),
                    keepalives=1, keepalives_idle=10, keepalives_interval=5, keepalives_count=3) as conn:
                await conn.execute(f"LISTEN {CHANNEL}")
                if hub.reconnects:
                    log.warning("LISTEN reconnected; asking clients to resync")
                    await hub.broadcast({"type": "board.resync"})   # events may have been missed
                hub.listening = True
                while True:
                    async for note in conn.notifies(timeout=HEALTH_CHECK_SECONDS):
                        await hub.broadcast(json.loads(note.payload))
                    await conn.execute("SELECT 1")                  # raises if the server went away
        except asyncio.CancelledError:
            hub.listening = False
            raise
        except Exception as exc:  # noqa: BLE001
            hub.listening = False
            hub.reconnects += 1
            log.warning("LISTEN connection lost (%s); retrying in %s s", exc, RECONNECT_SECONDS)
            await asyncio.sleep(RECONNECT_SECONDS)
