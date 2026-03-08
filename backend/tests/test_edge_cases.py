"""Edge case tests for cards, deck, game engine, and pot calculations."""

import pytest

from app.engine.game import GameEngine
from app.engine.game_state import PlayerState, Pot
from app.engine.pot import calculate_pots, merge_pots
from app.engine.validators import get_legal_actions
from app.models.card import Card, Deck
from app.models.types import ActionType, Rank, Suit


class TestCardFromStrValidation:
    def test_empty_string(self):
        with pytest.raises(ValueError, match="Invalid card string"):
            Card.from_str("")

    def test_single_char(self):
        with pytest.raises(ValueError, match="Invalid card string"):
            Card.from_str("A")

    def test_too_long(self):
        with pytest.raises(ValueError, match="Invalid card string"):
            Card.from_str("AhXX")

    def test_invalid_rank(self):
        with pytest.raises(ValueError, match="Invalid rank"):
            Card.from_str("Xh")

    def test_invalid_suit(self):
        with pytest.raises(ValueError, match="Invalid suit"):
            Card.from_str("Ax")

    def test_non_string(self):
        with pytest.raises(ValueError, match="Invalid card string"):
            Card.from_str(42)  # type: ignore

    def test_lowercase_rank(self):
        card = Card.from_str("ah")
        assert card.rank == Rank.ACE
        assert card.suit == Suit.HEARTS

    def test_lowercase_face_cards(self):
        assert Card.from_str("kd").rank == Rank.KING
        assert Card.from_str("qs").rank == Rank.QUEEN
        assert Card.from_str("jc").rank == Rank.JACK
        assert Card.from_str("th").rank == Rank.TEN

    def test_10_format(self):
        card = Card.from_str("10h")
        assert card.rank == Rank.TEN
        assert card.suit == Suit.HEARTS


class TestDeckEdgeCases:
    def test_deal_zero(self):
        deck = Deck()
        result = deck.deal(0)
        assert result == []
        assert deck.remaining == 52

    def test_deal_all(self):
        deck = Deck()
        all_cards = deck.deal(52)
        assert len(all_cards) == 52
        assert deck.remaining == 0

    def test_deal_more_than_remaining(self):
        deck = Deck()
        deck.deal(50)
        with pytest.raises(ValueError, match="Cannot deal"):
            deck.deal(5)

    def test_deal_one_from_empty(self):
        deck = Deck()
        deck.deal(52)
        with pytest.raises(ValueError, match="Cannot deal"):
            deck.deal_one()


class TestPotEdgeCases:
    def test_empty_players(self):
        pots = calculate_pots([])
        assert pots == []

    def test_no_bets(self):
        players = [
            PlayerState("a", 0, 1000, current_bet=0, is_active=True),
            PlayerState("b", 1, 1000, current_bet=0, is_active=True),
        ]
        pots = calculate_pots(players)
        assert pots == []

    def test_all_folded_with_bets(self):
        players = [
            PlayerState("a", 0, 990, current_bet=10, is_active=True),
            PlayerState("b", 1, 990, current_bet=10, is_active=False),
        ]
        pots = calculate_pots(players)
        total = sum(p.amount for p in pots)
        assert total == 20

    def test_three_way_all_in_different_stacks(self):
        players = [
            PlayerState("a", 0, 0, current_bet=100, is_active=True, is_all_in=True),
            PlayerState("b", 1, 0, current_bet=200, is_active=True, is_all_in=True),
            PlayerState("c", 2, 0, current_bet=300, is_active=True, is_all_in=True),
        ]
        pots = calculate_pots(players)
        total = sum(p.amount for p in pots)
        assert total == 600
        assert len(pots) == 3
        assert pots[0].amount == 300  # 100 from each
        assert set(pots[0].eligible_players) == {"a", "b", "c"}
        assert pots[1].amount == 200  # 100 from b and c
        assert "a" not in pots[1].eligible_players
        assert pots[2].amount == 100  # 100 from c only
        assert pots[2].eligible_players == ["c"]

    def test_merge_pots_empty(self):
        result = merge_pots([], [])
        assert result == []

    def test_merge_pots_same_eligible(self):
        existing = [Pot(amount=100, eligible_players=["a", "b"])]
        new = [Pot(amount=50, eligible_players=["a", "b"])]
        result = merge_pots(existing, new)
        assert len(result) == 1
        assert result[0].amount == 150

    def test_merge_pots_different_eligible(self):
        existing = [Pot(amount=100, eligible_players=["a", "b"])]
        new = [Pot(amount=50, eligible_players=["a"])]
        result = merge_pots(existing, new)
        assert len(result) == 2


