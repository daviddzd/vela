"""Placeholder WebSocket so the /ws route through Caddy can be tested before the live board
(step 4) exists. It sends one message and closes; no data is exposed."""
from fastapi import APIRouter, WebSocket

router = APIRouter()


@router.websocket("/ws/ping")
async def ws_ping(websocket: WebSocket) -> None:
    await websocket.accept()
    await websocket.send_json({"type": "pong"})
    await websocket.close()
