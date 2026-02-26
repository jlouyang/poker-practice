"""Comprehensive tests for card primitives and hand evaluation."""

from app.models.card import Card, Deck
from app.models.hand import evaluate_hand, compare_hands, HandResult
from app.models.types import HandRanking, Rank, Suit


def c(s: str) -> Card:
    return Card.from_str(s)


def cards(s: str) -> list[Card]:
    return [c(x) for x in s.split()]


class TestCard:
    def test_from_str(self):
        card = Card.from_str("Ah")
        assert card.rank == Rank.ACE
        assert card.suit == Suit.HEARTS

    def test_str_roundtrip(self):
        for s in ["2c", "Td", "Jh", "Qs", "Kd", "Ah"]:
            assert str(Card.from_str(s)) == s

    def test_frozen(self):
        card = Card.from_str("Ah")
        try:
            card.rank = Rank.KING  # type: ignore
            assert False, "Should raise"
        except AttributeError:
            pass


class TestDeck:
    def test_52_cards(self):
        deck = Deck()
        assert deck.remaining == 52

    def test_deal_reduces_remaining(self):
        deck = Deck()
        deck.deal(5)
        assert deck.remaining == 47

    def test_deal_unique(self):
        deck = Deck()
        all_cards = deck.deal(52)
        assert len(set(str(c) for c in all_cards)) == 52

    def test_shuffle_randomness(self):
        decks = [Deck() for _ in range(5)]
        first_cards = [str(d.deal_one()) for d in decks]
        # Extremely unlikely all 5 decks produce the same first card
        assert len(set(first_cards)) > 1


class TestHandEvaluation:
    def test_royal_flush(self):
        result = evaluate_hand(cards("Ah Kh"), cards("Qh Jh Th"))
        assert result.hand_ranking == HandRanking.ROYAL_FLUSH
        assert result.hand_name == "Royal Flush"
        assert result.is_royal_flush

    def test_straight_flush(self):
        result = evaluate_hand(cards("9h 8h"), cards("7h 6h 5h"))
        assert result.hand_ranking == HandRanking.STRAIGHT_FLUSH

    def test_four_of_a_kind(self):
        result = evaluate_hand(cards("Ah Ad"), cards("Ac As Kh"))
        assert result.hand_ranking == HandRanking.FOUR_OF_A_KIND

    def test_full_house(self):
        result = evaluate_hand(cards("Ah Ad"), cards("Ac Kh Kd"))
        assert result.hand_ranking == HandRanking.FULL_HOUSE

    def test_flush(self):
        result = evaluate_hand(cards("Ah Jh"), cards("8h 5h 3h"))
        assert result.hand_ranking == HandRanking.FLUSH

    def test_straight(self):
        result = evaluate_hand(cards("Ah Kd"), cards("Qh Js Th"))
        assert result.hand_ranking == HandRanking.STRAIGHT

    def test_three_of_a_kind(self):
        result = evaluate_hand(cards("Ah Ad"), cards("Ac Kh Qs"))
        assert result.hand_ranking == HandRanking.THREE_OF_A_KIND

    def test_two_pair(self):
        result = evaluate_hand(cards("Ah Ad"), cards("Kh Kd Qs"))
        assert result.hand_ranking == HandRanking.TWO_PAIR

    def test_one_pair(self):
        result = evaluate_hand(cards("Ah Ad"), cards("Kh Qd Js"))
        assert result.hand_ranking == HandRanking.ONE_PAIR

    def test_high_card(self):
        result = evaluate_hand(cards("Ah Kd"), cards("Qh Js 9c"))
        assert result.hand_ranking == HandRanking.HIGH_CARD

    def test_7_card_evaluation(self):
        result = evaluate_hand(cards("Ah Ad"), cards("Ac Kh Kd 2s 3c"))
        assert result.hand_ranking == HandRanking.FULL_HOUSE

    def test_7_card_picks_best(self):
        # Hole: Ah Kh, Board: Qh Jh Th 2c 3d -> Royal flush
        result = evaluate_hand(cards("Ah Kh"), cards("Qh Jh Th 2c 3d"))
        assert result.hand_ranking == HandRanking.ROYAL_FLUSH

    def test_wheel_straight(self):
        # A-2-3-4-5 straight
        result = evaluate_hand(cards("Ah 2d"), cards("3h 4s 5c"))
        assert result.hand_ranking == HandRanking.STRAIGHT

    def test_beats(self):
        rf = evaluate_hand(cards("Ah Kh"), cards("Qh Jh Th"))
        hc = evaluate_hand(cards("2c 7d"), cards("5h 9s Jc"))
        assert rf.beats(hc)
        assert not hc.beats(rf)

    def test_ties(self):
        h1 = evaluate_hand(cards("Ah Kd"), cards("Qh Js Th"))
        h2 = evaluate_hand(cards("As Kc"), cards("Qd Jc Ts"))
        assert h1.ties(h2)


class TestKickerResolution:
    def test_pair_with_different_kickers(self):
        better = evaluate_hand(cards("Ah Ad"), cards("Kh Qd Js"))
        worse = evaluate_hand(cards("Ah Ad"), cards("Kh Qd 2s"))
        assert better.beats(worse)

    def test_two_pair_kicker(self):
        better = evaluate_hand(cards("Ah Ad"), cards("Kh Kd Qs"))
        worse = evaluate_hand(cards("Ah Ad"), cards("Kh Kd 2s"))
        assert better.beats(worse)

    def test_trips_kicker(self):
        better = evaluate_hand(cards("Ah Ad"), cards("Ac Kh Qs"))
        worse = evaluate_hand(cards("Ah Ad"), cards("Ac Kh 2s"))
        assert better.beats(worse)

    def test_high_card_kicker(self):
        better = evaluate_hand(cards("Ah Kd"), cards("Qh Js 9c"))
        worse = evaluate_hand(cards("Ah Kd"), cards("Qh Js 8c"))
        assert better.beats(worse)


class TestCompareHands:
    def test_single_winner(self):
        hands = [
            (cards("Ah Kh"), cards("Qh Jh Th")),  # Royal flush
            (cards("2c 7d"), cards("Qh Jh Th")),   # Pair (7s dont help)
        ]
        groups = compare_hands(hands)
        assert groups[0] == [0]

    def test_tie(self):
        community = cards("Ah Kd Qh Js Th")
        hands = [
            (cards("2c 3d"), community),
            (cards("4c 5d"), community),
        ]
        groups = compare_hands(hands)
        assert sorted(groups[0]) == [0, 1]

    def test_three_players_ranked(self):
        community = cards("2h 5d 9c Js Kh")
        hands = [
            (cards("Ah Ad"), community),  # Pair of aces - best
            (cards("Kd Ks"), community),  # Pair of kings (trips actually with board K)
            (cards("3c 4d"), community),  # High card - worst
        ]
        groups = compare_hands(hands)
        # Kd Ks + board Kh = three kings, beats pair of aces
        assert 1 in groups[0]
