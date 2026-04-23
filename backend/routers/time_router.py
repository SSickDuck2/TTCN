from fastapi import APIRouter
from services.time_engine import time_engine

router = APIRouter(prefix="/api/time")

@router.get("/status")
def get_time_status():
    """Trả về trạng thái thời gian và TTCN hiện tại."""
    return time_engine.get_current_time_info()
