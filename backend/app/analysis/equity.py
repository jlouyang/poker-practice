"""Monte Carlo equity calculator."""

from __future__ import annotations

import itertools
import random
from collections import Counter

from app.models.card import Card
from app.models.hand import evaluate_hand
from app.models.types import Rank, Suit

ALL_CARDS = [Card(rank=r, suit=s) for s in Suit for r in Rank]

RANK_FROM_CHAR = {
    "A": Rank.ACE, "K": Rank.KING, "Q": Rank.QUEEN, "J": Rank.JACK,
    "T": Rank.TEN, "9": Rank.NINE, "8": Rank.EIGHT, "7": Rank.SEVEN,
    "6": Rank.SIX, "5": Rank.FIVE, "4": Rank.FOUR, "3": Rank.THREE, "2": Rank.TWO,
}


def _two_cards_to_label(c1: Card, c2: Card) -> str:
    """Return the 169 hand label for two cards, e.g. 'AKs', 'AKo', 'AA'."""
    r1, r2 = (c1.rank, c2.rank) if c1.rank >= c2.rank else (c2.rank, c1.rank)
    hi, lo = r1.short, r2.short
    if r1 == r2:
        return hi + lo
    suited = c1.suit == c2.suit
    return hi + lo + ("s" if suited else "o")


def _valid_combos_from_cards(
    cards: list[Card],
    range_hand_labels: set[str],
) -> list[tuple[Card, Card]]:
    """Return all (c1, c2) pairs from cards whose hand label is in range_hand_labels."""
    out: list[tuple[Card, Card]] = []
    for c1, c2 in itertools.combinations(cards, 2):
        if c1 is c2:
            continue
        label = _two_cards_to_label(c1, c2)
        if label in range_hand_labels:
            out.append((c1, c2))
    return out


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


def calculate_equity_vs_range(
    hole_cards: list[Card],
    community_cards: list[Card],
    range_hand_labels: set[str],
    num_simulations: int = 2000,
) -> float:
    """Estimate equity vs one opponent whose hand is in the given range (Monte Carlo)."""
    return calculate_equity_vs_range_detailed(
        hole_cards, community_cards, range_hand_labels, num_simulations
    )["equity"]


def calculate_equity_vs_range_detailed(
    hole_cards: list[Card],
    community_cards: list[Card],
    range_hand_labels: set[str],
    num_simulations: int = 2000,
) -> dict:
    """Monte Carlo equity vs one opponent with hand sampled from range_hand_labels.

    For each simulation: complete the board from available deck, then sample one
    opponent hand from all (c1, c2) in the remaining deck that form a hand in range.
    Returns same shape as calculate_equity_detailed.
    """
    if not range_hand_labels:
        return calculate_equity_detailed(
            hole_cards, community_cards, num_opponents=1, num_simulations=num_simulations
        )

    known = set(str(c) for c in hole_cards + community_cards)
    available = [c for c in ALL_CARDS if str(c) not in known]
    board_needed = 5 - len(community_cards)
    if board_needed < 0 or board_needed + 2 > len(available):
        return calculate_equity_detailed(
            hole_cards, community_cards, num_opponents=1, num_simulations=num_simulations
        )

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
        sim_community = list(community_cards) + deck[idx : idx + board_needed]
        idx += board_needed
        rest = deck[idx:]

        valid_combos = _valid_combos_from_cards(rest, range_hand_labels)
        if not valid_combos:
            continue
        opp_c1, opp_c2 = random.choice(valid_combos)
        opponent_hand = [opp_c1, opp_c2]

        my_result = evaluate_hand(hole_cards, sim_community)
        hand_type_counts[my_result.hand_name] += 1
        opp_result = evaluate_hand(opponent_hand, sim_community)

        if my_result.rank > opp_result.rank:
            wins += 1.0
            win_count += 1
        elif my_result.rank == opp_result.rank:
            wins += 0.5
            tie_count += 1
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
