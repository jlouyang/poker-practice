"""Tier 4 'GTO' bot: near-optimal play using balanced mixed strategies."""

from __future__ import annotations

import random

from app.analysis.equity import calculate_equity
from app.bots.interface import BotAction, BotStrategy
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
            num_opponents=state.num_active_players - 1,
            num_simulations=2000,
        )

        to_call = state.to_call
        pot = state.pot_total

        if to_call == 0:
            return self._decide_as_aggressor(state, equity, pot)
        return self._decide_facing_bet(state, equity, pot, to_call)

    def _decide_as_aggressor(
        self, state: VisibleGameState, equity: float, pot: int
    ) -> BotAction:
        # GTO bet sizing: choose between 33%, 66%, and pot-size bets
        # with balanced value/bluff ratios at each sizing

        if equity > 0.75:
            # Strong value: bet large
            if random.random() < 0.7:
                bet = max(state.big_blind, int(pot * 0.75))
                return BotAction(ActionType.BET, min(bet, state.my_stack))
            # Slow-play some strong hands for balance
            return BotAction(ActionType.CHECK)

        if equity > 0.55:
            # Medium strength: bet small or check
            if random.random() < 0.5:
                bet = max(state.big_blind, int(pot * 0.33))
                return BotAction(ActionType.BET, min(bet, state.my_stack))
            return BotAction(ActionType.CHECK)

        # Bluff range: bet with ~optimal frequency
        # MDF (minimum defense frequency) logic:
        # If betting pot-size, opponent must defend 50%
        # So bluff frequency should be ~33% of betting range
        bluff_threshold = self._get_bluff_threshold(state)
        if equity < 0.25 and random.random() < bluff_threshold:
            bet = max(state.big_blind, int(pot * 0.66))
            return BotAction(ActionType.BET, min(bet, state.my_stack))

        return BotAction(ActionType.CHECK)

    def _decide_facing_bet(
        self, state: VisibleGameState, equity: float, pot: int, to_call: int
    ) -> BotAction:
        pot_odds = to_call / max(pot + to_call, 1)

        # Alpha = 1 - MDF. If villain bets B into P, MDF = P/(P+B)
        mdf = pot / max(pot + to_call, 1)

        # Strong hands: raise for value with balanced frequency
        if equity > pot_odds + 0.25:
            raise_freq = min(0.3, (equity - pot_odds) * 0.8)
            if random.random() < raise_freq:
                raise_amount = to_call + self._gto_raise_size(pot, to_call, state)
                raise_amount = min(raise_amount, state.my_stack)
                return BotAction(ActionType.RAISE, raise_amount)
            return BotAction(ActionType.CALL, min(to_call, state.my_stack))

        # Profitable call based on pot odds
        if equity > pot_odds:
            return BotAction(ActionType.CALL, min(to_call, state.my_stack))

        # Bluff-raise at balanced frequency
        bluff_raise_freq = self._get_bluff_threshold(state) * 0.5
        if (
            equity > pot_odds * 0.5
            and random.random() < bluff_raise_freq
            and state.street != Street.RIVER
        ):
            raise_amount = to_call + int(pot * 0.75)
            raise_amount = min(raise_amount, state.my_stack)
            return BotAction(ActionType.RAISE, raise_amount)

        # Defend at MDF to prevent exploitation
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

    def _gto_raise_size(
        self, pot: int, to_call: int, state: VisibleGameState
    ) -> int:
        """Choose a GTO-appropriate raise size."""
        sizes = [
            int(pot * 0.33),
            int(pot * 0.66),
            pot,
        ]
        # Randomly pick from standard GTO sizing options
        chosen = random.choice(sizes)
        return max(state.big_blind, chosen)
