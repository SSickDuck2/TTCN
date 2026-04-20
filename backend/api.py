import asyncio
import logging
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database.database import init_db
from utils import state

from routers.auth_router import router as auth_router
from routers.market_router import router as market_router
from routers.squad_router import router as squad_router
from routers.player_router import router as player_router
from routers.admin_router import router as admin_router
from routers.ws_router import router as ws_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

@app.on_event("startup")
async def startup_event():
    state.async_event_loop = asyncio.get_running_loop()
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database initialization: {e}")
    state.scheduler.start()

@app.on_event("shutdown")
async def shutdown_event():
    state.scheduler.shutdown()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
