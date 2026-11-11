"""
Database session and SQLite engine configuration for DesktopPilot AI.
Persists execution logs, task history, and human-in-the-loop approvals.
Provides reliable synchronous SQLite engine using Python standard library sqlite3 + SQLAlchemy.
"""

from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from utils.logger import logger

DB_PATH = Path("database/desktoppilot.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)
DB_URL = f"sqlite:///{DB_PATH.resolve()}"

class Base(DeclarativeBase):
    pass

engine = create_engine(DB_URL, echo=False, connect_args={"check_same_thread": False})
session_factory = sessionmaker(bind=engine, expire_on_commit=False, class_=Session)


def get_db():
    """Context or dependency generator for database sessions."""
    db = session_factory()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initializes database tables on application startup."""
    try:
        # Import models so they register with Base.metadata
        import database.models  # noqa: F401
        Base.metadata.create_all(bind=engine)
        logger.info(f"Database initialized successfully at {DB_PATH.resolve()}")
    except Exception as e:
        logger.warning(f"Database initialization warning: {e}")

