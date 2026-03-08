"""Hand history persistence service.

Extracts hand-saving logic from GameSession so it can be tested and
maintained independently.
"""

from __future__ import annotations

import logging

from app.db.models import get_session_factory
from app.db.repository import save_hand
from app.engine.game_state import GameState

logger = logging.getLogger(__name__)


def extract_winner_ids(state: GameState) -> list[str]:
    """Extract winner IDs from game state events."""
    winner_ids: list[str] = []
    for e in state.events:
        if e["type"] == "showdown" and "winners" in e["data"]:
            winner_ids = list(e["data"]["winners"].keys())
        elif e["type"] == "win_uncontested":
            winner_ids = [e["data"]["player_id"]]
    return winner_ids


def extract_winnings(state: GameState) -> dict[str, int]:
    """Extract per-player winnings from game state events."""
    winnings: dict[str, int] = {}
    for e in state.events:
        if e["type"] == "showdown" and "winners" in e["data"]:
            for pid, info in e["data"]["winners"].items():
                winnings[pid] = info["amount"]
        elif e["type"] == "win_uncontested":
            winnings[e["data"]["player_id"]] = e["data"]["amount"]
    return winnings


def save_hand_history(
    game_id: str,
    state: GameState,
    starting_stacks: dict[str, int],
) -> int | None:
    """Save a completed hand to the database. Returns the hand DB id or None on error."""
    db_factory = get_session_factory()
    db = db_factory()
    try:
        winner_ids = extract_winner_ids(state)

        players = [
            {
                "player_id": p.player_id,
                "seat": p.seat,
                "starting_stack": starting_stacks.get(p.player_id, p.stack),
                "ending_stack": p.stack,
                "hole_cards": [str(c) for c in p.hole_cards] if p.hole_cards else [],
                "is_human": p.is_human,
            }
            for p in state.players
        ]

        actions = [
            {
                "player_id": a.player_id,
                "street": a.street.value,
                "action_type": a.action_type.value,
                "amount": a.amount,
            }
            for a in state.action_history
        ]

        hand = save_hand(
            db=db,
            session_id=game_id,
            hand_number=state.hand_number,
            dealer_seat=state.dealer_seat,
            small_blind=state.small_blind,
            big_blind=state.big_blind,
            community_cards=[str(c) for c in state.community_cards],
            pot_size=state.total_pot,
            winner_ids=winner_ids,
            players=players,
            actions=actions,
        )
        return hand.id
    except Exception as e:
        logger.error("Error saving hand history: %s", e, exc_info=True)
        return None
    finally:
        db.close()
