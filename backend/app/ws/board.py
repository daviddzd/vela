"""/ws/board — live events for the coordination board (and the owner, who sees every institution).

Authentication: the same httpOnly session cookie as the REST API, re-checked in the database at
connect time and every minute. Messages are small events without personal data; the page reacts by
re-reading /api/board.

Close codes: 4401 not logged in / session no longer valid · 4403 role not allowed or foreign Origin.
"""
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool

from app.core.db import SessionLocal
from app.core.deps import CurrentUser, load_active_user
from app.core.events import Client, hub
from app.core.proxy import same_origin
from app.core.roles import COORDINATOR, OWNER
from app.core.security import COOKIE_NAME, decode_token

router = APIRouter()
BOARD_ROLES = (COORDINATOR, OWNER)
PING_SECONDS = 25          # Cloudflare closes idle WebSockets after ~100 s
RECHECK_SECONDS = 60


def _user_from_cookie(token: str | None) -> CurrentUser | None:
    claims = decode_token(token) if token else None
    if claims is None:
        return None
    with SessionLocal() as session:
        return load_active_user(session, claims)


@router.websocket("/ws/board")
async def board(websocket: WebSocket) -> None:
    await websocket.accept()          # accept first so the browser receives a meaningful close code
    if not same_origin(websocket):
        await websocket.close(code=4403, reason="origin")
        return
    token = websocket.cookies.get(COOKIE_NAME)
    user = await run_in_threadpool(_user_from_cookie, token)
    if user is None:
        await websocket.close(code=4401, reason="login")
        return
    if user.role not in BOARD_ROLES:
        await websocket.close(code=4403, reason="role")
        return

    client = Client(websocket, user.role, user.institution_id)
    hub.add(client)
    await websocket.send_json({"type": "ready", "listening": hub.listening})
    loop = asyncio.get_running_loop()
    last_check = loop.time()
    try:
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=PING_SECONDS)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
            if loop.time() - last_check >= RECHECK_SECONDS:
                last_check = loop.time()
                if await run_in_threadpool(_user_from_cookie, token) is None:
                    await websocket.close(code=4401, reason="login")
                    return
    except WebSocketDisconnect:
        pass
    finally:
        hub.remove(client)
