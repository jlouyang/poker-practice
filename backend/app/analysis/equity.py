"""Monte Carlo equity calculator."""

from __future__ import annotations

import random

from app.models.card import Card, Deck
from app.models.hand import evaluate_hand
from app.models.types import Rank, Suit


ALL_CARDS = [Card(rank=r, suit=s) for s in Suit for r in Rank]


def calculate_equity(
    hole_cards: list[Card],
    community_cards: list[Card],
    num_opponents: int = 1,
    num_simulations: int = 2000,
) -> float:
    """Estimate hand equity via Monte Carlo simulation.

    Returns a float between 0.0 and 1.0 representing the probability
    of winning (ties count as partial wins).
    """
    known = set(str(c) for c in hole_cards + community_cards)
    available = [c for c in ALL_CARDS if str(c) not in known]

    wins = 0.0
    valid_sims = 0

    for _ in range(num_simulations):
        deck = list(available)
        random.shuffle(deck)

        idx = 0
        board_needed = 5 - len(community_cards)
        sim_community = list(community_cards) + deck[idx : idx + board_needed]
        idx += board_needed

        opponent_hands = []
        for _ in range(num_opponents):
            opp = deck[idx : idx + 2]
            idx += 2
            opponent_hands.append(opp)

        my_result = evaluate_hand(hole_cards, sim_community)

        beaten_all = True
        tied_count = 0
        for opp in opponent_hands:
            opp_result = evaluate_hand(opp, sim_community)
            if opp_result.rank < my_result.rank:
                beaten_all = False
                break
            elif opp_result.rank == my_result.rank:
                tied_count += 1

        if beaten_all:
            if tied_count > 0:
                wins += 1.0 / (tied_count + 1)
            else:
                wins += 1.0

        valid_sims += 1

    return wins / max(valid_sims, 1)
