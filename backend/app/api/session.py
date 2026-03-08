"""Game session manager: orchestrates game loop, bot turns, human input."""

from __future__ import annotations

import asyncio
import logging
import secrets
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

SESSION_TTL_SECONDS = 3600  # 1 hour
CLEANUP_INTERVAL_SECONDS = 300  # 5 minutes
MAX_SESSIONS = 100

from app.analysis.stats import SessionStatsTracker
from app.bots.interface import BotStrategy
from app.bots.profiles import PRESET_PROFILES, BotProfile
from app.bots.visible_state import make_visible_state
from app.engine.game import GameEngine
from app.engine.game_state import PlayerState
from app.engine.validators import get_legal_actions
from app.models.types import ActionType
from app.services.hand_analysis import run_analysis
from app.services.hand_history import extract_winner_ids, extract_winnings, save_hand_history


@dataclass
class GameSession:
    game_id: str
    session_token: str
    engine: GameEngine
    bots: dict[str, BotStrategy]
    human_id: str
    human_seat: int
    _action_queue: asyncio.Queue = field(default_factory=asyncio.Queue)
    _continue_event: asyncio.Event = field(default_factory=asyncio.Event)
    _ws_send: asyncio.Queue = field(default_factory=asyncio.Queue)
    _running: bool = False
    _last_hand_id: int | None = None
    _starting_stacks: dict[str, int] = field(default_factory=dict)
    stats_tracker: SessionStatsTracker = field(default_factory=SessionStatsTracker)
    _last_active: float = field(default_factory=time.monotonic)

    def touch(self) -> None:
        """Update last-active timestamp to prevent TTL expiry."""
        self._last_active = time.monotonic()

    @property
    def is_expired(self) -> bool:
        return (time.monotonic() - self._last_active) > SESSION_TTL_SECONDS

    async def run_game_loop(self) -> None:
        """Main game loop: start hands, process turns, repeat."""
        self._running = True

        try:
            while self._running:
                active_count = sum(1 for p in self.engine.state.players if p.stack > 0)
                if active_count < 2:
                    await self._send_ws({"type": "game_over", "data": {}})
                    break

                self.engine.start_hand()
                self._starting_stacks = {p.player_id: p.stack for p in self.engine.state.players}
                await self._send_ws(self._make_state_message("new_hand"))

                while not self.engine.state.is_complete:
                    current = self.engine.state.current_player
                    if current is None:
                        break

                    if current.player_id == self.human_id:
                        await self._handle_human_turn()
                    else:
                        await self._handle_bot_turn(current.player_id)

                    if not self.engine.state.is_complete:
                        await self._send_ws(self._make_state_message("state_update"))

                self._record_stats()
                hand_result = self._make_showdown_message()
                hand_id = self._save_hand_history()
                analysis = self._run_analysis(hand_id)
                if analysis:
                    hand_result["data"]["analysis"] = analysis
                hand_result["data"]["hand_db_id"] = hand_id
                await self._send_ws(hand_result)

                self._continue_event.clear()
                await self._continue_event.wait()

                self.engine.rotate_dealer()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Game loop error: %s", e, exc_info=True)
            await self._send_ws({"type": "error", "data": {"message": "An internal server error occurred."}})

    async def submit_action(self, action_type: str, amount: int = 0) -> None:
        self.touch()
        await self._action_queue.put((action_type, amount))

    def continue_to_next_hand(self) -> None:
        self.touch()
        self._continue_event.set()

    def get_hand_strength(self) -> dict | None:
        """Return the current hand strength for the human player."""
        state = self.engine.state
        human_player = state.get_player(self.human_id)

        if not human_player.hole_cards:
            return None

        community = list(state.community_cards)

        if len(community) < 3:
            return self._preflop_hand_strength(human_player.hole_cards)

        from app.models.hand import evaluate_hand

        result = evaluate_hand(human_player.hole_cards, community)
        percentile = round((1 - result.rank / 7462) * 100)

        desc_map = {
            "Royal Flush": "The best possible hand!",
            "Straight Flush": "Extremely strong — almost unbeatable",
            "Four of a Kind": "Monster hand — bet for max value",
            "Full House": "Very strong — usually the best hand",
            "Flush": "Strong hand — watch for board pairs",
            "Straight": "Good hand — beware of flush possibilities",
            "Three of a Kind": "Solid hand — usually worth a big bet",
            "Two Pair": "Decent — be cautious on wet boards",
            "One Pair": "Marginal — depends on pair strength and kicker",
            "High Card": "Weak — you'll need to bluff or improve",
        }

        cat_map = {
            "Royal Flush": "premium",
            "Straight Flush": "premium",
            "Four of a Kind": "premium",
            "Full House": "strong",
            "Flush": "strong",
            "Straight": "good",
            "Three of a Kind": "good",
            "Two Pair": "playable",
            "One Pair": "speculative",
            "High Card": "weak",
        }

        return {
            "hand_name": result.hand_name,
            "category": cat_map.get(result.hand_name, "weak"),
            "percentile": max(1, min(99, percentile)),
            "description": desc_map.get(result.hand_name, ""),
        }

    def _preflop_hand_strength(self, hole_cards: list) -> dict:
        """Classify a preflop hand into strength categories."""
        c1, c2 = hole_cards[0], hole_cards[1]
        r1, r2 = c1.rank.value, c2.rank.value
        suited = c1.suit == c2.suit
        high = max(r1, r2)
        low = min(r1, r2)
        pair = r1 == r2
        gap = high - low

        if pair and high >= 13:
            return {
                "hand_name": "Premium Pair",
                "category": "premium",
                "percentile": 95,
                "description": "Top pair — raise from any position",
            }
        if pair and high >= 10:
            return {
                "hand_name": "High Pair",
                "category": "strong",
                "percentile": 85,
                "description": "Strong pair — open-raise from most positions",
            }
        if not pair and high == 14 and low >= 13 and suited:
            return {
                "hand_name": "Big Suited Ace",
                "category": "premium",
                "percentile": 92,
                "description": "Premium suited hand — raise from any position",
            }
        if not pair and high == 14 and low >= 13:
            return {
                "hand_name": "Big Ace",
                "category": "strong",
                "percentile": 86,
                "description": "Strong hand — raise from most positions",
            }
        if not pair and high == 14 and low >= 10:
            cat = "strong" if suited else "good"
            pct = 80 if suited else 72
            return {
                "hand_name": "Ace-Broadway" + (" Suited" if suited else ""),
                "category": cat,
                "percentile": pct,
                "description": "Good hand — open from mid position or later",
            }
        if pair and high >= 7:
            return {
                "hand_name": "Medium Pair",
                "category": "good",
                "percentile": 68,
                "description": "Set-mining hand — plays well in position",
            }
        if not pair and high >= 10 and low >= 10 and suited:
            return {
                "hand_name": "Broadway Suited",
                "category": "good",
                "percentile": 70,
                "description": "Connected broadway — good postflop potential",
            }
        if not pair and high >= 10 and low >= 10:
            return {
                "hand_name": "Broadway",
                "category": "playable",
                "percentile": 58,
                "description": "Decent broadway — better in position",
            }
        if suited and gap <= 2 and low >= 5:
            return {
                "hand_name": "Suited Connector",
                "category": "playable",
                "percentile": 52,
                "description": "Good implied odds — play in position for straights/flushes",
            }
        if pair:
            return {
                "hand_name": "Small Pair",
                "category": "playable",
                "percentile": 50,
                "description": "Set-mine only — fold to big raises without odds",
            }
        if suited and high == 14:
            return {
                "hand_name": "Suited Ace",
                "category": "playable",
                "percentile": 48,
                "description": "Nut flush draw potential — play in position",
            }
        if suited and gap <= 3 and low >= 4:
            return {
                "hand_name": "Suited Gapper",
                "category": "speculative",
                "percentile": 38,
                "description": "Needs good position and odds to play",
            }
        if not pair and high == 14:
            return {
                "hand_name": "Off-suit Ace",
                "category": "speculative",
                "percentile": 35,
                "description": "Dominated easily — proceed with caution",
            }
        return {
            "hand_name": "Weak Hand",
            "category": "weak",
            "percentile": 18,
            "description": "Fold unless you have a specific read",
        }

    def get_hint(self) -> dict | None:
        """Calculate the optimal action for the human player right now."""
        state = self.engine.state
        if state.is_complete:
            return None

        current = state.current_player
        if current is None or current.player_id != self.human_id:
            return None

        human_player = current
        if not human_player.hole_cards:
            return None

        # Reconstruct to_call and pot at this moment
        bet_to_match = state.current_bet_to_match
        to_call = max(0, bet_to_match - human_player.current_bet)
        pot = state.total_pot
        num_opp = max(1, len([p for p in state.players if p.is_active]) - 1)

        community = list(state.community_cards)

        from app.analysis.scoring import score_decision

        result = score_decision(
            hole_cards=human_player.hole_cards,
            community_cards=community,
            action_type=ActionType.CHECK,
            amount=0,
            pot_before_action=pot,
            to_call=to_call,
            num_opponents=num_opp,
            include_details=True,
        )

        return {
            "optimal_action": result["optimal_action"],
            "equity": result["equity"],
            "pot_odds": result["pot_odds"],
            "recommendation": result["recommendation"],
            "equity_details": result.get("equity_details"),
        }

    async def get_ws_message(self) -> dict:
        return await self._ws_send.get()

    def stop(self) -> None:
        self._running = False

    async def _handle_human_turn(self) -> None:
        state = self.engine.state
        player = self._get_player(self.human_id)
        legal = get_legal_actions(state, player)

        await self._send_ws(
            {
                "type": "action_required",
                "data": {
                    **self._make_state_data(),
                    "legal_actions": [
                        {"action_type": a.action_type.value, "min_amount": a.min_amount, "max_amount": a.max_amount}
                        for a in legal
                    ],
                },
            }
        )

        action_str, amount = await self._action_queue.get()
        action_type = ActionType(action_str)

        try:
            self.engine.apply_action(self.human_id, action_type, amount)
        except ValueError as e:
            logger.warning("Invalid human action %s/%s: %s — re-requesting action", action_type, amount, e)
            await self._send_ws(
                {
                    "type": "error",
                    "data": {"message": str(e) or f"Invalid action: {action_type.value} with amount {amount}. Please try again."},
                }
            )
            await self._handle_human_turn()
            return

    async def _handle_bot_turn(self, bot_id: str) -> None:
        bot = self.bots.get(bot_id)
        if bot is None:
            self._safe_fallback_action(bot_id)
            return

        vs = make_visible_state(self.engine.state, bot_id)
        bot_action = bot.decide(vs)

        await asyncio.sleep(0.5)

        try:
            self.engine.apply_action(bot_id, bot_action.action_type, bot_action.amount)
        except ValueError as e:
            logger.warning("Invalid bot action for %s: %s — applying fallback", bot_id, e)
            self._safe_fallback_action(bot_id)

        data = self._make_state_data()
        data["last_action"] = {
            "player_id": bot_id,
            "action": bot_action.action_type.value,
            "amount": bot_action.amount,
        }
        await self._send_ws({"type": "bot_action", "data": data})

    def _safe_fallback_action(self, player_id: str) -> None:
        """Try CHECK, then FOLD, then ALL_IN as fallback when an action is invalid."""
        for fallback in (ActionType.CHECK, ActionType.FOLD, ActionType.ALL_IN):
            try:
                self.engine.apply_action(player_id, fallback)
                return
            except ValueError:
                continue

    def _get_player(self, player_id: str) -> PlayerState:
        return self.engine.state.get_player(player_id)

    def _make_state_data(self) -> dict:
        state = self.engine.state
        current = state.current_player

        players = []
        for p in state.players:
            pinfo = {
                "player_id": p.player_id,
                "seat": p.seat,
                "stack": p.stack,
                "current_bet": p.current_bet,
                "is_active": p.is_active,
                "is_all_in": p.is_all_in,
                "is_human": p.is_human,
            }
            if p.player_id == self.human_id or (state.is_complete and p.is_active and p.hole_cards):
                pinfo["hole_cards"] = [str(c) for c in p.hole_cards]
            players.append(pinfo)

        return {
            "hand_number": state.hand_number,
            "street": state.street.value,
            "pot": state.total_pot,
            "community_cards": [str(c) for c in state.community_cards],
            "players": players,
            "current_player_id": current.player_id if current else None,
            "dealer_seat": state.dealer_seat,
            "is_complete": state.is_complete,
            "player_stats": self.stats_tracker.get_all_stats(),
        }

    def _make_state_message(self, msg_type: str) -> dict:
        return {"type": msg_type, "data": self._make_state_data()}

    def _make_showdown_message(self) -> dict:
        data = self._make_state_data()
        events = self.engine.state.events
        showdown_events = [e for e in events if e["type"] in ("showdown", "win_uncontested")]
        if showdown_events:
            data["result"] = showdown_events[-1]["data"]
        return {"type": "hand_complete", "data": data}

    def _record_stats(self) -> None:
        """Record per-player stats for this hand."""
        state = self.engine.state
        player_ids = [
            p.player_id
            for p in state.players
            if p.stack > 0 or any(a.player_id == p.player_id for a in state.action_history)
        ]
        preflop_actions = [
            {"player_id": a.player_id, "action_type": a.action_type.value}
            for a in state.action_history
            if a.street.value == "preflop" and a.action_type != ActionType.POST_BLIND
        ]
        all_actions = [{"player_id": a.player_id, "action_type": a.action_type.value} for a in state.action_history]
        winner_ids = extract_winner_ids(state)
        winnings = extract_winnings(state)
        self.stats_tracker.record_hand(player_ids, preflop_actions, all_actions, winner_ids, winnings)

    def _save_hand_history(self) -> int | None:
        """Save the completed hand to the database."""
        hand_id = save_hand_history(self.game_id, self.engine.state, self._starting_stacks)
        if hand_id is not None:
            self._last_hand_id = hand_id
        return hand_id

    def _run_analysis(self, hand_id: int | None) -> list[dict] | None:
        """Analyze the human player's decisions in the completed hand."""
        return run_analysis(hand_id, self.engine.state, self.human_id, self._starting_stacks)

    async def _send_ws(self, msg: dict) -> None:
        await self._ws_send.put(msg)


