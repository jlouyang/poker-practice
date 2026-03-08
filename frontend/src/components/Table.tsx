/**
 * Poker table layout with oval felt, player seats, chip stacks, and bets.
 *
 * Partitioned layout (see docs/TABLE_LAYOUT.md):
 * - Player zone: seats on rays from center, just outside felt — cards and name box.
 * - Chip rail: stack chips on the ellipse boundary (ray–ellipse intersection).
 * - Bet ring: bet chips inward from rail toward center, clamped on felt.
 */
import Player from "./Player";
import CommunityCards from "./CommunityCards";
import Pot from "./Pot";
import ChipStack from "./ChipStack";
import type { PlayerInfo, HUDStats } from "../types";

import type { PositionName } from "./Player";

/** Felt oval inset from table container (%). Seats are placed just outside this. */
const FELT_INSET = { top: 15, right: 10, bottom: 15, left: 10 };
const FELT_CX = 50;
const FELT_CY = 50;
/** Ellipse half-axes: horizontal 40%, vertical 35% from center */
const FELT_RX = (100 - FELT_INSET.left - FELT_INSET.right) / 2;
const FELT_RY = (100 - FELT_INSET.top - FELT_INSET.bottom) / 2;

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

/**
 * Seat positions derived from the felt ellipse: each seat is placed on a ray
 * from the center, strictly outside the ellipse so the full player box (cards +
 * name) and chip stack area never overlap the felt. Angle 0° = top, 90° = right,
 * 180° = bottom (seat 0 / human). Evenly spaced so players sit around the felt.
 */
const SEAT_OUTWARD = 1.55; // >1 so seat center is outside ellipse; 1.55 keeps player box clear of felt without pushing seats too far

function getSeatPositionsAroundFelt(n: number): { x: number; y: number }[] {
  const positions: { x: number; y: number }[] = [];
  for (let i = 0; i < n; i++) {
    // 180° = bottom (human); then counter-clockwise
    const angleDeg = 180 + (i * 360) / n;
    const angleRad = (angleDeg * Math.PI) / 180;
    const x = FELT_CX + FELT_RX * SEAT_OUTWARD * Math.sin(angleRad);
    const y = FELT_CY - FELT_RY * SEAT_OUTWARD * Math.cos(angleRad);
    positions.push({ x, y });
  }
  return positions;
}

/**
 * Stack chips: on the table, strictly within the green. Position = rail (ellipse
 * along ray from seat to center), then scaled inward so the whole stack sits inside the felt.
 */
const STACK_AT_EDGE = 0.90; // scale from center toward rail: 0.90 = stack center well inside felt so stack is strictly on green

function chipOnRail(seat: { x: number; y: number }): { x: number; y: number } {
  const dx = FELT_CX - seat.x;
  const dy = FELT_CY - seat.y;
  const A = (seat.x - FELT_CX) / FELT_RX;
  const B = (seat.y - FELT_CY) / FELT_RY;
  const C = dx / FELT_RX;
  const D = dy / FELT_RY;
  const a = C * C + D * D;
  const b = 2 * (A * C + B * D);
  const c = A * A + B * B - 1;
  const disc = b * b - 4 * a * c;
  if (disc < 0) return { x: FELT_CX, y: FELT_CY };
  const sqrtDisc = Math.sqrt(disc);
  const t0 = (-b - sqrtDisc) / (2 * a);
  const t1 = (-b + sqrtDisc) / (2 * a);
  const valid = [t0, t1].filter((t) => t > 0 && t <= 1);
  const t = valid.length ? Math.min(...valid) : 1;
  const rail = { x: seat.x + t * dx, y: seat.y + t * dy };
  const atEdge = {
    x: FELT_CX + (rail.x - FELT_CX) * STACK_AT_EDGE,
    y: FELT_CY + (rail.y - FELT_CY) * STACK_AT_EDGE,
  };
  return atEdge;
}

/** Clamp (px, py) to lie inside the felt ellipse. */
function clampToFeltEllipse(px: number, py: number): { x: number; y: number } {
  const dx = (px - FELT_CX) / FELT_RX;
  const dy = (py - FELT_CY) / FELT_RY;
  const r2 = dx * dx + dy * dy;
  if (r2 <= 1) return { x: px, y: py };
  const r = Math.sqrt(r2);
  return {
    x: FELT_CX + ((px - FELT_CX) / r) * FELT_RX * 0.98,
    y: FELT_CY + ((py - FELT_CY) / r) * FELT_RY * 0.98,
  };
}

/**
 * Bet chips: placed along the ray from rail toward center. Lower = closer to the player (rail).
 * Fraction = how far from rail toward center (0.4 = 40% of the way, so bet sits closer to player).
 */
const BET_INWARD_FRACTION = 0.4;

function betOnTable(seat: { x: number; y: number }): { x: number; y: number } {
  const rail = chipOnRail(seat);
  const inward = {
    x: rail.x + (FELT_CX - rail.x) * BET_INWARD_FRACTION,
    y: rail.y + (FELT_CY - rail.y) * BET_INWARD_FRACTION,
  };
  return clampToFeltEllipse(inward.x, inward.y);
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
  const positions = getSeatPositionsAroundFelt(n);
  const { sb, bb } = computeBlindSeats(players, dealerSeat);
  const positionMap = computePositions(players, dealerSeat);

  return (
    <div
      className="table-container"
      style={{
        position: "relative",
        width: "100%",
        maxWidth: 960,
        aspectRatio: "16/11",
        margin: "0 auto",
        overflow: "visible",
      }}
    >
      {/* Table felt — oval inset from container; matches FELT_INSET / clampToFeltEllipse. z-index below seats so players never render under felt. */}
      <div
        className="table-felt"
        data-testid="table-felt"
        style={{
          position: "absolute",
          top: `${FELT_INSET.top}%`,
          right: `${FELT_INSET.right}%`,
          bottom: `${FELT_INSET.bottom}%`,
          left: `${FELT_INSET.left}%`,
          background:
            "radial-gradient(ellipse at center, #1a5c34 0%, #0d3b20 70%, #0a2e18 100%)",
          borderRadius: "50%",
          border: "6px solid #2c1810",
          boxShadow:
            "inset 0 0 60px rgba(0,0,0,0.5), 0 0 30px rgba(0,0,0,0.5)",
          zIndex: 0,
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

      {/* Stack chips — on the rail (ellipse edge) in front of each player */}
      {players.map((player, i) => {
        if (player.stack <= 0 && player.current_bet <= 0) return null;
        const pos = positions[i] || { x: 50, y: 50 };
        const cs = chipOnRail(pos);
        return (
          <div
            key={`stack-${player.player_id}`}
            className="table-chip-stack"
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

      {/* Bet chips — on table, inward from rail toward center */}
      {players.map((player, i) => {
        if (player.current_bet <= 0) return null;
        const pos = positions[i] || { x: 50, y: 50 };
        const bs = betOnTable(pos);
        return (
          <div
            key={`bet-${player.player_id}`}
            className="table-bet"
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

      {/* Player seats — just outside felt, no overlap with table or header */}
      {players.map((player, i) => {
        const pos = positions[i] || { x: 50, y: 50 };
        return (
          <div
            key={player.player_id}
            className="table-seat"
            data-testid={`table-seat-${player.seat}`}
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
