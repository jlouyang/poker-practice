from __future__ import annotations

import secrets
from dataclasses import dataclass

from app.models.types import Rank, Suit


@dataclass(frozen=True, slots=True)
class Card:
    rank: Rank
    suit: Suit

    def __str__(self) -> str:
        return f"{self.rank.short}{self.suit.value}"

    def __repr__(self) -> str:
        return f"Card({self})"

    @classmethod
    def from_str(cls, s: str) -> Card:
        """Parse 'Ah', '2c', 'Td' etc."""
        rank_ch = s[:-1]
        suit_ch = s[-1]
        rank_map = {
            "2": Rank.TWO, "3": Rank.THREE, "4": Rank.FOUR, "5": Rank.FIVE,
            "6": Rank.SIX, "7": Rank.SEVEN, "8": Rank.EIGHT, "9": Rank.NINE,
            "T": Rank.TEN, "J": Rank.JACK, "Q": Rank.QUEEN, "K": Rank.KING,
            "A": Rank.ACE,
        }
        suit_map = {"c": Suit.CLUBS, "d": Suit.DIAMONDS, "h": Suit.HEARTS, "s": Suit.SPADES}
        return cls(rank=rank_map[rank_ch], suit=suit_map[suit_ch])


class Deck:
    def __init__(self) -> None:
        self._cards: list[Card] = [
            Card(rank=r, suit=s) for s in Suit for r in Rank
        ]
        self.shuffle()

    def shuffle(self) -> None:
        """Fisher-Yates shuffle using cryptographically secure randomness."""
        cards = self._cards
        for i in range(len(cards) - 1, 0, -1):
            j = secrets.randbelow(i + 1)
            cards[i], cards[j] = cards[j], cards[i]

    def deal(self, n: int = 1) -> list[Card]:
        if n > len(self._cards):
            raise ValueError(f"Cannot deal {n} cards, only {len(self._cards)} remaining")
        dealt = self._cards[:n]
        self._cards = self._cards[n:]
        return dealt

    def deal_one(self) -> Card:
        return self.deal(1)[0]

    @property
    def remaining(self) -> int:
        return len(self._cards)
