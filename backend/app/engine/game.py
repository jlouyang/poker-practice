from __future__ import annotations

from app.engine.game_state import GameState, PlayerState, PlayerAction, Pot
from app.engine.pot import calculate_pots, merge_pots
from app.engine.validators import get_legal_actions, validate_action
from app.models.card import Card, Deck
from app.models.hand import evaluate_hand
from app.models.types import ActionType, Street


class GameEngine:
    def __init__(
        self,
        player_ids: list[str],
        starting_stacks: dict[str, int] | int = 1000,
        small_blind: int = 1,
        big_blind: int = 2,
        human_ids: set[str] | None = None,
    ):
        if len(player_ids) < 2 or len(player_ids) > 9:
            raise ValueError("Need 2-9 players")

        stacks = (
            starting_stacks
            if isinstance(starting_stacks, dict)
            else {pid: starting_stacks for pid in player_ids}
        )
        human_ids = human_ids or set()

        self.state = GameState(
            players=[
                PlayerState(
                    player_id=pid,
                    seat=i,
                    stack=stacks[pid],
                    is_human=pid in human_ids,
                )
                for i, pid in enumerate(player_ids)
            ],
            small_blind=small_blind,
            big_blind=big_blind,
        )
        self._deck = Deck()

    @property
    def hand_complete(self) -> bool:
        return self.state.is_complete

    def start_hand(self) -> GameState:
        """Start a new hand: shuffle, deal, post blinds."""
        state = self.state
        state.hand_number += 1
        state.is_complete = False
        state.community_cards = []
        state.action_history = []
        state.events = []
        state.street = Street.PREFLOP
        state.last_raise_size = state.big_blind
        state.min_raise = state.big_blind
        state.last_raiser_idx = None

        # Reset player state; skip busted players
        for p in state.players:
            if p.stack <= 0:
                p.is_active = False
                p.hole_cards = []
                continue
            p.is_active = True
            p.is_all_in = False
            p.current_bet = 0
            p.has_acted = False
            p.hole_cards = []

        active = [p for p in state.players if p.is_active]
        if len(active) < 2:
            state.is_complete = True
            return state

        state.pots = [Pot(amount=0, eligible_players=[p.player_id for p in active])]

        self._deck = Deck()

        for p in active:
            p.hole_cards = self._deck.deal(2)

        self._emit("deal", {"hand_number": state.hand_number})

        self._post_blinds()
        self._set_first_to_act_preflop()

        return state

    def apply_action(self, player_id: str, action_type: ActionType, amount: int = 0) -> GameState:
        """Apply a player action to the game state."""
        state = self.state
        player = self._get_player(player_id)

        if state.is_complete:
            raise ValueError("Hand is complete")

        current = state.current_player
        if current is None or current.player_id != player_id:
            raise ValueError(f"Not {player_id}'s turn (current: {current.player_id if current else 'none'})")

        if action_type == ActionType.ALL_IN:
            amount = player.stack
            legal = get_legal_actions(state, player)
            legal_types = {a.action_type for a in legal}
            if ActionType.ALL_IN in legal_types:
                pass  # keep as ALL_IN
            elif ActionType.RAISE in legal_types:
                action_type = ActionType.RAISE
            elif ActionType.BET in legal_types:
                action_type = ActionType.BET
            elif ActionType.CALL in legal_types:
                action_type = ActionType.CALL

        is_valid, error = validate_action(state, player, action_type, amount)
        if not is_valid:
            raise ValueError(error)

        self._execute_action(player, action_type, amount)

        player.has_acted = True
        state.action_history.append(
            PlayerAction(player_id=player_id, action_type=action_type, amount=amount, street=state.street)
        )
        self._emit("action", {
            "player_id": player_id,
            "action": action_type,
            "amount": amount,
            "street": state.street,
        })

        if self._check_hand_over():
            return state

        if self._is_betting_round_over():
            self._end_betting_round()
            if not state.is_complete:
                self._advance_street()
        else:
            self._advance_to_next_player()

        return state

    def get_legal_actions(self, player_id: str) -> list:
        player = self._get_player(player_id)
        return get_legal_actions(self.state, player)

    def rotate_dealer(self) -> None:
        """Advance dealer button for next hand."""
        state = self.state
        n = len(state.players)
        seat = state.dealer_seat
        for _ in range(n):
            seat = (seat + 1) % n
            if state.players[seat].stack > 0:
                state.dealer_seat = seat
                return

    # --- Private methods ---

    def _get_player(self, player_id: str) -> PlayerState:
        for p in self.state.players:
            if p.player_id == player_id:
                return p
        raise ValueError(f"Player {player_id} not found")

    def _post_blinds(self) -> None:
        state = self.state
        active_seats = [i for i, p in enumerate(state.players) if p.is_active]
        n_active = len(active_seats)
        dealer_pos = state.dealer_seat

        # Find SB and BB positions among active players
        if n_active == 2:
            sb_idx = dealer_pos
            bb_idx = self._next_active_seat(sb_idx)
        else:
            sb_idx = self._next_active_seat(dealer_pos)
            bb_idx = self._next_active_seat(sb_idx)

        sb_player = state.players[sb_idx]
        bb_player = state.players[bb_idx]

        sb_amount = min(state.small_blind, sb_player.stack)
        self._place_bet(sb_player, sb_amount)
        state.action_history.append(
            PlayerAction(sb_player.player_id, ActionType.POST_BLIND, sb_amount, Street.PREFLOP)
        )
        self._emit("blind", {"player_id": sb_player.player_id, "amount": sb_amount, "type": "small"})

        bb_amount = min(state.big_blind, bb_player.stack)
        self._place_bet(bb_player, bb_amount)
        state.action_history.append(
            PlayerAction(bb_player.player_id, ActionType.POST_BLIND, bb_amount, Street.PREFLOP)
        )
        self._emit("blind", {"player_id": bb_player.player_id, "amount": bb_amount, "type": "big"})

    def _place_bet(self, player: PlayerState, amount: int) -> None:
        actual = min(amount, player.stack)
        player.stack -= actual
        player.current_bet += actual
        if player.stack == 0:
            player.is_all_in = True

    def _execute_action(self, player: PlayerState, action_type: ActionType, amount: int) -> None:
        state = self.state

        if action_type == ActionType.FOLD:
            player.is_active = False
            return

        if action_type == ActionType.CHECK:
            return

        if action_type == ActionType.CALL:
            to_call = state.current_bet_to_match - player.current_bet
            actual_call = min(to_call, player.stack)
            self._place_bet(player, actual_call)
            return

        if action_type in (ActionType.BET, ActionType.RAISE, ActionType.ALL_IN):
            if action_type == ActionType.ALL_IN:
                amount = player.stack

            new_total_bet = player.current_bet + amount
            raise_size = new_total_bet - state.current_bet_to_match

            if raise_size > 0:
                is_full_raise = raise_size >= state.last_raise_size
                state.last_raise_size = max(raise_size, state.last_raise_size)
                state.last_raiser_idx = self.state.players.index(player)

                if is_full_raise:
                    for p in state.players:
                        if p.player_id != player.player_id and p.can_act:
                            p.has_acted = False

            self._place_bet(player, amount)

    def _next_active_seat(self, seat: int) -> int:
        n = len(self.state.players)
        for _ in range(n):
            seat = (seat + 1) % n
            if self.state.players[seat].is_active:
                return seat
        return seat

    def _next_actionable_seat(self, seat: int) -> int:
        n = len(self.state.players)
        for _ in range(n):
            seat = (seat + 1) % n
            if self.state.players[seat].can_act:
                return seat
        return -1

    def _set_first_to_act_preflop(self) -> None:
        state = self.state
        active_seats = [i for i, p in enumerate(state.players) if p.is_active]

        if len(active_seats) == 2:
            # Heads-up: SB (dealer) acts first preflop
            sb_idx = state.dealer_seat
            bb_idx = self._next_active_seat(sb_idx)
            state.current_player_idx = sb_idx
            # But if SB is all-in from blind, advance
            if not state.players[sb_idx].can_act:
                state.current_player_idx = bb_idx
        else:
            bb_idx = self._next_active_seat(self._next_active_seat(state.dealer_seat))
            utg = self._next_actionable_seat(bb_idx)
            if utg == -1:
                self._end_hand_early()
                return
            state.current_player_idx = utg

    def _set_first_to_act_postflop(self) -> None:
        state = self.state
        first = self._next_actionable_seat(state.dealer_seat)
        if first == -1:
            self._run_out_board()
            return
        state.current_player_idx = first

    def _advance_to_next_player(self) -> None:
        state = self.state
        current = state.current_player_idx
        next_seat = self._next_actionable_seat(current)
        if next_seat == -1 or next_seat == current:
            if self._is_betting_round_over():
                self._end_betting_round()
                if not state.is_complete:
                    self._advance_street()
        else:
            state.current_player_idx = next_seat

    def _is_betting_round_over(self) -> bool:
        state = self.state
        actionable = state.players_who_can_act

        if len(actionable) == 0:
            return True

        if len(actionable) == 1:
            p = actionable[0]
            to_call = state.current_bet_to_match - p.current_bet
            if to_call == 0 and p.has_acted:
                return True
            if to_call == 0 and state.street == Street.PREFLOP:
                # BB special case: hasn't acted yet, gets option
                return p.has_acted
            if to_call > 0:
                return False
            return p.has_acted

        bet_to_match = state.current_bet_to_match
        for p in actionable:
            if not p.has_acted:
                return False
            if p.current_bet != bet_to_match:
                return False
        return True

    def _check_hand_over(self) -> bool:
        state = self.state
        active = state.active_players

        if len(active) == 1:
            self._award_pot_to_last_standing(active[0])
            return True

        if len(active) == 0:
            state.is_complete = True
            return True

        return False

    def _end_betting_round(self) -> None:
        state = self.state
        new_pots = calculate_pots(state.players)
        state.pots = merge_pots(state.pots, new_pots)

        for p in state.players:
            p.current_bet = 0

    def _advance_street(self) -> None:
        state = self.state

        # Check if only one or zero players can still act
        actionable = state.players_who_can_act
        if len(actionable) <= 1:
            self._run_out_board()
            return

        for p in state.players:
            p.has_acted = False

        state.last_raise_size = state.big_blind
        state.last_raiser_idx = None

        if state.street == Street.PREFLOP:
            state.street = Street.FLOP
            state.community_cards.extend(self._deck.deal(3))
            self._emit("community", {"street": "flop", "cards": [str(c) for c in state.community_cards]})
        elif state.street == Street.FLOP:
            state.street = Street.TURN
            state.community_cards.extend(self._deck.deal(1))
            self._emit("community", {"street": "turn", "cards": [str(c) for c in state.community_cards]})
        elif state.street == Street.TURN:
            state.street = Street.RIVER
            state.community_cards.extend(self._deck.deal(1))
            self._emit("community", {"street": "river", "cards": [str(c) for c in state.community_cards]})
        elif state.street == Street.RIVER:
            self._showdown()
            return

        self._set_first_to_act_postflop()

    def _run_out_board(self) -> None:
        """Deal remaining community cards when no more betting is possible."""
        state = self.state
        cards_needed = 5 - len(state.community_cards)
        if cards_needed > 0:
            state.community_cards.extend(self._deck.deal(cards_needed))
            self._emit("community", {"street": "runout", "cards": [str(c) for c in state.community_cards]})
        self._showdown()

    def _showdown(self) -> None:
        state = self.state
        state.street = Street.SHOWDOWN

        # Collect any remaining bets into pots
        remaining_bets = sum(p.current_bet for p in state.players)
        if remaining_bets > 0:
            self._end_betting_round()

        active = state.active_players
        community = state.community_cards

        results = {}
        for p in active:
            results[p.player_id] = evaluate_hand(p.hole_cards, community)

        winnings: dict[str, int] = {p.player_id: 0 for p in state.players}

        for pot in state.pots:
            if pot.amount == 0:
                continue

            eligible_in_pot = [pid for pid in pot.eligible_players if pid in results]
            if not eligible_in_pot:
                continue

            # Find best hand among eligible
            best_rank = min(results[pid].rank for pid in eligible_in_pot)
            winners = [pid for pid in eligible_in_pot if results[pid].rank == best_rank]

            share = pot.amount // len(winners)
            remainder = pot.amount % len(winners)

            for i, pid in enumerate(winners):
                winnings[pid] += share + (1 if i < remainder else 0)

        for p in state.players:
            if winnings[p.player_id] > 0:
                p.stack += winnings[p.player_id]

        self._emit("showdown", {
            "winners": {pid: {"amount": amt, "hand": results[pid].hand_name}
                       for pid, amt in winnings.items() if amt > 0 and pid in results},
            "hands": {p.player_id: {"cards": [str(c) for c in p.hole_cards],
                                     "result": results[p.player_id].hand_name}
                     for p in active},
            "community": [str(c) for c in community],
        })

        state.is_complete = True

    def _award_pot_to_last_standing(self, winner: PlayerState) -> None:
        state = self.state

        # Collect remaining bets
        total = sum(p.amount for p in state.pots) + sum(p.current_bet for p in state.players)
        winner.stack += total
        state.pots = []
        for p in state.players:
            p.current_bet = 0

        self._emit("win_uncontested", {
            "player_id": winner.player_id,
            "amount": total,
        })
        state.is_complete = True

    def _end_hand_early(self) -> None:
        self.state.is_complete = True

    def _emit(self, event_type: str, data: dict) -> None:
        self.state.events.append({"type": event_type, "data": data})
