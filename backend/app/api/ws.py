"""WebSocket endpoint for real-time poker gameplay.

Handles the bidirectional communication channel between frontend and backend:
  - Client sends: action (fold/check/call/raise/all_in), continue, quit
  - Server sends: new_hand, action_required, state_update, bot_action,
                  hand_complete, game_over, error

On connect, spawns two async tasks:
  1. session.run_game_loop()  — drives the game forward
  2. _send_loop()             — drains the session's WS queue and sends to client

On disconnect (or quit), cancels both tasks and removes the session.
"""

import asyncio
import contextlib
import json
import logging
import secrets

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from app.api.schemas import PlayerActionRequest
from app.api.session import get_session, remove_session

logger = logging.getLogger(__name__)
router = APIRouter()

_VALID_WS_MSG_TYPES = {"action", "continue", "quit"}
_WS_MAX_MESSAGE_LEN = 4096


@router.websocket("/game/{game_id}/ws")
async def game_websocket(websocket: WebSocket, game_id: str, token: str = Query()):
    session = get_session(game_id)
    if session is None:
        await websocket.close(code=4004, reason="Game not found")
        return

    if not secrets.compare_digest(session.session_token, token):
        await websocket.close(code=4003, reason="Invalid session token")
        return

    await websocket.accept()

    game_task = asyncio.create_task(session.run_game_loop())
    send_task = asyncio.create_task(_send_loop(websocket, session))

    try:
        while True:
            data = await websocket.receive_text()

            if len(data) > _WS_MAX_MESSAGE_LEN:
                logger.warning("Oversized WS message (%d bytes), ignoring", len(data))
                continue

            try:
                msg = json.loads(data)
            except json.JSONDecodeError:
                logger.warning("Malformed JSON from client: %s", data[:200])
                continue

            msg_type = msg.get("type")
            if msg_type not in _VALID_WS_MSG_TYPES:
                continue

            if msg_type == "action":
                try:
                    parsed = PlayerActionRequest(**msg)
                except (ValidationError, TypeError):
                    logger.warning("Invalid action payload: %s", data[:200])
                    continue
                await session.submit_action(parsed.action, parsed.amount)
            elif msg_type == "continue":
                session.continue_to_next_hand()
            elif msg_type == "quit":
                break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("WebSocket receive error: %s", e, exc_info=True)
        with contextlib.suppress(Exception):
            await websocket.send_json(
                {
                    "type": "error",
                    "data": {"message": "An unexpected server error occurred."},
                }
            )
    finally:
        session.stop()
        game_task.cancel()
        send_task.cancel()
        remove_session(game_id)
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await game_task
        with contextlib.suppress(asyncio.CancelledError, Exception):
            await send_task


async def _send_loop(websocket: WebSocket, session):
    try:
        while True:
            msg = await session.get_ws_message()
            await websocket.send_json(msg)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error("WebSocket send error: %s", e, exc_info=True)
        with contextlib.suppress(Exception):
            await websocket.send_json(
                {
                    "type": "error",
                    "data": {"message": "Connection error - please reconnect."},
                }
            )
