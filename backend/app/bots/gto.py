"""Tier 4 'GTO' bot: near-optimal play using balanced mixed strategies."""

from __future__ import annotations

import random

from app.analysis.equity import calculate_equity
from app.bots.interface import BotAction, BotStrategy, snap_to_bb
from app.bots.visible_state import VisibleGameState
from app.models.types import ActionType, Street


class GTOBot(BotStrategy):
    """Approximates GTO play through balanced equity-based strategies
    with theoretically correct bluff-to-value ratios."""

    def __init__(self, tightness: int = 60, aggression: int = 55):
        self._tightness = max(0, min(100, tightness))
        self._aggression = max(0, min(100, aggression))

    @property
    def name(self) -> str:
        return "GTO"

    @property
    def tier(self) -> int:
        return 4

    def decide(self, state: VisibleGameState) -> BotAction:
        equity = calculate_equity(
            hole_cards=state.my_hole_cards,
            community_cards=state.community_cards,
            num_opponents=max(1, state.num_active_players - 1),
            num_simulations=2000,
        )

        to_call = state.to_call
        pot = state.pot_total

        if to_call == 0:
            return self._decide_as_aggressor(state, equity, pot)
        return self._decide_facing_bet(state, equity, pot, to_call)

    def _decide_as_aggressor(self, state: VisibleGameState, equity: float, pot: int) -> BotAction:
        bb = state.big_blind

        if equity > 0.75:
            if random.random() < 0.7:
                bet = snap_to_bb(int(pot * 0.75), bb, bb)
                return BotAction(ActionType.BET, min(bet, state.my_stack))
            return BotAction(ActionType.CHECK)

        if equity > 0.55:
            if random.random() < 0.5:
                bet = snap_to_bb(int(pot * 0.33), bb, bb)
                return BotAction(ActionType.BET, min(bet, state.my_stack))
            return BotAction(ActionType.CHECK)

        bluff_threshold = self._get_bluff_threshold(state)
        if equity < 0.25 and random.random() < bluff_threshold:
            bet = snap_to_bb(int(pot * 0.66), bb, bb)
            return BotAction(ActionType.BET, min(bet, state.my_stack))

        return BotAction(ActionType.CHECK)

    def _decide_facing_bet(self, state: VisibleGameState, equity: float, pot: int, to_call: int) -> BotAction:
        bb = state.big_blind
        pot_odds = to_call / max(pot + to_call, 1)
        mdf = pot / max(pot + to_call, 1)

        if equity > pot_odds + 0.25:
            raise_freq = min(0.3, (equity - pot_odds) * 0.8)
            if random.random() < raise_freq:
                raise_amount = to_call + self._gto_raise_size(pot, to_call, state)
                raise_amount = min(raise_amount, state.my_stack)
                return BotAction(ActionType.RAISE, raise_amount)
            return BotAction(ActionType.CALL, min(to_call, state.my_stack))

        if equity > pot_odds:
            return BotAction(ActionType.CALL, min(to_call, state.my_stack))

        bluff_raise_freq = self._get_bluff_threshold(state) * 0.5
        if equity > pot_odds * 0.5 and random.random() < bluff_raise_freq and state.street != Street.RIVER:
            raise_amount = snap_to_bb(to_call + int(pot * 0.75), bb, to_call + bb)
            raise_amount = min(raise_amount, state.my_stack)
            return BotAction(ActionType.RAISE, raise_amount)

        if random.random() < mdf and equity > pot_odds * 0.6:
            return BotAction(ActionType.CALL, min(to_call, state.my_stack))

        return BotAction(ActionType.FOLD)

    def _get_bluff_threshold(self, state: VisibleGameState) -> float:
        """Calculate optimal bluff frequency based on street and bet sizing."""
        base = 0.25
        if state.street == Street.RIVER:
            base = 0.15  # Bluff less on river
        elif state.street == Street.PREFLOP:
            base = 0.10
        return base

    def _gto_raise_size(self, pot: int, to_call: int, state: VisibleGameState) -> int:
        """Choose a GTO-appropriate raise size, snapped to BB."""
        bb = state.big_blind
        sizes = [
            snap_to_bb(int(pot * 0.33), bb, bb),
            snap_to_bb(int(pot * 0.66), bb, bb),
            snap_to_bb(pot, bb, bb),
        ]
        return random.choice(sizes)
