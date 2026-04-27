import asyncio
import logging
import uvicorn
import os
import sys
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Add the current directory (backend) to sys.path so it can find 'database', 'routers', etc.
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import init_db
from utils import state
from services.time_engine import time_engine

from routers.auth_router import router as auth_router
from routers.market_router import router as market_router
from routers.squad_router import router as squad_router
from routers.player_router import router as player_router
from routers.admin_router import router as admin_router
from routers.ws_router import router as ws_router
from routers.negotiation_router import router as negotiation_router
from routers.time_router import router as time_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Tắt bớt log rác của apscheduler (tick mỗi giây)
logging.getLogger('apscheduler').setLevel(logging.WARNING)

app = FastAPI(title="TTCN API", description="Transfermarkt Club Network API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(market_router)
app.include_router(squad_router)
app.include_router(player_router)
app.include_router(admin_router)
app.include_router(ws_router)
app.include_router(negotiation_router)
app.include_router(time_router)

@app.on_event("startup")
async def startup_event():
    state.async_event_loop = asyncio.get_running_loop()
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database initialization: {e}")
        
    def run_simulation_job():
        if not getattr(state, 'AI_SIMULATION_ENABLED', False):
            return
        
        from database.database import SessionLocal
        from services.simulation_engine import simulation_engine
        try:
            with SessionLocal() as db:
                simulation_engine.run_simulation_cycle(db)
        except Exception as sim_ext:
            logger.error(f"Lỗi khi chạy Market Bot Simulator: {sim_ext}")

    state.scheduler.add_job(time_engine.advance_time, 'interval', seconds=1)
    state.scheduler.add_job(run_simulation_job, 'interval', seconds=5, id="simulation_bot")
    state.scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    state.scheduler.shutdown()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
