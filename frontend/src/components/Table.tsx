/**
 * Poker table layout with oval felt, player seats, chip stacks, and bets.
 *
 * Players are positioned around the table using pre-computed seat coordinates
 * (SEAT_POSITIONS) for 2-9 player configurations. Each player's chip stack
 * sits between them and the center (chipSpot), and their current bet sits
 * closer to center (betSpot).
 *
 * Also computes SB/BB positions from dealer seat for blind labels.
 */
import Player from "./Player";
import CommunityCards from "./CommunityCards";
import Pot from "./Pot";
import ChipStack from "./ChipStack";
import type { PlayerInfo, HUDStats } from "../types";

import type { PositionName } from "./Player";

interface TableProps {
  players: PlayerInfo[];
  communityCards: string[];
  pot: number;
  dealerSeat: number;
  currentPlayerId: string | null;
  street: string;
  handNumber: number;
  playerStats?: Record<string, HUDStats>;
  showPositionGuide?: boolean;
}

function computePositions(players: PlayerInfo[], dealerSeat: number): Map<number, PositionName> {
  const activeSeats = players.filter((p) => p.is_active || p.stack > 0).map((p) => p.seat).sort((a, b) => a - b);
  const n = activeSeats.length;
  if (n < 2) return new Map();

  const nextActive = (fromSeat: number): number => {
    for (let i = 1; i <= players.length; i++) {
      const s = (fromSeat + i) % players.length;
      if (activeSeats.includes(s)) return s;
    }
    return -1;
  };

  const ordered: number[] = [];
  let current = dealerSeat;
  for (let i = 0; i < n; i++) {
    if (i === 0) {
      ordered.push(current);
    } else {
      current = nextActive(current);
      ordered.push(current);
    }
  }

  const posMap = new Map<number, PositionName>();
  if (n === 2) {
    posMap.set(ordered[0], "BTN");
    posMap.set(ordered[1], "BB");
  } else if (n === 3) {
    posMap.set(ordered[0], "BTN");
    posMap.set(ordered[1], "SB");
    posMap.set(ordered[2], "BB");
  } else {
    posMap.set(ordered[0], "BTN");
    posMap.set(ordered[1], "SB");
    posMap.set(ordered[2], "BB");

    const remaining = ordered.slice(3);
    const posNames: PositionName[] =
      remaining.length === 1 ? ["UTG"] :
      remaining.length === 2 ? ["UTG", "CO"] :
      remaining.length === 3 ? ["UTG", "MP", "CO"] :
      remaining.length === 4 ? ["UTG", "UTG+1", "MP", "CO"] :
      remaining.length === 5 ? ["UTG", "UTG+1", "MP", "MP+1", "CO"] :
      ["UTG", "UTG+1", "UTG+2", "MP", "MP+1", "CO"];

    remaining.forEach((seat, i) => {
      if (i < posNames.length) posMap.set(seat, posNames[i]);
    });
  }

  return posMap;
}

function computeBlindSeats(players: PlayerInfo[], dealerSeat: number): { sb: number; bb: number } {
  const activeSeats = players.filter((p) => p.is_active).map((p) => p.seat).sort((a, b) => a - b);
  if (activeSeats.length < 2) return { sb: -1, bb: -1 };

  const nextActive = (fromSeat: number): number => {
    for (let i = 1; i <= players.length; i++) {
      const s = (fromSeat + i) % players.length;
      if (activeSeats.includes(s)) return s;
    }
    return -1;
  };

  if (activeSeats.length === 2) {
    return { sb: dealerSeat, bb: nextActive(dealerSeat) };
  }
  const sb = nextActive(dealerSeat);
  const bb = nextActive(sb);
  return { sb, bb };
}

