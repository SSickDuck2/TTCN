import sys
sys.path.insert(0, 'backend')
from database.database import SessionLocal
from database.models import PlayerInfo
from sqlalchemy import func

db = SessionLocal()

# Get clubs with clean names (no comma = not dual-season player)
for league in ['bundesliga', 'epl', 'la_liga', 'ligue_1', 'serie_a']:
    clubs = db.query(PlayerInfo.team_title).filter(
        PlayerInfo.league == league,
        PlayerInfo.team_title.notlike('%,%')
    ).distinct().order_by(PlayerInfo.team_title).all()
    print(f"\n{league} ({len(clubs)} clubs):", [c[0] for c in clubs])

db.close()
