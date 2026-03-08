"""Monte Carlo equity calculator."""

from __future__ import annotations

import random
from collections import Counter

from app.models.card import Card
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
    return calculate_equity_detailed(hole_cards, community_cards, num_opponents, num_simulations)["equity"]


def calculate_equity_detailed(
    hole_cards: list[Card],
    community_cards: list[Card],
    num_opponents: int = 1,
    num_simulations: int = 2000,
) -> dict:
    """Monte Carlo equity with full breakdown.

    Returns dict with equity, win/tie/loss counts, and hand distribution.
    """
    num_opponents = max(1, num_opponents)

    known = set(str(c) for c in hole_cards + community_cards)
    available = [c for c in ALL_CARDS if str(c) not in known]

    board_needed = 5 - len(community_cards)
    cards_per_sim = board_needed + num_opponents * 2
    if cards_per_sim > len(available):
        num_opponents = max(1, (len(available) - board_needed) // 2)
        cards_per_sim = board_needed + num_opponents * 2

    wins = 0.0
    win_count = 0
    tie_count = 0
    loss_count = 0
    valid_sims = 0
    hand_type_counts: Counter[str] = Counter()

    current_hand_name = None
    if len(community_cards) >= 3:
        current_result = evaluate_hand(hole_cards, community_cards)
        current_hand_name = current_result.hand_name

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
        hand_type_counts[my_result.hand_name] += 1

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
                tie_count += 1
            else:
                wins += 1.0
                win_count += 1
        else:
            loss_count += 1

        valid_sims += 1

    equity = wins / max(valid_sims, 1)

    top_hands = [
        {"hand": name, "pct": round(count / max(valid_sims, 1) * 100, 1)}
        for name, count in hand_type_counts.most_common(5)
    ]

    return {
        "equity": equity,
        "simulations": valid_sims,
        "wins": win_count,
        "ties": tie_count,
        "losses": loss_count,
        "current_hand": current_hand_name,
        "hand_distribution": top_hands,
    }
