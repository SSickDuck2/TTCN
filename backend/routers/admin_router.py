from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel

from database.database import get_db
from database.models import SystemState, SystemStateEnum, Club, Negotiation, MarketListing, Bid, Contract
from services.simulation_engine import SimulationEngine

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
    return {"status": "success", "new_date": state_record.current_date.isoformat()}

@router.post("/simulation/trigger")
def trigger_simulation(db: Session = Depends(get_db)):
    engine = SimulationEngine()
    engine.run_simulation_cycle(db)
    return {"status": "success", "message": "Simulation cycle completed"}

@router.post("/data/reset")
def reset_data(db: Session = Depends(get_db)):
    # Reset date to 2024-06-01
    state_record = db.query(SystemState).first()
    if state_record:
        state_record.current_date = datetime(2024, 6, 1)
        state_record.current_state = SystemStateEnum.TRANSFER_OPEN
    
    # Delete all negotiations
    db.query(Negotiation).delete()
    
    # Delete all bids
    db.query(Bid).delete()
    
    # Delete all market listings
    db.query(MarketListing).delete()
    
    # Reset club budgets to 100M
    db.query(Club).update({Club.budget_remaining: 100000000.0})
    
    db.commit()
    return {"status": "success", "message": "System reset to defaults"}

@router.get("/system/health")
def system_health(db: Session = Depends(get_db)):
    total_clubs = db.query(Club).count()
    total_contracts = db.query(Contract).count()
    clubs_in_debt = db.query(Club).filter(Club.budget_remaining < 0).count()
    
    return {
        "total_clubs": total_clubs,
        "total_contracts": total_contracts,
        "clubs_in_debt": clubs_in_debt
    }
