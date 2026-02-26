import React from "react";
import Card from "./Card";
import HUD from "./HUD";
import type { PlayerInfo } from "../types";

interface PlayerProps {
  player: PlayerInfo;
  isDealer: boolean;
  isCurrent: boolean;
  showCards: boolean;
  stats?: { vpip: number; pfr: number; af: number; hands_played: number };
}

const Player: React.FC<PlayerProps> = ({ player, isDealer, isCurrent, showCards, stats }) => {
  const isHuman = player.is_human;
  const folded = !player.is_active;

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
    >
      {isDealer && (
        <div
          style={{
            position: "absolute",
            top: -10,
            right: -10,
            background: "#f1c40f",
            color: "#000",
            borderRadius: "50%",
            width: 22,
            height: 22,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 11,
            fontWeight: 800,
          }}
        >
          D
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
          background: isCurrent
            ? "rgba(46, 204, 113, 0.2)"
            : isHuman
            ? "rgba(52, 152, 219, 0.15)"
            : "rgba(255,255,255,0.05)",
          border: isCurrent
            ? "2px solid #2ecc71"
            : isHuman
            ? "2px solid #3498db"
            : "1px solid #4a6785",
          borderRadius: 10,
          padding: "6px 12px",
          textAlign: "center",
          minWidth: 90,
        }}
      >
        <div
          style={{
            fontSize: 13,
            fontWeight: 600,
            color: isHuman ? "#3498db" : "#ccc",
            marginBottom: 2,
          }}
        >
          {isHuman ? "You" : player.player_id}
        </div>
        <div style={{ fontSize: 15, fontWeight: 700, color: "#fff" }}>
          {player.stack}
        </div>
        {player.current_bet > 0 && (
          <div style={{ fontSize: 12, color: "#f1c40f", marginTop: 2 }}>
            Bet: {player.current_bet}
          </div>
        )}
        {player.is_all_in && (
          <div
            style={{
              fontSize: 11,
              color: "#e74c3c",
              fontWeight: 700,
              marginTop: 2,
            }}
          >
            ALL IN
          </div>
        )}
      </div>

      {!player.is_human && stats && stats.hands_played > 0 && (
        <HUD stats={stats} playerName={player.player_id} />
      )}
    </div>
  );
};

export default Player;