# Global session registry
_sessions: dict[str, GameSession] = {}
_cleanup_task: asyncio.Task | None = None


def _pick_bots_for_difficulty(difficulty: int, count: int) -> list[BotProfile]:
    """Pick bot profiles using weighted random selection based on difficulty (0-100).

    Low difficulty  → mostly fish, few regulars
    Mid difficulty  → mix of fish, regulars, sharks
    High difficulty → mostly sharks and GTO bots
    """
    import random

    tier_pools: dict[int, list[BotProfile]] = {1: [], 2: [], 3: [], 4: []}
    for profile in PRESET_PROFILES.values():
        if profile.name.startswith("Coach"):
            continue
        tier_pools[profile.tier].append(profile)

    d = max(0, min(100, difficulty))

    # Weights per tier at key difficulty breakpoints, linearly interpolated
    #              Tier1  Tier2  Tier3  Tier4
    # d=0:          90     10      0      0
    # d=25:         60     30     10      0
    # d=50:         20     35     35     10
    # d=75:          5     20     50     25
    # d=100:         0      5     45     50
    breakpoints = [
        (0, [90, 10, 0, 0]),
        (25, [60, 30, 10, 0]),
        (50, [20, 35, 35, 10]),
        (75, [5, 20, 50, 25]),
        (100, [0, 5, 45, 50]),
    ]

    # Find the two breakpoints to interpolate between
    lower = breakpoints[0]
    upper = breakpoints[-1]
    for i in range(len(breakpoints) - 1):
        if breakpoints[i][0] <= d <= breakpoints[i + 1][0]:
            lower = breakpoints[i]
            upper = breakpoints[i + 1]
            break

    span = upper[0] - lower[0] if upper[0] != lower[0] else 1
    t = (d - lower[0]) / span
    weights = [lower[1][j] + t * (upper[1][j] - lower[1][j]) for j in range(4)]

    # Build the weighted pool: only include tiers that have profiles and weight > 0
    pool: list[BotProfile] = []
    pool_weights: list[float] = []
    for tier_idx, tier_num in enumerate([1, 2, 3, 4]):
        tier_profiles = tier_pools[tier_num]
        if not tier_profiles or weights[tier_idx] <= 0:
            continue
        weight_per_profile = weights[tier_idx] / len(tier_profiles)
        for p in tier_profiles:
            pool.append(p)
            pool_weights.append(weight_per_profile)

    if not pool:
        pool = list(PRESET_PROFILES.values())[:count]
        return pool

    return random.choices(pool, weights=pool_weights, k=count)


