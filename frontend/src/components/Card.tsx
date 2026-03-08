/**
 * Playing card component — renders a face-up card or face-down back.
 *
 * Parses the card string (e.g., "Ah" → Ace of Hearts) and displays the
 * rank and suit symbol in the appropriate color. Supports small and
 * standard sizes for use in player seats vs. community cards.
 */
import type { CSSProperties } from "react";

interface CardProps {
  card?: string;
  faceDown?: boolean;
  small?: boolean;
  animationDelay?: number;
}

const SUIT_SYMBOLS: Record<string, string> = {
  h: "\u2665",
  d: "\u2666",
  c: "\u2663",
  s: "\u2660",
};

const SUIT_COLORS: Record<string, string> = {
  h: "#e74c3c",
  d: "#3498db",
  c: "#1a1a1a",
  s: "#1a1a1a",
};

function parseCard(card: string): { rank: string; suit: string } {
  const suit = card.slice(-1);
  const rank = card.slice(0, -1);
  return { rank, suit };
}

function Card({ card, faceDown = false, small = false, animationDelay }: CardProps) {
  const w = small ? 44 : 56;
  const h = small ? 64 : 80;
  const animate = animationDelay !== undefined;

  const animStyle: CSSProperties = animate
    ? { animation: `card-reveal 0.35s ease-out ${animationDelay}s both` }
    : {};

  if (faceDown || !card) {
    return (
      <div
        style={{
          width: w,
          height: h,
          borderRadius: 6,
          background: "linear-gradient(135deg, var(--border-default), #3d566e)",
          border: "2px solid var(--border-input)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: small ? 14 : 18,
          ...animStyle,
        }}
      >
        🂠
      </div>
    );
  }

  const { rank, suit } = parseCard(card);
  const color = SUIT_COLORS[suit] || "#fff";
  const symbol = SUIT_SYMBOLS[suit] || suit;

  return (
    <div
      style={{
        width: w,
        height: h,
        borderRadius: 6,
        background: "#f8f9fa",
        border: "2px solid #dee2e6",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        color,
        fontWeight: 700,
        fontSize: small ? 14 : 18,
        fontFamily: "monospace",
        gap: 2,
        boxShadow: "0 2px 4px rgba(0,0,0,0.3)",
        ...animStyle,
      }}
    >
      <span>{rank}</span>
      <span style={{ fontSize: small ? 16 : 20 }}>{symbol}</span>
    </div>
  );
}

export default Card;
