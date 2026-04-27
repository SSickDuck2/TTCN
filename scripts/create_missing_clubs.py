import sys
import os
import sqlite3

# Thêm đường dẫn backend vào sys.path để import được utils
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from utils.auth import get_password_hash

conn = sqlite3.connect('backend/database/ttcn.db')
c = conn.cursor()

# Lấy danh sách các club name từ player_info
c.execute("SELECT DISTINCT tm_club FROM player_info WHERE tm_club IS NOT NULL")
all_club_names = [r[0] for r in c.fetchall()]

# Lấy danh sách club name đã tồn tại
c.execute("SELECT name FROM clubs")
existing_club_names = [r[0] for r in c.fetchall()]

# Lọc ra các club chưa có tài khoản
missing_clubs = [name for name in all_club_names if name not in existing_club_names]

print(f"Found {len(missing_clubs)} missing clubs.")

password_hash = get_password_hash("password123")
created_count = 0

for club_name in missing_clubs:
    # Bỏ qua các trường hợp có dấu phẩy (thường là nhiều đội hoặc lỗi data)
    if ',' in club_name:
        continue
        
    # Tạo username: viết thường, xóa khoảng trắng và ký tự đặc biệt
    username = "".join(e for e in club_name.lower() if e.isalnum())
    
    # Kiểm tra xem username đã tồn tại chưa (có thể trùng sau khi normalize)
    c.execute("SELECT id FROM clubs WHERE username = ?", (username,))
    if c.fetchone():
        # Nếu trùng username, thêm hậu tố
        username = username + "_club"
        c.execute("SELECT id FROM clubs WHERE username = ?", (username,))
        if c.fetchone():
            continue # Skip if still duplicate

    try:
        c.execute("""
            INSERT INTO clubs (username, password_hash, name, budget_remaining, wage_budget, wage_spent)
            VALUES (?, ?, ?, 100000000.0, 1000000.0, 0.0)
        """, (username, password_hash, club_name))
        created_count += 1
    except Exception as e:
        print(f"Error creating club {club_name}: {e}")

conn.commit()
print(f"Successfully created {created_count} new club accounts.")
conn.close()
