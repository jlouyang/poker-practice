"""Tests for the extracted service modules (hand_history, hand_analysis)."""

from app.engine.game_state import GameState, PlayerAction, PlayerState
from app.models.card import Card
from app.models.types import ActionType, Rank, Street, Suit
from app.services.hand_analysis import _community_for_street, analyze_hand
from app.services.hand_history import extract_winner_ids, extract_winnings


def _card(rank: Rank, suit: Suit) -> Card:
    return Card(rank=rank, suit=suit)


def _make_state_with_showdown():
    state = GameState(
        players=[
            PlayerState(
                player_id="human",
                seat=0,
                stack=1100,
                is_human=True,
                hole_cards=[_card(Rank.ACE, Suit.HEARTS), _card(Rank.KING, Suit.HEARTS)],
            ),
            PlayerState(
                player_id="bot_1",
                seat=1,
                stack=900,
                hole_cards=[_card(Rank.QUEEN, Suit.SPADES), _card(Rank.JACK, Suit.SPADES)],
            ),
        ],
        community_cards=[
            _card(Rank.TEN, Suit.HEARTS),
            _card(Rank.NINE, Suit.HEARTS),
            _card(Rank.EIGHT, Suit.HEARTS),
            _card(Rank.TWO, Suit.CLUBS),
            _card(Rank.THREE, Suit.DIAMONDS),
        ],
        events=[
            {"type": "showdown", "data": {"winners": {"human": {"amount": 200, "hand": "Flush"}}}},
        ],
        action_history=[
            PlayerAction("human", ActionType.POST_BLIND, 5, Street.PREFLOP),
            PlayerAction("bot_1", ActionType.POST_BLIND, 10, Street.PREFLOP),
            PlayerAction("human", ActionType.CALL, 5, Street.PREFLOP),
            PlayerAction("bot_1", ActionType.CHECK, 0, Street.PREFLOP),
        ],
    )
    return state


def _make_state_with_uncontested():
    state = GameState(
        players=[
            PlayerState(
                player_id="human",
                seat=0,
                stack=1030,
                is_human=True,
                hole_cards=[_card(Rank.ACE, Suit.HEARTS), _card(Rank.KING, Suit.HEARTS)],
            ),
            PlayerState(player_id="bot_1", seat=1, stack=970, is_active=False),
        ],
        events=[
            {"type": "win_uncontested", "data": {"player_id": "human", "amount": 30}},
        ],
    )
    return state


class TestExtractWinnerIds:
    def test_showdown(self):
        state = _make_state_with_showdown()
        assert extract_winner_ids(state) == ["human"]

    def test_uncontested(self):
        state = _make_state_with_uncontested()
        assert extract_winner_ids(state) == ["human"]

    def test_empty_events(self):
        state = GameState()
        assert extract_winner_ids(state) == []


class TestExtractWinnings:
    def test_showdown(self):
        state = _make_state_with_showdown()
        assert extract_winnings(state) == {"human": 200}

    def test_uncontested(self):
        state = _make_state_with_uncontested()
        assert extract_winnings(state) == {"human": 30}


class TestCommunityForStreet:
    def test_preflop(self):
        assert _community_for_street(["A", "B", "C", "D", "E"], "preflop") == []

    def test_flop(self):
        assert _community_for_street(["A", "B", "C", "D", "E"], "flop") == ["A", "B", "C"]

    def test_turn(self):
        assert _community_for_street(["A", "B", "C", "D", "E"], "turn") == ["A", "B", "C", "D"]

    def test_river(self):
        assert _community_for_street(["A", "B", "C", "D", "E"], "river") == ["A", "B", "C", "D", "E"]


class TestAnalyzeHand:
    def test_returns_none_without_hole_cards(self):
        state = GameState(
            players=[PlayerState(player_id="human", seat=0, stack=1000, is_human=True)],
        )
        assert analyze_hand(state, "human", {"human": 1000}) is None

    def test_returns_none_without_actions(self):
        state = GameState(
            players=[
                PlayerState(
                    player_id="human",
                    seat=0,
                    stack=1000,
                    is_human=True,
                    hole_cards=[_card(Rank.ACE, Suit.HEARTS), _card(Rank.KING, Suit.HEARTS)],
                ),
            ],
        )
        assert analyze_hand(state, "human", {"human": 1000}) is None

    def test_analyzes_human_decisions(self):
        state = _make_state_with_showdown()
        starting = {"human": 1000, "bot_1": 1000}
        results = analyze_hand(state, "human", starting)
        assert results is not None
        assert len(results) >= 1
        for r in results:
            assert r["player_id"] == "human"
            assert "equity" in r
            assert "score" in r
            assert r["score"] in ("good", "mistake", "blunder")

    def test_returns_none_for_unknown_player(self):
        state = _make_state_with_showdown()
        assert analyze_hand(state, "nonexistent", {}) is None
