from pydantic import BaseModel
from typing import List, Optional

class LoginRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class ClubInfo(BaseModel):
    id: int
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
    sell_type: str
    duration_minutes: int = 5

class BidRequest(BaseModel):
    listing_id: int
    bid_amount: float
