"""Information-filtered game state that bots receive for decision-making.

VisibleGameState hides opponent hole cards and exposes only what a player
at the table could legitimately see: their own cards, community cards, pot,
stacks, bets, action history, and opponent presence.

make_visible_state(game_state, player_id) constructs the filtered view.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.engine.game_state import GameState, PlayerAction
from app.models.card import Card
from app.models.types import Street


@dataclass
class OpponentInfo:
    player_id: str
    seat: int
    stack: int
    current_bet: int
    is_active: bool
    is_all_in: bool


@dataclass
class VisibleGameState:
    """Game state filtered to what a specific player can see."""

    my_id: str
    my_seat: int
    my_stack: int
    my_hole_cards: list[Card]
    my_current_bet: int
    community_cards: list[Card]
    pot_total: int
    current_bet_to_match: int
    street: Street
    dealer_seat: int
    is_my_turn: bool
    opponents: list[OpponentInfo]
    action_history: list[PlayerAction]
    small_blind: int
    big_blind: int
    num_active_players: int

    @property
    def to_call(self) -> int:
        return max(0, self.current_bet_to_match - self.my_current_bet)


def make_visible_state(game_state: GameState, player_id: str) -> VisibleGameState:
    """Create a view of the game state visible to a specific player."""
    player = game_state.get_player(player_id)

    opponents = [
        OpponentInfo(
            player_id=p.player_id,
            seat=p.seat,
            stack=p.stack,
            current_bet=p.current_bet,
            is_active=p.is_active,
            is_all_in=p.is_all_in,
        )
        for p in game_state.players
        if p.player_id != player_id
    ]

    current = game_state.current_player
    is_my_turn = current is not None and current.player_id == player_id

    return VisibleGameState(
        my_id=player.player_id,
        my_seat=player.seat,
        my_stack=player.stack,
        my_hole_cards=list(player.hole_cards),
        my_current_bet=player.current_bet,
        community_cards=list(game_state.community_cards),
        pot_total=game_state.total_pot,
        current_bet_to_match=game_state.current_bet_to_match,
        street=game_state.street,
        dealer_seat=game_state.dealer_seat,
        is_my_turn=is_my_turn,
        opponents=opponents,
        action_history=list(game_state.action_history),
        small_blind=game_state.small_blind,
        big_blind=game_state.big_blind,
        num_active_players=len(game_state.active_players),
    )
