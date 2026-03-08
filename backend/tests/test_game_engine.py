"""Tests for the game engine: betting, pots, showdown, edge cases."""

import pytest

from app.engine.game import GameEngine
from app.engine.pot import calculate_pots
from app.models.types import ActionType, Street


def make_engine(n_players=2, stacks=1000, sb=1, bb=2):
    ids = [f"p{i}" for i in range(n_players)]
    return GameEngine(ids, stacks, sb, bb)


class TestBasicHandLifecycle:
    def test_start_hand_deals_cards(self):
        engine = make_engine(2)
        engine.start_hand()
        for p in engine.state.players:
            if p.is_active:
                assert len(p.hole_cards) == 2

    def test_blinds_posted(self):
        engine = make_engine(3, stacks=1000, sb=5, bb=10)
        engine.start_hand()
        # In 3-player: dealer=seat0, SB=seat1, BB=seat2
        state = engine.state
        blind_actions = [a for a in state.action_history if a.action_type == ActionType.POST_BLIND]
        assert len(blind_actions) == 2
        amounts = sorted(a.amount for a in blind_actions)
        assert amounts == [5, 10]

    def test_fold_wins_pot(self):
        engine = make_engine(2, stacks=1000, sb=5, bb=10)
        engine.start_hand()
        state = engine.state
        current = state.current_player
        assert current is not None
        engine.apply_action(current.player_id, ActionType.FOLD)
        assert state.is_complete

    def test_check_check_advances(self):
        engine = make_engine(2, stacks=1000, sb=5, bb=10)
        engine.start_hand()
        state = engine.state
        # Heads-up: SB acts first preflop. SB calls.
        current = state.current_player
        assert current is not None
        engine.apply_action(current.player_id, ActionType.CALL, 5)
        # BB checks (option)
        current = state.current_player
        assert current is not None
        engine.apply_action(current.player_id, ActionType.CHECK)
        # Should advance to flop
        assert state.street == Street.FLOP
        assert len(state.community_cards) == 3

    def test_full_hand_to_showdown(self):
        engine = make_engine(2, stacks=1000, sb=5, bb=10)
        engine.start_hand()
        state = engine.state

        # Preflop: SB calls, BB checks
        engine.apply_action(state.current_player.player_id, ActionType.CALL, 5)
        engine.apply_action(state.current_player.player_id, ActionType.CHECK)
        assert state.street == Street.FLOP

        # Flop: check check
        engine.apply_action(state.current_player.player_id, ActionType.CHECK)
        engine.apply_action(state.current_player.player_id, ActionType.CHECK)
        assert state.street == Street.TURN

        # Turn: check check
        engine.apply_action(state.current_player.player_id, ActionType.CHECK)
        engine.apply_action(state.current_player.player_id, ActionType.CHECK)
        assert state.street == Street.RIVER

        # River: check check
        engine.apply_action(state.current_player.player_id, ActionType.CHECK)
        engine.apply_action(state.current_player.player_id, ActionType.CHECK)
        assert state.is_complete

        # Total stacks should still equal 2000
        total = sum(p.stack for p in state.players)
        assert total == 2000

    def test_multiway_hand(self):
        engine = make_engine(4, stacks=1000, sb=5, bb=10)
        engine.start_hand()
        state = engine.state

        # All fold to BB
        for _ in range(3):
            current = state.current_player
            if current and not state.is_complete:
                if current.current_bet < state.current_bet_to_match:
                    engine.apply_action(current.player_id, ActionType.FOLD)
                else:
                    engine.apply_action(current.player_id, ActionType.CHECK)

        # Verify completion or BB wins
        assert state.is_complete or state.street != Street.PREFLOP


class TestBetting:
    def test_raise_and_call(self):
        engine = make_engine(2, stacks=1000, sb=5, bb=10)
        engine.start_hand()
        state = engine.state

        # SB raises to 25 (put in 20 more on top of 5 already in)
        sb = state.current_player
        engine.apply_action(sb.player_id, ActionType.RAISE, 20)
        assert sb.current_bet == 25

        # BB calls
        bb = state.current_player
        engine.apply_action(bb.player_id, ActionType.CALL, 15)
        assert state.street == Street.FLOP

    def test_bet_on_flop(self):
        engine = make_engine(2, stacks=1000, sb=5, bb=10)
        engine.start_hand()
        state = engine.state

        # Get to flop
        engine.apply_action(state.current_player.player_id, ActionType.CALL, 5)
        engine.apply_action(state.current_player.player_id, ActionType.CHECK)
        assert state.street == Street.FLOP

        # First to act bets
        current = state.current_player
        engine.apply_action(current.player_id, ActionType.BET, 10)
        assert current.current_bet == 10

    def test_invalid_action_raises(self):
        engine = make_engine(2, stacks=1000, sb=5, bb=10)
        engine.start_hand()
        state = engine.state
        current = state.current_player
        # Can't check when there's a bet to call
        with pytest.raises(ValueError):
            engine.apply_action(current.player_id, ActionType.CHECK)

    def test_wrong_player_raises(self):
        engine = make_engine(2, stacks=1000, sb=5, bb=10)
        engine.start_hand()
        state = engine.state
        current = state.current_player
        other = next(p for p in state.players if p.player_id != current.player_id)
        with pytest.raises(ValueError):
            engine.apply_action(other.player_id, ActionType.FOLD)


