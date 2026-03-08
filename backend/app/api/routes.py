"""REST API routes for the Poker Training Engine.

Endpoints:
  POST /game/create          — create a new game session
  GET  /game/{id}/hint       — get equity-based action recommendation
  GET  /profiles             — list available bot profiles
  GET  /hand/{id}/analysis   — get scored analysis for a hand
  GET  /hand/{id}/replay     — get full hand data for step-by-step replay
  GET  /session/{id}/hands   — list all hands in a session
  GET  /session/{id}/summary — aggregate session statistics
  GET  /session/{id}/review  — AI-generated coaching review
  POST /coach/ask            — post-hand Q&A with coach bot
"""

import json
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.analysis.ai_review import generate_session_review
from app.api.schemas import CreateGameRequest, CreateGameResponse
from app.api.session import SessionLimitError, create_game_session, validate_session_token
from app.bots.llm_coach import LLMCoachBot
from app.bots.profiles import get_all_profiles
from app.db.models import ActionRecord, PlayerStateRecord, get_db
from app.db.repository import get_analysis_for_hand, get_hand, get_hands_for_session

logger = logging.getLogger(__name__)

router = APIRouter()

from app.api.rate_limit import limiter


def _require_session(game_id: str, x_session_token: str):
    """Validate the session token and return the session, or raise 403."""
    session = validate_session_token(game_id, x_session_token)
    if session is None:
        raise HTTPException(403, "Invalid or missing session token")
    return session


@router.post("/game/create", response_model=CreateGameResponse)
@limiter.limit("10/minute")
async def create_game(request: Request, req: CreateGameRequest):
    bot_configs = [{"seat": bc.seat, "profile": bc.profile} for bc in req.bot_configs]

    try:
        session = create_game_session(
            num_players=req.num_players,
            starting_stack=req.starting_stack,
            small_blind=req.small_blind,
            big_blind=req.big_blind,
            difficulty=req.difficulty,
            bot_configs=bot_configs if bot_configs else None,
        )
    except SessionLimitError:
        raise HTTPException(503, "Server at capacity — try again later") from None

    return CreateGameResponse(
        game_id=session.game_id,
        session_token=session.session_token,
        player_seat=session.human_seat,
        num_players=req.num_players,
    )


@router.get("/game/{game_id}/hint")
async def get_hint(game_id: str, x_session_token: str = Header()):
    session = _require_session(game_id, x_session_token)
    hint = session.get_hint()
    if not hint:
        raise HTTPException(400, "Not your turn or hand is complete")
    return hint


@router.get("/game/{game_id}/hand-strength")
async def get_hand_strength(game_id: str, x_session_token: str = Header()):
    session = _require_session(game_id, x_session_token)
    result = session.get_hand_strength()
    if not result:
        raise HTTPException(400, "Hand strength unavailable")
    return result


@router.get("/profiles")
async def list_profiles():
    profiles = get_all_profiles()
    return [
        {
            "name": p.name,
            "tier": p.tier,
            "tightness": p.tightness,
            "aggression": p.aggression,
            "description": p.description,
        }
        for p in profiles
    ]


@router.get("/hand/{hand_id}/analysis")
async def get_hand_analysis(hand_id: int, db: Session = Depends(get_db)):
    hand = get_hand(db, hand_id)
    if not hand:
        raise HTTPException(404, "Hand not found")

    analysis = get_analysis_for_hand(db, hand_id)
    return {
        "hand_id": hand_id,
        "hand_number": hand.hand_number,
        "community_cards": json.loads(hand.community_cards),
        "pot_size": hand.pot_size,
        "decisions": [
            {
                "player_id": a.player_id,
                "street": a.street,
                "equity": a.equity_at_decision,
                "score": a.score,
                "optimal_action": a.optimal_action,
            }
            for a in analysis
        ],
    }


@router.get("/session/{session_id}/hands")
async def get_session_hands(session_id: str, db: Session = Depends(get_db)):
    hands = get_hands_for_session(db, session_id)
    return [
        {
            "id": h.id,
            "hand_number": h.hand_number,
            "pot_size": h.pot_size,
            "winner_ids": json.loads(h.winner_ids),
        }
        for h in hands
    ]


