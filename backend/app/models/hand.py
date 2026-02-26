from __future__ import annotations

from dataclasses import dataclass

import phevaluator

from app.models.card import Card
from app.models.types import HandRanking, HAND_RANKING_NAMES

# phevaluator rank boundaries (rank 1 = best, 7462 = worst)
_RANK_BOUNDARIES = [
    (1, 10, HandRanking.STRAIGHT_FLUSH),   # includes royal flush at rank 1
    (11, 166, HandRanking.FOUR_OF_A_KIND),
    (167, 322, HandRanking.FULL_HOUSE),
    (323, 1599, HandRanking.FLUSH),
    (1600, 1609, HandRanking.STRAIGHT),
    (1610, 2467, HandRanking.THREE_OF_A_KIND),
    (2468, 3325, HandRanking.TWO_PAIR),
    (3326, 6185, HandRanking.ONE_PAIR),
    (6186, 7462, HandRanking.HIGH_CARD),
]


@dataclass(frozen=True, slots=True)
class HandResult:
    rank: int
    hand_ranking: HandRanking
    hand_name: str

    @property
    def is_royal_flush(self) -> bool:
        return self.rank == 1

    def beats(self, other: HandResult) -> bool:
        """Lower rank = stronger hand in phevaluator."""
        return self.rank < other.rank

    def ties(self, other: HandResult) -> bool:
        return self.rank == other.rank


def _classify_rank(rank: int) -> HandRanking:
    if rank == 1:
        return HandRanking.ROYAL_FLUSH
    for lo, hi, ranking in _RANK_BOUNDARIES:
        if lo <= rank <= hi:
            return ranking
    raise ValueError(f"Unknown phevaluator rank: {rank}")


def _card_to_str(card: Card) -> str:
    return str(card)


def evaluate_hand(hole_cards: list[Card], community_cards: list[Card]) -> HandResult:
    """Evaluate a poker hand from hole cards + community cards.

    Accepts 5, 6, or 7 total cards (2 hole + 3-5 community).
    """
    all_cards = hole_cards + community_cards
    if not (5 <= len(all_cards) <= 7):
        raise ValueError(f"Need 5-7 total cards, got {len(all_cards)}")

    card_strs = [_card_to_str(c) for c in all_cards]
    rank = phevaluator.evaluate_cards(*card_strs)
    hand_ranking = _classify_rank(rank)
    hand_name = (
        "Royal Flush" if hand_ranking == HandRanking.ROYAL_FLUSH
        else HAND_RANKING_NAMES[hand_ranking]
    )
    return HandResult(rank=rank, hand_ranking=hand_ranking, hand_name=hand_name)


def compare_hands(
    hands: list[tuple[list[Card], list[Card]]],
) -> list[list[int]]:
    """Compare multiple hands, returning groups of winner indices (handles ties).

    Args:
        hands: list of (hole_cards, community_cards) tuples

    Returns:
        List of groups, where the first group contains the winner indices.
        e.g. [[0, 2], [1]] means players 0 and 2 tie for best, player 1 loses.
    """
    results = [evaluate_hand(hole, comm) for hole, comm in hands]
    indexed = sorted(enumerate(results), key=lambda x: x[1].rank)

    groups: list[list[int]] = []
    current_group: list[int] = []
    current_rank: int | None = None

    for idx, result in indexed:
        if result.rank != current_rank:
            if current_group:
                groups.append(current_group)
            current_group = [idx]
            current_rank = result.rank
        else:
            current_group.append(idx)

    if current_group:
        groups.append(current_group)

    return groups
