from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel

from database.database import get_db
from database.models import SystemState, SystemStateEnum, Club, Negotiation, MarketListing, Bid, Contract, PlayerInfo
from services.simulation_engine import SimulationEngine
from services.time_engine import time_engine
from utils import state

router = APIRouter(prefix="/api/admin")

class TimeAdvanceRequest(BaseModel):
    days: int

class StateSetRequest(BaseModel):
    state: str

@router.post("/time/set-state")
def set_system_state(req: StateSetRequest, db: Session = Depends(get_db)):
    state_record = db.query(SystemState).first()
    if not state_record:
        raise HTTPException(status_code=400, detail="No system state found")
    
    try:
        new_state = SystemStateEnum(req.state)
        state_record.current_state = new_state
        db.commit()
        
        # Đồng bộ lại TimeEngine cache
        time_engine.force_sync()
        
        return {"status": "success", "new_state": req.state}
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid state")

@router.post("/time/advance")
def advance_time(req: TimeAdvanceRequest, db: Session = Depends(get_db)):
    state_record = db.query(SystemState).first()
    if not state_record or not state_record.current_date:
        raise HTTPException(status_code=400, detail="No system state found")
    
    state_record.current_date += timedelta(days=req.days)
    db.commit()
    
    # Đồng bộ lại TimeEngine cache
    time_engine.force_sync()
    
    return {"status": "success", "new_date": state_record.current_date.isoformat()}

@router.post("/simulation/trigger")
def trigger_simulation(db: Session = Depends(get_db)):
    engine = SimulationEngine()
    engine.run_simulation_cycle(db)
    return {"status": "success", "message": "Simulation cycle completed"}

@router.post("/data/reset")
def reset_data(db: Session = Depends(get_db)):
    """Reset toàn bộ dữ liệu về trạng thái ban đầu."""
    from database.models import BudgetLock, ClubSeasonRecord, SystemState
    try:
        # 1. Xóa các bảng giao dịch & dữ liệu động
        db.query(BudgetLock).delete()
        db.query(Bid).delete()
        db.query(MarketListing).delete()
        db.query(Negotiation).delete()
        db.query(Contract).delete()
        db.query(ClubSeasonRecord).delete()
        
        # 2. Reset ngân sách CLB & lương theo độ giàu thực tế
        from sqlalchemy import func
        # Lấy danh sách tổng giá trị đội hình dựa trên CLB HIỆN TẠI (tm_club)
        squad_values = db.query(
            PlayerInfo.tm_club, 
            PlayerInfo.league, 
            func.sum(PlayerInfo.market_value_in_eur)
        ).filter(
            PlayerInfo.tm_club.isnot(None),
            PlayerInfo.tm_club != "",
            PlayerInfo.tm_club != "Free Agent"
        ).group_by(PlayerInfo.tm_club).all()
        
        league_bonuses = {'epl': 50e6, 'la_liga': 30e6, 'bundesliga': 30e6, 'serie_a': 30e6, 'ligue_1': 20e6}
        
        for club_name, league, total_val in squad_values:
            bonus = league_bonuses.get(league, 10e6)
            calc_budget = (total_val * 0.15) + bonus
            final_budget = max(20e6, min(600e6, calc_budget))
            db.query(Club).filter(Club.name == club_name).update({"budget_remaining": final_budget})
        
        db.query(Club).update({"wage_spent": 0.0})
        db.query(Club).update({"is_transfer_banned": False})
        
        # 3. TRẢ CẦU THỦ VỀ CLB GỐC
        from sqlalchemy import not_
        db.query(PlayerInfo).filter(not_(PlayerInfo.team_title.contains(','))).update({
            "tm_club": PlayerInfo.team_title
        }, synchronize_session=False)
        
        # 4. Reset ngày hệ thống & trạng thái
        db.query(SystemState).delete()
        new_state = SystemState(
            id=1,
            current_date=datetime(2026, 6, 1),
            current_state=SystemStateEnum.TRANSFER_OPEN,
            season_year=2025
        )
        db.add(new_state)

        # 5. Khôi phục lại League gốc
        from sqlalchemy import text
        db.execute(text('''
            UPDATE player_info 
            SET league = (
                SELECT league 
                FROM player_info p2 
                WHERE p2.team_title = player_info.team_title 
                AND p2.league IS NOT NULL 
                AND p2.league != ""
                LIMIT 1
            )
            WHERE team_title NOT LIKE "%,%"
        '''))
        
        db.commit()
        
        # QUAN TRỌNG: Đồng bộ lại TimeEngine sau khi reset ngày
        time_engine.force_sync()
        state.AI_SIMULATION_ENABLED = False
        
        return {"status": "success", "message": "System reset to defaults."}
    except Exception as e:
        db.rollback()
        # Trả về lỗi chi tiết trong thông báo success để dễ debug
        return {"status": "error", "message": f"Reset failed: {str(e)}"}

@router.get("/simulation/status")
def get_simulation_status():
    return {"enabled": getattr(state, "AI_SIMULATION_ENABLED", False)}

@router.post("/simulation/toggle")
def toggle_simulation():
    current_state = getattr(state, "AI_SIMULATION_ENABLED", False)
    state.AI_SIMULATION_ENABLED = not current_state
    return {"enabled": state.AI_SIMULATION_ENABLED}

@router.get("/negotiations")
def get_all_negotiations(db: Session = Depends(get_db)):
    """Admin: Theo dõi tất cả các phiên đàm phán."""
    negos = db.query(Negotiation).order_by(Negotiation.updated_at.desc()).all()
    result = []
    for n in negos:
        player = db.query(PlayerInfo).filter(PlayerInfo.id == n.player_id).first()
        buyer = db.query(Club).filter(Club.id == n.buying_club_id).first()
        seller = db.query(Club).filter(Club.id == n.selling_club_id).first()
        result.append({
            "id": n.id,
            "player_name": player.player_name if player else "Unknown",
            "buyer_name": buyer.name if buyer else "System",
            "seller_name": seller.name if seller else "Free Agent",
            "status": n.status,
            "current_offer": n.current_offer,
            "demand": n.selling_club_demand,
            "round": n.round_number,
            "updated_at": n.updated_at.isoformat()
        })
    return result

@router.post("/negotiations/{negotiation_id}/cancel")
def admin_cancel_nego(negotiation_id: int, db: Session = Depends(get_db)):
    """Admin: Hủy phiên đàm phán bất kỳ."""
    from database.models import NegotiationStatusEnum
    nego = db.query(Negotiation).filter(Negotiation.id == negotiation_id).first()
    if not nego:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    
    nego.status = NegotiationStatusEnum.CANCELLED
    db.commit()
    return {"status": "success", "message": "Negotiation cancelled by Admin"}

@router.get("/system/health")
def system_health(db: Session = Depends(get_db)):
    total_clubs = db.query(Club).count()
    total_contracts = db.query(Contract).count()
    from sqlalchemy import or_
    clubs_in_debt = db.query(Club).filter(or_(Club.budget_remaining < 0, Club.is_transfer_banned == True)).count()
    
    return {
        "total_clubs": total_clubs,
        "total_contracts": total_contracts,
        "clubs_in_debt": clubs_in_debt
    }

@router.get("/clubs/debt")
def get_clubs_in_debt(db: Session = Depends(get_db)):
    from sqlalchemy import or_
    clubs = db.query(Club).filter(or_(Club.budget_remaining < 0, Club.is_transfer_banned == True)).all()
    return [{
        "id": c.id,
        "name": c.name,
        "budget": c.budget_remaining,
        "is_banned": c.is_transfer_banned
    } for c in clubs]