@router.get("/hand/{hand_id}/replay")
async def get_hand_replay(hand_id: int, db: Session = Depends(get_db)):
    """Get full hand data for step-by-step replay."""
    hand = get_hand(db, hand_id)
    if not hand:
        raise HTTPException(404, "Hand not found")

    actions = db.query(ActionRecord).filter(ActionRecord.hand_id == hand_id).order_by(ActionRecord.sequence).all()
    player_states = db.query(PlayerStateRecord).filter(PlayerStateRecord.hand_id == hand_id).all()
    analysis = get_analysis_for_hand(db, hand_id)

    return {
        "hand_id": hand_id,
        "hand_number": hand.hand_number,
        "dealer_seat": hand.dealer_seat,
        "small_blind": hand.small_blind,
        "big_blind": hand.big_blind,
        "community_cards": json.loads(hand.community_cards),
        "pot_size": hand.pot_size,
        "winner_ids": json.loads(hand.winner_ids),
        "players": [
            {
                "player_id": ps.player_id,
                "seat": ps.seat,
                "starting_stack": ps.starting_stack,
                "ending_stack": ps.ending_stack,
                "hole_cards": json.loads(ps.hole_cards),
                "is_human": ps.is_human,
            }
            for ps in player_states
        ],
        "actions": [
            {
                "player_id": a.player_id,
                "street": a.street,
                "action_type": a.action_type,
                "amount": a.amount,
                "sequence": a.sequence,
            }
            for a in actions
        ],
        "analysis": [
            {
                "player_id": ar.player_id,
                "street": ar.street,
                "equity": ar.equity_at_decision,
                "score": ar.score,
            }
            for ar in analysis
        ],
    }


@router.get("/session/{session_id}/summary")
async def get_session_summary(session_id: str, x_session_token: str = Header(), db: Session = Depends(get_db)):
    """Session summary: aggregate stats."""
    session = _require_session(session_id, x_session_token)
    hands = get_hands_for_session(db, session_id)
    if not hands:
        raise HTTPException(404, "Session not found")

    total_hands = len(hands)
    human_wins = 0
    biggest_pot = 0
    mistake_count = 0
    blunder_count = 0

    for h in hands:
        try:
            winners = json.loads(h.winner_ids)
        except (json.JSONDecodeError, TypeError):
            winners = []
        if "human" in winners:
            human_wins += 1
        if h.pot_size > biggest_pot:
            biggest_pot = h.pot_size

        analysis = get_analysis_for_hand(db, h.id)
        for a in analysis:
            if a.score == "mistake":
                mistake_count += 1
            elif a.score == "blunder":
                blunder_count += 1

    stats = session.stats_tracker.get_all_stats() if session else {}

    return {
        "session_id": session_id,
        "total_hands": total_hands,
        "human_win_rate": round(human_wins / max(total_hands, 1) * 100, 1),
        "biggest_pot": biggest_pot,
        "mistakes": mistake_count,
        "blunders": blunder_count,
        "player_stats": stats,
    }


class CoachQuestionRequest(BaseModel):
    question: str = Field(max_length=2000)
    game_id: str


@router.post("/coach/ask")
@limiter.limit("5/minute")
async def ask_coach(request: Request, req: CoachQuestionRequest, x_session_token: str = Header()):
    """Post-hand Q&A with the coach bot."""
    session = _require_session(req.game_id, x_session_token)

    for bot in session.bots.values():
        if isinstance(bot, LLMCoachBot):
            answer = bot.ask_about_hand(req.question)
            return {"answer": answer}

    return {"answer": "No coach bot in this game session. Add a Coach bot to use this feature."}


@router.get("/session/{session_id}/review")
@limiter.limit("3/minute")
async def get_session_review(
    request: Request, session_id: str, x_session_token: str = Header(), db: Session = Depends(get_db)
):
    """Generate an AI coaching review of the session."""
    session = _require_session(session_id, x_session_token)
    hands = get_hands_for_session(db, session_id)
    if not hands:
        raise HTTPException(404, "Session not found")

    total_hands = len(hands)
    human_wins = 0
    for h in hands:
        try:
            winners = json.loads(h.winner_ids)
        except (json.JSONDecodeError, TypeError):
            winners = []
        if "human" in winners:
            human_wins += 1
    win_rate = human_wins / max(total_hands, 1) * 100
    mistakes = 0
    blunders = 0
    sample_decisions = []

    for h in hands:
        analysis = get_analysis_for_hand(db, h.id)
        for a in analysis:
            if a.score == "mistake":
                mistakes += 1
            elif a.score == "blunder":
                blunders += 1
            if len(sample_decisions) < 10:
                sample_decisions.append(
                    {
                        "street": a.street,
                        "equity": a.equity_at_decision,
                        "score": a.score,
                    }
                )

    stats = session.stats_tracker.get_all_stats().get("human", {}) if session else {}

    review = generate_session_review(
        total_hands=total_hands,
        win_rate=win_rate,
        mistakes=mistakes,
        blunders=blunders,
        player_stats=stats,
        sample_decisions=sample_decisions,
    )

    return {"review": review}
