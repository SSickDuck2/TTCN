import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    MAX_WAGE_BUDGET: float = float(os.getenv("MAX_WAGE_BUDGET", "400000.0"))
    MAX_TOTAL_BUDGET: float = float(os.getenv("MAX_TOTAL_BUDGET", "200000000.0"))
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./ttcn.db")
    
    LEAGUE_OPTIONS = {
        "Premier League": "ENG-Premier League",
        "La Liga": "ES-La Liga",
        "Serie A": "IT-Serie A",
        "Bundesliga": "DE-Bundesliga",
        "Ligue 1": "FR-Ligue 1",
    }
    
    PAGE_SIZE: int = 30

settings = Settings()
