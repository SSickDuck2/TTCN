import sqlite3

db_path = 'backend/database/ttcn.db'
conn = sqlite3.connect(db_path)
cur = conn.cursor()

print('=== CLUBS ===')
cur.execute('SELECT id, name, username, budget_remaining FROM clubs')
for r in cur.fetchall():
    print(f'  id={r[0]}  name="{r[1]}"  user="{r[2]}"  budget={r[3]:,.0f}')

print()
print('=== PLAYER_INFO sample (first 5) ===')
cur.execute('SELECT id, player_name, position, team_title, market_value_in_eur FROM player_info LIMIT 5')
for r in cur.fetchall():
    print(f'  id={r[0]}  name="{r[1]}"  pos={r[2]}  team="{r[3]}"  val={r[4]}')

conn.close()
