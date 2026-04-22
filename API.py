from fastapi import FastAPI, HTTPException, Depends, Query, status, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional, Dict, Set
import pandas as pd
import os
from datetime import datetime, timedelta
import unicodedata
from jose import JWTError, jwt
from passlib.context import CryptContext
import uvicorn
from sqlalchemy.orm import Session
from apscheduler.schedulers.background import BackgroundScheduler
import asyncio
import logging
import sys

# Add backend to path so moved files can be found
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from database.database import get_db, init_db
from database.models import Club, Player as DBPlayer, ClubPlayer, MarketListing, Bid, BudgetLock, PlayerInfo

# ============================================================================
# Logging
# ============================================================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# Configuration
# ============================================================================

SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
MAX_WAGE_BUDGET = 400000.0  # Weekly wage budget limit (FFP)
MAX_TOTAL_BUDGET = 200000000.0  # Maximum total budget (FFP)

LEAGUE_OPTIONS = {
    "Premier League": "ENG-Premier League",
    "La Liga": "ES-La Liga",
    "Serie A": "IT-Serie A",
    "Bundesliga": "DE-Bundesliga",
    "Ligue 1": "FR-Ligue 1",
}

PAGE_SIZE = 30


def normalize_text(value: Optional[str]) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def get_display_league(league_code: Optional[str]) -> str:
    if not league_code:
        return ""
    for display_name, code in LEAGUE_OPTIONS.items():
        if league_code.lower().startswith(code.lower()) or league_code.lower() == code.lower():
            return display_name
    return league_code or ""

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

app = FastAPI(title="TTCN API", description="Transfermarkt Club Network API", version="2.0.0")

# Background scheduler for auction resolution
scheduler = BackgroundScheduler()
scheduler.start()
async_event_loop = None

# ============================================================================
# WebSocket Connection Manager
# ============================================================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, Set[WebSocket]] = {}  # player_id -> set of WebSockets
    
    async def connect(self, websocket: WebSocket, player_id: int):
        await websocket.accept()
        if player_id not in self.active_connections:
            self.active_connections[player_id] = set()
        self.active_connections[player_id].add(websocket)
        logger.info(f"WebSocket connected for player {player_id}")
    
    async def disconnect(self, player_id: int, websocket: WebSocket):
        if player_id in self.active_connections:
            self.active_connections[player_id].discard(websocket)
            if not self.active_connections[player_id]:
                del self.active_connections[player_id]
        logger.info(f"WebSocket disconnected for player {player_id}")
    
    async def broadcast(self, player_id: int, message: dict):
        if player_id in self.active_connections:
            disconnected = set()
            for websocket in self.active_connections[player_id]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Error sending message: {e}")
                    disconnected.add(websocket)
            
            # Clean up disconnected connections
            for ws in disconnected:
                await self.disconnect(player_id, ws)

manager = ConnectionManager()
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# ============================================================================
# Data Models (Pydantic)
# ============================================================================

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ClubInfo(BaseModel):
    name: str
    budget_remaining: float
    current_wage_budget: float
    wage_spent: float

class Player(BaseModel):
    player_id: int
    listing_id: int = 0
    name: str
    position: str
    market_value: float
    club: str
    league: str
    weekly_wage: float

class MarketResponse(BaseModel):
    players: List[Player]
    page: int
    pages: int
    total: int

class SellRequest(BaseModel):
    player_id: int
    sell_type: str  # "quick_sell" or "auction"
    duration_minutes: int = 5  # For auction duration

class BidRequest(BaseModel):
    listing_id: int
    bid_amount: float

class AuctionUpdate(BaseModel):
    player_id: int
    player_name: str
    current_price: float
    highest_bidder_club: Optional[str] = None
    remaining_seconds: Optional[int] = None

# ============================================================================
# Mock Data for Development
# ============================================================================

MOCK_USERS = {
    "arsenal": {"password": "password123", "club_id": 1},
    "chelsea": {"password": "password123", "club_id": 2},
    "man_city": {"password": "password123", "club_id": 3},
}

MOCK_CLUBS = {
    1: {"name": "Arsenal", "budget_remaining": 50000000, "wage_budget": 300000, "wage_spent": 0},
    2: {"name": "Chelsea", "budget_remaining": 75000000, "wage_budget": 350000, "wage_spent": 0},
    3: {"name": "Manchester City", "budget_remaining": 100000000, "wage_budget": 400000, "wage_spent": 0},
}

