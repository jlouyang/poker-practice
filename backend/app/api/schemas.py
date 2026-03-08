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
    difficulty: int = Field(ge=0, le=100, default=30)
    bot_configs: list[BotConfig] = Field(default_factory=list)


class CreateGameResponse(BaseModel):
    game_id: str
    session_token: str
    player_seat: int
    num_players: int


class PlayerActionRequest(BaseModel):
    action: str
    amount: int = 0
