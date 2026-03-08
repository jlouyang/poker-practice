"""Hand analysis service.

Replays a completed hand to score each human decision. Extracted from
GameSession so the replay logic can be tested independently.

Uses the same range-based equity as the live hint when opponent actions
are available, so in-game hints and hand review are consistent.
"""

from __future__ import annotations

import logging

from app.analysis.equity import calculate_equity, calculate_equity_vs_range_detailed
from app.analysis.range_engine import infer_range_pct, range_pct_to_hand_labels
from app.analysis.scoring import score_decision
from app.db.models import get_session_factory
from app.db.repository import save_analysis
from app.engine.game_state import GameState
from app.models.types import ActionType

logger = logging.getLogger(__name__)


def _community_for_street(community: list, street: str) -> list:
    if street == "preflop":
        return []
    if street == "flop":
        return community[:3]
    if street == "turn":
        return community[:4]
    return community[:5]


def analyze_hand(
    state: GameState,
    human_id: str,
    starting_stacks: dict[str, int],
) -> list[dict] | None:
    """Replay action history and score each human decision.

    Returns a list of score result dicts, or None if analysis isn't possible.
    """
    try:
        human_player = state.get_player(human_id)
    except ValueError:
        return None
    if not human_player.hole_cards:
        return None

    all_actions = state.action_history
    if not all_actions:
        return None

    pot = 0
    current_bets: dict[str, int] = {}
    active_players: set[str] = {p.player_id for p in state.players if starting_stacks.get(p.player_id, 0) > 0}
    current_street = "preflop"
    community = list(state.community_cards)

    results = []
    for i, action in enumerate(all_actions):
        pid = action.player_id
        street = action.street.value

        if street != current_street:
            pot += sum(current_bets.values())
            current_bets = {}
            current_street = street

        if pid == human_id and action.action_type != ActionType.POST_BLIND:
            bet_to_match = max(current_bets.values()) if current_bets else 0
            human_bet_so_far = current_bets.get(human_id, 0)
            to_call = max(0, bet_to_match - human_bet_so_far)
            pot_at_decision = pot + sum(current_bets.values())
            num_opp = max(1, len(active_players) - 1)

            # Use range-based equity when we have aggressor actions (same as live hint)
            equity_override = None
            equity_details_override = None
            equity_vs_random = None
            opponents_here = [pid for pid in active_players if pid != human_id]
            aggressor_id = max(opponents_here, key=lambda pid: current_bets.get(pid, 0), default=None) if opponents_here else None
            if aggressor_id:
                actions_before_this = all_actions[:i]
                opponent_actions = [a for a in actions_before_this if a.player_id == aggressor_id]
                range_pct, _ = infer_range_pct(opponent_actions, action.street)
                if 0 < range_pct < 100 and opponent_actions:
                    range_labels = range_pct_to_hand_labels(range_pct)
                    eq_data = calculate_equity_vs_range_detailed(
                        human_player.hole_cards,
                        _community_for_street(community, street),
                        range_labels,
                        num_simulations=1000,
                    )
                    equity_override = eq_data["equity"]
                    equity_details_override = eq_data
                    equity_vs_random = calculate_equity(
                        human_player.hole_cards,
                        _community_for_street(community, street),
                        num_opponents=num_opp,
                        num_simulations=1000,
                    )

            score_result = score_decision(
                hole_cards=human_player.hole_cards,
                community_cards=_community_for_street(community, street),
                action_type=action.action_type,
                amount=action.amount,
                pot_before_action=pot_at_decision,
                to_call=to_call,
                num_opponents=num_opp,
                include_details=True,
                equity_override=equity_override,
                equity_details_override=equity_details_override,
            )
            score_result["player_id"] = pid
            score_result["street"] = street
            score_result["action_type"] = action.action_type.value
            if equity_vs_random is not None:
                score_result["equity_vs_random"] = round(equity_vs_random, 3)
            results.append(score_result)

        if action.action_type == ActionType.FOLD:
            active_players.discard(pid)
        elif action.action_type in (
            ActionType.POST_BLIND,
            ActionType.CALL,
            ActionType.BET,
            ActionType.RAISE,
            ActionType.ALL_IN,
        ):
            current_bets[pid] = current_bets.get(pid, 0) + action.amount

    return results or None


def run_analysis(
    hand_id: int | None,
    state: GameState,
    human_id: str,
    starting_stacks: dict[str, int],
) -> list[dict] | None:
    """Analyze a hand and persist results to the database.

    Returns the analysis results list, or None on error.
    """
    if hand_id is None:
        return None

    try:
        results = analyze_hand(state, human_id, starting_stacks)
        if not results:
            return None

        db_factory = get_session_factory()
        db = db_factory()
        try:
            save_analysis(db, hand_id, results)
        finally:
            db.close()

        return results
    except Exception as e:
        logger.error("Error running analysis: %s", e, exc_info=True)
        return None