# Load player data from CSV if available
DATA_FOLDER = r"c:\Users\admin\PycharmProjects\TTCN"
CSV_PATH = os.path.join(DATA_FOLDER, "merged_fbref_transfermarkt.csv")

try:
    if os.path.exists(CSV_PATH):
        df = pd.read_csv(CSV_PATH)
        ALL_PLAYERS = df.to_dict('records')
    else:
        ALL_PLAYERS = []
except Exception as e:
    logger.error(f"Error loading CSV: {e}")
    ALL_PLAYERS = []

# Mock market and owned players
MARKET_PLAYERS = [p for p in ALL_PLAYERS[:50]] if ALL_PLAYERS else []
OWNED_PLAYERS = {
    1: [p for p in ALL_PLAYERS[50:70]] if ALL_PLAYERS else [],
    2: [p for p in ALL_PLAYERS[70:90]] if ALL_PLAYERS else [],
    3: [p for p in ALL_PLAYERS[90:110]] if ALL_PLAYERS else [],
}

# Track auction listings and bids in memory (for development)
AUCTION_LISTINGS: Dict[int, dict] = {}  # listing_id -> auction data
CLUB_BUDGET_LOCKS: Dict[int, float] = {}  # club_id -> locked amount

# ============================================================================
# FFP & Budget Logic
# ============================================================================

def check_ffp_compliance(db: Session, club_id: int, new_wage: float, bid_amount: float) -> tuple[bool, str]:
    """
    Check Financial Fair Play compliance.
    
    Returns: (is_compliant, message)
    """
    club = db.query(Club).filter(Club.id == club_id).first()
    if not club:
        return False, "Club not found"
        
    # Check 1: Budget remaining
    budget_remaining = club.budget_remaining
    if budget_remaining < bid_amount:
        return False, f"Insufficient budget. Required: {bid_amount:,.0f}, Available: {budget_remaining:,.0f}"
    
    # Check 2: Wage budget compliance
    current_wages = club.wage_spent
    new_total_wages = current_wages + new_wage
    wage_budget = club.wage_budget
    
    if new_total_wages > wage_budget:
        excess = new_total_wages - wage_budget
        return False, f"Wage budget exceeded by {excess:,.0f}. Max weekly wage: {wage_budget:,.0f}"
    
    # Check 3: Budget locks (reserved for other bids)
    locked_amount = CLUB_BUDGET_LOCKS.get(club_id, 0)
    available_budget = budget_remaining - locked_amount
    
    if available_budget < bid_amount:
        return False, f"Insufficient available budget (locked: {locked_amount:,.0f}). Available: {available_budget:,.0f}"
    
    return True, "FFP compliant"

def lock_budget(club_id: int, amount: float, bid_id: int):
    """Lock budget for a specific bid."""
    if club_id not in CLUB_BUDGET_LOCKS:
        CLUB_BUDGET_LOCKS[club_id] = 0
    CLUB_BUDGET_LOCKS[club_id] += amount
    logger.info(f"Locked {amount:,.0f} for club {club_id} (bid {bid_id})")

def unlock_budget(club_id: int, amount: float):
    """Unlock budget (bid lost or cancelled)."""
    if club_id in CLUB_BUDGET_LOCKS:
        CLUB_BUDGET_LOCKS[club_id] = max(0, CLUB_BUDGET_LOCKS[club_id] - amount)
    logger.info(f"Unlocked {amount:,.0f} for club {club_id}")

# ============================================================================
# Authentication Functions
# ============================================================================

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid token")
        return username
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_club_id(username: str = Depends(verify_token), db: Session = Depends(get_db)):
    user = db.query(Club).filter(Club.username == username).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user.id

# ============================================================================
# Scheduler Tasks
# ============================================================================

