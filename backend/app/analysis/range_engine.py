"""Rule-based opponent range inference and range-percentage to hand-label mapping."""

from __future__ import annotations

from app.engine.game_state import PlayerAction
from app.models.types import ActionType, Street

# Combo counts: pairs=6, suited=4, offsuit=12. Total 1326.
COMBO_COUNT: dict[str, int] = {}

# All 169 hand types in strength order (strongest first), matching frontend HAND_TIER.
# Tier 1-7 from RangeVisualization; tier 8 = remaining hands.
HANDS_BY_STRENGTH: list[str] = [
    # Tier 1
    "AA", "KK", "QQ", "AKs",
    # Tier 2
    "JJ", "TT", "AKo", "AQs",
    # Tier 3
    "99", "88", "AQo", "AJs", "KQs", "ATs", "KJs",
    # Tier 4
    "77", "66", "AJo", "KQo", "KTs", "QJs", "JTs", "A9s", "QTs",
    # Tier 5
    "55", "44", "33", "22", "ATo", "KJo", "QJo", "JTo",
    "A8s", "A7s", "A6s", "A5s", "K9s", "Q9s", "J9s", "T9s", "98s", "87s",
    # Tier 6
    "A4s", "A3s", "A2s", "K8s", "K7s", "K6s", "K5s", "Q8s", "J8s", "T8s",
    "97s", "86s", "76s", "65s", "54s", "A9o", "KTo", "QTo",
    # Tier 7
    "K4s", "K3s", "K2s", "Q7s", "Q6s", "Q5s", "Q4s", "J7s", "T7s", "96s",
    "85s", "75s", "64s", "53s", "43s",
    "A8o", "A7o", "A6o", "A5o", "A4o", "K9o", "Q9o", "J9o", "T9o", "98o",
    # Tier 8 (remaining suited then offsuit)
    "Q3s", "Q2s", "J6s", "J5s", "J4s", "J3s", "J2s", "T6s", "T5s", "T4s", "T3s", "T2s",
    "95s", "94s", "93s", "92s", "84s", "83s", "82s", "74s", "73s", "72s", "63s", "62s", "52s", "42s", "32s",
    "A3o", "A2o", "K8o", "K7o", "K6o", "K5o", "K4o", "K3o", "K2o",
    "Q8o", "Q7o", "Q6o", "Q5o", "Q4o", "Q3o", "Q2o",
    "J8o", "J7o", "J6o", "J5o", "J4o", "J3o", "J2o",
    "T8o", "T7o", "T6o", "T5o", "T4o", "T3o", "T2o",
    "97o", "96o", "95o", "94o", "93o", "92o",
    "87o", "86o", "85o", "84o", "83o", "82o",
    "76o", "75o", "74o", "73o", "72o",
    "65o", "64o", "63o", "62o",
    "54o", "53o", "52o",
    "43o", "42o",
    "32o",
]


def _init_combo_counts() -> None:
    for h in HANDS_BY_STRENGTH:
        if len(h) == 2:
            COMBO_COUNT[h] = 6  # pair
        elif h.endswith("s"):
            COMBO_COUNT[h] = 4
        else:
            COMBO_COUNT[h] = 12


_init_combo_counts()

TOTAL_COMBOS = sum(COMBO_COUNT[h] for h in HANDS_BY_STRENGTH)


def range_pct_to_hand_labels(pct: float) -> set[str]:
    """Return the set of hand labels constituting the top pct% of hands by strength.

    pct is 0-100. Uses combo counts so that "top 18%" is by total combos, not
    number of hand types.
    """
    if pct <= 0:
        return set()
    if pct >= 100:
        return set(HANDS_BY_STRENGTH)
    target_combos = (pct / 100.0) * TOTAL_COMBOS
    cumulative = 0.0
    out: set[str] = set()
    for h in HANDS_BY_STRENGTH:
        out.add(h)
        cumulative += COMBO_COUNT[h]
        if cumulative >= target_combos:
            break
    return out


def infer_range_pct(
    opponent_actions: list[PlayerAction],
    street: Street,
) -> tuple[float, str]:
    """Infer opponent range percentage and description from their actions this hand.

    Returns (range_pct, description). range_pct is 0-100. If no actions, returns
    (100, "Unknown — no actions yet").
    """
    if not opponent_actions:
        return (100.0, "Unknown — no actions yet")

    preflop = [a for a in opponent_actions if a.street == Street.PREFLOP]
    postflop = [a for a in opponent_actions if a.street != Street.PREFLOP]

    range_pct = 100.0
    desc = ""

    for a in preflop:
        if a.action_type == ActionType.FOLD:
            return (0.0, "Folded preflop")
        if a.action_type in (ActionType.RAISE, ActionType.BET):
            if range_pct > 50:
                range_pct = 18.0
                desc = "Preflop raiser — likely strong holdings"
            else:
                range_pct = max(4.0, range_pct * 0.35)
                desc = "3-bet/4-bet — very strong range"
        elif a.action_type == ActionType.CALL:
            range_pct = min(range_pct, 35.0)
            desc = "Called preflop — wide but capped range"
        elif a.action_type == ActionType.ALL_IN:
            range_pct = 6.0
            desc = "All-in preflop — premium or desperate"

    for a in postflop:
        if a.action_type == ActionType.FOLD:
            return (0.0, "Folded")
        if a.action_type in (ActionType.BET, ActionType.RAISE):
            range_pct = max(3.0, range_pct * 0.55)
            desc = "Betting/raising — narrowing to strong hands and bluffs"
        elif a.action_type == ActionType.CALL:
            range_pct = max(5.0, range_pct * 0.75)
            desc = "Calling — draws, medium-strength hands, or trapping"
        elif a.action_type == ActionType.ALL_IN:
            range_pct = max(2.0, range_pct * 0.3)
            desc = "All-in — polarized: very strong or bluff"

    return (round(range_pct, 1), desc or "Range estimated from actions")
