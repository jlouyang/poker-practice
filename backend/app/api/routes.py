import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.api.schemas import CreateGameRequest, CreateGameResponse
from app.api.session import create_game_session, get_session
from app.bots.profiles import get_all_profiles
from app.bots.llm_coach import LLMCoachBot
from app.analysis.ai_review import generate_session_review
from app.db.models import get_session_factory
from app.db.repository import get_hand, get_hands_for_session, get_analysis_for_hand

router = APIRouter()
_db_factory = get_session_factory()


@router.post("/game/create", response_model=CreateGameResponse)
async def create_game(req: CreateGameRequest):
    bot_configs = [{"seat": bc.seat, "profile": bc.profile} for bc in req.bot_configs]

    session = create_game_session(
        num_players=req.num_players,
        starting_stack=req.starting_stack,
        small_blind=req.small_blind,
        big_blind=req.big_blind,
        bot_configs=bot_configs if bot_configs else None,
    )

    return CreateGameResponse(
        game_id=session.game_id,
        player_seat=session.human_seat,
        num_players=req.num_players,
    )


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
async def get_hand_analysis(hand_id: int):
    db = _db_factory()
    try:
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
    finally:
        db.close()


@router.get("/session/{session_id}/hands")
async def get_session_hands(session_id: str):
    db = _db_factory()
    try:
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
    finally:
        db.close()


@router.get("/hand/{hand_id}/replay")
async def get_hand_replay(hand_id: int):
    """Get full hand data for step-by-step replay."""
    db = _db_factory()
    try:
        hand = get_hand(db, hand_id)
        if not hand:
            raise HTTPException(404, "Hand not found")

        from app.db.models import ActionRecord, PlayerStateRecord
        actions = (
            db.query(ActionRecord)
            .filter(ActionRecord.hand_id == hand_id)
            .order_by(ActionRecord.sequence)
            .all()
        )
        player_states = (
            db.query(PlayerStateRecord)
            .filter(PlayerStateRecord.hand_id == hand_id)
            .all()
        )
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
    finally:
        db.close()


@router.get("/session/{session_id}/summary")
async def get_session_summary(session_id: str):
    """Session summary: aggregate stats."""
    session = get_session(session_id)
    db = _db_factory()
    try:
        hands = get_hands_for_session(db, session_id)
        if not hands:
            raise HTTPException(404, "Session not found")

        total_hands = len(hands)
        human_wins = 0
        biggest_pot = 0
        total_won = 0
        total_lost = 0
        mistake_count = 0
        blunder_count = 0

        for h in hands:
            winners = json.loads(h.winner_ids)
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
    finally:
        db.close()


class CoachQuestionRequest(BaseModel):
    question: str
    game_id: str


@router.post("/coach/ask")
async def ask_coach(req: CoachQuestionRequest):
    """Post-hand Q&A with the coach bot."""
    session = get_session(req.game_id)
    if not session:
        raise HTTPException(404, "Game session not found")

    for bot in session.bots.values():
        if isinstance(bot, LLMCoachBot):
            answer = bot.ask_about_hand(req.question)
            return {"answer": answer}

    return {"answer": "No coach bot in this game session. Add a Coach bot to use this feature."}


@router.get("/session/{session_id}/review")
async def get_session_review(session_id: str):
    """Generate an AI coaching review of the session."""
    session = get_session(session_id)
    db = _db_factory()
    try:
        hands = get_hands_for_session(db, session_id)
        if not hands:
            raise HTTPException(404, "Session not found")

        total_hands = len(hands)
        human_wins = sum(1 for h in hands if "human" in json.loads(h.winner_ids))
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
                    sample_decisions.append({
                        "street": a.street,
                        "equity": a.equity_at_decision,
                        "score": a.score,
                    })

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
    finally:
        db.close()
