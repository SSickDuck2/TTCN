import logging
import random
from sqlalchemy.orm import Session
from database.models import Club, ClubSeasonRecord, SystemState, SystemStateEnum

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────
# BẢNG TIỀN THƯỞNG XẾP HẠNG (Prize Money)
# Dựa theo mốc tương đương EPL/La Liga chuẩn hoá thành 5 giải
# ─────────────────────────────────────────────────────
PRIZE_MONEY_TABLE = {
    1:  100_000_000,
    2:   85_000_000,
    3:   75_000_000,
    4:   65_000_000,
    5:   57_000_000,
    6:   52_000_000,
    7:   48_000_000,
    8:   45_000_000,
    9:   42_000_000,
    10:  40_000_000,
    11:  38_000_000,
    12:  36_000_000,
    13:  34_000_000,
    14:  32_000_000,
    15:  30_000_000,
    16:  28_000_000,
    17:  25_000_000,
    18:  20_000_000,   # Xuống hạng
    19:  18_000_000,   # Xuống hạng
    20:  15_000_000,   # Xuống hạng
}

# ─────────────────────────────────────────────────────
# Hệ số bản quyền theo thứ hạng (Broadcasting multiplier)
# Ở hạng cao hơn → phát sóng nhiều hơn → doanh thu cao hơn
# ─────────────────────────────────────────────────────
def broadcasting_multiplier(position: int) -> float:
    if position <= 4:   return 1.5   # Top 4: Tham dự Champions League
    if position <= 6:   return 1.2   # Europa League
    if position <= 10:  return 1.0
    if position <= 15:  return 0.85
    return 0.70

class SeasonalEngine:
    """
    Module kết thúc mùa giải:
    - Snapshot thành tích & tài chính vào bảng ClubSeasonRecord
    - Tính doanh thu đa nguồn (Vé, Bản quyền, Áo đấu, Thưởng hạng)
    - Cộng doanh thu vào budget_remaining
    - Reset season stats chuẩn bị cho mùa mới
    """

    def run_end_of_season(self, db: Session):
        """Điểm vào duy nhất — gọi khi TimeEngine chuyển sang SEASON_UPDATE."""
        logger.info("[SEASON] Bắt đầu kết thúc mùa giải — tính toán doanh thu...")

        state = db.query(SystemState).first()
        season_year = state.season_year if state else 2024

        clubs = db.query(Club).all()
        for club in clubs:
            self._process_club(db, club, season_year)

        # Tăng season year sau khi xong
        if state:
            state.season_year = season_year + 1

        db.commit()
        logger.info(f"[SEASON] Kết thúc mùa {season_year}. Bắt đầu chuẩn bị mùa {season_year + 1}.")

    def _process_club(self, db: Session, club: Club, season_year: int):
        """Tính doanh thu và lưu lịch sử cho 1 CLB."""
        position = club.season_position or 10

        # ── 1. Tiền thưởng xếp hạng ──────────────────────────
        prize_money = PRIZE_MONEY_TABLE.get(position, 15_000_000)

        # ── 2. Doanh thu Bản quyền phát sóng ─────────────────
        # Base: 50M × hệ số hạng
        broadcast = 50_000_000 * broadcasting_multiplier(position)

        # ── 3. Doanh thu vé trận đấu ──────────────────────────
        # Tương quan với thành tích: Thắng nhiều → fan đến nhiều
        total_matches = (club.season_wins or 0) + (club.season_draws or 0) + (club.season_losses or 0)
        avg_attendance_rate = 0.5 + min((club.season_wins or 0) / max(total_matches, 1) * 0.6, 0.5)
        ticket_per_match = 2_500_000  # Giả định sân 40k chỗ × giá vé trung bình
        ticket_revenue = ticket_per_match * total_matches * avg_attendance_rate

        # ── 4. Doanh thu áo đấu & merchandise ────────────────
        # Gắn với vị trí & số trận đấu (CLB nổi tiếng hơn → bán nhiều hơn)
        merch_base = 10_000_000
        merch_boost = max(0, (10 - position)) * 500_000  # Top10 nhận thêm
        merchandise = merch_base + merch_boost

        # ── 5. Tổng doanh thu ─────────────────────────────────
        total_revenue = prize_money + broadcast + ticket_revenue + merchandise

        # ── 6. Snapshot vào ClubSeasonRecord ──────────────────
        record = ClubSeasonRecord(
            club_id=club.id,
            season_year=season_year,
            final_position=position,
            wins=club.season_wins or 0,
            draws=club.season_draws or 0,
            losses=club.season_losses or 0,
            goals_scored=club.season_goals_scored or 0,
            goals_conceded=club.season_goals_conceded or 0,
            ticket_revenue=round(ticket_revenue, 2),
            broadcasting_revenue=round(broadcast, 2),
            merchandise_revenue=round(merchandise, 2),
            prize_money=round(prize_money, 2),
            total_revenue=round(total_revenue, 2),
            budget_start=club.budget_remaining,
            budget_end=club.budget_remaining + total_revenue,
        )
        db.add(record)

        # ── 7. Cộng doanh thu vào ngân sách ───────────────────
        club.budget_remaining += total_revenue
        club.last_season_revenue = total_revenue

        # ── 8. Reset season stats ──────────────────────────────
        club.season_position = 10
        club.season_wins = 0
        club.season_draws = 0
        club.season_losses = 0
        club.season_goals_scored = 0
        club.season_goals_conceded = 0

        logger.info(
            f"[SEASON] {club.name} | Hạng {position} | "
            f"Doanh thu: €{total_revenue:,.0f} | Budget mới: €{club.budget_remaining:,.0f}"
        )

seasonal_engine = SeasonalEngine()
