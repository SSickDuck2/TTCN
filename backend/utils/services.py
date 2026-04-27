import unicodedata
from typing import Optional
from datetime import datetime
import asyncio
import logging
from sqlalchemy.orm import Session

from utils.config import settings
from utils import state
from database.database import SessionLocal
from database.models import Club, PlayerInfo
from services.contract_engine import contract_engine

logger = logging.getLogger(__name__)

def normalize_text(value: Optional[str]) -> str:
    if not value: return ""
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()

def get_display_league(league_code: Optional[str]) -> str:
    if not league_code: return ""
    for display_name, code in settings.LEAGUE_OPTIONS.items():
        if league_code.lower().startswith(code.lower()) or league_code.lower() == code.lower():
            return display_name
    return league_code or ""

def check_ffp_compliance(db: Session, club_id: int, new_wage: float, bid_amount: float) -> tuple[bool, str]:
    club = db.query(Club).filter(Club.id == club_id).first()
    if not club: return False, "Club not found"
    
    if club.is_transfer_banned:
        return False, "Câu lạc bộ đang bị cấm chuyển nhượng do vi phạm quy định tài chính."
        
    new_total_wages = club.wage_spent + new_wage
    if new_total_wages > club.wage_budget:
        excess = new_total_wages - club.wage_budget
        return False, f"Wage budget exceeded by {excess:,.0f}. Max weekly wage: {club.wage_budget:,.0f}"
        
    return True, "FFP compliant"

def lock_budget(club_id: int, amount: float, bid_id: int):
    if club_id not in state.CLUB_BUDGET_LOCKS:
        state.CLUB_BUDGET_LOCKS[club_id] = 0
    state.CLUB_BUDGET_LOCKS[club_id] += amount

def unlock_budget(club_id: int, amount: float):
    if club_id in state.CLUB_BUDGET_LOCKS:
        state.CLUB_BUDGET_LOCKS[club_id] = max(0, state.CLUB_BUDGET_LOCKS[club_id] - amount)

async def resolve_auction(listing_id: int):
    if listing_id not in state.AUCTION_LISTINGS: return
    auction_data = state.AUCTION_LISTINGS[listing_id]
    bids = auction_data.get("bids", [])
    
    if not bids:
        auction_data["status"] = "cancelled"
        return
        
    winning_bid = max(bids, key=lambda b: b["amount"])
    winning_club_id = winning_bid["club_id"]
    winning_amount = winning_bid["amount"]
    player_id = auction_data["player_id"]
    player = auction_data["player_data"]
    
    with SessionLocal() as db:
        winning_club = db.query(Club).filter(Club.id == winning_club_id).first()
        if winning_club:
            winning_club.budget_remaining -= winning_amount
            winning_club.wage_spent += float(player.get("weekly_wage", 0))
            
            # Cập nhật thông tin cũ
            player_info = db.query(PlayerInfo).filter(PlayerInfo.id == player_id).first()
            if player_info:
                player_info.tm_club = winning_club.name
                
            # Tạo mới Hợp đồng với CLB trúng đấu giá sử dụng ContractEngine
            contract_engine.create_contract(
                db=db, 
                player_id=player_id, 
                club_id=winning_club_id, 
                base_salary=float(player.get("weekly_wage", 10000)),
                remaining_years=4
            )
        db.commit()
        
    for bid in bids:
        if bid["club_id"] != winning_club_id:
            unlock_budget(bid["club_id"], bid["amount"])
            
    auction_data["status"] = "sold"
    auction_data["winning_bid"] = winning_bid
    
    await state.manager.broadcast(player_id, {
        "type": "auction_closed",
        "listing_id": listing_id,
        "player_id": player_id,
        "winner_club_id": winning_club_id,
        "final_price": winning_amount,
        "player_name": player.get("player_name", ""),
    })

def run_auction_resolution(listing_id: int):
    if state.async_event_loop is None:
        asyncio.run(resolve_auction(listing_id))
    else:
        asyncio.run_coroutine_threadsafe(resolve_auction(listing_id), state.async_event_loop)

def schedule_auction_resolution(listing_id: int, end_time: datetime):
    delay_seconds = (end_time - datetime.utcnow()).total_seconds()
    if delay_seconds > 0:
        state.scheduler.add_job(
            run_auction_resolution,
            'date',
            run_date=end_time,
            args=[listing_id],
            id=f"auction_{listing_id}",
            replace_existing=True,
        )
