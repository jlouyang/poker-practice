/**
 * Player seat component showing name, stack, hole cards, and position badges.
 *
 * Displays dealer button (D), blind labels (SB/BB), and ALL IN indicator.
 * On hover over a bot player, shows the HUD overlay (VPIP/PFR/AF stats).
 * Human player cards are always shown face-up; bot cards are face-down
 * until showdown (controlled by the showCards prop from Table).
 */
import { useState } from "react";
import Card from "./Card";
import HUD from "./HUD";
import type { PlayerInfo, HUDStats } from "../types";
import { formatPlayerName } from "../utils/format";

export type PositionName = "UTG" | "UTG+1" | "UTG+2" | "MP" | "MP+1" | "CO" | "BTN" | "SB" | "BB";

interface PlayerProps {
  player: PlayerInfo;
  isDealer: boolean;
  isCurrent: boolean;
  showCards: boolean;
  stats?: HUDStats;
  blindLabel?: "SB" | "BB";
  positionName?: PositionName;
  showPositionGuide?: boolean;
}

function positionColor(pos?: PositionName): string {
  if (!pos) return "var(--text-dim)";
  if (pos === "BTN" || pos === "CO") return "var(--color-success)";
  if (pos === "MP" || pos === "MP+1") return "var(--color-warning)";
  return "var(--color-danger)";
}

function positionTip(pos?: PositionName): string {
  if (!pos) return "";
  switch (pos) {
    case "BTN": return "Best position — you act last on every street";
    case "CO": return "Strong position — act late, can steal blinds";
    case "MP": case "MP+1": return "Middle position — moderate hand range";
    case "UTG": case "UTG+1": case "UTG+2": return "Early position — play tight, many players behind";
    case "SB": return "Worst position — forced bet, out of position postflop";
    case "BB": return "Forced bet — defend profitably, act last preflop";
    default: return "";
  }
}

function Player({ player, isDealer, isCurrent, showCards, stats, blindLabel, positionName, showPositionGuide }: PlayerProps) {
  const isHuman = player.is_human;
  const folded = !player.is_active;
  const [hovered, setHovered] = useState(false);

  const showHud = !isHuman && hovered && stats && stats.hands_played > 0;

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 6,
        opacity: folded ? 0.4 : 1,
        position: "relative",
      }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Single box outside table: cards + name (chip stack is on the table in Table.tsx) */}
      <div
        style={{
          background: "rgba(0,0,0,0.75)",
          border: isCurrent
            ? "2px solid var(--color-success)"
            : isHuman
            ? "2px solid var(--color-info)"
            : "1px solid var(--border-input)",
          borderRadius: 12,
          padding: "8px 10px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 6,
          minWidth: 90,
          cursor: !isHuman ? "pointer" : "default",
          boxShadow: "0 4px 12px rgba(0,0,0,0.4)",
        }}
      >
        {isDealer && (
          <div
            style={{
              position: "absolute",
              top: -10,
              right: -10,
              background: "var(--color-gold)",
              color: "#000",
              borderRadius: "50%",
              width: 22,
              height: 22,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 11,
              fontWeight: 800,
              zIndex: 1,
            }}
          >
            D
          </div>
        )}

        {blindLabel && (
          <div
            style={{
              position: "absolute",
              top: -10,
              left: -10,
              background: blindLabel === "SB" ? "var(--color-info)" : "var(--color-orange)",
              color: "#fff",
              borderRadius: "50%",
              width: 22,
              height: 22,
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 9,
              fontWeight: 800,
              letterSpacing: -0.5,
              zIndex: 1,
            }}
          >
            {blindLabel}
          </div>
        )}

        <div style={{ display: "flex", gap: 4 }}>
          {player.hole_cards && showCards
            ? player.hole_cards.map((c, i) => <Card key={i} card={c} small />)
            : player.is_active
            ? [<Card key={0} faceDown small />, <Card key={1} faceDown small />]
            : null}
        </div>

        <div
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: isHuman ? "var(--color-info)" : "var(--text-light)",
          }}
        >
          {formatPlayerName(player.player_id)}
        </div>
        {player.is_all_in && (
          <div
            style={{
              fontSize: 11,
              color: "var(--color-danger)",
              fontWeight: 700,
            }}
          >
            ALL IN
          </div>
        )}
        {showPositionGuide && positionName && (
          <div
            title={positionTip(positionName)}
            style={{
              fontSize: 10,
              fontWeight: 700,
              color: positionColor(positionName),
              background: "rgba(0,0,0,0.6)",
              padding: "2px 6px",
              borderRadius: 4,
              letterSpacing: 0.5,
              cursor: "help",
              border: `1px solid ${positionColor(positionName)}33`,
            }}
          >
            {positionName}
          </div>
        )}
      </div>

      {showHud && (
        <div style={{ position: "absolute", top: "100%", marginTop: 4, zIndex: 20 }}>
          <HUD stats={stats} />
        </div>
      )}
    </div>
  );
}

export default Player;
