/**
 * Game setup / configuration screen.
 *
 * Allows the user to configure:
 *   - Difficulty (5 preset stops from Beginner to Expert)
 *   - Number of players (2-9)
 *   - Starting stack, small blind, big blind
 *
 * On submit, calls onStart(config) which triggers game creation on the backend.
 */
import { useState, type CSSProperties } from "react";
import type { CreateGameRequest } from "../types";

interface SetupScreenProps {
  onStart: (config: CreateGameRequest) => void;
}

const DIFFICULTY_STOPS = [
  { value: 10,  label: "Beginner", color: "#2ecc71", desc: "Mostly fish — loose, passive opponents" },
  { value: 30,  label: "Easy",     color: "#87d37c", desc: "Fish with a few solid regulars mixed in" },
  { value: 50,  label: "Medium",   color: "#f39c12", desc: "A realistic mix of fish, regulars, and sharks" },
  { value: 75,  label: "Hard",     color: "#e67e22", desc: "Mostly sharks with strong equity-based play" },
  { value: 95,  label: "Expert",   color: "#e74c3c", desc: "Sharks and GTO bots — near-optimal opponents" },
];

function getDifficultyInfo(d: number) {
  let closest = DIFFICULTY_STOPS[0];
  for (const stop of DIFFICULTY_STOPS) {
    if (Math.abs(stop.value - d) <= Math.abs(closest.value - d)) {
      closest = stop;
    }
  }
  return closest;
}


function SetupScreen({ onStart }: SetupScreenProps) {
  const [numPlayers, setNumPlayers] = useState(6);
  const [startingStack, setStartingStack] = useState(1000);
  const [smallBlind, setSmallBlind] = useState(5);
  const [bigBlind, setBigBlind] = useState(10);
  const [difficulty, setDifficulty] = useState(30);

  const diffInfo = getDifficultyInfo(difficulty);

  const handleStart = () => {
    onStart({
      num_players: numPlayers,
      starting_stack: startingStack,
      small_blind: smallBlind,
      big_blind: bigBlind,
      difficulty,
    });
  };

  const labelStyle: CSSProperties = {
    display: "flex",
    flexDirection: "column",
    gap: 6,
    fontSize: 14,
    color: "#aaa",
  };

  const inputStyle: CSSProperties = {
    padding: "8px 12px",
    borderRadius: 8,
    border: "1px solid #4a6785",
    background: "#16213e",
    color: "#fff",
    fontSize: 16,
    width: "100%",
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
        gap: 32,
        padding: 24,
      }}
    >
      <h1 style={{ color: "#4ecca3", fontSize: "2rem", marginBottom: 0 }}>
        Poker Training Engine
      </h1>
      <p style={{ color: "#888", fontSize: 16, marginTop: 0 }}>
        Configure your table and start practicing
      </p>

      <div
        style={{
          background: "rgba(255,255,255,0.03)",
          border: "1px solid #2c3e50",
          borderRadius: 16,
          padding: 32,
          display: "flex",
          flexDirection: "column",
          gap: 24,
          maxWidth: 440,
          width: "100%",
        }}
      >
        {/* Difficulty selector */}
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <span style={{ fontSize: 14, color: "#aaa" }}>Difficulty</span>
            <span style={{ fontSize: 15, fontWeight: 700, color: diffInfo.color }}>
              {diffInfo.label}
            </span>
          </div>
          <div style={{ display: "flex", gap: 6 }}>
            {DIFFICULTY_STOPS.map((stop) => (
              <button
                key={stop.value}
                onClick={() => setDifficulty(stop.value)}
                style={{
                  flex: 1,
                  padding: "8px 4px",
                  borderRadius: 8,
                  border: difficulty === stop.value
                    ? `2px solid ${stop.color}`
                    : "1px solid #4a6785",
                  background: difficulty === stop.value
                    ? `${stop.color}22`
                    : "transparent",
                  color: difficulty === stop.value ? stop.color : "#777",
                  fontWeight: difficulty === stop.value ? 700 : 500,
                  fontSize: 12,
                  cursor: "pointer",
                  transition: "all 0.15s",
                }}
              >
                {stop.label}
              </button>
            ))}
          </div>
          <div style={{ fontSize: 12, color: "#777", minHeight: 18 }}>
            {diffInfo.desc}
          </div>
        </div>

        {/* Table settings */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: 20,
          }}
        >
          <label style={labelStyle}>
            Players
            <select
              value={numPlayers}
              onChange={(e) => setNumPlayers(Number(e.target.value))}
              style={inputStyle}
            >
              {[2, 3, 4, 5, 6, 7, 8, 9].map((n) => (
                <option key={n} value={n}>
                  {n} players
                </option>
              ))}
            </select>
          </label>

          <label style={labelStyle}>
            Starting Stack
            <input
              type="number"
              value={startingStack}
              onChange={(e) => setStartingStack(Number(e.target.value))}
              style={inputStyle}
              min={10}
            />
          </label>

          <label style={labelStyle}>
            Small Blind
            <input
              type="number"
              value={smallBlind}
              onChange={(e) => setSmallBlind(Number(e.target.value))}
              style={inputStyle}
              min={1}
            />
          </label>

          <label style={labelStyle}>
            Big Blind
            <input
              type="number"
              value={bigBlind}
              onChange={(e) => setBigBlind(Number(e.target.value))}
              style={inputStyle}
              min={1}
            />
          </label>
        </div>
      </div>

      <button
        onClick={handleStart}
        style={{
          padding: "14px 48px",
          borderRadius: 10,
          border: "none",
          background: "linear-gradient(135deg, #4ecca3, #36b58e)",
          color: "#fff",
          fontWeight: 700,
          fontSize: 18,
          cursor: "pointer",
          boxShadow: "0 4px 15px rgba(78, 204, 163, 0.3)",
          transition: "transform 0.15s",
        }}
      >
        Start Game
      </button>
    </div>
  );
}

export default SetupScreen;
