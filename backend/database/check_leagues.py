import sqlite3
conn = sqlite3.connect('ttcn.db')
c = conn.cursor()
c.execute("SELECT DISTINCT league FROM player_info")
print(c.fetchall())
conn.close()
