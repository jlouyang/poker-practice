import React, { useState } from "react";
import type { CreateGameRequest } from "../types";

interface SetupScreenProps {
  onStart: (config: CreateGameRequest) => void;
}

const SetupScreen: React.FC<SetupScreenProps> = ({ onStart }) => {
  const [numPlayers, setNumPlayers] = useState(6);
  const [startingStack, setStartingStack] = useState(1000);
  const [smallBlind, setSmallBlind] = useState(5);
  const [bigBlind, setBigBlind] = useState(10);

  const handleStart = () => {
    onStart({
      num_players: numPlayers,
      starting_stack: startingStack,
      small_blind: smallBlind,
      big_blind: bigBlind,
    });
  };

  const labelStyle: React.CSSProperties = {
    display: "flex",
    flexDirection: "column",
    gap: 6,
    fontSize: 14,
    color: "#aaa",
  };

  const inputStyle: React.CSSProperties = {
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
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 20,
          maxWidth: 440,
          width: "100%",
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
};

export default SetupScreen;
