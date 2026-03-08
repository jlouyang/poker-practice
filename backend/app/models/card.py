"""Card and Deck primitives for a standard 52-card deck.

Card  — immutable (rank, suit) pair. Parseable from short strings like "Ah", "Td", "10h".
Deck  — 52 cards with Fisher-Yates shuffle using cryptographic randomness (secrets module).
"""

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
        if not isinstance(s, str) or len(s) < 2 or len(s) > 3:
            raise ValueError(f"Invalid card string: {s!r} (expected 2-3 chars like 'Ah' or '10h')")
        rank_ch = s[:-1]
        suit_ch = s[-1].lower()
        rank_map = {
            "2": Rank.TWO,
            "3": Rank.THREE,
            "4": Rank.FOUR,
            "5": Rank.FIVE,
            "6": Rank.SIX,
            "7": Rank.SEVEN,
            "8": Rank.EIGHT,
            "9": Rank.NINE,
            "T": Rank.TEN,
            "t": Rank.TEN,
            "J": Rank.JACK,
            "j": Rank.JACK,
            "Q": Rank.QUEEN,
            "q": Rank.QUEEN,
            "K": Rank.KING,
            "k": Rank.KING,
            "A": Rank.ACE,
            "a": Rank.ACE,
            "10": Rank.TEN,
        }
        suit_map = {"c": Suit.CLUBS, "d": Suit.DIAMONDS, "h": Suit.HEARTS, "s": Suit.SPADES}
        if rank_ch not in rank_map:
            raise ValueError(f"Invalid rank: {rank_ch!r} in card string {s!r}")
        if suit_ch not in suit_map:
            raise ValueError(f"Invalid suit: {suit_ch!r} in card string {s!r}")
        return cls(rank=rank_map[rank_ch], suit=suit_map[suit_ch])


class Deck:
    def __init__(self) -> None:
        self._cards: list[Card] = [Card(rank=r, suit=s) for s in Suit for r in Rank]
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
