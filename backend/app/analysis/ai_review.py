"""AI-generated session review using Claude API."""

from __future__ import annotations

import json
import logging
import os

logger = logging.getLogger(__name__)


def generate_session_review(
    total_hands: int,
    win_rate: float,
    mistakes: int,
    blunders: int,
    player_stats: dict,
    sample_decisions: list[dict],
) -> str:
    """Generate a natural-language session review.

    Falls back to template-based review if Claude API is unavailable.
    """
    try:
        import anthropic

        api_key = os.environ.get("ANTHROPIC_API_KEY", "")
        if not api_key:
            return _template_review(total_hands, win_rate, mistakes, blunders, player_stats)

        client = anthropic.Anthropic(api_key=api_key)

        system_msg = (
            "You are a poker coach reviewing a training session. "
            "Give a 3-4 sentence review covering: "
            "1) Overall assessment, 2) One specific strength observed, "
            "3) One specific area for improvement, 4) A concrete suggestion for the next session. "
            "Be encouraging but honest."
        )

        user_msg = (
            f"Session stats:\n"
            f"- Hands played: {total_hands}\n"
            f"- Win rate: {win_rate:.1f}%\n"
            f"- Mistakes: {mistakes}\n"
            f"- Blunders: {blunders}\n"
            f"- VPIP: {player_stats.get('vpip', 'N/A')}%\n"
            f"- PFR: {player_stats.get('pfr', 'N/A')}%\n"
            f"- Aggression Factor: {player_stats.get('af', 'N/A')}\n\n"
            f"Sample decisions: {json.dumps(sample_decisions[:5])}"
        )

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=500,
            system=system_msg,
            messages=[{"role": "user", "content": user_msg}],
        )
        return response.content[0].text.strip()

    except Exception as e:
        logger.warning("Claude API unavailable for session review, using template: %s", e)
        return _template_review(total_hands, win_rate, mistakes, blunders, player_stats)


def _template_review(
    total_hands: int,
    win_rate: float,
    mistakes: int,
    blunders: int,
    player_stats: dict,
) -> str:
    """Template-based fallback review."""
    parts = []

    parts.append(f"You played {total_hands} hands with a {win_rate:.1f}% win rate.")

    if blunders == 0 and mistakes <= 2:
        parts.append("Excellent decision-making this session!")
    elif blunders <= 1:
        parts.append("Solid play overall with room for minor improvements.")
    else:
        parts.append(f"You had {blunders} blunders that significantly impacted your results.")

    vpip = player_stats.get("vpip", 0)
    if isinstance(vpip, (int, float)):
        if vpip > 35:
            parts.append("Consider tightening your starting hand selection -- you're playing too many hands.")
        elif vpip < 15:
            parts.append("You might be playing too tight. Try opening up your range in late position.")
        else:
            parts.append("Your hand selection looks reasonable.")

    af = player_stats.get("af", 0)
    if isinstance(af, (int, float)):
        if af < 1.0:
            parts.append("Try being more aggressive -- betting and raising more when you have strong hands.")
        elif af > 3.0:
            parts.append("Your aggression is high. Make sure you're balancing your aggressive lines with some calls.")

    return " ".join(parts)
