"""Bot profile definitions and the preset bot roster.

BotProfile  — immutable config (name, tier, tightness, aggression, description).
              Its create_bot() factory method dispatches to the correct tier class.
              When creating a bot, tightness and aggression get a small random
              variance so the same preset plays slightly differently each game.

PRESET_PROFILES — dictionary of all built-in bot profiles, keyed by slug.
                  Used by the session manager to populate tables based on difficulty.

Profiles are selected at game creation time via _pick_bots_for_difficulty()
in session.py, which uses weighted random sampling across tiers.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

# Random variance applied to tightness/aggression when creating a bot (e.g. ±8 → 55 becomes 47–63).
# Keeps the preset's identity while making the same bot feel less robotic across sessions.
PERSONALITY_VARIANCE = 8

from app.bots.fish import FishBot
from app.bots.gto import GTOBot
from app.bots.interface import BotStrategy
from app.bots.llm_coach import LLMCoachBot
from app.bots.regular import RegularBot
from app.bots.shark import SharkBot


@dataclass(frozen=True)
class BotProfile:
    name: str
    tier: int
    tightness: int
    aggression: int
    description: str

    def create_bot(self) -> BotStrategy:
        t = max(0, min(100, self.tightness + random.randint(-PERSONALITY_VARIANCE, PERSONALITY_VARIANCE)))
        a = max(0, min(100, self.aggression + random.randint(-PERSONALITY_VARIANCE, PERSONALITY_VARIANCE)))
        if self.tier == 1:
            return FishBot(tightness=t, aggression=a)
        if self.tier == 2:
            return RegularBot(tightness=t, aggression=a)
        if self.tier == 3:
            return SharkBot(tightness=t, aggression=a)
        if self.tier == 4:
            if self.name.startswith("Coach"):
                return LLMCoachBot(tightness=t, aggression=a)
            return GTOBot(tightness=t, aggression=a)
        raise ValueError(f"Unknown tier: {self.tier}")


PRESET_PROFILES: dict[str, BotProfile] = {
    "calling_station": BotProfile(
        name="Calling Station Carl",
        tier=1,
        tightness=10,
        aggression=10,
        description="Calls almost everything, rarely raises or folds.",
    ),
    "passive_fish": BotProfile(
        name="Passive Pete",
        tier=1,
        tightness=30,
        aggression=15,
        description="Plays too many hands but slightly more selective than a pure calling station.",
    ),
    "maniac_fish": BotProfile(
        name="Maniac Mike",
        tier=1,
        tightness=15,
        aggression=80,
        description="Plays lots of hands and bets/raises wildly. Loose-aggressive but with no strategy.",
    ),
    "tight_passive": BotProfile(
        name="Nitty Nancy",
        tier=2,
        tightness=85,
        aggression=30,
        description="Only plays premium hands, rarely bets without the nuts. A 'nit'.",
    ),
    "tag_basic": BotProfile(
        name="TAG Tommy",
        tier=2,
        tightness=60,
        aggression=60,
        description="Solid tight-aggressive fundamentals. Plays a reasonable range with balanced aggression.",
    ),
    "lag_regular": BotProfile(
        name="LAG Larry",
        tier=2,
        tightness=40,
        aggression=75,
        description="Loose-aggressive regular. Plays more hands and applies constant pressure.",
    ),
    "shark_balanced": BotProfile(
        name="Shark Steve",
        tier=3,
        tightness=55,
        aggression=65,
        description="Equity-based decisions with Monte Carlo simulation. Balanced and tough.",
    ),
    "shark_aggressive": BotProfile(
        name="Shark Samantha",
        tier=3,
        tightness=45,
        aggression=80,
        description="Aggressive shark. Uses equity calculations with high bluff frequency.",
    ),
    "shark_tight": BotProfile(
        name="Shark Simon",
        tier=3,
        tightness=70,
        aggression=55,
        description="Tight shark. Waits for strong hands and maximizes value.",
    ),
    "gto_balanced": BotProfile(
        name="GTO Greg",
        tier=4,
        tightness=60,
        aggression=55,
        description="Near-optimal GTO play with balanced bet/bluff ratios.",
    ),
    "coach": BotProfile(
        name="Coach Claude",
        tier=4,
        tightness=55,
        aggression=60,
        description="AI coach that explains decisions. Ask questions after each hand.",
    ),
}


def get_profile(name: str) -> BotProfile:
    if name not in PRESET_PROFILES:
        raise ValueError(f"Unknown profile: {name}. Available: {list(PRESET_PROFILES.keys())}")
    return PRESET_PROFILES[name]


def get_all_profiles() -> list[BotProfile]:
    return list(PRESET_PROFILES.values())
