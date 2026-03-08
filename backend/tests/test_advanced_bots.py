"""Tests for Shark, GTO, and LLM Coach bots, plus edge cases."""

import random

import pytest

from app.bots.fish import FishBot
from app.bots.gto import GTOBot
from app.bots.interface import BotAction
from app.bots.llm_coach import LLMCoachBot
from app.bots.profiles import PRESET_PROFILES, BotProfile, get_profile
from app.bots.regular import RegularBot
from app.bots.shark import SharkBot
from app.bots.visible_state import make_visible_state
from app.engine.game import GameEngine
from app.models.types import ActionType


class TestSharkBot:
    def test_returns_valid_action(self):
        bot = SharkBot()
        engine = GameEngine(["bot", "human"], 1000, 5, 10)
        engine.start_hand()
        vs = make_visible_state(engine.state, "bot")
        action = bot.decide(vs)
        assert isinstance(action, BotAction)
        assert action.action_type in ActionType

    def test_various_configs(self):
        for tight, agg in [(0, 0), (50, 50), (100, 100), (0, 100), (100, 0)]:
            bot = SharkBot(tightness=tight, aggression=agg)
            engine = GameEngine(["bot", "opp"], 1000, 5, 10)
            engine.start_hand()
            vs = make_visible_state(engine.state, "bot")
            action = bot.decide(vs)
            assert action.action_type in ActionType

    def test_bluff_frequency_clamped(self):
        bot = SharkBot(tightness=0, aggression=100)
        assert bot._bluff_frequency <= 1.0

    def test_amount_within_stack(self):
        random.seed(42)
        bot = SharkBot()
        for _ in range(20):
            engine = GameEngine(["bot", "opp"], 500, 5, 10)
            engine.start_hand()
            vs = make_visible_state(engine.state, "bot")
            action = bot.decide(vs)
            assert action.amount <= vs.my_stack


class TestGTOBot:
    def test_returns_valid_action(self):
        bot = GTOBot()
        engine = GameEngine(["bot", "human"], 1000, 5, 10)
        engine.start_hand()
        vs = make_visible_state(engine.state, "bot")
        action = bot.decide(vs)
        assert isinstance(action, BotAction)

    def test_various_configs(self):
        for tight, agg in [(0, 0), (50, 50), (100, 100)]:
            bot = GTOBot(tightness=tight, aggression=agg)
            engine = GameEngine(["bot", "opp"], 1000, 5, 10)
            engine.start_hand()
            vs = make_visible_state(engine.state, "bot")
            action = bot.decide(vs)
            assert action.action_type in ActionType

    def test_amount_within_stack(self):
        random.seed(99)
        bot = GTOBot()
        for _ in range(20):
            engine = GameEngine(["bot", "opp"], 500, 5, 10)
            engine.start_hand()
            vs = make_visible_state(engine.state, "bot")
            action = bot.decide(vs)
            assert action.amount <= vs.my_stack


class TestLLMCoachBot:
    def test_fallback_without_api_key(self):
        """Without ANTHROPIC_API_KEY, should fall back to SharkBot strategy."""
        import os

        old_key = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            bot = LLMCoachBot()
            engine = GameEngine(["bot", "opp"], 1000, 5, 10)
            engine.start_hand()
            vs = make_visible_state(engine.state, "bot")
            action = bot.decide(vs)
            assert isinstance(action, BotAction)
            assert action.action_type in ActionType
        finally:
            if old_key is not None:
                os.environ["ANTHROPIC_API_KEY"] = old_key

    def test_records_decisions(self):
        import os

        old_key = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            bot = LLMCoachBot()
            engine = GameEngine(["bot", "opp"], 1000, 5, 10)
            engine.start_hand()
            vs = make_visible_state(engine.state, "bot")
            bot.decide(vs)
            assert len(bot.hand_context.decisions) == 1
            assert len(bot.hand_context.equity_data) == 1
        finally:
            if old_key is not None:
                os.environ["ANTHROPIC_API_KEY"] = old_key

    def test_offline_explanation(self):
        bot = LLMCoachBot()
        bot._hand_context.decisions.append(
            {
                "street": "flop",
                "action": "bet",
                "amount": 30,
                "equity": 0.72,
                "source": "fallback",
                "pot": 40,
                "to_call": 0,
            }
        )
        explanation = bot._generate_offline_explanation("Why did you bet?")
        assert len(explanation) > 0
        assert "flop" in explanation.lower()

    def test_reset_context(self):
        bot = LLMCoachBot()
        bot._hand_context.decisions.append({"test": True})
        bot.reset_context()
        assert len(bot.hand_context.decisions) == 0

    def test_parse_action_fold(self):
        bot = LLMCoachBot()
        engine = GameEngine(["bot", "opp"], 1000, 5, 10)
        engine.start_hand()
        vs = make_visible_state(engine.state, "bot")
        action = bot._parse_action("fold 0", vs)
        assert action.action_type == ActionType.FOLD

    def test_parse_action_all_in_uses_stack(self):
        bot = LLMCoachBot()
        engine = GameEngine(["bot", "opp"], 500, 5, 10)
        engine.start_hand()
        vs = make_visible_state(engine.state, "bot")
        action = bot._parse_action("all_in 0", vs)
        assert action.action_type == ActionType.ALL_IN
        assert action.amount == vs.my_stack


