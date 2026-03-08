"""Tests for analysis engine: equity calculation, decision scoring, and EV."""

from app.analysis.equity import calculate_equity, calculate_equity_detailed
from app.analysis.ev import calculate_action_ev
from app.analysis.scoring import _compute_score, analyze_hand, score_decision
from app.models.card import Card
from app.models.types import ActionType


def c(s: str) -> Card:
    return Card.from_str(s)


def cards(s: str) -> list[Card]:
    return [c(x) for x in s.split()]


class TestEquityCalculation:
    def test_pocket_aces_high_equity(self):
        equity = calculate_equity(cards("Ah As"), [], num_opponents=1, num_simulations=500)
        assert equity > 0.75

    def test_72o_low_equity(self):
        equity = calculate_equity(cards("7h 2c"), [], num_opponents=1, num_simulations=500)
        assert equity < 0.45

    def test_equity_between_zero_and_one(self):
        equity = calculate_equity(cards("Kh Qh"), cards("Jh Th 2c"), num_opponents=1)
        assert 0.0 <= equity <= 1.0

    def test_equity_on_river_known_board(self):
        equity = calculate_equity(
            cards("Ah Kh"),
            cards("Qh Jh Th 2c 3d"),
            num_opponents=1,
            num_simulations=200,
        )
        assert equity > 0.95

    def test_negative_opponents_clamped_to_one(self):
        equity = calculate_equity(cards("Ah As"), [], num_opponents=-1, num_simulations=200)
        assert 0.0 <= equity <= 1.0

    def test_zero_opponents_clamped_to_one(self):
        equity = calculate_equity(cards("Ah As"), [], num_opponents=0, num_simulations=200)
        assert 0.0 <= equity <= 1.0

    def test_many_opponents_reduces_equity(self):
        eq1 = calculate_equity(cards("Ah Kh"), [], num_opponents=1, num_simulations=500)
        eq5 = calculate_equity(cards("Ah Kh"), [], num_opponents=5, num_simulations=500)
        assert eq1 > eq5

    def test_too_many_opponents_handled_gracefully(self):
        equity = calculate_equity(
            cards("Ah As"),
            cards("Kh Qh Jh Th 9h"),
            num_opponents=20,
            num_simulations=100,
        )
        assert 0.0 <= equity <= 1.0


class TestEquityDetailed:
    def test_returns_all_fields(self):
        result = calculate_equity_detailed(cards("Ah Kh"), cards("Qh Jh 2c"), num_simulations=200)
        assert "equity" in result
        assert "simulations" in result
        assert "wins" in result
        assert "ties" in result
        assert "losses" in result
        assert "current_hand" in result
        assert "hand_distribution" in result

    def test_wins_ties_losses_sum(self):
        result = calculate_equity_detailed(cards("Ah As"), [], num_simulations=500)
        assert result["wins"] + result["ties"] + result["losses"] == result["simulations"]

    def test_current_hand_on_flop(self):
        result = calculate_equity_detailed(cards("Ah As"), cards("Ac Kh 2d"), num_simulations=200)
        assert result["current_hand"] is not None

    def test_current_hand_preflop_is_none(self):
        result = calculate_equity_detailed(cards("Ah As"), [], num_simulations=200)
        assert result["current_hand"] is None


