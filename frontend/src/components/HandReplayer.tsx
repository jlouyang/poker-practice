/**
 * Step-by-step hand replayer modal.
 *
 * Lets the user scrub through a completed hand's actions one at a time.
 * Shows community cards revealed progressively by street, player hole cards
 * (revealed at the final step), and analysis scores at each decision point.
 */
import { useState } from "react";
import Card from "./Card";
import Modal from "./Modal";
import type { HandReplayData } from "../types";
import { SCORE_COLORS } from "../types";
import { formatPlayerName } from "../utils/format";

interface HandReplayerProps {
  handData: HandReplayData;
  onClose: () => void;
}

const HandReplayer = ({ handData, onClose }: HandReplayerProps) => {
  const [step, setStep] = useState(0);
  const maxStep = handData.actions.length;

  const visibleActions = handData.actions.slice(0, step);
  const currentStreet = visibleActions.length > 0 ? visibleActions[visibleActions.length - 1].street : "preflop";

  let visibleCommunity: string[] = [];
  if (currentStreet === "flop" || currentStreet === "turn" || currentStreet === "river")
    visibleCommunity = handData.community_cards.slice(0, 3);
  if (currentStreet === "turn" || currentStreet === "river")
    visibleCommunity = handData.community_cards.slice(0, 4);
  if (currentStreet === "river")
    visibleCommunity = handData.community_cards.slice(0, 5);
  if (step === maxStep) visibleCommunity = handData.community_cards;

  const currentAnalysis = step > 0
    ? handData.analysis.find(
        (a) => a.street === visibleActions[step - 1]?.street && a.player_id === visibleActions[step - 1]?.player_id
      )
    : null;

  const navBtn = (active: boolean): React.CSSProperties => ({
    padding: "6px 14px",
    borderRadius: "var(--radius-sm)",
    border: "1px solid var(--border-input)",
    background: active ? "var(--border-default)" : "var(--bg-primary)",
    color: active ? "#fff" : "var(--text-dim)",
    cursor: active ? "pointer" : "not-allowed",
    fontSize: 13,
  });

  return (
    <Modal open onClose={onClose} title={`Hand #${handData.hand_number} Replay`} maxWidth={640} titleId="replayer-title">
      {/* Community cards */}
      <div style={{ display: "flex", gap: 6, justifyContent: "center", marginBottom: 16 }}>
        {visibleCommunity.map((c, i) => <Card key={i} card={c} small />)}
      </div>

      {/* Players */}
      <div style={{ display: "flex", gap: 16, justifyContent: "center", marginBottom: 20, flexWrap: "wrap" }}>
        {handData.players.map((p) => (
          <div
            key={p.player_id}
            style={{
              background: "var(--bg-surface)",
              borderRadius: 8,
              padding: "8px 12px",
              textAlign: "center",
              border: handData.winner_ids.includes(p.player_id) ? "1px solid var(--color-success)" : "1px solid #333",
            }}
          >
            <div style={{ fontSize: 12, color: p.is_human ? "var(--color-info)" : "var(--text-muted)" }}>
              {formatPlayerName(p.player_id)}
            </div>
            <div style={{ display: "flex", gap: 3, justifyContent: "center", margin: "4px 0" }}>
              {(step === maxStep || p.is_human) && p.hole_cards.map((c, i) => <Card key={i} card={c} small />)}
            </div>
            <div style={{ fontSize: 11, color: "var(--text-dim)" }}>
              {p.starting_stack} → {p.ending_stack}
            </div>
          </div>
        ))}
      </div>

      {/* Action log */}
      <div style={{ marginBottom: 16, maxHeight: 200, overflowY: "auto" }}>
        {visibleActions.map((a, i) => (
          <div
            key={`${a.sequence}-${a.player_id}`}
            style={{
              padding: "4px 8px",
              fontSize: 13,
              color: i === step - 1 ? "#fff" : "var(--text-muted)",
              background: i === step - 1 ? "rgba(78,204,163,0.1)" : "transparent",
              borderRadius: 4,
            }}
          >
            <span style={{ color: "var(--border-input)", marginRight: 8 }}>[{a.street}]</span>
            <span style={{ fontWeight: 600 }}>{formatPlayerName(a.player_id)}</span>{" "}
            {a.action_type}
            {a.amount > 0 ? ` ${a.amount}` : ""}
          </div>
        ))}
      </div>

      {/* Analysis */}
      {currentAnalysis && (
        <div style={{ padding: "8px 12px", background: "var(--bg-surface)", borderRadius: 8, borderLeft: `3px solid ${SCORE_COLORS[currentAnalysis.score] || "var(--text-muted)"}`, marginBottom: 16, fontSize: 13 }}>
          <span style={{ color: "var(--text-muted)" }}>Equity: {Math.round(currentAnalysis.equity * 100)}%</span>
          <span style={{ marginLeft: 12, color: SCORE_COLORS[currentAnalysis.score], fontWeight: 700, textTransform: "capitalize" }}>{currentAnalysis.score}</span>
        </div>
      )}

      {/* Controls */}
      <div style={{ display: "flex", gap: 8, justifyContent: "center" }}>
        <button onClick={() => setStep(0)} disabled={step === 0} style={navBtn(step > 0)} aria-label="First step">«</button>
        <button onClick={() => setStep(Math.max(0, step - 1))} disabled={step === 0} style={navBtn(step > 0)} aria-label="Previous step">‹ Prev</button>
        <span style={{ color: "var(--text-muted)", alignSelf: "center", fontSize: 13 }}>{step} / {maxStep}</span>
        <button onClick={() => setStep(Math.min(maxStep, step + 1))} disabled={step === maxStep} style={navBtn(step < maxStep)} aria-label="Next step">Next ›</button>
        <button onClick={() => setStep(maxStep)} disabled={step === maxStep} style={navBtn(step < maxStep)} aria-label="Last step">»</button>
      </div>
    </Modal>
  );
};

export default HandReplayer;
