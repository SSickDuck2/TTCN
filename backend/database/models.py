from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Enum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()

class Club(Base):
    __tablename__ = "clubs"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    name = Column(String, index=True)
    password_hash = Column(String)
    budget_remaining = Column(Float, default=100000000.0)  # 100M euros
    wage_budget = Column(Float, default=300000.0)  # Weekly wage budget
    wage_spent = Column(Float, default=0.0)  # Currently spent on wages
    created_at = Column(DateTime, default=datetime.utcnow)
    
    players = relationship("ClubPlayer", back_populates="club")
    bids = relationship("Bid", back_populates="club")
    
    class Config:
        from_attributes = True

class Player(Base):
    __tablename__ = "players"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(String, unique=True, index=True)  # From FBRef/Transfermarkt
    name = Column(String, index=True)
    position = Column(String)  # FWD, MID, DEF, GK
    market_value = Column(Float)
    club_name = Column(String)
    league = Column(String)
    weekly_wage = Column(Float, default=0.0)
    
    club_players = relationship("ClubPlayer", back_populates="player")
    market_listings = relationship("MarketListing", back_populates="player")
    bids = relationship("Bid", back_populates="player")
    
    class Config:
        from_attributes = True

class ClubPlayer(Base):
    __tablename__ = "club_players"
    
    id = Column(Integer, primary_key=True, index=True)
    club_id = Column(Integer, ForeignKey("clubs.id"), index=True)
    player_id = Column(Integer, ForeignKey("players.id"), index=True)
    bought_price = Column(Float)
    bought_at = Column(DateTime, default=datetime.utcnow)
    
    club = relationship("Club", back_populates="players")
    player = relationship("Player", back_populates="club_players")
    
    class Config:
        from_attributes = True

class AuctionStatus(str, enum.Enum):
    ACTIVE = "active"
    CLOSED = "closed"
    SOLD = "sold"
    CANCELLED = "cancelled"

class MarketListing(Base):
    __tablename__ = "market_listings"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), index=True)
    seller_club_id = Column(Integer, ForeignKey("clubs.id"))
    listing_type = Column(String)  # "quick_sell" or "auction"
    starting_price = Column(Float)
    current_price = Column(Float)
    status = Column(String, default="active")  # active, sold, cancelled
    created_at = Column(DateTime, default=datetime.utcnow)
    auction_end_time = Column(DateTime, nullable=True)  # NULL for quick sell
    
    player = relationship("Player", back_populates="market_listings")
    bids = relationship("Bid", back_populates="listing")
    
    class Config:
        from_attributes = True

class Bid(Base):
    __tablename__ = "bids"
    
    id = Column(Integer, primary_key=True, index=True)
    listing_id = Column(Integer, ForeignKey("market_listings.id"), index=True)
    player_id = Column(Integer, ForeignKey("players.id"), index=True)
    club_id = Column(Integer, ForeignKey("clubs.id"), index=True)
    bid_amount = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_winning = Column(Boolean, default=False)
    
    listing = relationship("MarketListing", back_populates="bids")
    player = relationship("Player", back_populates="bids")
    club = relationship("Club", back_populates="bids")
    
    class Config:
        from_attributes = True

class BudgetLock(Base):
    __tablename__ = "budget_locks"
    
    id = Column(Integer, primary_key=True, index=True)
    club_id = Column(Integer, ForeignKey("clubs.id"), index=True)
    bid_id = Column(Integer, ForeignKey("bids.id"), index=True)
    locked_amount = Column(Float)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    class Config:
        from_attributes = True

class PlayerInfo(Base):
    __tablename__ = "player_info"

    id = Column(Integer, primary_key=True, index=True)
    player_name = Column(String, index=True)
    games = Column(Integer)
    time = Column(Integer)
    goals = Column(Integer)
    xG = Column(Float)
    assists = Column(Integer)
    xA = Column(Float)
    shots = Column(Integer)
    key_passes = Column(Integer)
    yellow_cards = Column(Integer)
    red_cards = Column(Integer)
    position = Column(String)
    team_title = Column(String, index=True)
    npg = Column(Integer)
    npxG = Column(Float)
    xGChain = Column(Float)
    xGBuildup = Column(Float)
    league = Column(String, index=True)
    market_value_in_eur = Column(Float)
    foot = Column(String)
    height_in_cm = Column(Float)
    age = Column(Float)
    tm_club = Column(String)

    class Config:
        from_attributes = True