class TestAllIn:
    def test_all_in_call(self):
        engine = GameEngine(
            ["short", "big"],
            {"short": 50, "big": 1000},
            small_blind=5,
            big_blind=10,
        )
        engine.start_hand()
        state = engine.state

        # Short stack goes all-in
        current = state.current_player
        engine.apply_action(current.player_id, ActionType.ALL_IN)

        # Other player calls
        current = state.current_player
        if not state.is_complete:
            engine.apply_action(current.player_id, ActionType.CALL)

        assert state.is_complete
        total = sum(p.stack for p in state.players)
        assert total == 1050

    def test_three_way_all_in_side_pots(self):
        engine = GameEngine(
            ["p0", "p1", "p2"],
            {"p0": 100, "p1": 200, "p2": 300},
            small_blind=5,
            big_blind=10,
        )
        engine.start_hand()
        state = engine.state

        # Everyone goes all in
        while not state.is_complete:
            current = state.current_player
            if current is None:
                break
            engine.apply_action(current.player_id, ActionType.ALL_IN)

        assert state.is_complete
        total = sum(p.stack for p in state.players)
        assert total == 600


class TestPotCalculation:
    def test_simple_pot(self):
        from app.engine.game_state import PlayerState

        players = [
            PlayerState("a", 0, 900, current_bet=100, is_active=True),
            PlayerState("b", 1, 900, current_bet=100, is_active=True),
        ]
        pots = calculate_pots(players)
        assert sum(p.amount for p in pots) == 200

    def test_side_pot_with_all_in(self):
        from app.engine.game_state import PlayerState

        players = [
            PlayerState("a", 0, 0, current_bet=50, is_active=True, is_all_in=True),
            PlayerState("b", 1, 50, current_bet=100, is_active=True),
            PlayerState("c", 2, 50, current_bet=100, is_active=True),
        ]
        pots = calculate_pots(players)
        main_pot = pots[0]
        assert main_pot.amount == 150  # 50 from each
        assert len(main_pot.eligible_players) == 3
        side_pot = pots[1]
        assert side_pot.amount == 100  # 50 from b and c
        assert "a" not in side_pot.eligible_players

    def test_folded_bets_go_to_pot(self):
        from app.engine.game_state import PlayerState

        players = [
            PlayerState("a", 0, 900, current_bet=100, is_active=True),
            PlayerState("b", 1, 900, current_bet=100, is_active=True),
            PlayerState("c", 2, 950, current_bet=50, is_active=False),
        ]
        pots = calculate_pots(players)
        total = sum(p.amount for p in pots)
        assert total == 250


class TestDealerRotation:
    def test_rotate_skips_busted(self):
        engine = make_engine(3, stacks=1000)
        engine.state.players[1].stack = 0
        engine.state.dealer_seat = 0
        engine.rotate_dealer()
        assert engine.state.dealer_seat == 2


class TestMultipleHands:
    def test_two_consecutive_hands(self):
        engine = make_engine(2, stacks=1000, sb=5, bb=10)

        # Hand 1
        engine.start_hand()
        state = engine.state
        engine.apply_action(state.current_player.player_id, ActionType.FOLD)
        assert state.is_complete

        stacks_after_1 = [p.stack for p in state.players]
        assert sum(stacks_after_1) == 2000

        # Hand 2
        engine.rotate_dealer()
        engine.start_hand()
        state = engine.state
        assert state.hand_number == 2
        assert not state.is_complete
        engine.apply_action(state.current_player.player_id, ActionType.FOLD)
        assert state.is_complete
        assert sum(p.stack for p in state.players) == 2000


class TestEvents:
    def test_events_emitted(self):
        engine = make_engine(2, stacks=1000, sb=5, bb=10)
        engine.start_hand()
        state = engine.state

        event_types = [e["type"] for e in state.events]
        assert "deal" in event_types
        assert "blind" in event_types

    def test_showdown_event(self):
        engine = make_engine(2, stacks=1000, sb=5, bb=10)
        engine.start_hand()
        state = engine.state

        # Play to showdown
        engine.apply_action(state.current_player.player_id, ActionType.CALL, 5)
        engine.apply_action(state.current_player.player_id, ActionType.CHECK)
        for _ in range(3):
            if state.is_complete:
                break
            engine.apply_action(state.current_player.player_id, ActionType.CHECK)
            if state.is_complete:
                break
            engine.apply_action(state.current_player.player_id, ActionType.CHECK)

        assert state.is_complete
        event_types = [e["type"] for e in state.events]
        assert "showdown" in event_types


class TestSixMax:
    def test_six_player_fold_around(self):
        engine = make_engine(6, stacks=1000, sb=5, bb=10)
        engine.start_hand()
        state = engine.state

        fold_count = 0
        while not state.is_complete:
            current = state.current_player
            if current is None:
                break
            engine.apply_action(current.player_id, ActionType.FOLD)
            fold_count += 1
            if fold_count > 10:
                break

        assert state.is_complete
        assert sum(p.stack for p in state.players) == 6000
