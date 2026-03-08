import { useState } from "react";
import Modal from "./Modal";

const RANKS = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"] as const;

type Position = "UTG" | "MP" | "CO" | "BTN" | "SB" | "BB";

const ALL_POSITIONS: Position[] = ["UTG", "MP", "CO", "BTN", "SB", "BB"];

/**
 * Maps each hand to the earliest position it should be opened from.
 * Positions ordered tightest → loosest: UTG, MP, CO, BTN, SB
 * (BB defends vs raises so it's different — we mark hands to defend)
 *
 * Index: 0=UTG, 1=MP, 2=CO, 3=BTN, 4=SB, 5=BB(defend)
 * Value is the minimum position index where the hand is playable.
 * null = never open (or fold).
 */
const HAND_POSITION_MAP: Record<string, number> = {
  // Premium — open from everywhere
  AA: 0, KK: 0, QQ: 0, AKs: 0, AKo: 0,
  // Strong
  JJ: 0, TT: 0, AQs: 0, AQo: 1, AJs: 1, KQs: 1,
  // Good — open from MP+
  "99": 1, ATs: 1, KJs: 1, AJo: 2, KQo: 2,
  // Playable — open from CO+
  "88": 2, "77": 2, A9s: 2, KTs: 2, QJs: 2, JTs: 2, ATo: 2, QTs: 2,
  // Wide — open from BTN+
  "66": 3, "55": 3, A8s: 3, A7s: 3, A6s: 3, A5s: 3, K9s: 3, Q9s: 3,
  J9s: 3, T9s: 3, "98s": 3, "87s": 3, KJo: 3, QJo: 3, JTo: 3,
  // BTN/SB only
  "44": 3, "33": 3, "22": 3, A4s: 3, A3s: 3, A2s: 3,
  K8s: 4, K7s: 4, K6s: 4, K5s: 4, Q8s: 4, J8s: 4, T8s: 4,
  "97s": 4, "86s": 4, "76s": 4, "65s": 4, "54s": 4,
  A9o: 4, KTo: 4, QTo: 4,
  // BB defend only
  K4s: 5, K3s: 5, K2s: 5, Q7s: 5, Q6s: 5, Q5s: 5, Q4s: 5,
  J7s: 5, T7s: 5, "96s": 5, "85s": 5, "75s": 5, "64s": 5, "53s": 5, "43s": 5,
  A8o: 5, A7o: 5, A6o: 5, A5o: 5, A4o: 5,
  K9o: 5, Q9o: 5, J9o: 5, T9o: 5, "98o": 5,
};

const POSITION_INDEX: Record<Position, number> = {
  UTG: 0, MP: 1, CO: 2, BTN: 3, SB: 4, BB: 5,
};

function getHandLabel(row: number, col: number): string {
  if (row === col) return RANKS[row] + RANKS[col];
  if (row < col) return RANKS[row] + RANKS[col] + "s";
  return RANKS[col] + RANKS[row] + "o";
}

function getHandColor(hand: string, position: Position): string {
  const minPos = HAND_POSITION_MAP[hand];
  if (minPos === undefined) return "transparent";
  const posIdx = POSITION_INDEX[position];
  if (posIdx < minPos) return "transparent";

  if (minPos <= 0) return "rgba(46, 204, 113, 0.7)";
  if (minPos <= 1) return "rgba(46, 204, 113, 0.5)";
  if (minPos <= 2) return "rgba(241, 196, 15, 0.5)";
  if (minPos <= 3) return "rgba(230, 126, 34, 0.4)";
  return "rgba(230, 126, 34, 0.25)";
}

function getCategoryLabel(hand: string): string {
  const minPos = HAND_POSITION_MAP[hand];
  if (minPos === undefined) return "Fold";
  if (minPos <= 0) return "Premium";
  if (minPos <= 1) return "Strong";
  if (minPos <= 2) return "Good";
  if (minPos <= 3) return "Playable";
  if (minPos <= 4) return "Speculative";
  return "BB Defend";
}

function parseHoleCards(cards: string[]): string | null {
  if (!cards || cards.length !== 2) return null;
  const r1 = cards[0][0];
  const s1 = cards[0][1];
  const r2 = cards[1][0];
  const s2 = cards[1][1];

  const rankOrder = "AKQJT98765432";
  const i1 = rankOrder.indexOf(r1);
  const i2 = rankOrder.indexOf(r2);

  const high = i1 < i2 ? r1 : r2;
  const low = i1 < i2 ? r2 : r1;

  if (r1 === r2) return high + low;
  if (s1 === s2) return high + low + "s";
  return high + low + "o";
}

