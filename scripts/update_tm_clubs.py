import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database.database import SessionLocal
from database.models import PlayerInfo

db = SessionLocal()

mapping = {
    "Arsenal Football Club": "Arsenal",
    "Chelsea Football Club": "Chelsea",
    "Manchester City Football Club": "Manchester City",
    "Futbol Club Barcelona": "Barcelona",
    "Paris Saint-Germain Football Club": "Paris Saint-Germain",
}

for old_name, new_name in mapping.items():
    players = db.query(PlayerInfo).filter(PlayerInfo.tm_club == old_name).all()
    for p in players:
        p.tm_club = new_name
    db.commit()
    print(f"Updated {len(players)} players for {new_name}")

bayern_players = db.query(PlayerInfo).filter(PlayerInfo.tm_club.like('%Bayern%')).all()
for p in bayern_players:
    p.tm_club = "Bayern Munich"
db.commit()
print(f"Updated {len(bayern_players)} players for Bayern Munich")

real_players = db.query(PlayerInfo).filter(PlayerInfo.tm_club.like('Real Madrid%')).all()
for p in real_players:
    p.tm_club = "Real Madrid"
db.commit()
print(f"Updated {len(real_players)} players for Real Madrid")

db.close()
