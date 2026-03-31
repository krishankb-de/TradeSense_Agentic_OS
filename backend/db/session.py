"""Database session management."""

from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from backend.core.config import get_settings

settings = get_settings()

# Create SQLAlchemy engine with connection pooling
# pool_size: minimum number of connections (5)
# max_overflow: maximum additional connections (20)
# Total max connections: 25
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # Verify connections before using
    pool_size=5,  # Minimum connections in pool
    max_overflow=20,  # Maximum additional connections
    pool_recycle=3600,  # Recycle connections after 1 hour
    echo=settings.is_development,
)

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create declarative base
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    Get database session.

    Yields:
        Database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