class TestGameEngineEdgeCases:
    def test_single_player_raises(self):
        with pytest.raises((ValueError, IndexError)):
            engine = GameEngine(["solo"], 1000, 5, 10)
            engine.start_hand()

    def test_nine_player_game(self):
        ids = [f"p{i}" for i in range(9)]
        engine = GameEngine(ids, 1000, 5, 10)
        engine.start_hand()
        state = engine.state
        assert len(state.players) == 9
        for p in state.players:
            assert len(p.hole_cards) == 2

    def test_very_short_stacks(self):
        engine = GameEngine(["p0", "p1"], {"p0": 5, "p1": 1000}, 5, 10)
        engine.start_hand()
        state = engine.state
        while not state.is_complete:
            current = state.current_player
            if current is None:
                break
            try:
                engine.apply_action(current.player_id, ActionType.ALL_IN)
            except ValueError:
                engine.apply_action(current.player_id, ActionType.CALL)
        assert state.is_complete
        assert sum(p.stack for p in state.players) == 1005

    def test_stack_conservation_after_raise_fold(self):
        engine = GameEngine(["p0", "p1"], 1000, 5, 10)
        engine.start_hand()
        state = engine.state
        current = state.current_player
        engine.apply_action(current.player_id, ActionType.RAISE, 20)
        current = state.current_player
        engine.apply_action(current.player_id, ActionType.FOLD)
        assert state.is_complete
        assert sum(p.stack for p in state.players) == 2000

    def test_consecutive_hands_maintain_stacks(self):
        engine = GameEngine(["p0", "p1"], 1000, 5, 10)
        for _ in range(5):
            active = sum(1 for p in engine.state.players if p.stack > 0)
            if active < 2:
                break
            engine.start_hand()
            state = engine.state
            engine.apply_action(state.current_player.player_id, ActionType.FOLD)
            assert sum(p.stack for p in state.players) == 2000
            engine.rotate_dealer()

    def test_all_in_heads_up_runs_to_completion(self):
        engine = GameEngine(["p0", "p1"], 100, 5, 10)
        engine.start_hand()
        state = engine.state
        current = state.current_player
        engine.apply_action(current.player_id, ActionType.ALL_IN)
        if not state.is_complete:
            current = state.current_player
            engine.apply_action(current.player_id, ActionType.ALL_IN)
        assert state.is_complete
        assert sum(p.stack for p in state.players) == 200

    def test_rotate_dealer_wraps(self):
        engine = GameEngine(["p0", "p1", "p2"], 1000, 5, 10)
        engine.state.dealer_seat = 2
        engine.rotate_dealer()
        assert engine.state.dealer_seat == 0

    def test_rotate_dealer_skips_multiple_busted(self):
        engine = GameEngine(["p0", "p1", "p2", "p3"], 1000, 5, 10)
        engine.state.players[1].stack = 0
        engine.state.players[2].stack = 0
        engine.state.dealer_seat = 0
        engine.rotate_dealer()
        assert engine.state.dealer_seat == 3


class TestLegalActions:
    def test_preflop_sb_can_fold_call_raise(self):
        engine = GameEngine(["p0", "p1"], 1000, 5, 10)
        engine.start_hand()
        state = engine.state
        current = state.current_player
        legal = get_legal_actions(state, current)
        legal_types = {a.action_type for a in legal}
        assert ActionType.FOLD in legal_types
        assert ActionType.CALL in legal_types or ActionType.RAISE in legal_types

    def test_bb_option_can_check(self):
        engine = GameEngine(["p0", "p1"], 1000, 5, 10)
        engine.start_hand()
        state = engine.state
        engine.apply_action(state.current_player.player_id, ActionType.CALL, 5)
        current = state.current_player
        legal = get_legal_actions(state, current)
        legal_types = {a.action_type for a in legal}
        assert ActionType.CHECK in legal_types
