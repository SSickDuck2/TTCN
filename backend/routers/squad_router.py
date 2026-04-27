from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from utils.schemas import Player, SellRequest
from database.database import get_db
from database.models import PlayerInfo, Club
from utils.auth import get_current_club_id
from utils.services import schedule_auction_resolution
from utils import state

router = APIRouter(prefix="/api/squad")

LEAGUE_DISPLAY = {
    "bundesliga": "Bundesliga",
    "epl": "Premier League",
    "la_liga": "La Liga",
    "serie_a": "Serie A",
    "ligue_1": "Ligue 1",
}

def format_league(raw: str) -> str:
    if not raw: return ""
    return LEAGUE_DISPLAY.get(raw.lower(), raw)

@router.get("", response_model=List[Player])
async def get_squad(club_id: int = Depends(get_current_club_id), db: Session = Depends(get_db)):
    club = db.query(Club).filter(Club.id == club_id).first()
    if not club: return []
    players = db.query(PlayerInfo).filter(PlayerInfo.tm_club == club.name).all()
    result = []
    for p in players:
        club_name = p.tm_club or p.team_title or "Unknown"
        result.append(Player(
            player_id=p.id, listing_id=p.id, name=str(p.player_name),
            position=str(p.position or "N/A"),
            market_value=float(p.market_value_in_eur or 0.0),
            club=club_name,
            league=format_league(p.league),
            weekly_wage=0.0,
        ))
    return result

@router.post("/sell")
async def sell_player(request: SellRequest, club_id: int = Depends(get_current_club_id), db: Session = Depends(get_db)):
    club = db.query(Club).filter(Club.id == club_id).first()
    db_player = db.query(PlayerInfo).filter(PlayerInfo.id == request.player_id, PlayerInfo.tm_club == club.name).first()
    if not db_player: raise HTTPException(status_code=404, detail="Player not owned by this club")

    if request.sell_type == "quick_sell":
        market_value = float(db_player.market_value_in_eur or 0.0)
        sell_price = market_value * 0.8
        club.budget_remaining += sell_price
        
        db_player.tm_club = "Cầu thủ tự do"
        db_player.league = "Cầu thủ tự do"
        db_player.market_value_in_eur = 0.0
        
        db.commit()
        return {"message": f"Sold for {sell_price:,.0f}"}
    elif request.sell_type == "auction":
        try:
            listing_id = db_player.id
            start_price = float(db_player.market_value_in_eur or 0.0)
            if start_price <= 0:
                # Fallback or error if no market value
                start_price = 1000000.0 
                
            auction_end_time = datetime.utcnow() + timedelta(minutes=request.duration_minutes)
            
            state.AUCTION_LISTINGS[listing_id] = {
                "listing_id": listing_id,
                "player_id": db_player.id,
                "player_data": {
                    "player_id": db_player.id,
                    "player_name": db_player.player_name,
                    "weekly_wage": 0.0,
                    "market_value_in_eur": start_price
                },
                "seller_club_id": club_id,
                "starting_price": start_price,
                "current_price": start_price,
                "bids": [],
                "status": "active",
                "auction_end_time": auction_end_time
            }
            
            schedule_auction_resolution(listing_id, auction_end_time)
            db.commit()
            return {"message": "Listed for auction"}
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Internal error listing auction: {str(e)}")
