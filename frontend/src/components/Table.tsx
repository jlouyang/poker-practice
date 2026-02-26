import React from "react";
import Player from "./Player";
import CommunityCards from "./CommunityCards";
import Pot from "./Pot";
import type { PlayerInfo } from "../types";

interface TableProps {
  players: PlayerInfo[];
  communityCards: string[];
  pot: number;
  dealerSeat: number;
  currentPlayerId: string | null;
  street: string;
  handNumber: number;
  playerStats?: Record<string, { vpip: number; pfr: number; af: number; hands_played: number }>;
}

// Seat positions around an oval table (percentages)
// Top row at y:15 so cards/HUD don't clip above the container
const SEAT_POSITIONS: Record<number, { x: number; y: number }[]> = {
  2: [
    { x: 50, y: 85 },
    { x: 50, y: 15 },
  ],
  3: [
    { x: 50, y: 85 },
    { x: 15, y: 28 },
    { x: 85, y: 28 },
  ],
  4: [
    { x: 50, y: 85 },
    { x: 10, y: 50 },
    { x: 50, y: 15 },
    { x: 90, y: 50 },
  ],
  5: [
    { x: 50, y: 85 },
    { x: 10, y: 55 },
    { x: 25, y: 15 },
    { x: 75, y: 15 },
    { x: 90, y: 55 },
  ],
  6: [
    { x: 50, y: 85 },
    { x: 8, y: 55 },
    { x: 18, y: 15 },
    { x: 50, y: 15 },
    { x: 82, y: 15 },
    { x: 92, y: 55 },
  ],
  7: [
    { x: 50, y: 85 },
    { x: 8, y: 60 },
    { x: 12, y: 22 },
    { x: 35, y: 15 },
    { x: 65, y: 15 },
    { x: 88, y: 22 },
    { x: 92, y: 60 },
  ],
  8: [
    { x: 50, y: 85 },
    { x: 8, y: 65 },
    { x: 8, y: 30 },
    { x: 30, y: 15 },
    { x: 50, y: 15 },
    { x: 70, y: 15 },
    { x: 92, y: 30 },
    { x: 92, y: 65 },
  ],
  9: [
    { x: 50, y: 85 },
    { x: 8, y: 68 },
    { x: 6, y: 38 },
    { x: 22, y: 15 },
    { x: 40, y: 15 },
    { x: 60, y: 15 },
    { x: 78, y: 15 },
    { x: 94, y: 38 },
    { x: 92, y: 68 },
  ],
};

const Table: React.FC<TableProps> = ({
  players,
  communityCards,
  pot,
  dealerSeat,
  currentPlayerId,
  street,
  handNumber,
  playerStats,
}) => {
  const n = players.length;
  const positions = SEAT_POSITIONS[n] || SEAT_POSITIONS[6];

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        maxWidth: 900,
        aspectRatio: "16/10",
        margin: "0 auto",
        overflow: "visible",
      }}
    >
      {/* Table felt */}
      <div
        style={{
          position: "absolute",
          inset: "15% 10%",
          background:
            "radial-gradient(ellipse at center, #1a5c34 0%, #0d3b20 70%, #0a2e18 100%)",
          borderRadius: "50%",
          border: "6px solid #2c1810",
          boxShadow:
            "inset 0 0 60px rgba(0,0,0,0.5), 0 0 30px rgba(0,0,0,0.5)",
        }}
      />

      {/* Center info */}
      <div
        style={{
          position: "absolute",
          top: "50%",
          left: "50%",
          transform: "translate(-50%, -50%)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 10,
          zIndex: 2,
        }}
      >
        <div
          style={{
            fontSize: 12,
            color: "#888",
            textTransform: "uppercase",
            letterSpacing: 1,
          }}
        >
          {street !== "preflop" ? street : ""} {handNumber > 0 ? `#${handNumber}` : ""}
        </div>
        <CommunityCards cards={communityCards} />
        <Pot amount={pot} />
      </div>

      {/* Player seats */}
      {players.map((player, i) => {
        const pos = positions[i] || { x: 50, y: 50 };
        return (
          <div
            key={player.player_id}
            style={{
              position: "absolute",
              left: `${pos.x}%`,
              top: `${pos.y}%`,
              transform: "translate(-50%, -50%)",
              zIndex: 3,
            }}
          >
            <Player
              player={player}
              isDealer={player.seat === dealerSeat}
              isCurrent={player.player_id === currentPlayerId}
              showCards={player.is_human || !!player.hole_cards}
              stats={playerStats?.[player.player_id]}
            />
          </div>
        );
      })}
    </div>
  );
};

export default Table;
