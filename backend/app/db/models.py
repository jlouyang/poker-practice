"""SQLAlchemy models for hand history persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

Base = declarative_base()


class HandRecord(Base):
    __tablename__ = "hands"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, index=True)
    hand_number = Column(Integer)
    dealer_seat = Column(Integer)
    small_blind = Column(Integer)
    big_blind = Column(Integer)
    community_cards = Column(String)  # JSON array
    pot_size = Column(Integer)
    winner_ids = Column(String)  # JSON array
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    player_states = relationship("PlayerStateRecord", back_populates="hand", cascade="all, delete-orphan")
    actions = relationship("ActionRecord", back_populates="hand", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisRecord", back_populates="hand", cascade="all, delete-orphan")


class PlayerStateRecord(Base):
    __tablename__ = "player_states"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hand_id = Column(Integer, ForeignKey("hands.id"))
    player_id = Column(String)
    seat = Column(Integer)
    starting_stack = Column(Integer)
    ending_stack = Column(Integer)
    hole_cards = Column(String)  # JSON array
    is_human = Column(Boolean, default=False)

    hand = relationship("HandRecord", back_populates="player_states")


class ActionRecord(Base):
    __tablename__ = "actions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hand_id = Column(Integer, ForeignKey("hands.id"))
    player_id = Column(String)
    street = Column(String)
    action_type = Column(String)
    amount = Column(Integer, default=0)
    sequence = Column(Integer)

    hand = relationship("HandRecord", back_populates="actions")


class AnalysisRecord(Base):
    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    hand_id = Column(Integer, ForeignKey("hands.id"))
    action_id = Column(Integer, ForeignKey("actions.id"), nullable=True)
    player_id = Column(String)
    street = Column(String)
    equity_at_decision = Column(Float)
    ev_of_action = Column(Float, nullable=True)
    optimal_action = Column(String, nullable=True)
    score = Column(String)  # "good", "mistake", "blunder"
    sequence = Column(Integer)

    hand = relationship("HandRecord", back_populates="analysis_results")


import os

# Railway: when a volume is attached, RAILWAY_VOLUME_MOUNT_PATH is set (e.g. /data)
_railway_volume = os.environ.get("RAILWAY_VOLUME_MOUNT_PATH")
_default_db = (
    f"{_railway_volume.rstrip('/')}/poker_history.db"
    if _railway_volume
    else os.environ.get("POKER_DB_PATH", "poker_history.db")
)
_DEFAULT_DB_PATH = _default_db


def get_engine(db_path: str = _DEFAULT_DB_PATH):
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session_factory(db_path: str = _DEFAULT_DB_PATH):
    engine = get_engine(db_path)
    return sessionmaker(bind=engine)


_default_factory = None


def _get_default_factory():
    global _default_factory
    if _default_factory is None:
        _default_factory = get_session_factory()
    return _default_factory


def get_db():
    """FastAPI dependency that yields a DB session and auto-closes it."""
    factory = _get_default_factory()
    db = factory()
    try:
        yield db
    finally:
        db.close()