def create_game_session(
    num_players: int = 6,
    starting_stack: int = 1000,
    small_blind: int = 5,
    big_blind: int = 10,
    difficulty: int = 30,
    bot_configs: list[dict] | None = None,
) -> GameSession:
    if len(_sessions) >= MAX_SESSIONS:
        raise SessionLimitError(f"Server at capacity ({MAX_SESSIONS} active sessions)")

    game_id = secrets.token_urlsafe(16)
    session_token = secrets.token_urlsafe(32)
    human_id = "human"
    human_seat = 0

    player_ids = [human_id]
    bots: dict[str, BotStrategy] = {}

    bot_count = num_players - 1
    selected_profiles = _pick_bots_for_difficulty(difficulty, bot_count)

    for i in range(1, num_players):
        bot_id = f"bot_{i}"
        player_ids.append(bot_id)

        if bot_configs and i - 1 < len(bot_configs):
            cfg = bot_configs[i - 1]
            profile_name = cfg.get("profile", "tag_basic")
            profile = PRESET_PROFILES.get(profile_name, selected_profiles[i - 1])
        else:
            profile = selected_profiles[i - 1]

        bots[bot_id] = profile.create_bot()

    engine = GameEngine(
        player_ids=player_ids,
        starting_stacks=starting_stack,
        small_blind=small_blind,
        big_blind=big_blind,
        human_ids={human_id},
    )

    session = GameSession(
        game_id=game_id,
        session_token=session_token,
        engine=engine,
        bots=bots,
        human_id=human_id,
        human_seat=human_seat,
    )

    _sessions[game_id] = session
    return session


class SessionLimitError(Exception):
    pass


def validate_session_token(game_id: str, token: str) -> GameSession:
    """Look up a session and verify the caller's token matches."""
    session = get_session(game_id)
    if session is None:
        return None
    if not secrets.compare_digest(session.session_token, token):
        return None
    return session


def get_session(game_id: str) -> GameSession | None:
    session = _sessions.get(game_id)
    if session is not None:
        session.touch()
    return session


def remove_session(game_id: str) -> None:
    session = _sessions.pop(game_id, None)
    if session is not None:
        session.stop()


async def _cleanup_loop() -> None:
    """Periodically remove expired sessions."""
    while True:
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
        expired = [gid for gid, s in _sessions.items() if s.is_expired]
        for gid in expired:
            logger.info("Cleaning up expired session %s", gid)
            remove_session(gid)


def start_cleanup_task() -> None:
    """Start the background cleanup loop (call once at app startup)."""
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(_cleanup_loop())


def active_session_count() -> int:
    return len(_sessions)
