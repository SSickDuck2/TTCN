import sqlite3

def repair_leagues():
    conn = sqlite3.connect('backend/database/ttcn.db')
    c = conn.cursor()
    
    # Lấy tất cả các CLB đang sở hữu cầu thủ
    clubs = c.execute('SELECT DISTINCT tm_club FROM player_info WHERE tm_club IS NOT NULL AND tm_club != ""').fetchall()
    
    updated_count = 0
    for (club_name,) in clubs:
        # Tìm giải đấu phổ biến nhất của CLB này
        # (Loại trừ các dòng có dấu phẩy trong team_title vì đó là dữ liệu lịch sử)
        league_res = c.execute('''
            SELECT league, COUNT(*) as count 
            FROM player_info 
            WHERE tm_club = ? 
            GROUP BY league 
            ORDER BY count DESC 
            LIMIT 1
        ''', (club_name,)).fetchone()
        
        if league_res:
            dominant_league = league_res[0]
            # Cập nhật tất cả cầu thủ trong CLB này về giải đấu đó
            c.execute('UPDATE player_info SET league = ? WHERE tm_club = ?', (dominant_league, club_name))
            updated_count += c.rowcount
            
    conn.commit()
    print(f"Updated leagues for {updated_count} players.")
    conn.close()

if __name__ == "__main__":
    repair_leagues()
