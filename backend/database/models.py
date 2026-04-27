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
    is_transfer_banned = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Season stats (reset mỗi năm)
    season_position = Column(Integer, default=10)       # Hạng trong giải
    season_wins = Column(Integer, default=0)
    season_draws = Column(Integer, default=0)
    season_losses = Column(Integer, default=0)
    season_goals_scored = Column(Integer, default=0)
    season_goals_conceded = Column(Integer, default=0)
    last_season_revenue = Column(Float, default=0.0)    # Doanh thu mùa trước
    
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

class SystemStateEnum(str, enum.Enum):
    TRANSFER_OPEN = "TRANSFER_OPEN"
    TRANSFER_CLOSED = "TRANSFER_CLOSED"
    OFF_SEASON = "OFF_SEASON"
    SEASON_UPDATE = "SEASON_UPDATE"

class SystemState(Base):
    __tablename__ = "system_states"
    
    id = Column(Integer, primary_key=True, index=True)
    current_state = Column(Enum(SystemStateEnum), default=SystemStateEnum.TRANSFER_CLOSED)
    current_date = Column(DateTime, default=datetime.utcnow)
    season_year = Column(Integer, default=2025)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class ContractStatusEnum(str, enum.Enum):
    ACTIVE = "ACTIVE"
    TERMINATED = "TERMINATED"
    TRANSFERRED = "TRANSFERRED"

class Contract(Base):
    __tablename__ = "contracts"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("player_info.id"), index=True)
    club_id = Column(Integer, ForeignKey("clubs.id"), index=True)
    start_date = Column(DateTime, default=datetime.utcnow)
    end_date = Column(DateTime)
    remaining_years = Column(Integer, default=0)
    base_salary = Column(Float, default=0.0)
    release_clause = Column(Float, nullable=True)
    performance_bonus = Column(Float, default=0.0)
    loyalty_bonus = Column(Float, default=0.0)
    early_termination_fee = Column(Float, default=0.0)
    status = Column(Enum(ContractStatusEnum), default=ContractStatusEnum.ACTIVE)
    
    player = relationship("PlayerInfo", backref="contracts")
    club = relationship("Club", backref="contracts")

class NegotiationStatusEnum(str, enum.Enum):
    INQUIRY = "INQUIRY"
    NEGOTIATING = "NEGOTIATING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"

class Negotiation(Base):
    __tablename__ = "negotiations"
    
    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("player_info.id"), index=True)
    buying_club_id = Column(Integer, ForeignKey("clubs.id"), index=True)
    selling_club_id = Column(Integer, ForeignKey("clubs.id"), index=True)
    
    current_offer = Column(Float, default=0.0)
    selling_club_demand = Column(Float, default=0.0)
    round_number = Column(Integer, default=1)
    
    status = Column(Enum(NegotiationStatusEnum), default=NegotiationStatusEnum.INQUIRY)
    is_public_release_clause = Column(Boolean, default=True) 
    questions_asked_this_round = Column(Integer, default=0)
    expires_at_game_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    player = relationship("PlayerInfo", backref="negotiations")
    buying_club = relationship("Club", foreign_keys=[buying_club_id], backref="buy_negotiations")
    selling_club = relationship("Club", foreign_keys=[selling_club_id], backref="sell_negotiations")

class SimulationConfig(Base):
    __tablename__ = "simulation_configs"
    
    id = Column(Integer, primary_key=True, index=True)
    club_id = Column(Integer, ForeignKey("clubs.id"), unique=True, index=True)
    is_simulated = Column(Boolean, default=True)
    strategy = Column(String, default="BALANCED")  # VD: AGGRESSIVE_BUYER, SELLING_CLUB, v.v.
    willingness_to_sell = Column(Float, default=0.5) 
    negotiation_flexibility = Column(Float, default=0.5) 
    
    club = relationship("Club", backref="simulation_config")

class ClubSeasonRecord(Base):
    """
    Lưu lịch sử kết quả tài chính và thi đấu theo từng mùa giải.
    Snapshot này được chụp lại trước khi reset sang mùa mới.
    """
    __tablename__ = "club_season_records"
    
    id = Column(Integer, primary_key=True, index=True)
    club_id = Column(Integer, ForeignKey("clubs.id"), index=True)
    season_year = Column(Integer, index=True)            # VD: 2024 = mùa 2024/25
    
    # Thành tích thi đấu
    final_position = Column(Integer, default=0)
    wins = Column(Integer, default=0)
    draws = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    goals_scored = Column(Integer, default=0)
    goals_conceded = Column(Integer, default=0)
    
    # Tài chính
    ticket_revenue = Column(Float, default=0.0)          # Doanh thu vé trận đấu
    broadcasting_revenue = Column(Float, default=0.0)    # Bản quyền giải đấu
    merchandise_revenue = Column(Float, default=0.0)     # Áo đấu, phụ kiện
    prize_money = Column(Float, default=0.0)             # Tiền thưởng xếp hạng
    total_revenue = Column(Float, default=0.0)
    
    budget_start = Column(Float, default=0.0)            # Budget lúc đầu mùa
    budget_end = Column(Float, default=0.0)              # Budget cuối mùa
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    club = relationship("Club", backref="season_records")