interface PreflopChartProps {
  open: boolean;
  onClose: () => void;
  holeCards?: string[];
  playerPosition?: Position | null;
}

function PreflopChart({ open, onClose, holeCards, playerPosition }: PreflopChartProps) {
  const [selectedPos, setSelectedPos] = useState<Position>(playerPosition ?? "CO");
  const currentHand = holeCards ? parseHoleCards(holeCards) : null;

  return (
    <Modal open={open} onClose={onClose} title="Preflop Starting Hands" maxWidth={560} titleId="preflop-chart-title">
      <div style={{ display: "flex", gap: 8, marginBottom: 14, flexWrap: "wrap" }}>
        {ALL_POSITIONS.map((pos) => (
          <button
            key={pos}
            onClick={() => setSelectedPos(pos)}
            style={{
              padding: "5px 14px",
              borderRadius: 6,
              border: selectedPos === pos ? "2px solid var(--accent)" : "1px solid var(--border-input)",
              background: selectedPos === pos ? "rgba(78, 204, 163, 0.15)" : "transparent",
              color: selectedPos === pos ? "var(--accent)" : "var(--text-secondary)",
              fontWeight: 700,
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            {pos}
          </button>
        ))}
      </div>

      {currentHand && (
        <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 10 }}>
          Your hand: <span style={{ color: "var(--accent)", fontWeight: 700 }}>{currentHand}</span>
          {" — "}
          <span style={{ fontWeight: 600 }}>{getCategoryLabel(currentHand)}</span>
          {HAND_POSITION_MAP[currentHand] !== undefined &&
            POSITION_INDEX[selectedPos] >= HAND_POSITION_MAP[currentHand] && (
              <span style={{ color: "var(--color-success)", marginLeft: 6 }}>✓ Playable from {selectedPos}</span>
            )}
          {(HAND_POSITION_MAP[currentHand] === undefined ||
            POSITION_INDEX[selectedPos] < HAND_POSITION_MAP[currentHand]) && (
            <span style={{ color: "var(--color-danger)", marginLeft: 6 }}>✗ Fold from {selectedPos}</span>
          )}
        </div>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(13, 1fr)`,
          gap: 1,
          fontSize: 10,
          fontWeight: 600,
          fontFamily: "var(--font-mono)",
        }}
      >
        {RANKS.map((_, row) =>
          RANKS.map((_, col) => {
            const label = getHandLabel(row, col);
            const color = getHandColor(label, selectedPos);
            const isCurrentHand = label === currentHand;
            return (
              <div
                key={`${row}-${col}`}
                title={`${label} — ${getCategoryLabel(label)}`}
                style={{
                  background: color,
                  padding: "4px 2px",
                  textAlign: "center",
                  borderRadius: 2,
                  color: color === "transparent" ? "var(--text-dim)" : "#fff",
                  border: isCurrentHand ? "2px solid #fff" : "1px solid rgba(255,255,255,0.05)",
                  lineHeight: 1.3,
                  cursor: "default",
                  boxShadow: isCurrentHand ? "0 0 8px rgba(78, 204, 163, 0.6)" : undefined,
                }}
              >
                {label}
              </div>
            );
          })
        )}
      </div>

      <div style={{ display: "flex", gap: 12, marginTop: 14, flexWrap: "wrap", fontSize: 11 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <div style={{ width: 12, height: 12, borderRadius: 2, background: "rgba(46, 204, 113, 0.7)" }} />
          <span style={{ color: "var(--text-secondary)" }}>Premium/Strong</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <div style={{ width: 12, height: 12, borderRadius: 2, background: "rgba(241, 196, 15, 0.5)" }} />
          <span style={{ color: "var(--text-secondary)" }}>Good</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <div style={{ width: 12, height: 12, borderRadius: 2, background: "rgba(230, 126, 34, 0.4)" }} />
          <span style={{ color: "var(--text-secondary)" }}>Playable</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <div style={{ width: 12, height: 12, borderRadius: 2, background: "rgba(230, 126, 34, 0.25)" }} />
          <span style={{ color: "var(--text-secondary)" }}>Speculative</span>
        </div>
      </div>

      <div style={{ fontSize: 11, color: "var(--text-dim)", marginTop: 12, lineHeight: 1.5 }}>
        Rows↓ × Columns→ · Diagonal = pairs · Upper-right = suited · Lower-left = offsuit
        <br />
        These are simplified opening ranges for a 6-max table. Adjust based on table dynamics.
      </div>
    </Modal>
  );
}

export type { Position };
export default PreflopChart;
