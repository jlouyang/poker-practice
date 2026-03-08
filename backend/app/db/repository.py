"""CRUD operations for hand history."""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from app.db.models import ActionRecord, AnalysisRecord, HandRecord, PlayerStateRecord


def save_hand(
    db: Session,
    session_id: str,
    hand_number: int,
    dealer_seat: int,
    small_blind: int,
    big_blind: int,
    community_cards: list[str],
    pot_size: int,
    winner_ids: list[str],
    players: list[dict],
    actions: list[dict],
) -> HandRecord:
    hand = HandRecord(
        session_id=session_id,
        hand_number=hand_number,
        dealer_seat=dealer_seat,
        small_blind=small_blind,
        big_blind=big_blind,
        community_cards=json.dumps(community_cards),
        pot_size=pot_size,
        winner_ids=json.dumps(winner_ids),
    )
    db.add(hand)
    db.flush()

    for p in players:
        ps = PlayerStateRecord(
            hand_id=hand.id,
            player_id=p["player_id"],
            seat=p["seat"],
            starting_stack=p["starting_stack"],
            ending_stack=p["ending_stack"],
            hole_cards=json.dumps(p.get("hole_cards", [])),
            is_human=p.get("is_human", False),
        )
        db.add(ps)

    for i, a in enumerate(actions):
        ar = ActionRecord(
            hand_id=hand.id,
            player_id=a["player_id"],
            street=a["street"],
            action_type=a["action_type"],
            amount=a.get("amount", 0),
            sequence=i,
        )
        db.add(ar)

    db.commit()
    return hand


def save_analysis(
    db: Session,
    hand_id: int,
    results: list[dict],
) -> list[AnalysisRecord]:
    records = []
    for i, r in enumerate(results):
        ar = AnalysisRecord(
            hand_id=hand_id,
            action_id=r.get("action_id"),
            player_id=r["player_id"],
            street=r["street"],
            equity_at_decision=r["equity"],
            optimal_action=r.get("optimal_action"),
            ev_of_action=r.get("ev_of_action"),
            score=r["score"],
            sequence=i,
        )
        db.add(ar)
        records.append(ar)
    db.commit()
    return records


def get_hand(db: Session, hand_id: int) -> HandRecord | None:
    return db.query(HandRecord).filter(HandRecord.id == hand_id).first()


def get_hands_for_session(db: Session, session_id: str) -> list[HandRecord]:
    return db.query(HandRecord).filter(HandRecord.session_id == session_id).order_by(HandRecord.hand_number).all()


def get_analysis_for_hand(db: Session, hand_id: int) -> list[AnalysisRecord]:
    return db.query(AnalysisRecord).filter(AnalysisRecord.hand_id == hand_id).order_by(AnalysisRecord.sequence).all()
