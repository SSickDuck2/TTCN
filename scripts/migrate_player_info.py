"""
Script to add missing columns to player_info table in ttcn.db.
Run from project root: python scripts/migrate_player_info.py
"""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), '..', 'backend', 'database', 'ttcn.db')
conn = sqlite3.connect(db_path)
c = conn.cursor()

# Get current columns
c.execute("PRAGMA table_info(player_info)")
existing_cols = {row[1] for row in c.fetchall()}
print("Existing columns:", existing_cols)

# Add tm_club if missing
if 'tm_club' not in existing_cols:
    c.execute("ALTER TABLE player_info ADD COLUMN tm_club TEXT")
    print("Added column: tm_club")
    # Initialize tm_club to team_title value
    c.execute("UPDATE player_info SET tm_club = team_title")
    print("Initialized tm_club from team_title")
else:
    print("Column tm_club already exists")

conn.commit()

# Verify
c.execute("SELECT COUNT(*) FROM player_info WHERE tm_club IS NOT NULL")
count = c.fetchone()[0]
print(f"Rows with tm_club set: {count}")

c.execute("SELECT id, player_name, tm_club, market_value_in_eur, position, league FROM player_info LIMIT 5")
for row in c.fetchall():
    print(row)

conn.close()
print("Migration complete.")
