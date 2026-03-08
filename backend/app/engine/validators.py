"""Legal action computation and validation for No-Limit Hold'em.

get_legal_actions() — returns the set of actions available to a player
                      given the current bet, their stack, and min-raise rules.
validate_action()   — checks that a specific (action_type, amount) pair is
                      legal, returning (is_valid, error_message).

Encodes NLHE rules: must call or fold facing a bet, can't raise less than
the last raise size (or big blind), all-in replaces actions when stack is
insufficient, etc.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.engine.game_state import GameState, PlayerState
from app.models.types import ActionType


@dataclass
class LegalAction:
    action_type: ActionType
    min_amount: int = 0
    max_amount: int = 0


def get_legal_actions(state: GameState, player: PlayerState) -> list[LegalAction]:
    """Return the set of legal actions for the given player in the current state."""
    actions: list[LegalAction] = []
    bet_to_match = state.current_bet_to_match
    to_call = bet_to_match - player.current_bet

    if to_call > 0:
        actions.append(LegalAction(ActionType.FOLD))

        if to_call >= player.stack:
            actions.append(LegalAction(ActionType.ALL_IN, min_amount=player.stack, max_amount=player.stack))
        else:
            actions.append(LegalAction(ActionType.CALL, min_amount=to_call, max_amount=to_call))

            min_raise_total = bet_to_match + max(state.last_raise_size, state.big_blind)
            min_raise_amount = min_raise_total - player.current_bet

            if min_raise_amount >= player.stack:
                actions.append(LegalAction(ActionType.ALL_IN, min_amount=player.stack, max_amount=player.stack))
            else:
                max_raise = player.stack
                actions.append(LegalAction(ActionType.RAISE, min_amount=min_raise_amount, max_amount=max_raise))
    else:
        actions.append(LegalAction(ActionType.CHECK))

        if player.stack > 0:
            min_bet = min(state.big_blind, player.stack)
            if min_bet >= player.stack:
                actions.append(LegalAction(ActionType.ALL_IN, min_amount=player.stack, max_amount=player.stack))
            else:
                actions.append(LegalAction(ActionType.BET, min_amount=min_bet, max_amount=player.stack))

    return actions


def validate_action(
    state: GameState,
    player: PlayerState,
    action_type: ActionType,
    amount: int = 0,
) -> tuple[bool, str]:
    """Validate a player action. Returns (is_valid, error_message)."""
    legal = get_legal_actions(state, player)
    legal_types = {a.action_type for a in legal}

    if action_type == ActionType.ALL_IN and ActionType.ALL_IN in legal_types:
        return True, ""

    if action_type not in legal_types:
        return False, f"Action {action_type} not legal. Legal: {[a.action_type for a in legal]}"

    if action_type in (ActionType.FOLD, ActionType.CHECK):
        return True, ""

    if action_type == ActionType.CALL:
        legal_call = next(a for a in legal if a.action_type == ActionType.CALL)
        if amount != 0 and amount != legal_call.min_amount:
            return False, f"Call amount must be {legal_call.min_amount}"
        return True, ""

    if action_type in (ActionType.BET, ActionType.RAISE):
        legal_br = next(a for a in legal if a.action_type == action_type)
        if amount < legal_br.min_amount:
            return False, f"Min {action_type} is {legal_br.min_amount}, got {amount}"
        if amount > legal_br.max_amount:
            return False, f"Max {action_type} is {legal_br.max_amount}, got {amount}"
        return True, ""

    return True, ""
