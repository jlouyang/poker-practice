"""Decision scoring: rate each player action against equity-optimal play."""

from __future__ import annotations

from app.analysis.equity import calculate_equity, calculate_equity_detailed
from app.models.card import Card
from app.models.types import ActionType


def _pct(v: float) -> int:
    return round(v * 100)


def score_decision(
    hole_cards: list[Card],
    community_cards: list[Card],
    action_type: ActionType,
    amount: int,
    pot_before_action: int,
    to_call: int,
    num_opponents: int,
    include_details: bool = False,
) -> dict:
    """Score a single decision.

    Returns dict with equity, optimal_action suggestion, score label,
    reasoning, and recommendation. If include_details is True, adds
    a full Monte Carlo breakdown under 'equity_details'.
    """
    if include_details:
        eq_data = calculate_equity_detailed(hole_cards, community_cards, num_opponents, num_simulations=1000)
        equity = eq_data["equity"]
    else:
        equity = calculate_equity(hole_cards, community_cards, num_opponents, num_simulations=1000)
        eq_data = None

    pot_odds = to_call / max(pot_before_action + to_call, 1) if to_call > 0 else 0.0

    if to_call > 0:
        if equity > pot_odds + 0.15:
            optimal = "raise"
        elif equity > pot_odds - 0.05:
            optimal = "call"
        else:
            optimal = "fold"
    else:
        if equity > 0.65:
            optimal = "bet"
        elif equity > 0.3:
            optimal = "check"
        else:
            optimal = "check"

    score = _compute_score(action_type, optimal, equity, pot_odds)
    reasoning = _build_reasoning(action_type, optimal, score, equity, pot_odds, to_call, pot_before_action)
    recommendation = _build_recommendation(optimal, equity, pot_odds, to_call)

    result = {
        "equity": round(equity, 3),
        "pot_odds": round(pot_odds, 3),
        "optimal_action": optimal,
        "score": score,
        "reasoning": reasoning,
        "recommendation": recommendation,
    }

    if include_details and eq_data:
        decision_steps = _build_decision_steps(equity, pot_odds, to_call, optimal)
        result["equity_details"] = {
            "simulations": eq_data["simulations"],
            "wins": eq_data["wins"],
            "ties": eq_data["ties"],
            "losses": eq_data["losses"],
            "current_hand": eq_data["current_hand"],
            "hand_distribution": eq_data["hand_distribution"],
            "hole_cards": [str(c) for c in hole_cards],
            "community_cards": [str(c) for c in community_cards],
            "num_opponents": num_opponents,
            "pot": pot_before_action,
            "to_call": to_call,
            "decision_steps": decision_steps,
        }

    return result


def _compute_score(
    actual: ActionType,
    optimal: str,
    equity: float,
    pot_odds: float,
) -> str:
    """Label a decision as good, mistake, or blunder."""
    actual_str = actual.value

    if actual_str == optimal:
        return "good"

    if actual_str == "fold" and equity > pot_odds + 0.2:
        return "blunder"

    if actual_str in ("call", "raise", "bet") and equity < pot_odds * 0.5:
        return "blunder"

    if actual_str == "fold" and equity > pot_odds:
        return "mistake"

    if actual_str in ("call",) and optimal == "raise":
        return "good"

    if actual_str in ("check",) and optimal == "bet":
        return "mistake"

    return "mistake"


def _build_reasoning(
    actual: ActionType,
    optimal: str,
    score: str,
    equity: float,
    pot_odds: float,
    to_call: int,
    pot: int,
) -> str:
    """Generate a static explanation for why the decision was scored this way."""
    actual_str = actual.value
    eq = _pct(equity)
    po = _pct(pot_odds)

    if score == "good":
        if actual_str == "fold":
            return f"Correct fold. Your equity was only {eq}% and you needed {po}% to call profitably."
        if actual_str == "call":
            if optimal == "raise":
                return f"Acceptable call. With {eq}% equity vs {po}% pot odds, calling is fine — raising would also be strong here."
            return f"Good call. Your {eq}% equity comfortably beats the {po}% pot odds needed to call."
        if actual_str in ("raise", "bet"):
            if to_call > 0:
                return f"Good raise. With {eq}% equity, you're well ahead and applying pressure is correct."
            return f"Good bet. With {eq}% equity, you should be building the pot with your strong hand."
        if actual_str == "check":
            return f"Smart check. With {eq}% equity, controlling the pot size is the right approach."
        return f"Good play with {eq}% equity."

    if score == "blunder":
        if actual_str == "fold":
            return (
                f"Major missed opportunity. You folded with {eq}% equity when you only needed "
                f"{po}% to call profitably. You were well ahead and left significant value on the table."
            )
        if actual_str in ("call", "raise", "bet"):
            return (
                f"Costly mistake. You put chips in with only {eq}% equity when you needed at least "
                f"{po}% to break even. This is a significant leak over time."
            )
        return f"Blunder with {eq}% equity."

    # mistake
    if actual_str == "fold":
        return (
            f"Unprofitable fold. Your equity was {eq}% and pot odds required only {po}% to call. "
            f"You had enough equity to continue."
        )
    if actual_str == "check" and optimal == "bet":
        return (
            f"Missed value. With {eq}% equity, you should bet to build the pot and charge "
            f"opponents with weaker hands to continue."
        )
    if actual_str in ("call",) and optimal == "fold":
        return (
            f"Loose call. Your {eq}% equity didn't justify calling — you needed at least "
            f"{po}% to break even against this bet."
        )
    if actual_str in ("raise", "bet") and optimal == "fold":
        return (
            f"Overplayed hand. With only {eq}% equity, putting more chips in was too aggressive. "
            f"You needed at least {po}% equity to continue profitably."
        )
    if actual_str in ("raise", "bet") and optimal in ("call", "check"):
        return (
            f"Sizing error. With {eq}% equity, your hand is worth continuing with but raising "
            f"bloats the pot and puts you in a tough spot against stronger ranges."
        )
    if actual_str == "call" and optimal == "raise":
        return (
            f"Passive play. With {eq}% equity well above the {po}% pot odds, you should raise "
            f"to build value and deny opponents a cheap draw."
        )
    return f"Suboptimal play with {eq}% equity — the better move was to {optimal}."


