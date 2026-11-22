"""Vela API. All HTTP routes live under /api and WebSockets under /ws, so Caddy forwards
them unchanged (no prefix stripping)."""
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core import events
from app.routers import approvals, auth, board, catalog, family, health, patients, requests, visits
from app.ws import board as ws_board
from app.ws import ping


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the LISTEN loop that feeds /ws/board; stop it on shutdown."""
    task = asyncio.create_task(events.listen_forever())
    try:
        yield
    finally:
        task.cancel()


app = FastAPI(title="Vela API", docs_url="/api/docs", openapi_url="/api/openapi.json", lifespan=lifespan)
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(patients.router)
for module in (catalog, requests, approvals, visits, family, board):
    app.include_router(module.router)
app.include_router(ping.router)
app.include_router(ws_board.router)