class TestProfiles:
    def test_all_profiles_create_bots(self):
        for _name, profile in PRESET_PROFILES.items():
            bot = profile.create_bot()
            assert bot.tier == profile.tier
            assert bot.name is not None

    def test_get_profile_valid(self):
        profile = get_profile("shark_balanced")
        assert profile.tier == 3

    def test_get_profile_invalid(self):
        with pytest.raises(ValueError, match="Unknown profile"):
            get_profile("nonexistent_bot")

    def test_coach_profile_creates_llm_bot(self):
        profile = get_profile("coach")
        bot = profile.create_bot()
        assert isinstance(bot, LLMCoachBot)

    def test_gto_profile_creates_gto_bot(self):
        profile = get_profile("gto_balanced")
        bot = profile.create_bot()
        assert isinstance(bot, GTOBot)

    def test_invalid_tier_raises(self):
        profile = BotProfile("Test", tier=99, tightness=50, aggression=50, description="test")
        with pytest.raises(ValueError, match="Unknown tier"):
            profile.create_bot()


class TestVisibleState:
    def test_to_call_correct(self):
        engine = GameEngine(["p0", "p1"], 1000, 5, 10)
        engine.start_hand()
        vs = make_visible_state(engine.state, "p0")
        assert vs.to_call >= 0

    def test_opponent_cards_hidden(self):
        engine = GameEngine(["p0", "p1"], 1000, 5, 10)
        engine.start_hand()
        vs = make_visible_state(engine.state, "p0")
        for opp in vs.opponents:
            assert not hasattr(opp, "hole_cards")

    def test_player_not_in_game_raises(self):
        engine = GameEngine(["p0", "p1"], 1000, 5, 10)
        engine.start_hand()
        with pytest.raises(ValueError, match="not found"):
            make_visible_state(engine.state, "ghost")


class TestStressTestAllBotTypes:
    def test_50_hands_mixed_bots(self):
        """Run 50 hands with all bot types. No crashes."""
        random.seed(777)
        player_ids = ["bot0", "bot1", "bot2", "bot3", "bot4"]
        bots = {
            "bot0": FishBot(20, 20),
            "bot1": RegularBot(60, 60),
            "bot2": SharkBot(55, 65),
            "bot3": GTOBot(60, 55),
            "bot4": FishBot(10, 80),
        }

        engine = GameEngine(player_ids, 1000, 5, 10)
        initial_total = sum(p.stack for p in engine.state.players)
        hands_completed = 0

        for _ in range(50):
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
                    engine.apply_action(current.player_id, bot_action.action_type, bot_action.amount)
                except ValueError:
                    for fallback in (ActionType.CHECK, ActionType.FOLD, ActionType.ALL_IN):
                        try:
                            engine.apply_action(current.player_id, fallback)
                            break
                        except ValueError:
                            continue

                action_count += 1
                if action_count > 100:
                    break

            assert state.is_complete
            hands_completed += 1

            total_stacks = sum(p.stack for p in state.players)
            assert total_stacks == initial_total

            engine.rotate_dealer()

        assert hands_completed >= 20
