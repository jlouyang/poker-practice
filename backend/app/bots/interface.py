from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.bots.visible_state import VisibleGameState
from app.models.types import ActionType


@dataclass
class BotAction:
    action_type: ActionType
    amount: int = 0


class BotStrategy(ABC):
    """Common interface for all bot strategies."""

    @abstractmethod
    def decide(self, state: VisibleGameState) -> BotAction:
        """Given the visible game state, decide on an action."""
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @property
    @abstractmethod
    def tier(self) -> int:
        ...
