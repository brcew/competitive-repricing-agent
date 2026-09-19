"""
Database utility functions for common operations.
"""

from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import settings
from models import Base


# Global engine and session factory
_engine = None
_SessionLocal = None


def get_engine():
    """Get or create database engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,  # Verify connections before using
            echo=settings.log_level == "DEBUG",  # SQL logging in debug mode
        )
    return _engine


def get_session_factory():
    """Get or create session factory."""
    global _SessionLocal
    if _SessionLocal is None:
        engine = get_engine()
        _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return _SessionLocal


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Usage:
        with get_db_session() as session:
            session.query(SKU).all()
    """
    SessionLocal = get_session_factory()
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db() -> None:
    """Initialize database - create all tables."""
    engine = get_engine()
    Base.metadata.create_all(bind=engine)


def drop_db() -> None:
    """Drop all tables - use with caution!"""
    engine = get_engine()
    Base.metadata.drop_all(bind=engine)


def reset_db() -> None:
    """Drop and recreate all tables - use with caution!"""
    drop_db()
    init_db()