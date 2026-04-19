from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os
from typing import Generator

# Database URL - Using SQLite for development, PostgreSQL for production
# For PostgreSQL: postgresql://user:password@localhost:5432/ttcn
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ttcn.db")

# SQLite connection with StaticPool for in-memory or file-based
if DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
        poolclass=StaticPool,
    )
else:
    # PostgreSQL
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_size=10,
        max_overflow=20,
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db() -> Generator[Session, None, None]:
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    """Initialize database tables."""
    from models import Base
    Base.metadata.create_all(bind=engine)
