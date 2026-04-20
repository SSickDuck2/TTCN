from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime

from database.database import get_db
from database.models import PlayerInfo, Club
from utils import state

router = APIRouter(prefix="/api/player")

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
        
        bid_history = []
        for b in sorted(auction.get("bids", []), key=lambda x: x["timestamp"], reverse=True):
            bid_club = db.query(Club).filter(Club.id == b["club_id"]).first()
            bid_history.append({
                "bidder": bid_club.name if bid_club else "Unknown",
                "amount": b["amount"],
                "time": b["timestamp"].isoformat()
            })

        auction_info = {
            "listing_id": auction["listing_id"],
            "current_price": auction["current_price"],
            "highest_bidder": highest_bidder,
            "end_time": auction["auction_end_time"].isoformat() if auction["auction_end_time"] else None,
            "bid_history": bid_history
        }

    return {
        "player": {
            "id": player.id, "name": player.player_name, "club": player.tm_club or player.team_title,
            "position": player.position, "age": player.age, "nation": None,
            "market_value": player.market_value_in_eur, "league": format_league(player.league),
            "foot": player.foot, "height": player.height_in_cm,
            "stats": {
                "matches": player.games,
                "minutes": player.time,
                "goals": player.goals,
                "assists": player.assists,
                "shots": player.shots,
                "key_passes": player.key_passes,
                "yellow_cards": player.yellow_cards,
                "red_cards": player.red_cards,
                "xG": player.xG,
                "xA": player.xA,
                "npg": player.npg,
                "npxG": player.npxG,
                "xGChain": player.xGChain,
                "xGBuildup": player.xGBuildup
            }
        },
        "auction": auction_info
    }
