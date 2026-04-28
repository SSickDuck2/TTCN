from typing import Dict, Set
from fastapi import WebSocket
from apscheduler.schedulers.background import BackgroundScheduler
import logging

logger = logging.getLogger(__name__)

AUCTION_LISTINGS: Dict[int, dict] = {}
CLUB_BUDGET_LOCKS: Dict[int, float] = {}

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, player_id: int):
        await websocket.accept()
        if player_id not in self.active_connections:
            self.active_connections[player_id] = set()
        self.active_connections[player_id].add(websocket)
    
    async def disconnect(self, player_id: int, websocket: WebSocket):
        if player_id in self.active_connections:
            self.active_connections[player_id].discard(websocket)
            if not self.active_connections[player_id]:
                del self.active_connections[player_id]
    
    async def broadcast(self, player_id: int, message: dict):
        if player_id in self.active_connections:
            disconnected = set()
            for ws in self.active_connections[player_id]:
                try:
                    await ws.send_json(message)
                except:
                    disconnected.add(ws)
            for ws in disconnected:
                await self.disconnect(player_id, ws)

manager = ConnectionManager()
scheduler = BackgroundScheduler()
async_event_loop = None

AI_SIMULATION_ENABLED = False
