"""Pydantic schemas for API requests/responses and WebSocket messages."""

from __future__ import annotations

from pydantic import BaseModel, Field


class BotConfig(BaseModel):
    seat: int
    profile: str = "tag_basic"


class CreateGameRequest(BaseModel):
    num_players: int = Field(ge=2, le=9, default=6)
    starting_stack: int = Field(gt=0, default=1000)
    small_blind: int = Field(gt=0, default=5)
    big_blind: int = Field(gt=0, default=10)
    bot_configs: list[BotConfig] = Field(default_factory=list)


class CreateGameResponse(BaseModel):
    game_id: str
    player_seat: int
    num_players: int


class PlayerInfo(BaseModel):
    player_id: str
    seat: int
    stack: int
    current_bet: int
    is_active: bool
    is_all_in: bool
    is_human: bool
    hole_cards: list[str] | None = None


class LegalActionInfo(BaseModel):
    action_type: str
    min_amount: int = 0
    max_amount: int = 0


class GameStateResponse(BaseModel):
    hand_number: int
    street: str
    pot: int
    community_cards: list[str]
    players: list[PlayerInfo]
    current_player_id: str | None
    is_complete: bool
    legal_actions: list[LegalActionInfo] = Field(default_factory=list)


# WebSocket message types (server -> client)
class WsMessage(BaseModel):
    type: str
    data: dict = Field(default_factory=dict)


class PlayerActionRequest(BaseModel):
    action: str
    amount: int = 0
