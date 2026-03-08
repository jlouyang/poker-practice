"""Tier 1 'Fish' bot: loose-passive, calls too much, rarely bluffs."""

from __future__ import annotations

import random

from app.bots.interface import BotAction, BotStrategy, snap_to_bb
from app.bots.visible_state import VisibleGameState
from app.models.types import ActionType


class FishBot(BotStrategy):
    def __init__(self, tightness: int = 20, aggression: int = 20):
        self._tightness = max(0, min(100, tightness))
        self._aggression = max(0, min(100, aggression))

    @property
    def name(self) -> str:
        return "Fish"

    @property
    def tier(self) -> int:
        return 1

    def decide(self, state: VisibleGameState) -> BotAction:
        to_call = state.to_call

        if to_call == 0:
            return self._decide_no_bet(state)
        return self._decide_facing_bet(state)

    def _decide_no_bet(self, state: VisibleGameState) -> BotAction:
        bb = state.big_blind
        if random.random() * 100 < self._aggression:
            bet_size = snap_to_bb(max(bb, state.pot_total // 4), bb, bb)
            bet_size = min(bet_size, state.my_stack)
            if bet_size > 0:
                return BotAction(ActionType.BET, bet_size)
        return BotAction(ActionType.CHECK)

    def _decide_facing_bet(self, state: VisibleGameState) -> BotAction:
        bb = state.big_blind
        to_call = state.to_call

        if to_call > state.my_stack:
            if random.random() * 100 > self._tightness:
                return BotAction(ActionType.ALL_IN, state.my_stack)
            return BotAction(ActionType.FOLD)

        fold_chance = self._tightness * 0.4
        if random.random() * 100 < fold_chance:
            return BotAction(ActionType.FOLD)

        if random.random() * 100 < self._aggression * 0.3:
            raise_amount = snap_to_bb(to_call + max(bb, state.pot_total // 4), bb, to_call + bb)
            raise_amount = min(raise_amount, state.my_stack)
            return BotAction(ActionType.RAISE, raise_amount)

        return BotAction(ActionType.CALL, to_call)
