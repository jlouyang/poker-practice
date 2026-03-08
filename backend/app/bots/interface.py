"""Abstract base class for bot strategies.

BotStrategy  — ABC that all bot tiers implement. Requires:
    decide(state) → BotAction   (choose an action given visible game state)
    name          → str         (display name)
    tier          → int         (1=Fish, 2=Regular, 3=Shark, 4=GTO/Coach)

BotAction    — the action a bot has decided to take (action_type + amount).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.bots.visible_state import VisibleGameState
from app.models.types import ActionType


@dataclass
class BotAction:
    action_type: ActionType
    amount: int = 0


def snap_to_bb(amount: int, bb: int, minimum: int = 0) -> int:
    """Round a bet/raise amount to the nearest big blind increment."""
    if bb <= 0:
        return max(minimum, amount)
    rounded = round(amount / bb) * bb
    return max(minimum, rounded)


class BotStrategy(ABC):
    """Common interface for all bot strategies."""

    @abstractmethod
    def decide(self, state: VisibleGameState) -> BotAction:
        """Given the visible game state, decide on an action."""
        ...

    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def tier(self) -> int: ...
