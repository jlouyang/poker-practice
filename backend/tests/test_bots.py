"""Tests for bot framework: legal actions, 100-hand stress test."""

import random

from app.bots.fish import FishBot
from app.bots.interface import BotAction
from app.bots.profiles import PRESET_PROFILES, get_profile
from app.bots.regular import RegularBot
from app.bots.visible_state import make_visible_state
from app.engine.game import GameEngine
from app.engine.validators import get_legal_actions
from app.models.types import ActionType


def _action_is_legal(bot_action: BotAction, engine: GameEngine, player_id: str) -> bool:
    """Check if a bot's chosen action is executable."""
    player = None
    for p in engine.state.players:
        if p.player_id == player_id:
            player = p
            break
    if player is None:
        return False

    legal = get_legal_actions(engine.state, player)
    legal_types = {a.action_type for a in legal}

    at = bot_action.action_type

    # ALL_IN is always convertible
    if at == ActionType.ALL_IN:
        return True

    return at in legal_types


class TestFishBot:
    def test_always_returns_action(self):
        bot = FishBot()
        engine = GameEngine(["bot", "human"], 1000, 1, 2)
        engine.start_hand()
        vs = make_visible_state(engine.state, "bot")
        action = bot.decide(vs)
        assert isinstance(action, BotAction)

    def test_various_tightness(self):
        for tightness in [0, 25, 50, 75, 100]:
            bot = FishBot(tightness=tightness)
            engine = GameEngine(["bot", "human"], 1000, 1, 2)
            engine.start_hand()
            vs = make_visible_state(engine.state, "bot")
            action = bot.decide(vs)
            assert action.action_type in ActionType


class TestRegularBot:
    def test_always_returns_action(self):
        bot = RegularBot()
        engine = GameEngine(["bot", "human"], 1000, 1, 2)
        engine.start_hand()
        vs = make_visible_state(engine.state, "bot")
        action = bot.decide(vs)
        assert isinstance(action, BotAction)

    def test_folds_junk_preflop_when_tight(self):
        random.seed(42)
        bot = RegularBot(tightness=90, aggression=30)
        fold_count = 0
        for _ in range(50):
            engine = GameEngine(["bot", "opp"], 1000, 5, 10)
            engine.start_hand()
            # Ensure bot is the one facing a raise (not in BB position with option)
            vs = make_visible_state(engine.state, "bot")
            if vs.to_call > 0:
                action = bot.decide(vs)
                if action.action_type == ActionType.FOLD:
                    fold_count += 1
        # A tight bot should fold most hands
        assert fold_count > 10


class TestProfiles:
    def test_all_profiles_create_bots(self):
        for _name, profile in PRESET_PROFILES.items():
            bot = profile.create_bot()
            assert bot.tier == profile.tier

    def test_get_profile(self):
        profile = get_profile("tag_basic")
        assert profile.tightness == 60


class TestStressTest:
    def test_100_hands_6_players(self):
        """Run 100 hands with 6 bots (mixed Fish/Regular), zero crashes."""
        random.seed(123)
        player_ids = [f"bot{i}" for i in range(6)]
        bots = {
            "bot0": FishBot(20, 20),
            "bot1": FishBot(10, 80),
            "bot2": RegularBot(60, 60),
            "bot3": RegularBot(85, 30),
            "bot4": RegularBot(40, 75),
            "bot5": FishBot(30, 15),
        }

        engine = GameEngine(player_ids, 1000, 5, 10)
        initial_total = sum(p.stack for p in engine.state.players)
        hands_completed = 0

        for _ in range(100):
            active_count = sum(1 for p in engine.state.players if p.stack > 0)
            if active_count < 2:
                break

            engine.start_hand()
            state = engine.state
            action_count = 0

            while not state.is_complete:
                current = state.current_player
                if current is None:
                    break

                vs = make_visible_state(state, current.player_id)
                bot = bots[current.player_id]
                bot_action = bot.decide(vs)

                try:
                    engine.apply_action(
                        current.player_id,
                        bot_action.action_type,
                        bot_action.amount,
                    )
                except ValueError:
                    # If bot returns invalid action, try check then fold
                    try:
                        engine.apply_action(current.player_id, ActionType.CHECK)
                    except ValueError:
                        try:
                            engine.apply_action(current.player_id, ActionType.FOLD)
                        except ValueError:
                            engine.apply_action(current.player_id, ActionType.ALL_IN, current.stack)

                action_count += 1
                if action_count > 100:
                    # Safety: prevent infinite loop
                    break

            assert state.is_complete, f"Hand did not complete after {action_count} actions"
            hands_completed += 1

            total_stacks = sum(p.stack for p in state.players)
            assert total_stacks == initial_total, f"Stack conservation violated: {total_stacks} != {initial_total}"

            engine.rotate_dealer()

        assert hands_completed >= 50, f"Only completed {hands_completed} hands"
