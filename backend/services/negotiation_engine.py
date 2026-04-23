import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session
from database.models import Negotiation, NegotiationStatusEnum, Contract, ContractStatusEnum, Club, PlayerInfo, SystemState
from services.contract_engine import contract_engine
from utils.services import check_ffp_compliance
from utils import state

logger = logging.getLogger(__name__)

AVAILABLE_QUESTIONS = {
    1: "Cầu thủ này đã dính bao nhiêu chấn thương lớn trong 2 năm qua?",
    2: "Thể lực hiện tại có đảm bảo đá chính 90 phút liên tục trong mùa giải không?",
    3: "Tiền sử chấn thương đầu gối/dây chằng có đáng lo ngại không?",
    4: "Cầu thủ có yêu cầu đặc biệt về tiền thưởng (Bonus) như ghi bàn/kiến tạo không?",
    5: "Mức lương kỳ vọng của cầu thủ nếu chuyển sang CLB của chúng tôi là bao nhiêu?",
    6: "Phía cầu thủ có yêu cầu lồng ghép điều khoản giải phóng hợp đồng (Release Clause) mới không?",
    7: "Gia đình và người đại diện có đòi hỏi thêm lót tay hoặc hỗ trợ đời sống không?",
    8: "Cầu thủ có đòi hỏi được đảm bảo suất đá chính không?",
    9: "Tiềm năng phát triển và khả năng bán lại (Resale Value) của cầu thủ trong 3 năm tới thế nào?",
    10: "Thái độ của cầu thủ nếu bị đưa lên băng ghế dự bị xoay tua ở các trận cúp?",
    11: "Sức hút truyền thông (PR) của cầu thủ này có cao không?",
    12: "Khả năng chuyên môn: Tỷ lệ tịnh tiến bóng/phát động tấn công có hiệu quả không?",
    13: "Sự phù hợp: Cầu thủ có chịu chạy nhiều để pressing tầm cao (Gegenpressing) không?",
    14: "Tính đồng đội: Khả năng hỗ trợ phòng ngự từ xa có tích cực không?",
    15: "Sự đa năng: Có thể thi đấu trái kèo hoặc luân phiên vị trí khác khi đội hình chấn thương không?",
    16: "Danh tiếng cá nhân: Cầu thủ có thói quen bay đêm, trễ giờ tập không?",
    17: "Kỷ luật truyền thông: Có hay phát ngôn gây sốc hoặc chỉ trích nội bộ trên MXH không?",
    18: "Quan hệ phòng thay đồ: Có hòa đồng và tôn trọng HLV hiện tại không?",
    19: "Tính ổn định: Có phải tuýp cầu thủ có phong độ thất thường theo mùa không?",
    20: "Khả năng thích nghi: Cầu thủ thường mất bao lâu để hòa nhập với môi trường CLB mới?"
}

