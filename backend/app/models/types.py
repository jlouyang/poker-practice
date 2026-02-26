from enum import IntEnum, StrEnum


class Suit(StrEnum):
    CLUBS = "c"
    DIAMONDS = "d"
    HEARTS = "h"
    SPADES = "s"


class Rank(IntEnum):
    TWO = 2
    THREE = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

    @property
    def short(self) -> str:
        names = {10: "T", 11: "J", 12: "Q", 13: "K", 14: "A"}
        return names.get(self.value, str(self.value))


class HandRanking(IntEnum):
    HIGH_CARD = 0
    ONE_PAIR = 1
    TWO_PAIR = 2
    THREE_OF_A_KIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOUR_OF_A_KIND = 7
    STRAIGHT_FLUSH = 8
    ROYAL_FLUSH = 9


HAND_RANKING_NAMES = {
    HandRanking.HIGH_CARD: "High Card",
    HandRanking.ONE_PAIR: "One Pair",
    HandRanking.TWO_PAIR: "Two Pair",
    HandRanking.THREE_OF_A_KIND: "Three of a Kind",
    HandRanking.STRAIGHT: "Straight",
    HandRanking.FLUSH: "Flush",
    HandRanking.FULL_HOUSE: "Full House",
    HandRanking.FOUR_OF_A_KIND: "Four of a Kind",
    HandRanking.STRAIGHT_FLUSH: "Straight Flush",
    HandRanking.ROYAL_FLUSH: "Royal Flush",
}


class Street(StrEnum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"


class ActionType(StrEnum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"
    POST_BLIND = "post_blind"
