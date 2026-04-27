from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import timedelta

from utils.schemas import LoginRequest, TokenResponse, ClubInfo
from database.database import get_db
from database.models import Club
from utils.auth import verify_password, create_access_token, get_current_club_id
from utils.config import settings

router = APIRouter(prefix="/api")

@router.post("/login", response_model=TokenResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.query(Club).filter(Club.username == request.username).first()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    access_token = create_access_token(data={"sub": request.username})
    return TokenResponse(access_token=access_token)

@router.get("/me", response_model=ClubInfo)
async def get_me(club_id: int = Depends(get_current_club_id), db: Session = Depends(get_db)):
    club = db.query(Club).filter(Club.id == club_id).first()
    if not club: raise HTTPException(status_code=404, detail="Club not found")
    return ClubInfo(
        id=club.id, 
        username=club.username, 
        name=club.name, 
        budget_remaining=club.budget_remaining, 
        current_wage_budget=club.wage_budget, 
        wage_spent=club.wage_spent
    )