async def resolve_auction(listing_id: int):
    """Resolve auction and transfer player to winning bidder."""
    logger.info(f"Resolving auction for listing {listing_id}")
    
    if listing_id not in AUCTION_LISTINGS:
        logger.warning(f"Listing {listing_id} not found")
        return
    
    auction_data = AUCTION_LISTINGS[listing_id]
    bids = auction_data.get("bids", [])
    
    if not bids:
        logger.info(f"No bids for listing {listing_id}, cancelling auction")
        auction_data["status"] = "cancelled"
        return
    
    # Get winning bid (highest amount)
    winning_bid = max(bids, key=lambda b: b["amount"])
    winning_club_id = winning_bid["club_id"]
    winning_amount = winning_bid["amount"]
    player_id = auction_data["player_id"]
    player = auction_data["player_data"]
    
    # Update DB
    from database import SessionLocal
    with SessionLocal() as db:
        winning_club = db.query(Club).filter(Club.id == winning_club_id).first()
        if winning_club:
            winning_club.budget_remaining -= winning_amount
            winning_club.wage_spent += float(player.get("weekly_wage", 0))
            
            player_info = db.query(PlayerInfo).filter(PlayerInfo.id == player_id).first()
            if player_info:
                player_info.tm_club = winning_club.name
        
        db.commit()
    
    # Unlock budget for other clubs
    for bid in bids:
        if bid["club_id"] != winning_club_id:
            unlock_budget(bid["club_id"], bid["amount"])
    
    auction_data["status"] = "sold"
    auction_data["winning_bid"] = winning_bid
    
    # Broadcast final update
    await manager.broadcast(player_id, {
        "type": "auction_closed",
        "listing_id": listing_id,
        "player_id": player_id,
        "winner_club_id": winning_club_id,
        "final_price": winning_amount,
        "player_name": player.get("player_name", ""),
    })
    
    logger.info(f"Auction resolved: Club {winning_club_id} won player for {winning_amount:,.0f}")

def run_auction_resolution(listing_id: int):
    """Schedule the async auction resolver on the active event loop."""
    global async_event_loop
    if async_event_loop is None:
        logger.error("No async event loop available for auction resolution. Running directly.")
        asyncio.run(resolve_auction(listing_id))
        return
    asyncio.run_coroutine_threadsafe(resolve_auction(listing_id), async_event_loop)


def schedule_auction_resolution(listing_id: int, end_time: datetime):
    """Schedule auction to be resolved at end_time."""
    delay_seconds = (end_time - datetime.utcnow()).total_seconds()
    if delay_seconds > 0:
        scheduler.add_job(
            run_auction_resolution,
            'date',
            run_date=end_time,
            args=[listing_id],
            id=f"auction_{listing_id}",
            replace_existing=True,
        )
        logger.info(f"Scheduled auction {listing_id} to resolve in {delay_seconds:.0f} seconds")

# ============================================================================
# WebSocket Endpoint
# ============================================================================

