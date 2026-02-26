"""SQLAlchemy models for hand history persistence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text, JSON,
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
    created_at = Column(DateTime, default=datetime.utcnow)

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


def get_engine(db_path: str = "poker_history.db"):
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    Base.metadata.create_all(engine)
    return engine


def get_session_factory(db_path: str = "poker_history.db"):
    engine = get_engine(db_path)
    return sessionmaker(bind=engine)
