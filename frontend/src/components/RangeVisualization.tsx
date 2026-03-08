import { useState } from "react";
import Modal from "./Modal";
import type { GameStateData } from "../types";

const RANKS = ["A", "K", "Q", "J", "T", "9", "8", "7", "6", "5", "4", "3", "2"] as const;

interface ActionEntry {
  player_id: string;
  action: string;
  amount: number;
  street: string;
}

function getHandLabel(row: number, col: number): string {
  if (row === col) return RANKS[row] + RANKS[col];
  if (row < col) return RANKS[row] + RANKS[col] + "s";
  return RANKS[col] + RANKS[row] + "o";
}

/**
 * Assign each hand a raw "strength tier" from 1 (strongest) to 8 (weakest).
 * Used to estimate which hands fall into a given range percentage.
 */
const HAND_TIER: Record<string, number> = {};
function initTiers() {
  const t = (hands: string[], tier: number) => hands.forEach((h) => { HAND_TIER[h] = tier; });
  t(["AA", "KK", "QQ", "AKs"], 1);
  t(["JJ", "TT", "AKo", "AQs"], 2);
  t(["99", "88", "AQo", "AJs", "KQs", "ATs", "KJs"], 3);
  t(["77", "66", "AJo", "KQo", "KTs", "QJs", "JTs", "A9s", "QTs"], 4);
  t(["55", "44", "33", "22", "ATo", "KJo", "QJo", "JTo", "A8s", "A7s", "A6s", "A5s", "K9s", "Q9s", "J9s", "T9s", "98s", "87s"], 5);
  t(["A4s", "A3s", "A2s", "K8s", "K7s", "K6s", "K5s", "Q8s", "J8s", "T8s", "97s", "86s", "76s", "65s", "54s", "A9o", "KTo", "QTo"], 6);
  t(["K4s", "K3s", "K2s", "Q7s", "Q6s", "Q5s", "Q4s", "J7s", "T7s", "96s", "85s", "75s", "64s", "53s", "43s", "A8o", "A7o", "A6o", "A5o", "A4o", "K9o", "Q9o", "J9o", "T9o", "98o"], 7);
}
initTiers();

function estimateRange(
  playerId: string,
  _gameState: GameStateData,
  actionLog: ActionEntry[],
): { pct: number; description: string } {
  const playerActions = actionLog.filter((a) => a.player_id === playerId);
  if (playerActions.length === 0) return { pct: 100, description: "Unknown — no actions yet" };

  let rangePct = 100;
  let desc = "";

  const preflopActions = playerActions.filter((a) => a.street === "preflop");
  const postflopActions = playerActions.filter((a) => a.street !== "preflop");

  for (const a of preflopActions) {
    if (a.action === "fold") return { pct: 0, description: "Folded preflop" };
    if (a.action === "raise" || a.action === "bet") {
      if (rangePct > 50) {
        rangePct = 18;
        desc = "Preflop raiser — likely strong holdings";
      } else {
        rangePct = Math.max(4, rangePct * 0.35);
        desc = "3-bet/4-bet — very strong range";
      }
    } else if (a.action === "call") {
      rangePct = Math.min(rangePct, 35);
      desc = "Called preflop — wide but capped range";
    } else if (a.action === "all_in") {
      rangePct = 6;
      desc = "All-in preflop — premium or desperate";
    }
  }

  for (const a of postflopActions) {
    if (a.action === "fold") return { pct: 0, description: "Folded" };
    if (a.action === "bet" || a.action === "raise") {
      rangePct = Math.max(3, rangePct * 0.55);
      desc = "Betting/raising — narrowing to strong hands and bluffs";
    } else if (a.action === "call") {
      rangePct = Math.max(5, rangePct * 0.75);
      desc = "Calling — draws, medium-strength hands, or trapping";
    } else if (a.action === "all_in") {
      rangePct = Math.max(2, rangePct * 0.3);
      desc = "All-in — polarized: very strong or bluff";
    }
  }

  return { pct: Math.round(rangePct), description: desc };
}