def _build_recommendation(
    optimal: str,
    equity: float,
    pot_odds: float,
    to_call: int,
) -> str:
    """Generate a static recommendation for what the player should have done."""
    eq = _pct(equity)
    po = _pct(pot_odds)

    if optimal == "fold":
        return f"Fold here. With only {eq}% equity, you don't have the odds to continue."
    if optimal == "call":
        return f"Call. Your {eq}% equity beats the {po}% pot odds — calling is profitable long-term."
    if optimal == "raise":
        return f"Raise for value. At {eq}% equity you're well ahead — build the pot and apply pressure."
    if optimal == "bet":
        return f"Bet to build value. With {eq}% equity, charge your opponents to see the next card."
    if optimal == "check":
        if equity < 0.3:
            return f"Check and consider folding to a bet. At {eq}% equity, your hand is weak."
        return f"Check to control the pot. At {eq}% equity, there's no need to bloat the pot."
    return f"The optimal play was to {optimal}."


def _build_decision_steps(equity: float, pot_odds: float, to_call: int, optimal: str) -> list[str]:
    """Build a step-by-step explanation of the decision logic."""
    eq = _pct(equity)
    po = _pct(pot_odds)
    steps = []

    steps.append(f"Equity = {eq}% (from Monte Carlo simulation of 1,000 random runouts)")

    if to_call > 0:
        steps.append(f"Pot odds = to_call / (pot + to_call) = {po}%")
        steps.append(f"Compare: equity ({eq}%) vs pot odds ({po}%)")
        if equity > pot_odds + 0.15:
            steps.append("Equity exceeds pot odds by >15% → raise for value")
        elif equity > pot_odds - 0.05:
            steps.append("Equity is close to pot odds (within 5%) → call is profitable")
        else:
            steps.append("Equity is below pot odds → fold to avoid losing chips long-term")
    else:
        steps.append("No bet to call (can check for free)")
        if equity > 0.65:
            steps.append(f"Equity ({eq}%) > 65% → bet to build the pot with a strong hand")
        elif equity > 0.3:
            steps.append(f"Equity ({eq}%) is moderate (30-65%) → check to control pot size")
        else:
            steps.append(f"Equity ({eq}%) < 30% → check with a weak hand")

    steps.append(f"Optimal action: {optimal}")
    return steps


def analyze_hand(
    hole_cards: list[Card],
    community_cards_by_street: dict[str, list[Card]],
    actions: list[dict],
    num_opponents_by_action: list[int],
    pot_by_action: list[int],
    to_call_by_action: list[int],
) -> list[dict]:
    """Analyze all human actions in a hand."""
    results = []

    for i, action in enumerate(actions):
        if action["action_type"] in ("post_blind",):
            continue

        street = action["street"]
        community = community_cards_by_street.get(street, [])
        num_opp = num_opponents_by_action[i] if i < len(num_opponents_by_action) else 1
        pot = pot_by_action[i] if i < len(pot_by_action) else 0
        to_call = to_call_by_action[i] if i < len(to_call_by_action) else 0

        result = score_decision(
            hole_cards=hole_cards,
            community_cards=community,
            action_type=ActionType(action["action_type"]),
            amount=action.get("amount", 0),
            pot_before_action=pot,
            to_call=to_call,
            num_opponents=num_opp,
        )
        result["player_id"] = action["player_id"]
        result["street"] = street
        result["action_type"] = action["action_type"]
        result["amount"] = action.get("amount", 0)
        results.append(result)

    return results
