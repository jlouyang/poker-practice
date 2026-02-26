"""Per-player session statistics: VPIP, PFR, Aggression Factor."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PlayerStats:
    player_id: str
    hands_played: int = 0
    vpip_hands: int = 0  # Voluntarily put $ in pot (preflop, excluding blinds)
    pfr_hands: int = 0   # Preflop raise
    total_bets_raises: int = 0
    total_calls: int = 0
    total_folds: int = 0
    pots_won: int = 0
    total_winnings: int = 0

    @property
    def vpip(self) -> float:
        """Voluntarily Put $ In Pot: % of hands player put money in preflop."""
        return (self.vpip_hands / max(self.hands_played, 1)) * 100

    @property
    def pfr(self) -> float:
        """Preflop Raise: % of hands player raised preflop."""
        return (self.pfr_hands / max(self.hands_played, 1)) * 100

    @property
    def aggression_factor(self) -> float:
        """Aggression Factor: (bets + raises) / calls."""
        return self.total_bets_raises / max(self.total_calls, 1)

    def to_dict(self) -> dict:
        return {
            "player_id": self.player_id,
            "hands_played": self.hands_played,
            "vpip": round(self.vpip, 1),
            "pfr": round(self.pfr, 1),
            "af": round(self.aggression_factor, 1),
            "pots_won": self.pots_won,
            "total_winnings": self.total_winnings,
        }


class SessionStatsTracker:
    """Tracks stats across a session for all players."""

    def __init__(self) -> None:
        self._stats: dict[str, PlayerStats] = {}

    def get_stats(self, player_id: str) -> PlayerStats:
        if player_id not in self._stats:
            self._stats[player_id] = PlayerStats(player_id=player_id)
        return self._stats[player_id]

    def get_all_stats(self) -> dict[str, dict]:
        return {pid: s.to_dict() for pid, s in self._stats.items()}

    def record_hand(
        self,
        player_ids: list[str],
        preflop_actions: list[dict],
        all_actions: list[dict],
        winner_ids: list[str],
        winnings: dict[str, int],
    ) -> None:
        for pid in player_ids:
            stats = self.get_stats(pid)
            stats.hands_played += 1

        for a in preflop_actions:
            pid = a["player_id"]
            action = a["action_type"]
            stats = self.get_stats(pid)

            if action in ("call", "raise", "bet", "all_in"):
                stats.vpip_hands += 1
            if action in ("raise", "bet"):
                stats.pfr_hands += 1

        for a in all_actions:
            pid = a["player_id"]
            action = a["action_type"]
            if action == "post_blind":
                continue

            stats = self.get_stats(pid)
            if action in ("bet", "raise"):
                stats.total_bets_raises += 1
            elif action == "call":
                stats.total_calls += 1
            elif action == "fold":
                stats.total_folds += 1

        for pid in winner_ids:
            stats = self.get_stats(pid)
            stats.pots_won += 1

        for pid, amount in winnings.items():
            stats = self.get_stats(pid)
            stats.total_winnings += amount
