import sqlite3

def init_wealth_budgets():
    conn = sqlite3.connect('backend/database/ttcn.db')
    c = conn.cursor()
    
    # 1. Tính tổng giá trị đội hình của từng CLB
    # Lấy dữ liệu từ player_info
    squad_data = c.execute('''
        SELECT tm_club, league, SUM(market_value_in_eur) as total_val
        FROM player_info 
        WHERE tm_club IS NOT NULL AND tm_club != ""
        GROUP BY tm_club
    ''').fetchall()
    
    league_bonuses = {
        'epl': 50_000_000.0,
        'la_liga': 30_000_000.0,
        'bundesliga': 30_000_000.0,
        'serie_a': 30_000_000.0,
        'ligue_1': 20_000_000.0
    }
    
    updated_count = 0
    for club_name, league, total_val in squad_data:
        if not total_val: total_val = 0
        
        # Công thức: 15% giá trị đội hình + Bonus giải đấu
        bonus = league_bonuses.get(league, 10_000_000.0)
        calculated_budget = (total_val * 0.15) + bonus
        
        # Đảm bảo tối thiểu 20M, tối đa 600M cho các siêu CLB
        final_budget = max(20_000_000.0, min(600_000_000.0, calculated_budget))
        
        # Cập nhật vào bảng clubs
        c.execute('UPDATE clubs SET budget_remaining = ? WHERE name = ?', (final_budget, club_name))
        if c.rowcount > 0:
            updated_count += 1
            
    conn.commit()
    print(f"Successfully updated budgets for {updated_count} clubs based on wealth distribution.")
    conn.close()

if __name__ == "__main__":
    init_wealth_budgets()
