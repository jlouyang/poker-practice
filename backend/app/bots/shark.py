"""Tier 3 'Shark' bot: equity-based decisions with Monte Carlo simulation."""

from __future__ import annotations

import random

from app.analysis.equity import calculate_equity
from app.bots.interface import BotAction, BotStrategy, snap_to_bb
from app.bots.visible_state import VisibleGameState
from app.models.types import ActionType, Street


class SharkBot(BotStrategy):
    """Uses Monte Carlo equity, pot odds, and balanced bluff frequencies."""

    def __init__(self, tightness: int = 55, aggression: int = 65):
        self._tightness = max(0, min(100, tightness))
        self._aggression = max(0, min(100, aggression))
        self._bluff_frequency = min(1.0, (100 - self._tightness) * 0.003 + self._aggression * 0.002)

    @property
    def name(self) -> str:
        return "Shark"

    @property
    def tier(self) -> int:
        return 3

    def decide(self, state: VisibleGameState) -> BotAction:
        equity = calculate_equity(
            hole_cards=state.my_hole_cards,
            community_cards=state.community_cards,
            num_opponents=max(1, state.num_active_players - 1),
            num_simulations=1500,
        )

        # Add noise to prevent exploitability (+-5%)
        equity += random.uniform(-0.05, 0.05)
        equity = max(0.0, min(1.0, equity))

        to_call = state.to_call
        pot = state.pot_total

        if to_call == 0:
            return self._decide_no_bet(state, equity, pot)
        return self._decide_facing_bet(state, equity, pot, to_call)

    def _decide_no_bet(self, state: VisibleGameState, equity: float, pot: int) -> BotAction:
        bb = state.big_blind
        if equity > 0.65:
            bet_size = self._size_bet(pot, equity, state)
            return BotAction(ActionType.BET, bet_size)

        if equity > 0.45 and random.random() < self._aggression / 200:
            bet_size = snap_to_bb(int(pot * 0.4), bb, bb)
            bet_size = min(bet_size, state.my_stack)
            return BotAction(ActionType.BET, bet_size)

        if equity < 0.35 and random.random() < self._bluff_frequency and state.street in (Street.TURN, Street.RIVER):
            bet_size = snap_to_bb(int(pot * 0.6), bb, bb)
            bet_size = min(bet_size, state.my_stack)
            return BotAction(ActionType.BET, bet_size)

        return BotAction(ActionType.CHECK)

    def _decide_facing_bet(self, state: VisibleGameState, equity: float, pot: int, to_call: int) -> BotAction:
        bb = state.big_blind
        pot_odds = to_call / max(pot + to_call, 1)

        if equity > pot_odds * 1.2 + 0.15:
            raise_amount = to_call + self._size_bet(pot + to_call, equity, state)
            raise_amount = min(raise_amount, state.my_stack)
            return BotAction(ActionType.RAISE, raise_amount)

        if equity > pot_odds:
            if to_call >= state.my_stack:
                return BotAction(ActionType.ALL_IN, state.my_stack)
            return BotAction(ActionType.CALL, min(to_call, state.my_stack))

        if (
            equity > pot_odds * 0.7
            and random.random() < self._bluff_frequency
            and state.street in (Street.FLOP, Street.TURN)
        ):
            raise_amount = snap_to_bb(to_call + max(bb * 3, int(pot * 0.5)), bb, to_call + bb)
            raise_amount = min(raise_amount, state.my_stack)
            return BotAction(ActionType.RAISE, raise_amount)

        if equity > pot_odds * 0.8 and state.street != Street.RIVER:
            return BotAction(ActionType.CALL, min(to_call, state.my_stack))

        return BotAction(ActionType.FOLD)

    def _size_bet(self, pot: int, equity: float, state: VisibleGameState) -> int:
        """Size bets proportional to hand strength and pot, snapped to BB."""
        bb = state.big_blind
        if equity > 0.85:
            fraction = 0.75 + random.uniform(0, 0.25)
        elif equity > 0.7:
            fraction = 0.5 + random.uniform(0, 0.25)
        else:
            fraction = 0.33 + random.uniform(0, 0.17)

        bet = snap_to_bb(int(pot * fraction), bb, bb)
        return min(bet, state.my_stack)