const SEAT_POSITIONS: Record<number, { x: number; y: number }[]> = {
  2: [
    { x: 50, y: 90 },
    { x: 50, y: 3 },
  ],
  3: [
    { x: 50, y: 90 },
    { x: 5, y: 18 },
    { x: 95, y: 18 },
  ],
  4: [
    { x: 50, y: 90 },
    { x: 2, y: 50 },
    { x: 50, y: 3 },
    { x: 98, y: 50 },
  ],
  5: [
    { x: 50, y: 90 },
    { x: 2, y: 58 },
    { x: 18, y: 3 },
    { x: 82, y: 3 },
    { x: 98, y: 58 },
  ],
  6: [
    { x: 50, y: 90 },
    { x: 2, y: 58 },
    { x: 10, y: 3 },
    { x: 50, y: 3 },
    { x: 90, y: 3 },
    { x: 98, y: 58 },
  ],
  7: [
    { x: 50, y: 90 },
    { x: 2, y: 65 },
    { x: 4, y: 15 },
    { x: 30, y: 3 },
    { x: 70, y: 3 },
    { x: 96, y: 15 },
    { x: 98, y: 65 },
  ],
  8: [
    { x: 50, y: 90 },
    { x: 2, y: 68 },
    { x: 2, y: 25 },
    { x: 24, y: 3 },
    { x: 50, y: 3 },
    { x: 76, y: 3 },
    { x: 98, y: 25 },
    { x: 98, y: 68 },
  ],
  9: [
    { x: 50, y: 90 },
    { x: 2, y: 72 },
    { x: 0, y: 35 },
    { x: 16, y: 3 },
    { x: 36, y: 3 },
    { x: 64, y: 3 },
    { x: 84, y: 3 },
    { x: 100, y: 35 },
    { x: 98, y: 72 },
  ],
};

const CX = 50, CY = 50;

function chipSpot(seat: { x: number; y: number }): { x: number; y: number } {
  return {
    x: seat.x + (CX - seat.x) * 0.38,
    y: seat.y + (CY - seat.y) * 0.38,
  };
}

function betSpot(seat: { x: number; y: number }): { x: number; y: number } {
  return {
    x: seat.x + (CX - seat.x) * 0.68,
    y: seat.y + (CY - seat.y) * 0.68,
  };
}

function Table({
  players,
  communityCards,
  pot,
  dealerSeat,
  currentPlayerId,
  street,
  handNumber,
  playerStats,
  showPositionGuide,
}: TableProps) {
  const n = players.length;
  const positions = SEAT_POSITIONS[n] || SEAT_POSITIONS[6];
  const { sb, bb } = computeBlindSeats(players, dealerSeat);
  const positionMap = computePositions(players, dealerSeat);

  return (
    <div
      style={{
        position: "relative",
        width: "100%",
        maxWidth: 960,
        aspectRatio: "16/11",
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

      {/* Stack chips — on felt edge in front of each player */}
      {players.map((player, i) => {
        if (player.stack <= 0 && player.current_bet <= 0) return null;
        const pos = positions[i] || { x: 50, y: 50 };
        const cs = chipSpot(pos);
        return (
          <div
            key={`stack-${player.player_id}`}
            style={{
              position: "absolute",
              left: `${cs.x}%`,
              top: `${cs.y}%`,
              transform: "translate(-50%, -50%)",
              zIndex: 4,
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <ChipStack amount={player.stack} size="sm" />
            <span
              style={{
                color: "#e0e0e0",
                fontSize: 11,
                fontWeight: 700,
                textShadow: "0 1px 3px rgba(0,0,0,0.8)",
                whiteSpace: "nowrap",
              }}
            >
              {player.stack}
            </span>
          </div>
        );
      })}

      {/* Bet chips — closer to center when a player has bet */}
      {players.map((player, i) => {
        if (player.current_bet <= 0) return null;
        const pos = positions[i] || { x: 50, y: 50 };
        const bs = betSpot(pos);
        return (
          <div
            key={`bet-${player.player_id}`}
            style={{
              position: "absolute",
              left: `${bs.x}%`,
              top: `${bs.y}%`,
              transform: "translate(-50%, -50%)",
              zIndex: 5,
              display: "flex",
              alignItems: "center",
              gap: 4,
            }}
          >
            <ChipStack amount={player.current_bet} size="sm" />
            <span
              style={{
                color: "#f1c40f",
                fontSize: 11,
                fontWeight: 700,
                textShadow: "0 1px 3px rgba(0,0,0,0.8)",
                whiteSpace: "nowrap",
              }}
            >
              {player.current_bet}
            </span>
          </div>
        );
      })}

      {/* Player boxes — outside the felt */}
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
              blindLabel={player.seat === sb ? "SB" : player.seat === bb ? "BB" : undefined}
              positionName={positionMap.get(player.seat)}
              showPositionGuide={showPositionGuide}
            />
          </div>
        );
      })}
    </div>
  );
}

export default Table;
