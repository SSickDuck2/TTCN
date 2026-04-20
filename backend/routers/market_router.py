from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta

from utils.schemas import MarketResponse, Player, BidRequest
from database.database import get_db
from database.models import PlayerInfo, Club
from utils.config import settings
from utils.auth import get_current_club_id
from utils.services import normalize_text, get_display_league, check_ffp_compliance, lock_budget, unlock_budget, schedule_auction_resolution
from utils import state

router = APIRouter(prefix="/api/market")

@router.get("/players", response_model=MarketResponse)
async def get_market_players(
    position: Optional[str] = None, min_price: Optional[float] = None, max_price: Optional[float] = None,
    league: Optional[str] = None, name: Optional[str] = None, page: int = 1, db: Session = Depends(get_db)
):
    query = db.query(PlayerInfo).filter(PlayerInfo.tm_club.isnot(None), PlayerInfo.tm_player_id.isnot(None))
    if position: query = query.filter(PlayerInfo.position.ilike(f"%{position}%"))
    if min_price: query = query.filter(PlayerInfo.market_value_eur >= min_price * 1000000)
    if max_price: query = query.filter(PlayerInfo.market_value_eur <= max_price * 1000000)
    if league: 
        lv = settings.LEAGUE_OPTIONS.get(league, league)
        query = query.filter(PlayerInfo.league.ilike(f"%{lv}%"))
        
    player_infos = query.all()
    if name:
        normalized_search = normalize_text(name)
        player_infos = [p for p in player_infos if normalized_search in normalize_text(p.player_name)]
        
    total = len(player_infos)
    pages = max((total + settings.PAGE_SIZE - 1) // settings.PAGE_SIZE, 1)
    page = min(page, pages)
    start = (page - 1) * settings.PAGE_SIZE
    sz = start + settings.PAGE_SIZE
    
    players = []
    for p in player_infos[start:sz]:
        market_value = p.market_value_eur or 0.0
        if p.id not in state.AUCTION_LISTINGS and market_value > 0:
            auction_end_time = datetime.utcnow() + timedelta(hours=2)
            state.AUCTION_LISTINGS[p.id] = {
                "listing_id": p.id,
                "player_id": p.id,
                "player_data": { "player_id": p.id, "player_name": p.player_name, "weekly_wage": 0.0, "market_value_in_eur": market_value },
                "seller_club_id": None,
                "starting_price": market_value,
                "current_price": market_value,
                "bids": [],
                "status": "active",
                "created_at": datetime.utcnow(),
                "auction_end_time": auction_end_time,
            }
            schedule_auction_resolution(p.id, auction_end_time)
            
        players.append(Player(player_id=p.id, listing_id=p.id, name=p.player_name, position=p.position, market_value=market_value, club=p.tm_club, league=get_display_league(p.league), weekly_wage=0.0))
        
    return MarketResponse(players=players, page=page, pages=pages, total=total)

@router.get("/auctions")
async def get_active_auctions():
    auctions = []
    for listing_id, auction in state.AUCTION_LISTINGS.items():
        if auction.get("status") == "active" and len(auction.get("bids", [])) > 0:
            auctions.append({
                "listing_id": listing_id, "player_id": auction.get("player_id"),
                "player_name": auction.get("player_data", {}).get("player_name", "Unknown"),
                "current_price": auction.get("current_price", 0), "status": "active",
                "auction_end_time": auction.get("auction_end_time").isoformat() if auction.get("auction_end_time") else None,
            })
    return auctions

@router.post("/bid")
async def place_bid(request: BidRequest, club_id: int = Depends(get_current_club_id), db: Session = Depends(get_db)):
    listing_id = request.listing_id
    bid_amount = request.bid_amount
    if listing_id not in state.AUCTION_LISTINGS: raise HTTPException(status_code=404, detail="Listing not found")
    auction_data = state.AUCTION_LISTINGS[listing_id]
    if bid_amount < auction_data.get("current_price", 0):
        raise HTTPException(status_code=400, detail=f"Bid amount must be at least {auction_data.get('current_price', 0)}")
        
    pwd = float(auction_data.get("player_data", {}).get("weekly_wage", 0))
    is_compliant, message = check_ffp_compliance(db, club_id, pwd, bid_amount)
    if not is_compliant: raise HTTPException(status_code=400, detail=message)
    
    existing_bids = [b for b in auction_data.get("bids", []) if b["club_id"] == club_id]
    if existing_bids:
        old_bid = existing_bids[0]
        unlock_budget(club_id, old_bid["amount"])
        auction_data["bids"].remove(old_bid)
        
    lock_budget(club_id, bid_amount, listing_id)
    auction_data["bids"].append({"club_id": club_id, "amount": bid_amount, "timestamp": datetime.utcnow()})
    auction_data["current_price"] = bid_amount
    
    club = db.query(Club).filter(Club.id == club_id).first()
    player_id = auction_data.get("player_id", 0)
    await state.manager.broadcast(player_id, {
        "type": "new_bid", "listing_id": listing_id, "player_id": player_id,
        "player_name": auction_data.get("player_data", {}).get("player_name", "Unknown"),
        "current_price": bid_amount, "highest_bidder": club.name if club else "Unknown",
        "bid_count": len(auction_data["bids"]), "timestamp": datetime.utcnow().isoformat()
    })
    return {"message": "Bid placed", "bid_amount": bid_amount, "listing_id": listing_id}