function getCellColor(hand: string, rangePct: number): string {
  const tier = HAND_TIER[hand];
  if (!tier) {
    return rangePct >= 80 ? "rgba(231, 76, 60, 0.2)" : "transparent";
  }

  const tierThresholds = [0, 3, 8, 15, 25, 40, 55, 80];
  const handMinPct = tierThresholds[tier - 1] ?? 80;

  if (rangePct < handMinPct) return "transparent";

  const strength = 1 - (tier - 1) / 7;
  if (strength > 0.7) return `rgba(231, 76, 60, ${0.3 + strength * 0.5})`;
  if (strength > 0.4) return `rgba(243, 156, 18, ${0.2 + strength * 0.4})`;
  return `rgba(243, 156, 18, ${0.1 + strength * 0.2})`;
}

interface RangeVisualizationProps {
  open: boolean;
  onClose: () => void;
  gameState: GameStateData;
  actionLog: ActionEntry[];
}

function RangeVisualization({ open, onClose, gameState, actionLog }: RangeVisualizationProps) {
  const bots = gameState.players.filter((p) => !p.is_human && p.is_active);
  const [selectedBot, setSelectedBot] = useState<string>(bots[0]?.player_id ?? "");

  const { pct, description } = estimateRange(selectedBot, gameState, actionLog);

  return (
    <Modal open={open} onClose={onClose} title="Opponent Range Estimate" maxWidth={520} titleId="range-viz-title">
      {bots.length === 0 ? (
        <div style={{ color: "var(--text-muted)", textAlign: "center", padding: 20 }}>
          No active opponents to analyze
        </div>
      ) : (
        <>
          <div style={{ display: "flex", gap: 6, marginBottom: 12, flexWrap: "wrap" }}>
            {bots.map((b) => (
              <button
                key={b.player_id}
                onClick={() => setSelectedBot(b.player_id)}
                style={{
                  padding: "5px 12px",
                  borderRadius: 6,
                  border: selectedBot === b.player_id ? "2px solid var(--color-danger)" : "1px solid var(--border-input)",
                  background: selectedBot === b.player_id ? "rgba(231, 76, 60, 0.15)" : "transparent",
                  color: selectedBot === b.player_id ? "var(--color-danger)" : "var(--text-secondary)",
                  fontWeight: 700,
                  fontSize: 13,
                  cursor: "pointer",
                }}
              >
                {b.player_id}
              </button>
            ))}
          </div>

          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
            <div>
              <span style={{ fontSize: 13, color: "var(--text-secondary)" }}>Estimated range: </span>
              <span style={{ fontSize: 15, fontWeight: 700, color: "var(--color-danger)" }}>{pct}%</span>
              <span style={{ fontSize: 12, color: "var(--text-muted)", marginLeft: 6 }}>of hands</span>
            </div>
          </div>

          <div style={{ fontSize: 12, color: "var(--text-secondary)", marginBottom: 10, lineHeight: 1.5 }}>
            {description || "Select a player to see their estimated range"}
          </div>

          <div
            style={{
              display: "grid",
              gridTemplateColumns: "repeat(13, 1fr)",
              gap: 1,
              fontSize: 10,
              fontWeight: 600,
              fontFamily: "var(--font-mono)",
            }}
          >
            {RANKS.map((_, row) =>
              RANKS.map((_, col) => {
                const label = getHandLabel(row, col);
                const color = pct > 0 ? getCellColor(label, pct) : "transparent";
                return (
                  <div
                    key={`${row}-${col}`}
                    title={label}
                    style={{
                      background: color,
                      padding: "4px 2px",
                      textAlign: "center",
                      borderRadius: 2,
                      color: color === "transparent" ? "var(--text-dim)" : "#fff",
                      border: "1px solid rgba(255,255,255,0.05)",
                      lineHeight: 1.3,
                    }}
                  >
                    {label}
                  </div>
                );
              })
            )}
          </div>

          <div style={{ fontSize: 10, color: "var(--text-dim)", marginTop: 12, lineHeight: 1.5 }}>
            This is an approximation based on actions taken this hand. Aggressive actions narrow the range;
            passive actions keep it wider. Actual holdings may differ.
          </div>
        </>
      )}
    </Modal>
  );
}

export default RangeVisualization;
export type { ActionEntry };
