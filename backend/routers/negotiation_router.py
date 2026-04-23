from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional

from database.database import get_db
from database.models import Negotiation, NegotiationStatusEnum, PlayerInfo
from utils.auth import get_current_club_id
from services.negotiation_engine import negotiation_engine
from services.time_engine import time_engine

router = APIRouter(prefix="/api/negotiations")

class RespondInquiryRequest(BaseModel):
    accept: bool
    initial_demand: float = 0.0

class OfferRequest(BaseModel):
    offer_amount: float

class CounterRequest(BaseModel):
    demand_amount: float

class AskRequest(BaseModel):
    question_id: int


class InquireRequest(BaseModel):
    player_id: int

@router.get("/questions")
def get_questions():
    """Lấy danh sách 20 câu hỏi đặt sẵn cho phiên đàm phán."""
    from services.negotiation_engine import AVAILABLE_QUESTIONS
    return AVAILABLE_QUESTIONS


@router.get("/my")
def get_my_negotiations(club_id: int = Depends(get_current_club_id), db: Session = Depends(get_db)):
    """Lấy tất cả các phiên đàm phán của CLB hiện tại."""
    from database.models import SystemState
    state = db.query(SystemState).first()
    current_game_date = state.current_date if state else None

    negos = db.query(Negotiation).filter(
        (Negotiation.buying_club_id == club_id) | (Negotiation.selling_club_id == club_id),
        Negotiation.status.in_([NegotiationStatusEnum.INQUIRY, NegotiationStatusEnum.NEGOTIATING, NegotiationStatusEnum.ACCEPTED])
    ).order_by(Negotiation.updated_at.desc()).all()

    result = []
    for n in negos:
        player = db.query(PlayerInfo).filter(PlayerInfo.id == n.player_id).first()
        
        expires_in_days = None
        if current_game_date and n.expires_at_game_date:
            delta = (n.expires_at_game_date - current_game_date).days
            expires_in_days = max(0, delta)

        result.append({
            "id": n.id,
            "player_id": n.player_id,
            "player_name": player.player_name if player else f"Player #{n.player_id}",
            "player_position": player.position if player else "N/A",
            "buying_club_id": n.buying_club_id,
            "selling_club_id": n.selling_club_id,
            "status": n.status.value,
            "current_offer": n.current_offer,
            "selling_club_demand": n.selling_club_demand,
            "round_number": n.round_number,
            "questions_asked_this_round": n.questions_asked_this_round,
            "is_public_release_clause": n.is_public_release_clause,
            "expires_at_game_date": n.expires_at_game_date.isoformat() if n.expires_at_game_date else None,
            "expires_in_days": expires_in_days,
        })
    return result


@router.get("/{negotiation_id}")
def get_negotiation_detail(negotiation_id: int, club_id: int = Depends(get_current_club_id), db: Session = Depends(get_db)):
    """Lấy chi tiết một phiên đàm phán."""
    nego = db.query(Negotiation).filter(Negotiation.id == negotiation_id).first()
    if not nego:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    if nego.buying_club_id != club_id and nego.selling_club_id != club_id:
        raise HTTPException(status_code=403, detail="Không có quyền xem phiên đàm phán này")

    player = db.query(PlayerInfo).filter(PlayerInfo.id == nego.player_id).first()
    return {
        "id": nego.id,
        "player_id": nego.player_id,
        "player_name": player.player_name if player else None,
        "status": nego.status.value,
        "current_offer": nego.current_offer,
        "selling_club_demand": nego.selling_club_demand,
        "round_number": nego.round_number,
        "questions_asked_this_round": nego.questions_asked_this_round,
    }


@router.post("/inquire")
def initiate_inquiry_endpoint(
    req: InquireRequest,
    club_id: int = Depends(get_current_club_id), db: Session = Depends(get_db)
):
    """Người chơi chủ động hỏi mua (khởi tạo đàm phán)."""
    if not time_engine.check_transfer_window_open():
        raise HTTPException(status_code=403, detail="Thị trường chuyển nhượng đang đóng cửa.")
    
    nego = negotiation_engine.initiate_inquiry(db, buying_club_id=club_id, player_id=req.player_id)
    if not nego:
        raise HTTPException(status_code=400, detail="Không thể tạo đàm phán cho cầu thủ này.")
    return {"ok": True, "negotiation_id": nego.id}


@router.post("/{negotiation_id}/respond-inquiry")
def respond_inquiry(
    negotiation_id: int, req: RespondInquiryRequest,
    club_id: int = Depends(get_current_club_id), db: Session = Depends(get_db)
):
    """Bên bán trả lời Inquiry."""
    nego = db.query(Negotiation).filter(Negotiation.id == negotiation_id).first()
    if not nego:
        raise HTTPException(status_code=404, detail="Negotiation not found")
    if nego.selling_club_id != club_id:
        raise HTTPException(status_code=403, detail="Chỉ CLB bán mới có quyền phản hồi Inquiry")
    result = negotiation_engine.respond_to_inquiry(db, negotiation_id, req.accept, req.initial_demand)
    return {"ok": result}


@router.post("/{negotiation_id}/offer")
def submit_offer(
    negotiation_id: int, req: OfferRequest,
    club_id: int = Depends(get_current_club_id), db: Session = Depends(get_db)
):
    """Bên mua gửi giá."""
    if not time_engine.check_transfer_window_open():
        raise HTTPException(status_code=403, detail="Thị trường đóng cửa.")
    nego = db.query(Negotiation).filter(Negotiation.id == negotiation_id).first()
    if not nego or nego.buying_club_id != club_id:
        raise HTTPException(status_code=403, detail="Không có quyền submit offer")
    return negotiation_engine.submit_offer(db, negotiation_id, req.offer_amount)


@router.post("/{negotiation_id}/counter")
def counter_offer(
    negotiation_id: int, req: CounterRequest,
    club_id: int = Depends(get_current_club_id), db: Session = Depends(get_db)
):
    """Bên bán phản giá."""
    if not time_engine.check_transfer_window_open():
        raise HTTPException(status_code=403, detail="Thị trường đóng cửa.")
    nego = db.query(Negotiation).filter(Negotiation.id == negotiation_id).first()
    if not nego or nego.selling_club_id != club_id:
        raise HTTPException(status_code=403, detail="Không có quyền phản giá")
    return negotiation_engine.respond_to_offer(db, negotiation_id, req.demand_amount)


@router.post("/{negotiation_id}/cancel")
def cancel_nego(
    negotiation_id: int,
    club_id: int = Depends(get_current_club_id), db: Session = Depends(get_db)
):
    """Hủy đàm phán."""
    result = negotiation_engine.cancel_negotiation(db, negotiation_id, club_id)
    if not result:
        raise HTTPException(status_code=403, detail="Không thể hủy phiên đàm phán này")
    return {"ok": True}


@router.post("/{negotiation_id}/ask")
def ask_question(
    negotiation_id: int, req: AskRequest,
    club_id: int = Depends(get_current_club_id), db: Session = Depends(get_db)
):
    """Đặt câu hỏi trong phiên đàm phán."""
    return negotiation_engine.ask_question(db, negotiation_id, club_id, req.question_id)
