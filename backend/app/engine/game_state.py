from __future__ import annotations

from dataclasses import dataclass, field

from app.models.card import Card
from app.models.types import ActionType, Street


@dataclass
class PlayerAction:
    player_id: str
    action_type: ActionType
    amount: int = 0
    street: Street = Street.PREFLOP


@dataclass
class PlayerState:
    player_id: str
    seat: int
    stack: int
    hole_cards: list[Card] = field(default_factory=list)
    is_active: bool = True
    is_all_in: bool = False
    current_bet: int = 0
    has_acted: bool = False
    is_human: bool = False

    @property
    def can_act(self) -> bool:
        return self.is_active and not self.is_all_in


@dataclass
class Pot:
    amount: int = 0
    eligible_players: list[str] = field(default_factory=list)


@dataclass
class GameState:
    players: list[PlayerState] = field(default_factory=list)
    community_cards: list[Card] = field(default_factory=list)
    pots: list[Pot] = field(default_factory=list)
    street: Street = Street.PREFLOP
    dealer_seat: int = 0
    current_player_idx: int = 0
    small_blind: int = 1
    big_blind: int = 2
    min_raise: int = 0
    last_raise_size: int = 0
    last_raiser_idx: int | None = None
    action_history: list[PlayerAction] = field(default_factory=list)
    events: list[dict] = field(default_factory=list)
    hand_number: int = 0
    is_complete: bool = False

    @property
    def current_player(self) -> PlayerState | None:
        if self.is_complete:
            return None
        if 0 <= self.current_player_idx < len(self.players):
            return self.players[self.current_player_idx]
        return None

    @property
    def active_players(self) -> list[PlayerState]:
        return [p for p in self.players if p.is_active]

    @property
    def players_who_can_act(self) -> list[PlayerState]:
        return [p for p in self.players if p.can_act]

    @property
    def total_pot(self) -> int:
        return sum(p.amount for p in self.pots) + sum(p.current_bet for p in self.players)

    @property
    def current_bet_to_match(self) -> int:
        if not self.players:
            return 0
        return max(p.current_bet for p in self.players)