class NegotiationEngine:
    """
    Module xử lý logic Đàm phán trực tiếp giữa 2 CLB.
    Quy trình: INQUIRY -> NEGOTIATING -> ACCEPTED/REJECTED/CANCELLED.
    """

    def initiate_inquiry(self, db: Session, buying_club_id: int, player_id: int) -> Negotiation:
        """Bắt đầu hỏi giá/trao đổi"""
        # Kiểm tra xen có đang đàm phán không
        exist = db.query(Negotiation).filter(
            Negotiation.player_id == player_id,
            Negotiation.buying_club_id == buying_club_id,
            Negotiation.status.in_([NegotiationStatusEnum.INQUIRY, NegotiationStatusEnum.NEGOTIATING])
        ).first()
        if exist: return exist

        contract = db.query(Contract).filter(
            Contract.player_id == player_id,
            Contract.status == ContractStatusEnum.ACTIVE
        ).first()
        seller_id = contract.club_id if contract else None

        state = db.query(SystemState).first()
        expires_date = (state.current_date + timedelta(days=3)) if state and state.current_date else None

        new_nego = Negotiation(
            player_id=player_id,
            buying_club_id=buying_club_id,
            selling_club_id=seller_id,
            status=NegotiationStatusEnum.INQUIRY,
            round_number=1,
            is_public_release_clause=False,
            expires_at_game_date=expires_date
        )
        db.add(new_nego)
        db.commit()
        db.refresh(new_nego)
        return new_nego

    def respond_to_inquiry(self, db: Session, negotiation_id: int, accept: bool, initial_demand: float = 0.0):
        """CLB bán trả lời Inquiry (vòng trao đổi hỏi/đáp có/không)"""
        nego = db.query(Negotiation).filter(Negotiation.id == negotiation_id).first()
        if not nego or nego.status != NegotiationStatusEnum.INQUIRY: return False

        if not accept:
            nego.status = NegotiationStatusEnum.REJECTED
        else:
            nego.status = NegotiationStatusEnum.NEGOTIATING
            nego.is_public_release_clause = True  # Mở khóa hiển thị giải phóng HD
            nego.selling_club_demand = initial_demand
            nego.questions_asked_this_round = 0
            state = db.query(SystemState).first()
            if state and state.current_date:
                nego.expires_at_game_date = state.current_date + timedelta(days=3)
            
        nego.updated_at = datetime.utcnow()
        db.commit()
        return True

    def submit_offer(self, db: Session, negotiation_id: int, offer_amount: float) -> Optional[dict]:
        """Bên mua chốt 1 giá (kéo thanh slide)"""
        nego = db.query(Negotiation).filter(Negotiation.id == negotiation_id).first()
        if not nego or nego.status != NegotiationStatusEnum.NEGOTIATING: return None

        # Check FFP
        is_compliant, msg = check_ffp_compliance(db, nego.buying_club_id, 0, offer_amount)
        if not is_compliant: return {"error": msg}

        nego.current_offer = offer_amount
        nego.updated_at = datetime.utcnow()
        state = db.query(SystemState).first()
        if state and state.current_date:
            nego.expires_at_game_date = state.current_date + timedelta(days=3)
        db.commit()

        return self._check_deal_intersection(db, nego)

    def respond_to_offer(self, db: Session, negotiation_id: int, demand_amount: float):
        """Bên bán phản giá hoặc giữ giá (kéo thanh slide)"""
        nego = db.query(Negotiation).filter(Negotiation.id == negotiation_id).first()
        if not nego or nego.status != NegotiationStatusEnum.NEGOTIATING: return None

        nego.selling_club_demand = demand_amount
        nego.round_number += 1
        nego.questions_asked_this_round = 0  # Reset hỏi đáp sang hiệp mới
        nego.updated_at = datetime.utcnow()
        state = db.query(SystemState).first()
        if state and state.current_date:
            nego.expires_at_game_date = state.current_date + timedelta(days=3)
        db.commit()
        
        return self._check_deal_intersection(db, nego)

    def _check_deal_intersection(self, db: Session, nego: Negotiation):
        """Tự động chốt deal khi hai mức giá giao nhau trong ngưỡng cho phép"""
        # Nếu mua >= bán HOẶC sự chênh lệch (gap) <= 5% giá trị bán
        if nego.current_offer > 0 and nego.selling_club_demand > 0:
            if nego.current_offer >= nego.selling_club_demand * 0.95:
                # BẮT TAY THÀNH CÔNG
                nego.status = NegotiationStatusEnum.ACCEPTED
                self._execute_transfer(db, nego)
                db.commit()
                return {"status": "ACCEPTED", "final_price": nego.current_offer}
        
        # Nếu đã qua 3 hiệp trao đổi mà không khớp
        if nego.round_number > 3:
            nego.status = NegotiationStatusEnum.CANCELLED
            db.commit()
            return {"status": "CANCELLED", "reason": "Quá 3 vòng đàm phán."}

        return {"status": "NEGOTIATING", "current_offer": nego.current_offer, "demand": nego.selling_club_demand}

    def cancel_negotiation(self, db: Session, negotiation_id: int, actor_club_id: int):
        """1 trong 2 bên rút khỏi đàm phán"""
        nego = db.query(Negotiation).filter(Negotiation.id == negotiation_id).first()
        if not nego: return False

        if nego.buying_club_id == actor_club_id or nego.selling_club_id == actor_club_id:
            nego.status = NegotiationStatusEnum.CANCELLED
            db.commit()
            return True
        return False

    def _execute_transfer(self, db: Session, nego: Negotiation):
        """Chuyển cầu thủ và tiền sau khi đàm phán thành công."""
        buyer = db.query(Club).filter(Club.id == nego.buying_club_id).first()
        seller = db.query(Club).filter(Club.id == nego.selling_club_id).first()

        transfer_fee = nego.current_offer

        # Trừ tiền/Cộng tiền
        if buyer: buyer.budget_remaining -= transfer_fee
        if seller: seller.budget_remaining += transfer_fee

        # Info Update
        player_info = db.query(PlayerInfo).filter(PlayerInfo.id == nego.player_id).first()
        if player_info and buyer:
            player_info.tm_club = buyer.name

        # Tạo hợp đồng mới
        contract_engine.create_contract(
            db=db,
            player_id=nego.player_id,
            club_id=nego.buying_club_id,
            base_salary=50000.0, # Sẽ được update ở UI sau
            remaining_years=4
        )

    def get_available_questions(self):
        """Trả về danh sách 20 câu preset cho Frontend hiển thị"""
        return AVAILABLE_QUESTIONS

    def ask_question(self, db: Session, negotiation_id: int, actor_club_id: int, question_id: int):
        """Hỏi 1 trong 20 câu hỏi. Tối đa 4 câu hỏi mỗi Round."""
        nego = db.query(Negotiation).filter(Negotiation.id == negotiation_id).first()
        if not nego or nego.status != NegotiationStatusEnum.NEGOTIATING:
            return {"error": "Đàm phán không ở trạng thái sẵn sàng để hỏi đáp."}

        # Kiểm tra người hỏi có thuộc 1 trong 2 club ko
        if actor_club_id not in [nego.buying_club_id, nego.selling_club_id]:
            return {"error": "Không có quyền tham gia phiên đàm phán này."}

        if getattr(nego, 'questions_asked_this_round', 0) >= 4:
            return {"error": "Bạn đã hết số lượt hỏi trong Hiệp đàm phán này. Hãy chốt giá/phản giá để bước sang hiệp tiếp theo."}

        # Tăng biến đếm
        nego.questions_asked_this_round = getattr(nego, 'questions_asked_this_round', 0) + 1
        nego.updated_at = datetime.utcnow()
        db.commit()

        # Nội suy câu trả lời dựa trên Data của cầu thủ
        player_info = db.query(PlayerInfo).filter(PlayerInfo.id == nego.player_id).first()
        answer = self._generate_dynamic_answer(question_id, player_info)

        return {
            "question_id": question_id,
            "question_text": AVAILABLE_QUESTIONS.get(question_id, "Unknown"),
            "answer": answer,
            "questions_remaining": 4 - nego.questions_asked_this_round
        }

    def _generate_dynamic_answer(self, q_id: int, player: PlayerInfo) -> str:
        """Sinh câu trả lời thông minh mượn thông tin DB hiện hữu"""
        if not player: return "Không lấy được dữ liệu nội bộ."
        age = player.age or 25
        games = player.games or 10
        reds = player.red_cards or 0
        goals = player.goals or 0
        xgbuildup = player.xGBuildup or 0.0

        if q_id == 1:
            if age > 30 and games < 10: return "Tiểu sử chấn thương khá xấu. Cầu thủ thường vắng mặt trong hơn nửa mùa giải."
            if games > 25: return "Hồ sơ y tế hoàn hảo. Cậu ấy không gặp chấn thương lớn nào đáng kể 2 năm qua."
            return "Vài chấn thương cơ bắp lặt vặt nhưng đã hồi phục 100%."
        elif q_id == 8:
            if games > 30: return "Cậu ấy đang là trụ cột ở đây. Sang bên bạn, nếu dự bị cậu ấy sẽ không đồng ý."
            return "Cậu ấy sẵn sàng cạnh tranh vị trí công bằng, không đòi hỏi suất mặc định."
        elif q_id == 16:
            if reds > 1: return "Rất tiếc phải thừa nhận cậu ấy đôi khi mất bình tĩnh trên sân. Đời tư thi thoảng có xích mích."
            return "Cực kỳ chuyên nghiệp, sinh hoạt điều độ."
        elif q_id == 19:
            if goals > 15: return "Phong độ đang đỉnh cao và cực kỳ bùng nổ, không có dấu hiệu chững lại."
            return "Mùa giải vừa qua có phần chệch choạc, nhưng với hlv mới cậu ấy sẽ toả sáng lại."
        # Fake trả lời chung cho các câu chưa code detail logic
        responses = {
            2: "Hoàn toàn đủ thể lực cày ải 40-50 trận đấu mỗi mùa.", 
            7: "Không, người đại diện rất chuyên nghiệp, khoản lót tay ở mức thông thường.",
            14: "Dù là tiền đạo, cậu ấy vẫn tham gia phòng ngự tuyến 1 khá tốt.",
            17: "Rất kín tiếng trên mạng Xã hội, chỉ tập trung vào gia đình và chuyên môn."
        }
        return responses.get(q_id, "Có, đó là điều chắc chắn. Chúng tôi nghĩ bạn chẳng cần phải lo lắng về điểm này.")

negotiation_engine = NegotiationEngine()
