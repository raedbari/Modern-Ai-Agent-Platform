"""SQLAlchemy base configuration for multi-tenant database."""

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import get_settings

settings = get_settings()

# Create engine - in production use real DATABASE_URL from settings
# For now using SQLite for development
DATABASE_URL = "sqlite:///./maap.db"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency that provides a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
