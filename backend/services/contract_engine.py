import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from database.models import Contract, ContractStatusEnum, PlayerInfo, Negotiation, NegotiationStatusEnum

logger = logging.getLogger(__name__)

class ContractEngine:
    """
    Module quản lý vòng đời và giá trị hợp đồng cầu thủ.
    """

    def create_contract(self, db: Session, player_id: int, club_id: int, **kwargs) -> Contract:
        """Tạo hợp đồng mới, cập nhật hợp đồng cũ."""
        # Chuyển trạng thái hợp đồng cũ của cầu thủ này sang TRANSFERRED
        old_contracts = db.query(Contract).filter(
            Contract.player_id == player_id,
            Contract.status == ContractStatusEnum.ACTIVE
        ).all()
        for c in old_contracts:
            c.status = ContractStatusEnum.TRANSFERRED
            
        remaining_years = kwargs.get("remaining_years", 3)
        end_date = datetime.utcnow() + timedelta(days=365 * remaining_years)
        
        new_contract = Contract(
            player_id=player_id,
            club_id=club_id,
            start_date=datetime.utcnow(),
            end_date=end_date,
            remaining_years=remaining_years,
            base_salary=kwargs.get("base_salary", 50000.0), # Lương mặc định
            release_clause=kwargs.get("release_clause", None),
            performance_bonus=kwargs.get("performance_bonus", 0.0),
            loyalty_bonus=kwargs.get("loyalty_bonus", 0.0),
            early_termination_fee=kwargs.get("early_termination_fee", 0.0),
            status=ContractStatusEnum.ACTIVE
        )
        db.add(new_contract)
        db.commit()
        db.refresh(new_contract)
        return new_contract

    def calculate_market_value(self, db: Session, player_id: int) -> float:
        """Tính market value dựa theo Form Factor + Age Factor + Contract Factor"""
        player_info = db.query(PlayerInfo).filter(PlayerInfo.id == player_id).first()
        if not player_info or not player_info.market_value_in_eur:
            return 0.0
            
        base_value = float(player_info.market_value_in_eur)
        age = player_info.age if player_info.age else 25.0
        
        # 1. Age Factor
        age_factor = 1.0
        if age <= 23: age_factor = 1.2
        elif age >= 32: age_factor = 0.8
        
        # 2. Contract Factor
        contract_factor = 1.0
        active_contract = db.query(Contract).filter(
            Contract.player_id == player_id, 
            Contract.status == ContractStatusEnum.ACTIVE
        ).first()
        
        if active_contract:
            if active_contract.remaining_years >= 3:
                contract_factor = 1.2
            elif active_contract.remaining_years <= 1:
                contract_factor = 0.7
                
        # 3. Form Factor (Linh hoạt theo vị trí)
        form_factor = 1.0
        pos = player_info.position.upper() if player_info.position else ""
        
        goals = player_info.goals or 0
        assists = player_info.assists or 0
        xg = player_info.xG or 0.0
        xa = player_info.xA or 0.0
        games = player_info.games or 1
        time_played = player_info.time or 0
        key_passes = player_info.key_passes or 0
        xg_buildup = player_info.xGBuildup or 0.0
        xg_chain = player_info.xGChain or 0.0
        yellows = player_info.yellow_cards or 0
        reds = player_info.red_cards or 0
        
        if "F" in pos or "FW" in pos:
            # Tiền đạo: Đánh giá bằng Bàn thắng, Kiến tạo, xG, xA
            total_contributions = goals + assists
            exp_contributions = xg + xa
            if total_contributions > 15 or exp_contributions > 15.0:
                form_factor = 1.15
            elif total_contributions > 8 or exp_contributions > 8.0:
                form_factor = 1.05
            elif total_contributions < 3 and games > 15:
                form_factor = 0.90 # Phong độ báo động
                
        elif "M" in pos:
            # Tiền vệ: xGChain, xGBuildup, Key passes (Kiểm soát, kiến tạo cơ hội)
            if key_passes > 40 or xg_chain > 12.0 or xg_buildup > 8.0:
                form_factor = 1.10
            elif key_passes > 20 or xg_chain > 6.0:
                form_factor = 1.05
            elif time_played > 1500 and key_passes < 10 and xg_chain < 3.0:
                form_factor = 0.95
                
        elif "D" in pos:
            # Hậu vệ: Vì thiếu data tranh chấp, tạm dùng thời gian đá chính (sự tin tưởng), phát động (xGBuildup) và Kỷ luật (Cards)
            if time_played > 2500 and yellows < 5 and reds == 0:
                form_factor = 1.10
            elif time_played > 1500 and xg_buildup > 5.0:
                form_factor = 1.05
            elif reds >= 2 or yellows > 10:
                form_factor = 0.90 # Bị trừ vì thiếu kỷ luật
                
        elif "GK" in pos:
            # Thủ môn: Ít data cản phá, đánh giá bằng mức độ tin tưởng (phút thi đấu)
            if time_played > 3000:
                form_factor = 1.10
            elif time_played > 2000:
                form_factor = 1.05
            
        fair_value = base_value * age_factor * contract_factor * form_factor
        return round(fair_value, 2)

    def get_public_info(self, db: Session, player_id: int) -> dict:
        """Trả về dữ liệu công khai (ẩn đi release_clause, thông tin lương dạng khoảng ước tính)"""
        market_val = self.calculate_market_value(db, player_id)
        
        # Lấy hợp đồng active
        contract = db.query(Contract).filter(
            Contract.player_id == player_id,
            Contract.status == ContractStatusEnum.ACTIVE
        ).first()
        
        if not contract:
            return {
                "market_value": market_val,
                "status": "No Active Contract",
                "remaining_years": 0
            }
            
        # Ước tính lương (xê dịch +/- 20%)
        salary = contract.base_salary
        salary_range = f"{int(salary * 0.8)} - {int(salary * 1.2)}"

        return {
            "player_id": player_id,
            "club_id": contract.club_id,
            "remaining_years": contract.remaining_years,
            "estimated_weekly_wage": salary_range,
            "market_value": market_val,
            "for_sale_status": "Available" # Có thể mở rộng
        }

    def get_private_info(self, db: Session, player_id: int, requesting_club_id: int) -> dict:
        """
        Trả về thông tin hợp đồng thật nếu club_id đúng là chủ sở hữu.
        Trường hợp đàm phán chính thức, release_clause có thể hiển thị công khai cho club được share.
        """
        contract = db.query(Contract).filter(
            Contract.player_id == player_id,
            Contract.status == ContractStatusEnum.ACTIVE
        ).first()
        
        if not contract:
            return self.get_public_info(db, player_id)
            
        is_owner = (contract.club_id == requesting_club_id)
        
        # Kiểm tra xem có đang có thương vụ đàm phán mở allow publish ko?
        has_active_negotiation = False
        if not is_owner:
            nego = db.query(Negotiation).filter(
                Negotiation.player_id == player_id,
                Negotiation.buying_club_id == requesting_club_id,
                Negotiation.status.in_([NegotiationStatusEnum.INQUIRY, NegotiationStatusEnum.NEGOTIATING]),
                Negotiation.is_public_release_clause == True
            ).first()
            if nego:
                has_active_negotiation = True
                
        # Nếu chưa đủ quyền truy cập private -> lùi về public
        if not (is_owner or has_active_negotiation):
            return self.get_public_info(db, player_id)
            
        return {
            "player_id": player_id,
            "club_id": contract.club_id,
            "remaining_years": contract.remaining_years,
            "exact_base_salary": contract.base_salary,
            "release_clause": contract.release_clause,
            "performance_bonus": contract.performance_bonus,
            "loyalty_bonus": contract.loyalty_bonus,
            "early_termination_fee": contract.early_termination_fee,
            "is_owner_view": is_owner
        }

contract_engine = ContractEngine()
