"""Tier 2 'Regular' bot: chart-based preflop + basic postflop heuristics."""

from __future__ import annotations

import random

from app.bots.interface import BotAction, BotStrategy
from app.bots.visible_state import VisibleGameState
from app.models.card import Card
from app.models.types import ActionType, Rank, Street

# Preflop hand strength tiers (simplified)
# Tier 1: Premium (AA, KK, QQ, AKs)
# Tier 2: Strong (JJ, TT, AQs, AKo, AQo)
# Tier 3: Playable (99-77, AJs-ATs, KQs, KQo, AJo)
# Tier 4: Speculative (66-22, suited connectors, suited aces)

_PREMIUM_PAIRS = {Rank.ACE, Rank.KING, Rank.QUEEN}
_STRONG_PAIRS = {Rank.JACK, Rank.TEN}
_MEDIUM_PAIRS = {Rank.NINE, Rank.EIGHT, Rank.SEVEN}
_SMALL_PAIRS = {Rank.SIX, Rank.FIVE, Rank.FOUR, Rank.THREE, Rank.TWO}


def _hand_tier(hole_cards: list[Card]) -> int:
    """Rate a preflop hand from 1 (best) to 5 (worst)."""
    c1, c2 = hole_cards
    r1, r2 = max(c1.rank, c2.rank), min(c1.rank, c2.rank)
    suited = c1.suit == c2.suit
    pair = r1 == r2

    if pair:
        if r1 in _PREMIUM_PAIRS:
            return 1
        if r1 in _STRONG_PAIRS:
            return 2
        if r1 in _MEDIUM_PAIRS:
            return 3
        return 4

    # AK
    if r1 == Rank.ACE and r2 == Rank.KING:
        return 1 if suited else 2
    # AQ
    if r1 == Rank.ACE and r2 == Rank.QUEEN:
        return 2
    # AJ, AT
    if r1 == Rank.ACE and r2 >= Rank.TEN:
        return 3
    # KQ
    if r1 == Rank.KING and r2 == Rank.QUEEN:
        return 2 if suited else 3
    # Suited connectors (T9s+)
    if suited and abs(r1 - r2) == 1 and r2 >= Rank.NINE:
        return 3
    # Suited aces
    if r1 == Rank.ACE and suited:
        return 4
    # Other suited connectors
    if suited and abs(r1 - r2) <= 2 and r2 >= Rank.SIX:
        return 4
    # Face cards
    if r1 >= Rank.JACK and r2 >= Rank.TEN:
        return 4

    return 5


class RegularBot(BotStrategy):
    def __init__(self, tightness: int = 60, aggression: int = 60):
        self._tightness = max(0, min(100, tightness))
        self._aggression = max(0, min(100, aggression))

    @property
    def name(self) -> str:
        return "Regular"

    @property
    def tier(self) -> int:
        return 2

    def decide(self, state: VisibleGameState) -> BotAction:
        if state.street == Street.PREFLOP:
            return self._preflop_decision(state)
        return self._postflop_decision(state)

    def _preflop_decision(self, state: VisibleGameState) -> BotAction:
        tier = _hand_tier(state.my_hole_cards)
        to_call = state.to_call

        # How tight we play: higher tightness -> fewer tiers played
        max_tier_to_play = max(1, 5 - int(self._tightness / 25))

        if tier > max_tier_to_play:
            if to_call > 0:
                return BotAction(ActionType.FOLD)
            return BotAction(ActionType.CHECK)

        if to_call == 0:
            # Raise with good hands
            if tier <= 2 or random.random() * 100 < self._aggression:
                raise_size = max(state.big_blind * 3, state.pot_total)
                raise_size = min(raise_size, state.my_stack)
                return BotAction(ActionType.BET, raise_size)
            return BotAction(ActionType.CHECK)

        # Facing a raise
        if tier == 1:
            # Re-raise premium hands
            raise_amount = to_call + max(to_call, state.pot_total)
            raise_amount = min(raise_amount, state.my_stack)
            return BotAction(ActionType.RAISE, raise_amount)

        if tier <= 2:
            # Call or sometimes re-raise
            if random.random() * 100 < self._aggression * 0.5:
                raise_amount = to_call + max(to_call, state.pot_total // 2)
                raise_amount = min(raise_amount, state.my_stack)
                return BotAction(ActionType.RAISE, raise_amount)
            return BotAction(ActionType.CALL, min(to_call, state.my_stack))

        # Tier 3-4: call smaller bets, fold to big raises
        pot_fraction = to_call / max(state.pot_total, 1)
        if pot_fraction > 0.5:
            return BotAction(ActionType.FOLD)

        return BotAction(ActionType.CALL, min(to_call, state.my_stack))

    def _postflop_decision(self, state: VisibleGameState) -> BotAction:
        to_call = state.to_call
        hand_strength = self._estimate_postflop_strength(state)

        if to_call == 0:
            if hand_strength > 0.7 or (hand_strength > 0.4 and random.random() * 100 < self._aggression):
                bet_size = int(state.pot_total * (0.5 + hand_strength * 0.5))
                bet_size = max(state.big_blind, min(bet_size, state.my_stack))
                return BotAction(ActionType.BET, bet_size)
            return BotAction(ActionType.CHECK)

        pot_odds = to_call / max(state.pot_total + to_call, 1)

        if hand_strength > pot_odds + 0.15:
            if hand_strength > 0.8 and random.random() * 100 < self._aggression:
                raise_amount = to_call + int(state.pot_total * 0.75)
                raise_amount = min(raise_amount, state.my_stack)
                return BotAction(ActionType.RAISE, raise_amount)
            return BotAction(ActionType.CALL, min(to_call, state.my_stack))

        if hand_strength > pot_odds - 0.05:
            return BotAction(ActionType.CALL, min(to_call, state.my_stack))

        return BotAction(ActionType.FOLD)

    def _estimate_postflop_strength(self, state: VisibleGameState) -> float:
        """Simple heuristic postflop hand strength estimate (0 to 1)."""
        from app.models.hand import evaluate_hand, HandResult

        if len(state.community_cards) < 3:
            return 0.5

        result = evaluate_hand(state.my_hole_cards, state.community_cards)
        rank = result.rank

        # Normalize: rank 1 = best (1.0), rank 7462 = worst (0.0)
        return 1.0 - (rank - 1) / 7461
