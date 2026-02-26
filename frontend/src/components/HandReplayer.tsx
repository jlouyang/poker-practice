import React, { useState } from "react";
import Card from "./Card";

interface ReplayAction {
  player_id: string;
  street: string;
  action_type: string;
  amount: number;
  sequence: number;
}

interface ReplayPlayer {
  player_id: string;
  seat: number;
  starting_stack: number;
  ending_stack: number;
  hole_cards: string[];
  is_human: boolean;
}

interface ReplayAnalysis {
  player_id: string;
  street: string;
  equity: number;
  score: string;
}

interface HandReplayerProps {
  handData: {
    hand_number: number;
    community_cards: string[];
    pot_size: number;
    winner_ids: string[];
    players: ReplayPlayer[];
    actions: ReplayAction[];
    analysis: ReplayAnalysis[];
  };
  onClose: () => void;
}

const SCORE_COLORS: Record<string, string> = {
  good: "#2ecc71",
  mistake: "#f39c12",
  blunder: "#e74c3c",
};

const HandReplayer: React.FC<HandReplayerProps> = ({ handData, onClose }) => {
  const [step, setStep] = useState(0);
  const maxStep = handData.actions.length;

  const visibleActions = handData.actions.slice(0, step);
  const currentStreet =
    visibleActions.length > 0
      ? visibleActions[visibleActions.length - 1].street
      : "preflop";

  let visibleCommunity: string[] = [];
  if (currentStreet === "flop" || currentStreet === "turn" || currentStreet === "river") {
    visibleCommunity = handData.community_cards.slice(0, 3);
  }
  if (currentStreet === "turn" || currentStreet === "river") {
    visibleCommunity = handData.community_cards.slice(0, 4);
  }
  if (currentStreet === "river") {
    visibleCommunity = handData.community_cards.slice(0, 5);
  }
  if (step === maxStep) {
    visibleCommunity = handData.community_cards;
  }

  const currentAnalysis =
    step > 0
      ? handData.analysis.find(
          (a) =>
            a.street === visibleActions[step - 1]?.street &&
            a.player_id === visibleActions[step - 1]?.player_id
        )
      : null;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.8)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        zIndex: 100,
      }}
    >
      <div
        style={{
          background: "#1a1a2e",
          border: "1px solid #2c3e50",
          borderRadius: 16,
          padding: 32,
          maxWidth: 640,
          width: "90%",
          maxHeight: "85vh",
          overflowY: "auto",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 20,
          }}
        >
          <h2 style={{ color: "#4ecca3", margin: 0, fontSize: 20 }}>
            Hand #{handData.hand_number} Replay
          </h2>
          <button
            onClick={onClose}
            style={{
              background: "none",
              border: "1px solid #4a6785",
              color: "#aaa",
              borderRadius: 6,
              padding: "4px 12px",
              cursor: "pointer",
            }}
          >
            Close
          </button>
        </div>

        {/* Community cards */}
        <div
          style={{
            display: "flex",
            gap: 6,
            justifyContent: "center",
            marginBottom: 16,
          }}
        >
          {visibleCommunity.map((c, i) => (
            <Card key={i} card={c} small />
          ))}
        </div>

        {/* Players */}
        <div
          style={{
            display: "flex",
            gap: 16,
            justifyContent: "center",
            marginBottom: 20,
            flexWrap: "wrap",
          }}
        >
          {handData.players.map((p) => (
            <div
              key={p.player_id}
              style={{
                background: "rgba(255,255,255,0.03)",
                borderRadius: 8,
                padding: "8px 12px",
                textAlign: "center",
                border: handData.winner_ids.includes(p.player_id)
                  ? "1px solid #2ecc71"
                  : "1px solid #333",
              }}
            >
              <div style={{ fontSize: 12, color: p.is_human ? "#3498db" : "#888" }}>
                {p.is_human ? "You" : p.player_id}
              </div>
              <div style={{ display: "flex", gap: 3, justifyContent: "center", margin: "4px 0" }}>
                {(step === maxStep || p.is_human) &&
                  p.hole_cards.map((c, i) => <Card key={i} card={c} small />)}
              </div>
              <div style={{ fontSize: 11, color: "#666" }}>
                {p.starting_stack} &rarr; {p.ending_stack}
              </div>
            </div>
          ))}
        </div>

        {/* Action log */}
        <div style={{ marginBottom: 16, maxHeight: 200, overflowY: "auto" }}>
          {visibleActions.map((a, i) => (
            <div
              key={i}
              style={{
                padding: "4px 8px",
                fontSize: 13,
                color: i === step - 1 ? "#fff" : "#888",
                background: i === step - 1 ? "rgba(78,204,163,0.1)" : "transparent",
                borderRadius: 4,
              }}
            >
              <span style={{ color: "#4a6785", marginRight: 8 }}>[{a.street}]</span>
              <span style={{ fontWeight: 600 }}>
                {a.player_id === "human" ? "You" : a.player_id}
              </span>{" "}
              {a.action_type}
              {a.amount > 0 ? ` ${a.amount}` : ""}
            </div>
          ))}
        </div>

        {/* Analysis for current step */}
        {currentAnalysis && (
          <div
            style={{
              padding: "8px 12px",
              background: "rgba(255,255,255,0.03)",
              borderRadius: 8,
              borderLeft: `3px solid ${SCORE_COLORS[currentAnalysis.score] || "#888"}`,
              marginBottom: 16,
              fontSize: 13,
            }}
          >
            <span style={{ color: "#888" }}>
              Equity: {Math.round(currentAnalysis.equity * 100)}%
            </span>
            <span
              style={{
                marginLeft: 12,
                color: SCORE_COLORS[currentAnalysis.score],
                fontWeight: 700,
                textTransform: "capitalize",
              }}
            >
              {currentAnalysis.score}
            </span>
          </div>
        )}

        {/* Controls */}
        <div style={{ display: "flex", gap: 8, justifyContent: "center" }}>
          <button
            onClick={() => setStep(0)}
            disabled={step === 0}
            style={navBtnStyle(step > 0)}
          >
            &laquo;
          </button>
          <button
            onClick={() => setStep(Math.max(0, step - 1))}
            disabled={step === 0}
            style={navBtnStyle(step > 0)}
          >
            &lsaquo; Prev
          </button>
          <span style={{ color: "#888", alignSelf: "center", fontSize: 13 }}>
            {step} / {maxStep}
          </span>
          <button
            onClick={() => setStep(Math.min(maxStep, step + 1))}
            disabled={step === maxStep}
            style={navBtnStyle(step < maxStep)}
          >
            Next &rsaquo;
          </button>
          <button
            onClick={() => setStep(maxStep)}
            disabled={step === maxStep}
            style={navBtnStyle(step < maxStep)}
          >
            &raquo;
          </button>
        </div>
      </div>
    </div>
  );
};

function navBtnStyle(active: boolean): React.CSSProperties {
  return {
    padding: "6px 14px",
    borderRadius: 6,
    border: "1px solid #4a6785",
    background: active ? "#2c3e50" : "#1a1a2e",
    color: active ? "#fff" : "#555",
    cursor: active ? "pointer" : "not-allowed",
    fontSize: 13,
  };
}

export default HandReplayer;
