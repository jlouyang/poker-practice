"""LLM Coach Bot: uses Claude API for decisions and post-hand Q&A."""

from __future__ import annotations

import json
import os
import random
from dataclasses import dataclass, field

from app.analysis.equity import calculate_equity
from app.bots.interface import BotAction, BotStrategy
from app.bots.shark import SharkBot
from app.bots.visible_state import VisibleGameState
from app.models.types import ActionType

# Lazy import to avoid requiring anthropic package if not using LLM bot
_anthropic_client = None


def _get_client():
    global _anthropic_client
    if _anthropic_client is None:
        try:
            import anthropic
            _anthropic_client = anthropic.Anthropic(
                api_key=os.environ.get("ANTHROPIC_API_KEY", "")
            )
        except ImportError:
            return None
        except Exception:
            return None
    return _anthropic_client


@dataclass
class HandContext:
    """Stores context for post-hand Q&A."""
    game_state_description: str = ""
    decisions: list[dict] = field(default_factory=list)
    equity_data: list[dict] = field(default_factory=list)


class LLMCoachBot(BotStrategy):
    """Claude-powered bot that can explain its reasoning after each hand."""

    def __init__(self, tightness: int = 55, aggression: int = 60):
        self._tightness = tightness
        self._aggression = aggression
        self._fallback = SharkBot(tightness, aggression)
        self._hand_context = HandContext()
        self._coach_mode = False

    @property
    def name(self) -> str:
        return "Coach"

    @property
    def tier(self) -> int:
        return 4

    @property
    def hand_context(self) -> HandContext:
        return self._hand_context

    def set_coach_mode(self, enabled: bool) -> None:
        self._coach_mode = enabled

    def decide(self, state: VisibleGameState) -> BotAction:
        equity = calculate_equity(
            state.my_hole_cards,
            state.community_cards,
            state.num_active_players - 1,
            num_simulations=1500,
        )

        client = _get_client()
        if client is None or not os.environ.get("ANTHROPIC_API_KEY"):
            action = self._fallback.decide(state)
            self._record_decision(state, action, equity, "fallback")
            return action

        try:
            action = self._llm_decide(state, equity, client)
            self._record_decision(state, action, equity, "llm")
            return action
        except Exception:
            action = self._fallback.decide(state)
            self._record_decision(state, action, equity, "fallback_error")
            return action

    def _llm_decide(self, state: VisibleGameState, equity: float, client) -> BotAction:
        prompt = self._build_decision_prompt(state, equity)

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        return self._parse_action(text, state)

    def _build_decision_prompt(self, state: VisibleGameState, equity: float) -> str:
        hole = " ".join(str(c) for c in state.my_hole_cards)
        community = " ".join(str(c) for c in state.community_cards) if state.community_cards else "none"
        to_call = state.to_call

        return f"""You are a poker bot. Decide your action.

Hole cards: {hole}
Community: {community}
Street: {state.street}
Pot: {state.pot_total}
To call: {to_call}
Your stack: {state.my_stack}
Your equity: {equity:.1%}
Active opponents: {state.num_active_players - 1}

Respond with EXACTLY one line in format: ACTION AMOUNT
Valid actions: fold, check, call, bet, raise, all_in
Examples: "fold 0", "call 20", "raise 60", "bet 30"
"""

    def _parse_action(self, text: str, state: VisibleGameState) -> BotAction:
        line = text.strip().split("\n")[0].lower()
        parts = line.split()

        if not parts:
            return BotAction(ActionType.FOLD)

        action_str = parts[0]
        amount = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0

        action_map = {
            "fold": ActionType.FOLD,
            "check": ActionType.CHECK,
            "call": ActionType.CALL,
            "bet": ActionType.BET,
            "raise": ActionType.RAISE,
            "all_in": ActionType.ALL_IN,
        }

        action_type = action_map.get(action_str, ActionType.FOLD)
        if action_type == ActionType.CALL and amount == 0:
            amount = state.to_call

        return BotAction(action_type, min(amount, state.my_stack))

    def _record_decision(
        self, state: VisibleGameState, action: BotAction, equity: float, source: str
    ) -> None:
        self._hand_context.decisions.append({
            "street": state.street.value,
            "action": action.action_type.value,
            "amount": action.amount,
            "equity": round(equity, 3),
            "source": source,
            "pot": state.pot_total,
            "to_call": state.to_call,
        })
        self._hand_context.equity_data.append({
            "street": state.street.value,
            "equity": round(equity, 3),
        })

    def ask_about_hand(self, question: str) -> str:
        """Post-hand Q&A: answer a question about the hand using Claude."""
        client = _get_client()
        if client is None or not os.environ.get("ANTHROPIC_API_KEY"):
            return self._generate_offline_explanation(question)

        context = json.dumps(self._hand_context.decisions, indent=2)
        prompt = f"""You are a poker coach reviewing a hand you just played. Here are your decisions:

{context}

The student asks: {question}

Give a clear, strategic explanation in 2-3 sentences. Reference pot odds, equity, and position when relevant."""

        try:
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=400,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text.strip()
        except Exception:
            return self._generate_offline_explanation(question)

    def _generate_offline_explanation(self, question: str) -> str:
        if not self._hand_context.decisions:
            return "No hand context available."

        explanations = []
        for d in self._hand_context.decisions:
            eq = d["equity"]
            action = d["action"]
            street = d["street"]
            pot = d["pot"]
            to_call = d["to_call"]

            if action == "fold":
                explanations.append(
                    f"On the {street}, I folded with {eq:.0%} equity. "
                    f"The pot odds weren't favorable enough to continue."
                )
            elif action in ("bet", "raise"):
                explanations.append(
                    f"On the {street}, I {'bet' if action == 'bet' else 'raised'} "
                    f"with {eq:.0%} equity into a pot of {pot}. "
                    f"This was {'a value bet' if eq > 0.6 else 'a semi-bluff/thin value bet'}."
                )
            elif action == "call":
                pot_odds = to_call / max(pot + to_call, 1)
                explanations.append(
                    f"On the {street}, I called {to_call} with {eq:.0%} equity "
                    f"(pot odds: {pot_odds:.0%}). "
                    f"{'A profitable call.' if eq > pot_odds else 'Slightly speculative but with implied odds.'}"
                )

        return " ".join(explanations) if explanations else "I played this hand using equity-based decisions."

    def reset_context(self) -> None:
        self._hand_context = HandContext()
