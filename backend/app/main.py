"""Vela API. All HTTP routes live under /api and WebSockets under /ws, so Caddy forwards
them unchanged (no prefix stripping)."""
from fastapi import FastAPI

from app.routers import approvals, auth, catalog, family, health, patients, requests, visits
from app.ws import ping

app = FastAPI(title="Vela API", docs_url="/api/docs", openapi_url="/api/openapi.json")
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(patients.router)
for module in (catalog, requests, approvals, visits, family):
    app.include_router(module.router)
app.include_router(ping.router)