class TestScoreDecision:
    def test_good_fold(self):
        result = score_decision(
            hole_cards=cards("2h 7c"),
            community_cards=cards("Ah Kd Qs"),
            action_type=ActionType.FOLD,
            amount=0,
            pot_before_action=100,
            to_call=50,
            num_opponents=1,
        )
        assert result["score"] == "good"
        assert result["optimal_action"] == "fold"

    def test_good_call_with_equity(self):
        result = score_decision(
            hole_cards=cards("Ah As"),
            community_cards=cards("Kh 2d 5c"),
            action_type=ActionType.CALL,
            amount=10,
            pot_before_action=100,
            to_call=10,
            num_opponents=1,
        )
        assert result["score"] in ("good", "mistake")
        assert result["equity"] > 0.5

    def test_blunder_fold_with_strong_hand(self):
        result = score_decision(
            hole_cards=cards("Ah Kh"),
            community_cards=cards("Qh Jh Th"),
            action_type=ActionType.FOLD,
            amount=0,
            pot_before_action=100,
            to_call=10,
            num_opponents=1,
        )
        assert result["score"] == "blunder"

    def test_includes_reasoning(self):
        result = score_decision(
            hole_cards=cards("Ah As"),
            community_cards=[],
            action_type=ActionType.RAISE,
            amount=30,
            pot_before_action=15,
            to_call=10,
            num_opponents=1,
        )
        assert len(result["reasoning"]) > 0
        assert len(result["recommendation"]) > 0

    def test_include_details_adds_equity_details(self):
        result = score_decision(
            hole_cards=cards("Ah Kh"),
            community_cards=cards("Qh 2c 3d"),
            action_type=ActionType.BET,
            amount=20,
            pot_before_action=30,
            to_call=0,
            num_opponents=1,
            include_details=True,
        )
        assert "equity_details" in result
        details = result["equity_details"]
        assert "simulations" in details
        assert "decision_steps" in details
        assert "hand_distribution" in details

    def test_check_when_no_bet(self):
        result = score_decision(
            hole_cards=cards("8h 5c"),
            community_cards=cards("Ah Kd Qs"),
            action_type=ActionType.CHECK,
            amount=0,
            pot_before_action=20,
            to_call=0,
            num_opponents=1,
        )
        assert result["score"] == "good"


class TestComputeScore:
    def test_matching_action_is_good(self):
        assert _compute_score(ActionType.FOLD, "fold", 0.1, 0.3) == "good"
        assert _compute_score(ActionType.CALL, "call", 0.5, 0.3) == "good"

    def test_fold_with_high_equity_is_blunder(self):
        assert _compute_score(ActionType.FOLD, "call", 0.7, 0.3) == "blunder"

    def test_call_with_very_low_equity_is_blunder(self):
        assert _compute_score(ActionType.CALL, "fold", 0.05, 0.3) == "blunder"

    def test_call_when_raise_optimal_is_good(self):
        assert _compute_score(ActionType.CALL, "raise", 0.7, 0.3) == "good"

    def test_check_when_bet_optimal_is_mistake(self):
        assert _compute_score(ActionType.CHECK, "bet", 0.8, 0.0) == "mistake"


class TestActionEV:
    def test_fold_ev_is_zero(self):
        ev = calculate_action_ev(
            cards("2h 7c"),
            cards("Ah Kd Qs"),
            ActionType.FOLD,
            0,
            pot_before=100,
            to_call=50,
            num_opponents=1,
        )
        assert ev == 0.0

    def test_check_ev_positive_with_equity(self):
        ev = calculate_action_ev(
            cards("Ah As"),
            cards("Kh 2d 5c"),
            ActionType.CHECK,
            0,
            pot_before=100,
            to_call=0,
            num_opponents=1,
        )
        assert ev > 0

    def test_call_ev_with_strong_hand(self):
        ev = calculate_action_ev(
            cards("Ah Kh"),
            cards("Qh Jh Th"),
            ActionType.CALL,
            50,
            pot_before=100,
            to_call=50,
            num_opponents=1,
        )
        assert ev > 0

    def test_raise_ev_considers_fold_equity(self):
        ev = calculate_action_ev(
            cards("Ah As"),
            [],
            ActionType.RAISE,
            30,
            pot_before=15,
            to_call=10,
            num_opponents=1,
        )
        assert ev > 0


class TestAnalyzeHand:
    def test_empty_actions(self):
        result = analyze_hand(
            cards("Ah Kh"),
            {"preflop": []},
            [],
            [],
            [],
            [],
        )
        assert result == []

    def test_skips_post_blind(self):
        actions = [
            {"player_id": "p0", "action_type": "post_blind", "street": "preflop", "amount": 5},
            {"player_id": "p0", "action_type": "call", "street": "preflop", "amount": 5},
        ]
        result = analyze_hand(
            cards("Ah Kh"),
            {"preflop": []},
            actions,
            [1, 1],
            [15, 15],
            [5, 5],
        )
        assert len(result) == 1
        assert result[0]["action_type"] == "call"
