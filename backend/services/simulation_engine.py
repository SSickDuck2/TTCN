import logging
import random
from sqlalchemy.orm import Session
from database.models import SimulationConfig, Club, Negotiation, NegotiationStatusEnum, Contract, PlayerInfo, SystemState
from services.contract_engine import contract_engine
from services.negotiation_engine import negotiation_engine

logger = logging.getLogger(__name__)

class SimulationEngine:
    """
    Module tự động lên script chốt giá, đưa ra quyết định hỏi mua dành cho các CLB do Máy điều khiển.
    """
    
    def run_simulation_cycle(self, db: Session):
        """Job chạy ngầm trigger hành động của CLB ảo: Hỏi mua, phản giá"""
        self._cancel_expired_negotiations(db)

        # Lấy các CLB máy
        sim_configs = db.query(SimulationConfig).filter(SimulationConfig.is_simulated == True).all()
        if not sim_configs: return
        
        for config in sim_configs:
            # Tỉ lệ 10% mỗi lần cycle bot sẽ rà soát mua
            if random.random() < 0.10:
                self._auto_scan_market(db, config)
                
            # Xử lý các đàm phán đang dang dở
            self._auto_negotiate(db, config)

    def _cancel_expired_negotiations(self, db: Session):
        """Hủy tự động các phiên đàm phán đã quá hạn"""
        state = db.query(SystemState).first()
        if not state or not state.current_date: return

        expired_negos = db.query(Negotiation).filter(
            Negotiation.status.in_([NegotiationStatusEnum.INQUIRY, NegotiationStatusEnum.NEGOTIATING]),
            Negotiation.expires_at_game_date != None,
            Negotiation.expires_at_game_date < state.current_date
        ).all()

        for nego in expired_negos:
            nego.status = NegotiationStatusEnum.CANCELLED
            logger.info(f"[SIMULATION] Canceled expired negotiation {nego.id}")
            
        if expired_negos:
            db.commit()

    def _auto_scan_market(self, db: Session, config: SimulationConfig):
        """AI quét thị trường và gửi Inquiry"""
        club = db.query(Club).filter(Club.id == config.club_id).first()
        if not club or club.is_transfer_banned:
            return # Bị cấm chuyển nhượng thì không quét
            
        # Cho phép nợ (âm tiền), nhưng hạn chế nợ quá sâu (VD: âm quá 100M thì ngừng mua)
        if club.budget_remaining < -100000000:
            return

        # Tìm ngẫu nhiên cầu thủ giỏi nhưng phù hợp độ tuổi/strategy
        query = db.query(PlayerInfo).filter(
            PlayerInfo.market_value_in_eur > 1000000
        )
        
        if config.strategy == "YOUTH_DEV":
            query = query.filter(PlayerInfo.age <= 23)
        elif config.strategy == "VETERAN_PREF":
            query = query.filter(PlayerInfo.age >= 29)
            
        players = query.order_by(PlayerInfo.market_value_in_eur.desc()).limit(10).all()
        if not players: return
        
        target = random.choice(players)
        
        # Đã sở hữu thì bỏ qua
        existing_contract = db.query(Contract).filter(
            Contract.player_id == target.id, Contract.club_id == club.id, Contract.status == "ACTIVE"
        ).first()
        if existing_contract: return
        
        logger.info(f"[SIMULATION] Club {club.name} initiating inquiry for player {target.player_name}")
        negotiation_engine.initiate_inquiry(db, club.id, target.id)


    def _auto_negotiate(self, db: Session, config: SimulationConfig):
        """Xử lý quyền trả giá của AI trong đàm phán kéo thanh (Thực hiện hành động nếu tới lượt)"""
        # Tìm các Negotiations AI đóng vai trò Người Bán hoặc Người Mua
        active_negos = db.query(Negotiation).filter(
            (Negotiation.selling_club_id == config.club_id) | (Negotiation.buying_club_id == config.club_id),
            Negotiation.status.in_([NegotiationStatusEnum.INQUIRY, NegotiationStatusEnum.NEGOTIATING])
        ).all()
        
        for nego in active_negos:
            is_seller = (nego.selling_club_id == config.club_id)
            
            if nego.status == NegotiationStatusEnum.INQUIRY:
                if is_seller:
                    # AI là người bán, khi nhận câu hỏi INQUIRY -> Trả lời Đồng ý or TỪ CHỐI
                    # Dựa vào willingness_to_sell
                    if random.random() < config.willingness_to_sell:
                        fair_value = contract_engine.calculate_market_value(db, nego.player_id)
                        # Hét giá khởi điểm (gấp 1.2 - 1.5 lần giá thật tùy độ linh hoạt)
                        starting_demand = fair_value * (1 + (1.0 - config.negotiation_flexibility))
                        negotiation_engine.respond_to_inquiry(db, nego.id, accept=True, initial_demand=starting_demand)
                    else:
                        negotiation_engine.respond_to_inquiry(db, nego.id, accept=False)
            
            elif nego.status == NegotiationStatusEnum.NEGOTIATING:
                fair_value = contract_engine.calculate_market_value(db, nego.player_id)
                
                if is_seller:
                    # Trả lời Offer của Buyer
                    # Nếu offer gần với Demand (cách 10%), hoặc offer > fair_value thì Ok, lùi một bước
                    if nego.current_offer >= nego.selling_club_demand * 0.9:
                        negotiation_engine.respond_to_offer(db, nego.id, nego.current_offer)
                    else:
                        # Rút giá xuống 5% để tiếp tục cưa cẩm
                        new_demand = nego.selling_club_demand * 0.95
                        if new_demand < fair_value * 0.8: 
                            # Giữ giá cứng nếu bị ép quá
                            new_demand = nego.selling_club_demand
                        negotiation_engine.respond_to_offer(db, nego.id, new_demand)
                        
                else:
                    # Buyer (máy đi hỏi mua)
                    if nego.selling_club_demand <= nego.current_offer * 1.1:
                        # Rất gần -> chốt giá
                        negotiation_engine.submit_offer(db, nego.id, nego.selling_club_demand)
                    else:
                        # Tăng offer lên 1 chút (10%)
                        new_offer = max(nego.current_offer * 1.1, fair_value * 0.8)
                        # Đảm bảo không vung quá budget
                        club = db.query(Club).filter(Club.id == config.club_id).first()
                        if new_offer > club.budget_remaining:
                            negotiation_engine.cancel_negotiation(db, nego.id, config.club_id)
                        else:
                            negotiation_engine.submit_offer(db, nego.id, new_offer)

simulation_engine = SimulationEngine()
