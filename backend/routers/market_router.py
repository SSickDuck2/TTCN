from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import distinct
from typing import Optional, List
from datetime import datetime, timedelta

from utils.schemas import MarketResponse, Player, BidRequest
from database.database import get_db
from database.models import PlayerInfo, Club
from utils.config import settings
from utils.auth import get_current_club_id
from utils.services import normalize_text, check_ffp_compliance, lock_budget, unlock_budget, schedule_auction_resolution
from utils import state

router = APIRouter(prefix="/api/market")

# Maps raw DB league slug -> display name
LEAGUE_DISPLAY = {
    "bundesliga": "Bundesliga",
    "epl": "Premier League",
    "la_liga": "La Liga",
    "serie_a": "Serie A",
    "ligue_1": "Ligue 1",
}
# Reverse map: display name -> DB slug
LEAGUE_SLUG = {v: k for k, v in LEAGUE_DISPLAY.items()}

def format_league(raw: str) -> str:
    if not raw:
        return ""
    return LEAGUE_DISPLAY.get(raw.lower(), raw)


@router.get("/clubs")
async def get_clubs_by_league(league: str, db: Session = Depends(get_db)):
    """Return distinct club names for a given league (display name)."""
    raw_league = LEAGUE_SLUG.get(league, league.lower())
    from sqlalchemy import func
    clubs = (
        db.query(func.coalesce(PlayerInfo.tm_club, PlayerInfo.team_title))
        .filter(
            PlayerInfo.league == raw_league,
            func.coalesce(PlayerInfo.tm_club, PlayerInfo.team_title).isnot(None),
            ~PlayerInfo.team_title.contains(","),  # exclude multi-season rows
        )
        .distinct()
        .order_by(func.coalesce(PlayerInfo.tm_club, PlayerInfo.team_title))
        .all()
    )
    return [c[0] for c in clubs if c[0]]


@router.get("/players", response_model=MarketResponse)
async def get_market_players(
    position: Optional[str] = Query(None),
    min_price: Optional[float] = Query(None),
    max_price: Optional[float] = Query(None),
    min_age: Optional[float] = Query(None),
    max_age: Optional[float] = Query(None),
    league: Optional[str] = Query(None),
    club: Optional[str] = Query(None),
    name: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    club_id: int = Depends(get_current_club_id),
):
    current_club = db.query(Club).filter(Club.id == club_id).first()
    current_club_name = current_club.name if current_club else None

    query = db.query(PlayerInfo).filter(
        PlayerInfo.market_value_in_eur.isnot(None),
        PlayerInfo.market_value_in_eur > 0,
    )

    if current_club_name:
        query = query.filter(PlayerInfo.tm_club != current_club_name)

    if position:
        query = query.filter(PlayerInfo.position == position)

    if min_price is not None and min_price >= 0:
        query = query.filter(PlayerInfo.market_value_in_eur >= min_price * 1_000_000)

    if max_price is not None:
        query = query.filter(PlayerInfo.market_value_in_eur <= max_price * 1_000_000)

    if min_age is not None:
        query = query.filter(PlayerInfo.age >= min_age)

    if max_age is not None:
        query = query.filter(PlayerInfo.age <= max_age)

    if league:
        raw_league = LEAGUE_SLUG.get(league, league.lower())
        query = query.filter(PlayerInfo.league == raw_league)

    if club:
        from sqlalchemy import func
        # Filter where current owner matches OR (if no owner set) original team matches
        query = query.filter(func.coalesce(PlayerInfo.tm_club, PlayerInfo.team_title) == club)

    if name:
        normalized_search = normalize_text(name)
        player_infos = query.all()
        player_infos = [p for p in player_infos if normalized_search in normalize_text(p.player_name)]
    else:
        player_infos = query.order_by(PlayerInfo.market_value_in_eur.desc()).all()

    total = len(player_infos)
    pages = max((total + page_size - 1) // page_size, 1)
    page = min(page, pages)
    start = (page - 1) * page_size
    paged = player_infos[start: start + page_size]

    players = []
    for p in paged:
        market_value = p.market_value_in_eur or 0.0
        club_name = p.tm_club or p.team_title or "Unknown"

        if p.id not in state.AUCTION_LISTINGS and market_value > 0:
            auction_end_time = datetime.utcnow() + timedelta(hours=2)
            state.AUCTION_LISTINGS[p.id] = {
                "listing_id": p.id,
                "player_id": p.id,
                "player_data": {"player_id": p.id, "player_name": p.player_name, "weekly_wage": 0.0, "market_value_in_eur": market_value},
                "seller_club_id": None,
                "starting_price": market_value,
                "current_price": market_value,
                "bids": [],
                "status": "active",
                "created_at": datetime.utcnow(),
                "auction_end_time": auction_end_time,
            }
            schedule_auction_resolution(p.id, auction_end_time)

        players.append(Player(
            player_id=p.id,
            listing_id=p.id,
            name=p.player_name or "Unknown",
            position=p.position or "N/A",
            market_value=market_value,
            club=club_name,
            league=format_league(p.league),
            weekly_wage=0.0,
        ))

    return MarketResponse(players=players, page=page, pages=pages, total=total)


@router.get("/auctions")
async def get_active_auctions(club_id: int = Depends(get_current_club_id)):
    auctions = []
    for listing_id, auction in state.AUCTION_LISTINGS.items():
        astat = auction.get("status")
        if astat in ["active", "sold"]:
            bids = auction.get("bids", [])
            is_seller = auction.get("seller_club_id") == club_id
            
            user_bid = next((b for b in bids if b["club_id"] == club_id), None)
            highest_bid = max(bids, key=lambda x: x["amount"]) if bids else None
            is_leading = highest_bid and highest_bid["club_id"] == club_id

            # Only show if seller OR has a bid
            if is_seller or user_bid:
                status = "unknown"
                if astat == "sold" and is_seller:
                    status = "sold"
                elif is_seller:
                    status = "selling"
                elif is_leading:
                    status = "leading"
                else:
                    status = "outbid"

                auctions.append({
                    "listing_id": listing_id,
                    "player_id": auction.get("player_id"),
                    "player_name": auction.get("player_data", {}).get("player_name", "Unknown"),
                    "current_price": auction.get("current_price", 0),
                    "status": status,
                    "auction_end_time": auction.get("auction_end_time").isoformat() if auction.get("auction_end_time") else None,
                })
    return auctions


@router.post("/bid")
async def place_bid(request: BidRequest, club_id: int = Depends(get_current_club_id), db: Session = Depends(get_db)):
    listing_id = request.listing_id
    bid_amount = request.bid_amount
    if listing_id not in state.AUCTION_LISTINGS:
        raise HTTPException(status_code=404, detail="Listing not found")
    auction_data = state.AUCTION_LISTINGS[listing_id]
    if bid_amount < auction_data.get("current_price", 0):
        raise HTTPException(status_code=400, detail=f"Bid must be at least {auction_data.get('current_price', 0):,.0f} €")

    pwd = float(auction_data.get("player_data", {}).get("weekly_wage", 0))
    is_compliant, message = check_ffp_compliance(db, club_id, pwd, bid_amount)
    if not is_compliant:
        raise HTTPException(status_code=400, detail=message)

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
        "bid_count": len(auction_data["bids"]), "timestamp": datetime.utcnow().isoformat(),
    })
    return {"message": "Bid placed", "bid_amount": bid_amount, "listing_id": listing_id}
