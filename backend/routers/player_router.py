from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from database.database import get_db
from database.models import PlayerInfo, Club
from utils import state

router = APIRouter(prefix="/api/player")

@router.get("/{player_id}")
async def get_player_api(player_id: int, db: Session = Depends(get_db)):
    player = db.query(PlayerInfo).filter(PlayerInfo.id == player_id).first()
    if not player: raise HTTPException(status_code=404, detail="Player not found")
        
    auction_info = None
    if player_id in state.AUCTION_LISTINGS and state.AUCTION_LISTINGS[player_id]["status"] == "active":
        auction = state.AUCTION_LISTINGS[player_id]
        highest_bidder = "None"
        bids = auction.get("bids", [])
        if bids:
            highest_bid = max(bids, key=lambda b: b["amount"])
            club = db.query(Club).filter(Club.id == highest_bid["club_id"]).first()
            if club: highest_bidder = club.name
        
        auction_info = {
            "listing_id": auction["listing_id"],
            "current_price": auction["current_price"],
            "highest_bidder": highest_bidder,
            "end_time": auction["auction_end_time"].isoformat() if auction["auction_end_time"] else None
        }

    return {
        "player": {
            "id": player.id, "name": player.player_name, "club": player.tm_club,
            "position": player.position, "age": player.age, "nation": player.nation,
            "market_value": player.market_value_eur, "league": player.league,
            "stats": {
                "matches": player.playing_time_mp, "starts": player.playing_time_starts,
                "minutes": player.playing_time_min, "goals": player.performance_gls,
                "assists": player.performance_ast, "yellow_cards": player.performance_crdy,
                "red_cards": player.performance_crdr
            }
        },
        "auction": auction_info
    }
