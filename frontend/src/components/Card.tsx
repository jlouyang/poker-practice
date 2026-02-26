import React from "react";

interface CardProps {
  card?: string;
  faceDown?: boolean;
  small?: boolean;
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

const Card: React.FC<CardProps> = ({ card, faceDown = false, small = false }) => {
  const w = small ? 44 : 56;
  const h = small ? 64 : 80;

  if (faceDown || !card) {
    return (
      <div
        style={{
          width: w,
          height: h,
          borderRadius: 6,
          background: "linear-gradient(135deg, #2c3e50, #3d566e)",
          border: "2px solid #4a6785",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: small ? 14 : 18,
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
      }}
    >
      <span>{rank}</span>
      <span style={{ fontSize: small ? 16 : 20 }}>{symbol}</span>
    </div>
  );
};

export default Card;
