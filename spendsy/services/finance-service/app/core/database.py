from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings

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
