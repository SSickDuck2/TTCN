import sqlite3

conn = sqlite3.connect('backend/database/ttcn.db')
c = conn.cursor()

# Lấy tất cả các đàm phán có selling_club_id là NULL
c.execute("""
    SELECT n.id, p.tm_club 
    FROM negotiations n
    JOIN player_info p ON n.player_id = p.id
    WHERE n.selling_club_id IS NULL
""")
null_negos = c.fetchall()

print(f"Found {len(null_negos)} negotiations with NULL selling_club_id")

updated_count = 0
for nego_id, club_name in null_negos:
    if not club_name:
        continue
    
    # Tìm club_id tương ứng với tên
    c.execute("SELECT id FROM clubs WHERE name = ?", (club_name,))
    club_row = c.fetchone()
    
    if club_row:
        club_id = club_row[0]
        c.execute("UPDATE negotiations SET selling_club_id = ? WHERE id = ?", (club_id, nego_id))
        updated_count += 1

conn.commit()
print(f"Successfully updated {updated_count} negotiations.")
conn.close()
