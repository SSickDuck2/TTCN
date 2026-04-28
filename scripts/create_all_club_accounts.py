import sys
import os
import unicodedata
import re

# Add backend directory to sys.path
sys.path.append(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

from database.database import SessionLocal
from sqlalchemy.orm import sessionmaker
from database.models import Club, PlayerInfo
from utils.auth import get_password_hash

def slugify(value):
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value).strip().lower()
    return re.sub(r'[-\s]+', '', value)

def create_all_clubs():
    # Use a custom session with longer timeout
    from sqlalchemy import create_engine
    from utils.config import settings
    engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False, "timeout": 60})
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        # Get all unique clubs from PlayerInfo
        tm_clubs = db.query(PlayerInfo.tm_club).filter(PlayerInfo.tm_club.isnot(None)).distinct().all()
        team_titles = db.query(PlayerInfo.team_title).filter(PlayerInfo.team_title.isnot(None)).distinct().all()
        
        all_club_names = set()
        for c in tm_clubs:
            if c[0] and "," not in c[0]:
                all_club_names.add(c[0])
        for c in team_titles:
            if c[0] and "," not in c[0]:
                all_club_names.add(c[0])
        
        print(f"Found {len(all_club_names)} unique clubs.")
        
        count = 0
        for name in sorted(all_club_names):
            username = slugify(name)
            if not username:
                continue
                
            existing = db.query(Club).filter(Club.username == username).first()
            if not existing:
                club = Club(
                    username=username,
                    name=name,
                    password_hash=get_password_hash("password123"),
                    budget_remaining=150000000.0,
                    wage_budget=3000000.0,
                    wage_spent=0.0
                )
                db.add(club)
                count += 1
                
                if count % 10 == 0:
                    db.commit()
                    print(f"Committed {count} clubs...")
        
        db.commit()
        print(f"Successfully added {count} new club accounts.")
    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    create_all_clubs()
