"""Expected Value (EV) calculation for decision points."""

from __future__ import annotations

from app.analysis.equity import calculate_equity
from app.models.card import Card
from app.models.types import ActionType

# Rough baseline for how often a bet/raise induces a fold.
# Real fold equity depends on board texture, opponent type, bet sizing, etc.
# but 30% is a reasonable middle-ground for a simplified model.
DEFAULT_FOLD_EQUITY = 0.3


def calculate_action_ev(
    hole_cards: list[Card],
    community_cards: list[Card],
    action_type: ActionType,
    amount: int,
    pot_before: int,
    to_call: int,
    num_opponents: int,
    fold_equity: float = DEFAULT_FOLD_EQUITY,
) -> float:
    """Estimate the EV of a specific action in chips.

    Returns positive for profitable actions, negative for unprofitable.
    """
    equity = calculate_equity(hole_cards, community_cards, num_opponents, num_simulations=1000)

    if action_type == ActionType.FOLD:
        return 0.0

    if action_type in (ActionType.CHECK,):
        return equity * pot_before

    if action_type == ActionType.CALL:
        cost = min(to_call, amount) if amount > 0 else to_call
        ev = equity * (pot_before + cost) - (1 - equity) * cost
        return ev

    if action_type in (ActionType.BET, ActionType.RAISE, ActionType.ALL_IN):
        call_ev = equity * (pot_before + amount) - (1 - equity) * amount
        fold_ev = pot_before
        ev = fold_equity * fold_ev + (1 - fold_equity) * call_ev
        return ev

    return 0.0
