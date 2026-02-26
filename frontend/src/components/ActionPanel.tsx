import React, { useState, useCallback, useEffect } from "react";
import type { LegalAction } from "../types";

interface ActionPanelProps {
  legalActions: LegalAction[];
  onAction: (action: string, amount: number) => void;
  disabled: boolean;
  potSize: number;
  bigBlind: number;
  myCurrentBet: number;
}

function snapToBB(value: number, min: number, max: number, bb: number): number {
  if (value <= min) return min;
  if (value >= max) return max;
  const rounded = Math.round(value / bb) * bb;
  return Math.min(max, Math.max(min, rounded));
}

const ActionPanel: React.FC<ActionPanelProps> = ({
  legalActions,
  onAction,
  disabled,
  potSize,
  bigBlind,
  myCurrentBet,
}) => {
  const legalTypes = new Set(legalActions.map((a) => a.action_type));
  const raiseAction = legalActions.find(
    (a) => a.action_type === "raise" || a.action_type === "bet"
  );

  // min/max from the backend are "additional chips to add"
  // Convert to total bet amounts for display
  const minTotal = raiseAction ? myCurrentBet + raiseAction.min_amount : 0;
  const maxTotal = raiseAction ? myCurrentBet + raiseAction.max_amount : 0;

  const [raiseTotal, setRaiseTotal] = useState(minTotal);

  useEffect(() => {
    setRaiseTotal(minTotal);
  }, [minTotal, maxTotal]);

  const clampAndSnap = useCallback(
    (v: number) => snapToBB(v, minTotal, maxTotal, bigBlind),
    [minTotal, maxTotal, bigBlind]
  );

  const handleBet = useCallback(() => {
    if (raiseAction) {
      const additional = raiseTotal - myCurrentBet;
      onAction(raiseAction.action_type, additional);
    }
  }, [raiseAction, raiseTotal, myCurrentBet, onAction]);

  const presetBtnStyle = (active: boolean): React.CSSProperties => ({
    padding: "4px 10px",
    borderRadius: 6,
    border: "1px solid #4a6785",
    background: active ? "rgba(230, 126, 34, 0.2)" : "transparent",
    color: active ? "#e67e22" : "#8899aa",
    fontWeight: 600,
    fontSize: 12,
    cursor: active ? "pointer" : "not-allowed",
    opacity: active ? 1 : 0.5,
    transition: "all 0.15s",
  });

  const btnStyle = (color: string, active: boolean): React.CSSProperties => ({
    padding: "10px 24px",
    borderRadius: 8,
    border: "none",
    background: active ? color : "#333",
    color: active ? "#fff" : "#666",
    fontWeight: 700,
    fontSize: 15,
    cursor: active ? "pointer" : "not-allowed",
    opacity: active ? 1 : 0.5,
    transition: "all 0.15s",
  });

  const isBet = raiseAction?.action_type === "bet";

  const presets = raiseAction
    ? [
        { label: "Min", value: minTotal },
        { label: "½ Pot", value: clampAndSnap(Math.floor(potSize / 2)) },
        { label: "¾ Pot", value: clampAndSnap(Math.floor((potSize * 3) / 4)) },
        { label: "Pot", value: clampAndSnap(potSize) },
      ]
    : [];

  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 12,
        padding: "16px 24px",
        background: "rgba(0,0,0,0.4)",
        borderRadius: 12,
        flexWrap: "wrap",
        justifyContent: "center",
      }}
    >
      <button
        style={btnStyle("#c0392b", !disabled && legalTypes.has("fold"))}
        disabled={disabled || !legalTypes.has("fold")}
        onClick={() => onAction("fold", 0)}
      >
        Fold
      </button>

      {legalTypes.has("check") && (
        <button
          style={btnStyle("#27ae60", !disabled)}
          disabled={disabled}
          onClick={() => onAction("check", 0)}
        >
          Check
        </button>
      )}

      {legalTypes.has("call") && (
        <button
          style={btnStyle("#2980b9", !disabled)}
          disabled={disabled}
          onClick={() => {
            const callAction = legalActions.find((a) => a.action_type === "call");
            onAction("call", callAction?.min_amount ?? 0);
          }}
        >
          Call{" "}
          {legalActions.find((a) => a.action_type === "call")?.min_amount ?? ""}
        </button>
      )}

      {raiseAction && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexWrap: "wrap", justifyContent: "center" }}>
          <div style={{ display: "flex", gap: 4 }}>
            {presets.map((p) => (
              <button
                key={p.label}
                style={presetBtnStyle(!disabled)}
                disabled={disabled}
                onClick={() => setRaiseTotal(p.value)}
              >
                {p.label}
              </button>
            ))}
          </div>

          <input
            type="range"
            min={minTotal}
            max={maxTotal}
            step={bigBlind}
            value={raiseTotal}
            onChange={(e) => setRaiseTotal(clampAndSnap(Number(e.target.value)))}
            style={{ width: 120, accentColor: "#e67e22" }}
            disabled={disabled}
          />
          <input
            type="number"
            min={minTotal}
            max={maxTotal}
            step={bigBlind}
            value={raiseTotal}
            onChange={(e) => setRaiseTotal(clampAndSnap(Number(e.target.value)))}
            style={{
              width: 70,
              padding: "6px 8px",
              borderRadius: 6,
              border: "1px solid #4a6785",
              background: "#1a1a2e",
              color: "#fff",
              fontSize: 14,
              textAlign: "center",
            }}
            disabled={disabled}
          />
          <button
            style={btnStyle("#e67e22", !disabled)}
            disabled={disabled}
            onClick={handleBet}
          >
            {isBet ? "Bet" : "Raise to"} {raiseTotal}
          </button>
        </div>
      )}

      {legalTypes.has("all_in") && (
        <button
          style={btnStyle("#8e44ad", !disabled)}
          disabled={disabled}
          onClick={() => {
            const allIn = legalActions.find((a) => a.action_type === "all_in");
            onAction("all_in", allIn?.max_amount ?? 0);
          }}
        >
          All In
        </button>
      )}
    </div>
  );
};

export default ActionPanel;
