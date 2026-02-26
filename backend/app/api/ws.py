import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.api.session import get_session, remove_session

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/game/{game_id}/ws")
async def game_websocket(websocket: WebSocket, game_id: str):
    session = get_session(game_id)
    if session is None:
        await websocket.close(code=4004, reason="Game not found")
        return

    await websocket.accept()

    game_task = asyncio.create_task(session.run_game_loop())
    send_task = asyncio.create_task(_send_loop(websocket, session))

    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)

            if msg.get("type") == "action":
                action = msg.get("action", "fold")
                amount = msg.get("amount", 0)
                await session.submit_action(action, amount)
            elif msg.get("type") == "continue":
                session.continue_to_next_hand()
            elif msg.get("type") == "quit":
                break
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error("WebSocket receive error: %s", e, exc_info=True)
    finally:
        session.stop()
        game_task.cancel()
        send_task.cancel()
        remove_session(game_id)
        try:
            await game_task
        except (asyncio.CancelledError, Exception):
            pass
        try:
            await send_task
        except (asyncio.CancelledError, Exception):
            pass


async def _send_loop(websocket: WebSocket, session):
    try:
        while True:
            msg = await session.get_ws_message()
            await websocket.send_json(msg)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error("WebSocket send error: %s", e, exc_info=True)
