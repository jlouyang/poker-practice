"""Game session manager: orchestrates game loop, bot turns, human input."""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

from app.bots.interface import BotStrategy
from app.bots.profiles import PRESET_PROFILES, BotProfile
from app.bots.visible_state import make_visible_state
from app.engine.game import GameEngine
from app.engine.validators import get_legal_actions
from app.models.types import ActionType
from app.db.models import get_session_factory
from app.db.repository import save_hand, save_analysis
from app.analysis.scoring import score_decision
from app.analysis.equity import calculate_equity
from app.analysis.stats import SessionStatsTracker
from app.models.card import Card


@dataclass
class GameSession:
    game_id: str
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
            await self._send_ws({"type": "error", "data": {"message": str(e)}})

    async def submit_action(self, action_type: str, amount: int = 0) -> None:
        await self._action_queue.put((action_type, amount))

    def continue_to_next_hand(self) -> None:
        self._continue_event.set()

    async def get_ws_message(self) -> dict:
        return await self._ws_send.get()

    def stop(self) -> None:
        self._running = False

    async def _handle_human_turn(self) -> None:
        state = self.engine.state
        player = self._get_player(self.human_id)
        legal = get_legal_actions(state, player)

        await self._send_ws({
            "type": "action_required",
            "data": {
                **self._make_state_data(),
                "legal_actions": [
                    {"action_type": a.action_type.value, "min_amount": a.min_amount, "max_amount": a.max_amount}
                    for a in legal
                ],
            },
        })

        action_str, amount = await self._action_queue.get()
        action_type = ActionType(action_str)

        try:
            self.engine.apply_action(self.human_id, action_type, amount)
        except ValueError:
            self._safe_fallback_action(self.human_id)

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
        except ValueError:
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

    def _get_player(self, player_id: str):
        for p in self.engine.state.players:
            if p.player_id == player_id:
                return p
        raise ValueError(f"Player {player_id} not found")

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
            if p.player_id == self.human_id:
                pinfo["hole_cards"] = [str(c) for c in p.hole_cards]
            elif state.is_complete and p.is_active and p.hole_cards:
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
        player_ids = [p.player_id for p in state.players if p.stack > 0 or any(
            a.player_id == p.player_id for a in state.action_history
        )]
        preflop_actions = [
            {"player_id": a.player_id, "action_type": a.action_type.value}
            for a in state.action_history
            if a.street.value == "preflop" and a.action_type != ActionType.POST_BLIND
        ]
        all_actions = [
            {"player_id": a.player_id, "action_type": a.action_type.value}
            for a in state.action_history
        ]
        winner_ids = []
        winnings: dict[str, int] = {}
        for e in state.events:
            if e["type"] == "showdown" and "winners" in e["data"]:
                for pid, info in e["data"]["winners"].items():
                    winner_ids.append(pid)
                    winnings[pid] = info["amount"]
            elif e["type"] == "win_uncontested":
                winner_ids = [e["data"]["player_id"]]
                winnings[e["data"]["player_id"]] = e["data"]["amount"]

        self.stats_tracker.record_hand(player_ids, preflop_actions, all_actions, winner_ids, winnings)

    def _save_hand_history(self) -> int | None:
        """Save the completed hand to the database."""
        try:
            db_factory = get_session_factory()
            db = db_factory()
            state = self.engine.state

            winner_ids = []
            for e in state.events:
                if e["type"] == "showdown" and "winners" in e["data"]:
                    winner_ids = list(e["data"]["winners"].keys())
                elif e["type"] == "win_uncontested":
                    winner_ids = [e["data"]["player_id"]]

            players = []
            for p in state.players:
                players.append({
                    "player_id": p.player_id,
                    "seat": p.seat,
                    "starting_stack": self._starting_stacks.get(p.player_id, p.stack),
                    "ending_stack": p.stack,
                    "hole_cards": [str(c) for c in p.hole_cards] if p.hole_cards else [],
                    "is_human": p.is_human,
                })

            actions = []
            for a in state.action_history:
                actions.append({
                    "player_id": a.player_id,
                    "street": a.street.value,
                    "action_type": a.action_type.value,
                    "amount": a.amount,
                })

            hand = save_hand(
                db=db,
                session_id=self.game_id,
                hand_number=state.hand_number,
                dealer_seat=state.dealer_seat,
                small_blind=state.small_blind,
                big_blind=state.big_blind,
                community_cards=[str(c) for c in state.community_cards],
                pot_size=state.total_pot,
                winner_ids=winner_ids,
                players=players,
                actions=actions,
            )
            self._last_hand_id = hand.id
            db.close()
            return hand.id
        except Exception as e:
            print(f"Error saving hand history: {e}")
            return None

    def _run_analysis(self, hand_id: int | None) -> list[dict] | None:
        """Analyze the human player's decisions in the completed hand."""
        if hand_id is None:
            return None

        try:
            state = self.engine.state
            human_player = None
            for p in state.players:
                if p.player_id == self.human_id:
                    human_player = p
                    break

            if not human_player or not human_player.hole_cards:
                return None

            all_actions = state.action_history
            if not all_actions:
                return None

            # Replay the action history to reconstruct state at each decision
            pot = 0
            current_bets: dict[str, int] = {}
            active_players: set[str] = {p.player_id for p in state.players if self._starting_stacks.get(p.player_id, 0) > 0}
            current_street = "preflop"

            results = []
            for i, action in enumerate(all_actions):
                pid = action.player_id
                street = action.street.value

                # Street advanced: collect bets into pot and reset
                if street != current_street:
                    pot += sum(current_bets.values())
                    current_bets = {}
                    current_street = street

                # If this is a human non-blind action, analyze it BEFORE applying
                if pid == self.human_id and action.action_type != ActionType.POST_BLIND:
                    bet_to_match = max(current_bets.values()) if current_bets else 0
                    human_bet_so_far = current_bets.get(self.human_id, 0)
                    to_call = max(0, bet_to_match - human_bet_so_far)
                    pot_at_decision = pot + sum(current_bets.values())
                    num_opp = max(1, len(active_players) - 1)

                    community = list(state.community_cards)
                    if street == "preflop":
                        community_for_street = []
                    elif street == "flop":
                        community_for_street = community[:3]
                    elif street == "turn":
                        community_for_street = community[:4]
                    else:
                        community_for_street = community[:5]

                    score_result = score_decision(
                        hole_cards=human_player.hole_cards,
                        community_cards=community_for_street,
                        action_type=action.action_type,
                        amount=action.amount,
                        pot_before_action=pot_at_decision,
                        to_call=to_call,
                        num_opponents=num_opp,
                    )
                    score_result["player_id"] = pid
                    score_result["street"] = street
                    score_result["action_type"] = action.action_type.value
                    results.append(score_result)

                # Apply the action to our tracking state
                if action.action_type == ActionType.FOLD:
                    active_players.discard(pid)
                elif action.action_type in (ActionType.POST_BLIND, ActionType.CALL, ActionType.BET,
                                            ActionType.RAISE, ActionType.ALL_IN):
                    current_bets[pid] = current_bets.get(pid, 0) + action.amount

            if not results:
                return None

            db_factory = get_session_factory()
            db = db_factory()
            save_analysis(db, hand_id, results)
            db.close()

            return results
        except Exception as e:
            print(f"Error running analysis: {e}")
            return None

    async def _send_ws(self, msg: dict) -> None:
        await self._ws_send.put(msg)


# Global session registry
_sessions: dict[str, GameSession] = {}


def create_game_session(
    num_players: int = 6,
    starting_stack: int = 1000,
    small_blind: int = 5,
    big_blind: int = 10,
    bot_configs: list[dict] | None = None,
) -> GameSession:
    game_id = str(uuid.uuid4())[:8]
    human_id = "human"
    human_seat = 0

    player_ids = [human_id]
    bots: dict[str, BotStrategy] = {}

    profiles_list = list(PRESET_PROFILES.values())

    for i in range(1, num_players):
        bot_id = f"bot_{i}"
        player_ids.append(bot_id)

        if bot_configs and i - 1 < len(bot_configs):
            cfg = bot_configs[i - 1]
            profile_name = cfg.get("profile", "tag_basic")
            profile = PRESET_PROFILES.get(profile_name, profiles_list[i % len(profiles_list)])
        else:
            profile = profiles_list[i % len(profiles_list)]

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
        engine=engine,
        bots=bots,
        human_id=human_id,
        human_seat=human_seat,
    )

    _sessions[game_id] = session
    return session


def get_session(game_id: str) -> GameSession | None:
    return _sessions.get(game_id)


def remove_session(game_id: str) -> None:
    _sessions.pop(game_id, None)