@app.websocket("/ws/auction/{player_id}")
async def websocket_auction(websocket: WebSocket, player_id: int):
    """WebSocket endpoint for real-time auction updates."""
    await manager.connect(websocket, player_id)
    try:
        while True:
            # Keep connection alive and receive any client messages
            data = await websocket.receive_json()
            logger.debug(f"Received from player {player_id}: {data}")
    except WebSocketDisconnect:
        await manager.disconnect(player_id, websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await manager.disconnect(player_id, websocket)

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/trade/market", response_class=HTMLResponse)
async def trade_market(request: Request):
    return templates.TemplateResponse("market.html", {"request": request})

@app.get("/trade/squad", response_class=HTMLResponse)
async def trade_squad(request: Request):
    return templates.TemplateResponse("squad.html", {"request": request})

@app.get("/trade/auction", response_class=HTMLResponse)
async def trade_auction(request: Request):
    return templates.TemplateResponse("auction.html", {"request": request})

@app.get("/trade/player/{player_id}", response_class=HTMLResponse)
async def trade_player_detail(request: Request, player_id: int):
    return templates.TemplateResponse("player.html", {"request": request, "player_id": player_id})

@app.get("/api/player/{player_id}")
async def get_player_api(player_id: int, db: Session = Depends(get_db)):
    player = db.query(PlayerInfo).filter(PlayerInfo.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
        
    auction_info = None
    if player_id in AUCTION_LISTINGS and AUCTION_LISTINGS[player_id]["status"] == "active":
        auction = AUCTION_LISTINGS[player_id]
        highest_bidder = "None"
        bids = auction.get("bids", [])
        if bids:
            highest_bid = max(bids, key=lambda b: b["amount"])
            club = db.query(Club).filter(Club.id == highest_bid["club_id"]).first()
            if club:
                highest_bidder = club.name
        
        auction_info = {
            "listing_id": auction["listing_id"],
            "current_price": auction["current_price"],
            "highest_bidder": highest_bidder,
            "end_time": auction["auction_end_time"].isoformat() if auction["auction_end_time"] else None
        }

    return {
        "player": {
            "id": player.id,
            "name": player.player_name,
            "club": player.tm_club,
            "position": player.position,
            "age": player.age,
            "nation": player.nation,
            "market_value": player.market_value_eur,
            "league": player.league,
            "stats": {
                "matches": player.playing_time_mp,
                "starts": player.playing_time_starts,
                "minutes": player.playing_time_min,
                "goals": player.performance_gls,
                "assists": player.performance_ast,
                "yellow_cards": player.performance_crdy,
                "red_cards": player.performance_crdr
            }
        },
        "auction": auction_info
    }

@app.post("/api/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Authenticate user and return JWT token."""
    user = db.query(Club).filter(Club.username == request.username).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": request.username}, expires_delta=access_token_expires
    )
    return TokenResponse(access_token=access_token)

@app.get("/api/me", response_model=ClubInfo)
async def get_me(club_id: int = Depends(get_current_club_id), db: Session = Depends(get_db)):
    """Get current club information."""
    club = db.query(Club).filter(Club.id == club_id).first()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    return ClubInfo(
        name=club.name,
        budget_remaining=club.budget_remaining,
        current_wage_budget=club.wage_budget,
        wage_spent=club.wage_spent
    )

@app.get("/api/market/players", response_model=MarketResponse)
async def get_market_players(
    position: Optional[str] = Query(None, description="Filter by position (e.g., FW, MF, DF, GK)"),
    min_price: Optional[float] = Query(None, description="Minimum market value in millions"),
    max_price: Optional[float] = Query(None, description="Maximum market value in millions"),
    league: Optional[str] = Query(None, description="Filter by league"),
    name: Optional[str] = Query(None, description="Search player name"),
    page: int = Query(1, ge=1, description="Page number"),
    db: Session = Depends(get_db)
):
    """Get list of players on the market with optional filters."""
    query = db.query(PlayerInfo).filter(
        PlayerInfo.tm_club.isnot(None),
        PlayerInfo.tm_player_id.isnot(None)
    )

    if position:
        query = query.filter(PlayerInfo.position.ilike(f"%{position}%"))

    if min_price is not None:
        min_value = min_price * 1000000
        query = query.filter(PlayerInfo.market_value_eur >= min_value)

    if max_price is not None:
        max_value = max_price * 1000000
        query = query.filter(PlayerInfo.market_value_eur <= max_value)

    if league:
        league_value = LEAGUE_OPTIONS.get(league, league)
        query = query.filter(PlayerInfo.league.ilike(f"%{league_value}%"))

    player_infos = query.all()

    if name:
        normalized_search = normalize_text(name)
        player_infos = [p for p in player_infos if normalized_search in normalize_text(p.player_name)]

    total = len(player_infos)
    pages = max((total + PAGE_SIZE - 1) // PAGE_SIZE, 1)
    page = min(page, pages)
    start = (page - 1) * PAGE_SIZE
    end = start + PAGE_SIZE
    paged_players = player_infos[start:end]

    players = []
    for p in paged_players:
        market_value = p.market_value_eur if p.market_value_eur is not None else 0.0
        
        if p.id not in AUCTION_LISTINGS and market_value > 0:
            auction_end_time = datetime.utcnow() + timedelta(hours=2)
            AUCTION_LISTINGS[p.id] = {
                "listing_id": p.id,
                "player_id": p.id,
                "player_data": {
                    "player_id": p.id,
                    "player_name": p.player_name,
                    "weekly_wage": 0.0,
                    "market_value_in_eur": market_value,
                },
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
            name=p.player_name,
            position=p.position,
            market_value=market_value,
            club=p.tm_club,
            league=get_display_league(p.league),
            weekly_wage=0.0
        ))

    return MarketResponse(players=players, page=page, pages=pages, total=total)

@app.get("/api/market/auctions")
async def get_active_auctions():
    auctions = []
    for listing_id, auction in AUCTION_LISTINGS.items():
        if auction.get("status") == "active" and len(auction.get("bids", [])) > 0:
            auctions.append({
                "listing_id": listing_id,
                "player_id": auction.get("player_id"),
                "player_name": auction.get("player_data", {}).get("player_name", "Unknown"),
                "current_price": auction.get("current_price", 0),
                "status": auction.get("status", "active"),
                "auction_end_time": auction.get("auction_end_time").isoformat() if auction.get("auction_end_time") else None,
            })
    return auctions

@app.get("/api/market/auction/{listing_id}")
async def get_auction(listing_id: int, db: Session = Depends(get_db)):
    auction = AUCTION_LISTINGS.get(listing_id)
    if not auction:
        p = db.query(PlayerInfo).filter(PlayerInfo.id == listing_id).first()
        if p and p.market_value_eur:
            auction_end_time = datetime.utcnow() + timedelta(hours=2)
            auction = {
                "listing_id": listing_id,
                "player_id": p.id,
                "player_data": {
                    "player_id": p.id,
                    "player_name": p.player_name,
                    "weekly_wage": 0.0,
                    "market_value_in_eur": p.market_value_eur,
                },
                "seller_club_id": None,
                "starting_price": p.market_value_eur,
                "current_price": p.market_value_eur,
                "bids": [],
                "status": "active",
                "created_at": datetime.utcnow(),
                "auction_end_time": auction_end_time,
            }
            AUCTION_LISTINGS[listing_id] = auction
            schedule_auction_resolution(listing_id, auction_end_time)
        else:
            raise HTTPException(status_code=404, detail="Auction listing not found")
            
    bids = auction.get("bids", [])
    highest_bidder = "None"
    if bids:
        highest_bid = max(bids, key=lambda b: b["amount"])
        club = db.query(Club).filter(Club.id == highest_bid["club_id"]).first()
        highest_bidder = club.name if club else "Unknown"

    return {
        "listing_id": listing_id,
        "player_id": auction.get("player_id"),
        "player_name": auction.get("player_data", {}).get("player_name", "Unknown"),
        "current_price": auction.get("current_price", 0),
        "status": auction.get("status", "active"),
        "auction_end_time": auction.get("auction_end_time").isoformat() if auction.get("auction_end_time") else None,
        "highest_bidder": highest_bidder
    }

@app.post("/api/market/bid")
async def place_bid(request: BidRequest, club_id: int = Depends(get_current_club_id), db: Session = Depends(get_db)):
    """
    Place a bid on a market listing.
    
    Implements FFP checks:
    1. Budget availability
    2. Wage budget compliance
    3. Budget locking to prevent double-spending
    """
    listing_id = request.listing_id
    bid_amount = request.bid_amount
    
    if listing_id not in AUCTION_LISTINGS:
        raise HTTPException(status_code=404, detail="Listing not found")
    
    auction_data = AUCTION_LISTINGS[listing_id]
    
    if bid_amount < auction_data.get("current_price", 0):
        raise HTTPException(status_code=400, detail=f"Bid amount must be at least the current price: {auction_data.get('current_price', 0):,.0f} €")
        
    player_data = auction_data.get("player_data", {})
    player_weekly_wage = float(player_data.get("weekly_wage", 0))
    
    # Check FFP compliance
    is_compliant, message = check_ffp_compliance(db, club_id, player_weekly_wage, bid_amount)
    if not is_compliant:
        raise HTTPException(status_code=400, detail=message)
    
    # Create bid record
    bid_record = {
        "club_id": club_id,
        "amount": bid_amount,
        "timestamp": datetime.utcnow(),
    }
    
    # Check if club already has a bid (replace old bid lock)
    existing_bids = [b for b in auction_data.get("bids", []) if b["club_id"] == club_id]
    if existing_bids:
        old_bid = existing_bids[0]
        unlock_budget(club_id, old_bid["amount"])
        auction_data["bids"].remove(old_bid)
    
    # Lock budget for this bid
    lock_budget(club_id, bid_amount, listing_id)
    auction_data["bids"].append(bid_record)
    
    # Update auction with new price
    auction_data["current_price"] = bid_amount
    
    club = db.query(Club).filter(Club.id == club_id).first()
    club_name = club.name if club else f"Club {club_id}"
    player_name = player_data.get("player_name", "Unknown")
    player_id = player_data.get("player_id", 0)
    
    # Broadcast bid update via WebSocket
    await manager.broadcast(player_id, {
        "type": "new_bid",
        "listing_id": listing_id,
        "player_id": player_id,
        "player_name": player_name,
        "current_price": bid_amount,
        "highest_bidder": club_name,
        "bid_count": len(auction_data["bids"]),
        "timestamp": datetime.utcnow().isoformat(),
    })
    
    return {
        "message": f"Bid placed successfully for {player_name}",
        "bid_amount": bid_amount,
        "listing_id": listing_id,
    }

@app.get("/api/squad", response_model=List[Player])
async def get_squad(club_id: int = Depends(get_current_club_id), db: Session = Depends(get_db)):
    """Get list of players owned by the current club."""
    club = db.query(Club).filter(Club.id == club_id).first()
    if not club:
        return []
    
    players = db.query(PlayerInfo).filter(PlayerInfo.tm_club == club.name).all()
    result = []
    for p in players:
        result.append(Player(
            player_id=p.id,
            listing_id=p.id,
            name=str(p.player_name),
            position=str(p.position),
            market_value=float(p.market_value_eur or 0.0),
            club=str(p.tm_club),
            league=get_display_league(str(p.league)),
            weekly_wage=0.0
        ))
    
    return result

@app.post("/api/squad/sell")
async def sell_player(request: SellRequest, club_id: int = Depends(get_current_club_id), db: Session = Depends(get_db)):
    """
    Sell a player via quick sell or auction.
    """
    club = db.query(Club).filter(Club.id == club_id).first()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
        
    db_player = db.query(PlayerInfo).filter(
        PlayerInfo.id == request.player_id, 
        PlayerInfo.tm_club == club.name
    ).first()
    
    if not db_player:
        raise HTTPException(status_code=404, detail="Player not owned by this club")
    
    if request.sell_type not in ["quick_sell", "auction"]:
        raise HTTPException(status_code=400, detail="Invalid sell_type")
        
    db_player.tm_club = "Free Agent"
    
    player_data = {
        "player_id": db_player.id,
        "player_name": db_player.player_name,
        "weekly_wage": 0.0,
        "market_value_in_eur": db_player.market_value_eur or 0.0
    }
    
    if request.sell_type == "quick_sell":
        market_value = float(db_player.market_value_eur or 0.0)
        sell_price = market_value * 0.8
        
        club.budget_remaining += sell_price
        club.wage_spent = max(0, club.wage_spent - 0.0)
        db.commit()
        
        return {
            "message": f"Player {db_player.player_name} quick-sold for {sell_price:,.0f}",
            "sell_price": sell_price,
            "sell_type": "quick_sell",
        }
    
    elif request.sell_type == "auction":
        listing_id = db_player.id
        start_price = float(db_player.market_value_eur or 0.0)
        auction_end_time = datetime.utcnow() + timedelta(minutes=request.duration_minutes)
        
        AUCTION_LISTINGS[listing_id] = {
            "listing_id": listing_id,
            "player_id": db_player.id,
            "player_data": player_data,
            "seller_club_id": club_id,
            "starting_price": start_price,
            "current_price": start_price,
            "bids": [],
            "status": "active",
            "created_at": datetime.utcnow(),
            "auction_end_time": auction_end_time,
        }
        
        schedule_auction_resolution(listing_id, auction_end_time)
        db.commit()
        
        return {
            "message": f"Player {db_player.player_name} listed for auction",
            "listing_id": listing_id,
            "starting_price": start_price,
            "auction_duration_minutes": request.duration_minutes,
            "auction_end_time": auction_end_time.isoformat(),
        }

@app.post("/api/admin/start-session")
async def start_market_session():
    """Admin endpoint to start transfer market session."""
    # In a real system, this would update market status
    return {"message": "Transfer market session started"}

@app.post("/api/admin/process-wages")
async def process_wages(db: Session = Depends(get_db)):
    """Admin endpoint to process weekly wages for all clubs."""
    processed_clubs = []
    
    clubs = db.query(Club).all()
    for club in clubs:
        players = db.query(PlayerInfo).filter(PlayerInfo.tm_club == club.name).all()
        total_wage = 0.0
        
        club.budget_remaining -= total_wage
        club.wage_spent = total_wage
        
        processed_clubs.append({
            "club_id": club.id,
            "club_name": club.name,
            "wage_deduction": total_wage,
            "budget_remaining": club.budget_remaining,
        })
    db.commit()
    
    return {
        "message": "Weekly wages processed for all clubs",
        "timestamp": datetime.utcnow().isoformat(),
        "clubs": processed_clubs,
    }

# ============================================================================
# Startup & Shutdown
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize database and start scheduler."""
    global async_event_loop
    async_event_loop = asyncio.get_running_loop()
    try:
        init_db()
        logger.info("Database initialized")
    except Exception as e:
        logger.warning(f"Database initialization: {e}")
    
    logger.info("TTCN API v2.0 started with WebSocket support and scheduler")

@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown scheduler."""
    scheduler.shutdown()
    logger.info("Scheduler shutdown")

# ============================================================================
# Run Server
# ============================================================================

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)