from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

engine = create_engine(
    settings.sqlalchemy_url,
    pool_size=10,          # Base connections kept open per-service
    max_overflow=20,       # Burst connections beyond pool_size
    pool_pre_ping=True,    # Detect stale connections from PgBouncer restarts
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def check_database_connection() -> tuple[bool, str]:
    """
    Lightweight connectivity probe used by health/readiness endpoints.
    Keeps failures out of request handlers that expect business tables.
    """
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return True, "ok"
    except SQLAlchemyError as exc:
        return False, str(exc)
