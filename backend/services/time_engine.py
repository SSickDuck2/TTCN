import logging
from datetime import datetime, timedelta
from database.database import SessionLocal
from database.models import SystemState, SystemStateEnum, Negotiation, NegotiationStatusEnum, Contract, ContractStatusEnum, Club

logger = logging.getLogger(__name__)

class TimeEngine:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TimeEngine, cls).__new__(cls)
            cls._instance._init_state()
        return cls._instance

    def _init_state(self):
        self.cached_state = SystemStateEnum.TRANSFER_OPEN
        self.cached_date = None
        self.season_year = 2025
        self.load_from_db()

    def load_from_db(self):
        try:
            with SessionLocal() as db:
                state = db.query(SystemState).first()
                if not state:
                    state = SystemState(
                        current_state=SystemStateEnum.TRANSFER_OPEN,
                        current_date=datetime(2026, 6, 1),
                        season_year=2025
                    )
                    db.add(state)
                    db.commit()
                    db.refresh(state)

                self.cached_state = state.current_state
                self.cached_date = state.current_date
                self.season_year = state.season_year
        except Exception as e:
            # DB chưa được init (startup race) — giữ giá trị mặc định an toàn
            logger.warning(f"[TimeEngine] load_from_db failed (DB not ready?): {e}")
            if self.cached_date is None:
                self.cached_date = datetime(2026, 6, 1)
                self.cached_state = SystemStateEnum.TRANSFER_OPEN
                self.season_year = 2025

    def force_sync(self):
        """Buộc TimeEngine tải lại dữ liệu từ DB (dùng sau khi Admin can thiệp)"""
        self.load_from_db()

    def save_to_db(self):
        if not self.cached_date: return
        with SessionLocal() as db:
            state = db.query(SystemState).first()
            if state:
                state.current_state = self.cached_state
                state.current_date = self.cached_date
                state.season_year = self.season_year
                db.commit()

    def advance_time(self):
        """Called periodically (e.g. every second) to advance in-game time."""
        if not self.cached_date:
            return

        with SessionLocal() as db:
            # Check for active negotiations
            active_nego = db.query(Negotiation).filter(
                Negotiation.status == NegotiationStatusEnum.NEGOTIATING
            ).first()

            if active_nego:
                # 5 minutes = 1 day -> 1 sec = 1/300 day
                delta = timedelta(days=1.0/300.0)
            elif self.cached_state == SystemStateEnum.TRANSFER_CLOSED:
                # 5 seconds = 1 day -> 1 sec = 1/5 day
                delta = timedelta(days=1.0/5.0)
            else:
                # 20 seconds = 1 day -> 1 sec = 1/20 day
                delta = timedelta(days=1.0/20.0)

            self.cached_date += delta
            self.check_transitions()
            
        # In a real heavy app, you might save DB every 10 secs to reduce load.
        # Here we can save on every tick or every X ticks.
        self.save_to_db()

    def check_transitions(self):
        """Transition states based on current_date"""
        m = self.cached_date.month
        d = self.cached_date.day

        # TRANSFER_OPEN: Summer (Jun 1 to Aug 31) and Winter (Jan 1 to Jan 31)
        is_open_window = (6 <= m <= 8) or (m == 1)

        new_state = SystemStateEnum.TRANSFER_OPEN if is_open_window else SystemStateEnum.TRANSFER_CLOSED

        if new_state != self.cached_state:
            if self.cached_state == SystemStateEnum.TRANSFER_OPEN and new_state == SystemStateEnum.TRANSFER_CLOSED:
                # Cửa sổ chuyển nhượng vừa đóng. Kiểm tra vi phạm FFP.
                with SessionLocal() as db:
                    clubs = db.query(Club).all()
                    for club in clubs:
                        if club.budget_remaining < 0:
                            club.is_transfer_banned = True
                            logger.info(f"[FFP] CLB {club.name} bị cấm chuyển nhượng kỳ tới do ngân sách âm ({club.budget_remaining:,.0f}).")
                        else:
                            # Nếu đã dương tiền thì gỡ án phạt (nếu có) cho kỳ sau
                            club.is_transfer_banned = False
                    db.commit()

            self.cached_state = new_state
            logger.info(f"System State transitioned to: {new_state} on {self.cached_date.strftime('%Y-%m-%d')}")

            # Example: Season updates when passing specific dates.
            if new_state == SystemStateEnum.TRANSFER_CLOSED and m == 9:
                self.trigger_season_update()

    def trigger_season_update(self):
        """Kết thúc mùa giải: Tính doanh thu, cập nhật hợp đồng, snapshot lịch sử."""
        logger.info("[TIME] Triggering Season Update...")
        try:
            from services.seasonal_engine import seasonal_engine
            with SessionLocal() as db:
                # B1: Tính doanh thu & snapshot mùa vừa qua
                seasonal_engine.run_end_of_season(db)

                # B2: Giảm remaining_years của tất cả Contract ACTIVE
                contracts = db.query(Contract).filter(
                    Contract.status == ContractStatusEnum.ACTIVE
                ).all()
                for c in contracts:
                    c.remaining_years = max(0, (c.remaining_years or 1) - 1)
                    # Hợp đồng hết hạn tự động TERMINATED
                    if c.remaining_years == 0:
                        c.status = ContractStatusEnum.TERMINATED
                        logger.info(f"[SEASON] Contract player_id={c.player_id} hết hạn sau mùa này.")

                db.commit()
        except Exception as e:
            logger.error(f"[SEASON] Lỗi khi xử lý season update: {e}")

    def check_transfer_window_open(self) -> bool:
        """Returns True if transfers are allowed"""
        return self.cached_state == SystemStateEnum.TRANSFER_OPEN

    def get_current_time_info(self) -> dict:
        return {
            "current_date": self.cached_date.isoformat() if self.cached_date else None,
            "current_state": self.cached_state.value if self.cached_state else None,
            "season_year": self.season_year
        }

time_engine = TimeEngine()
