import os
import sys
from datetime import datetime, timedelta
import random

# Đảm bảo import được các module từ backend
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.database import SessionLocal, init_db, engine
from database.models import (
    Club, PlayerInfo, Contract, ContractStatusEnum,
    SimulationConfig, SystemState, SystemStateEnum, Base
)

def seed_db():
    print("Khởi tạo schema database...")
    # Drop bảng contracts và negotiations để apply FK mới (tránh lỗi nếu SQLite đã tạo trước đó)
    try:
        from database.models import Contract, Negotiation
        Contract.__table__.drop(engine, checkfirst=True)
        Negotiation.__table__.drop(engine, checkfirst=True)
    except Exception as e:
        print(f"Bỏ qua drop bảng: {e}")
        
    init_db()

    db = SessionLocal()
    try:
        print("Đang chạy seed data...")

        # 1. SystemState
        state = db.query(SystemState).first()
        if not state:
            state = SystemState(
                current_state=SystemStateEnum.TRANSFER_OPEN,
                current_date=datetime(2024, 6, 1),
                season_year=2024
            )
            db.add(state)
            print("Đã tạo SystemState khởi đầu.")

        # 2. SimulationConfigs (Cho tất cả trừ Arsenal)
        # Lấy Arsenal (id = 2) để loại trừ
        arsenal = db.query(Club).filter(Club.username == "arsenal").first()
        arsenal_id = arsenal.id if arsenal else 2

        clubs = db.query(Club).filter(Club.id != 1).all() # Bỏ System Admin (id=1)
        for club in clubs:
            if club.id == arsenal_id:
                # Của người chơi -> Đảm bảo là ko bị simulated
                continue
                
            config = db.query(SimulationConfig).filter(SimulationConfig.club_id == club.id).first()
            if not config:
                strategy = random.choice(["YOUTH_DEV", "VETERAN_PREF", "BALANCED", "BARGAIN_HUNTER"])
                config = SimulationConfig(
                    club_id=club.id,
                    strategy=strategy,
                    is_simulated=True
                )
                db.add(config)
                print(f"Đã tạo SimulationConfig cho {club.name} ({strategy}).")

        # 3. Tạo Contracts cho cầu thủ
        players = db.query(PlayerInfo).all()
        contract_count = 0
        skip_count = 0
        
        # Tạo mapping name -> club_id
        club_map = {c.name.lower(): c.id for c in db.query(Club).all()}
        
        for player in players:
            # Kiểm tra xem cầu thủ đã có hợp đồng chưa
            existing = db.query(Contract).filter(
                Contract.player_id == player.id,
                Contract.status == ContractStatusEnum.ACTIVE
            ).first()
            
            if existing:
                skip_count += 1
                continue
                
            # Mapping team_title với club.name
            team_title_lower = str(player.team_title).lower() if player.team_title else ""
            club_id = None
            
            # Khớp tên chính xác hoặc chứa tên
            for c_name, c_id in club_map.items():
                if c_name in team_title_lower or team_title_lower in c_name:
                    club_id = c_id
                    break
                    
            if club_id:
                # Random remaining years (1 to 5)
                years = random.randint(1, 5)
                # Tính release clause (giá trị thị trường * 1.5 đến 3.0)
                market_val = player.market_value_in_eur or 1000000
                rc = market_val * random.uniform(1.5, 3.0)
                
                contract = Contract(
                    player_id=player.id,
                    club_id=club_id,
                    start_date=datetime(2024, 6, 1),
                    end_date=datetime(2024 + years, 6, 1),
                    base_salary=(market_val / 100) * random.uniform(0.8, 1.2), # Tạm tính
                    release_clause=rc,
                    remaining_years=years,
                    status=ContractStatusEnum.ACTIVE
                )
                db.add(contract)
                contract_count += 1

        db.commit()
        print(f"Đã tạo {contract_count} hợp đồng. Bỏ qua {skip_count} hợp đồng đã tồn tại.")
        print("\nSeed hoàn tất! Bạn có thể đăng nhập bằng tài khoản 'arsenal' để làm người chơi.")
        
    except Exception as e:
        db.rollback()
        print(f"LỖI: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_db()
