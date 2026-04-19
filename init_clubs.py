from database import SessionLocal
from models import Club
from API import get_password_hash

db = SessionLocal()

clubs_data = [
    {"username": "admin", "name": "System Admin", "budget_remaining": 9999999999.0, "wage_budget": 9999999999.0},
    {"username": "arsenal", "name": "Arsenal", "budget_remaining": 150000000.0, "wage_budget": 3000000.0},
    {"username": "chelsea", "name": "Chelsea", "budget_remaining": 150000000.0, "wage_budget": 3000000.0},
    {"username": "mancity", "name": "Manchester City", "budget_remaining": 150000000.0, "wage_budget": 3000000.0},
    {"username": "realmadrid", "name": "Real Madrid", "budget_remaining": 150000000.0, "wage_budget": 3000000.0},
    {"username": "barcelona", "name": "Barcelona", "budget_remaining": 150000000.0, "wage_budget": 3000000.0},
    {"username": "bayern", "name": "Bayern Munich", "budget_remaining": 150000000.0, "wage_budget": 3000000.0},
    {"username": "psg", "name": "Paris Saint-Germain", "budget_remaining": 150000000.0, "wage_budget": 3000000.0},
]

for c in clubs_data:
    existing = db.query(Club).filter(Club.username == c["username"]).first()
    if not existing:
        club = Club(
            username=c["username"],
            name=c["name"],
            password_hash=get_password_hash("password123"),
            budget_remaining=c["budget_remaining"],
            wage_budget=c["wage_budget"],
            wage_spent=0.0
        )
        db.add(club)
        print(f"Added club: {c['name']}")

db.commit()
db.close()
