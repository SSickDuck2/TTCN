from fastapi import APIRouter, WebSocket, WebSocketDisconnect
import logging
from utils.state import manager

logger = logging.getLogger(__name__)

router = APIRouter()

@router.websocket("/ws/auction/{player_id}")
async def websocket_auction(websocket: WebSocket, player_id: int):
    await manager.connect(websocket, player_id)
    try:
        while True:
            data = await websocket.receive_json()
            logger.debug(f"Received from player {player_id}: {data}")
    except WebSocketDisconnect:
        await manager.disconnect(player_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(player_id, websocket)
