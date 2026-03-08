"""Side pot calculation for multi-way all-in scenarios.

calculate_pots() — builds main pot and side pots from player bets
merge_pots()     — folds new-round pots into existing pots, combining
                   pots with identical eligible-player sets

Called by GameEngine at the end of each betting round before resetting bets.
"""

from __future__ import annotations

from app.engine.game_state import PlayerState, Pot


def calculate_pots(players: list[PlayerState]) -> list[Pot]:
    """Calculate main pot and side pots from player bets.

    Works for any number of all-in players with different stack commitments.
    Called at the end of each betting round before resetting bets.
    """
    active_with_bets = [p for p in players if p.current_bet > 0 and p.is_active]
    folded_bets = sum(p.current_bet for p in players if not p.is_active)

    if not active_with_bets and folded_bets == 0:
        return []

    sorted_all_in = sorted(set(p.current_bet for p in players if p.current_bet > 0 and p.is_all_in and p.is_active))

    if not sorted_all_in:
        eligible = [p.player_id for p in players if p.is_active]
        total = sum(p.current_bet for p in players)
        return [Pot(amount=total, eligible_players=eligible)]

    pots: list[Pot] = []
    prev_level = 0

    for level in sorted_all_in:
        contribution_per = level - prev_level
        if contribution_per <= 0:
            continue
        pot_amount = 0
        eligible = []
        for p in players:
            if p.current_bet > prev_level:
                pot_amount += min(p.current_bet - prev_level, contribution_per)
            if p.is_active and p.current_bet >= level:
                eligible.append(p.player_id)

        if pot_amount > 0:
            pots.append(Pot(amount=pot_amount, eligible_players=eligible))
        prev_level = level

    remaining_bets = 0
    for p in players:
        if p.current_bet > prev_level:
            remaining_bets += p.current_bet - prev_level

    if remaining_bets > 0:
        final_eligible = [p.player_id for p in players if p.is_active and p.current_bet > prev_level]
        pots.append(Pot(amount=remaining_bets, eligible_players=final_eligible))

    return pots


def merge_pots(existing: list[Pot], new_pots: list[Pot]) -> list[Pot]:
    """Merge new round pots into existing pots."""
    if not existing:
        return new_pots

    if not new_pots:
        return existing

    result = list(existing)
    for np in new_pots:
        merged = False
        for ep in result:
            if set(ep.eligible_players) == set(np.eligible_players):
                ep.amount += np.amount
                merged = True
                break
        if not merged:
            result.append(np)

    return result
