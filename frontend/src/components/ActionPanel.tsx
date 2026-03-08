/**
 * Action panel for player input: Fold, Check, Call, Raise/Bet, All-In.
 *
 * Features:
 *   - Buttons enabled/disabled based on legal actions from the server
 *   - Raise slider + numeric input with BB-snapping and pot-fraction presets
 *   - Hint button triggers equity calculation on the server
 *   - Amounts are displayed as "total bet" but sent as "additional chips" to the server
 */
import { useState, useCallback, useEffect, type CSSProperties } from "react";
import type { LegalAction } from "../types";

interface ActionPanelProps {
  legalActions: LegalAction[];
  onAction: (action: string, amount: number) => void;
  disabled: boolean;
  potSize: number;
  bigBlind: number;
  myCurrentBet: number;
  onHint?: () => void;
  hintLoading?: boolean;
  showHint?: boolean;
  showSizingTips?: boolean;
}

function snapToBB(value: number, min: number, max: number, bb: number): number {
  if (value <= min) return min;
  if (value >= max) return max;
  const rounded = Math.round(value / bb) * bb;
  return Math.min(max, Math.max(min, rounded));
}

function ActionPanel({
  legalActions,
  onAction,
  disabled,
  potSize,
  bigBlind,
  myCurrentBet,
  onHint,
  hintLoading,
  showHint,
  showSizingTips,
}: ActionPanelProps) {
  const legalTypes = new Set(legalActions.map((a) => a.action_type));
  const raiseAction = legalActions.find(
    (a) => a.action_type === "raise" || a.action_type === "bet"
  );

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

  const presetBtnStyle = (active: boolean): CSSProperties => ({
    padding: "4px 10px",
    borderRadius: 6,
    border: "1px solid var(--border-input)",
    background: active ? "rgba(230, 126, 34, 0.2)" : "transparent",
    color: active ? "var(--color-orange)" : "var(--text-subtle)",
    fontWeight: 600,
    fontSize: 12,
    cursor: active ? "pointer" : "not-allowed",
    opacity: active ? 1 : 0.5,
    transition: "all 0.15s",
  });

  const btnStyle = (color: string, active: boolean): CSSProperties => ({
    padding: "10px 24px",
    borderRadius: 8,
    border: "none",
    background: active ? color : "var(--bg-disabled)",
    color: active ? "#fff" : "var(--text-dim)",
    fontWeight: 700,
    fontSize: 15,
    cursor: active ? "pointer" : "not-allowed",
    opacity: active ? 1 : 0.5,
    transition: "all 0.15s",
  });

  const isBet = raiseAction?.action_type === "bet";

  const presets = raiseAction
    ? [
        { label: "Min", value: minTotal, tip: "Minimum raise — cheap but gives opponents good odds to call" },
        { label: "½ Pot", value: clampAndSnap(Math.floor(potSize / 2)), tip: "Half pot — good for dry boards, value bets, and controlling pot size" },
        { label: "¾ Pot", value: clampAndSnap(Math.floor((potSize * 3) / 4)), tip: "Three-quarter pot — standard size for value bets and semi-bluffs" },
        { label: "Pot", value: clampAndSnap(potSize), tip: "Full pot — strong sizing for wet boards, big draws, or polarized ranges" },
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
        style={btnStyle("var(--color-danger-dark)", !disabled && legalTypes.has("fold"))}
        disabled={disabled || !legalTypes.has("fold")}
        onClick={() => onAction("fold", 0)}
      >
        Fold
      </button>

      {legalTypes.has("check") && (
        <button
          style={btnStyle("var(--color-success-dark)", !disabled)}
          disabled={disabled}
          onClick={() => onAction("check", 0)}
        >
          Check
        </button>
      )}

      {legalTypes.has("call") && (
        <button
          style={btnStyle("var(--color-info-dark)", !disabled)}
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
                title={showSizingTips ? p.tip : undefined}
              >
                {p.label}
              </button>
            ))}
          </div>

          {showSizingTips && (
            <div style={{ width: "100%", fontSize: 10, color: "var(--text-dim)", lineHeight: 1.4, marginBottom: 2, textAlign: "center" }}>
              💡 Hover sizing buttons for tips
            </div>
          )}
          <input
            type="range"
            min={minTotal}
            max={maxTotal}
            step={bigBlind}
            value={raiseTotal}
            onChange={(e) => setRaiseTotal(clampAndSnap(Number(e.target.value)))}
            style={{ width: 120, accentColor: "var(--color-orange)" }}
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
              border: "1px solid var(--border-input)",
              background: "var(--bg-primary)",
              color: "#fff",
              fontSize: 14,
              textAlign: "center",
            }}
            disabled={disabled}
          />
          <button
            style={btnStyle("var(--color-orange)", !disabled)}
            disabled={disabled}
            onClick={handleBet}
          >
            {isBet ? "Bet" : "Raise to"} {raiseTotal}
          </button>
        </div>
      )}

      {legalTypes.has("all_in") && (
        <button
          style={btnStyle("var(--color-purple)", !disabled)}
          disabled={disabled}
          onClick={() => {
            const allIn = legalActions.find((a) => a.action_type === "all_in");
            onAction("all_in", allIn?.max_amount ?? 0);
          }}
        >
          All In
        </button>
      )}

      {onHint && !disabled && legalActions.length > 0 && (
        <button
          style={{
            padding: "10px 18px",
            borderRadius: 8,
            border: "1px solid var(--border-input)",
            background: showHint ? "rgba(78, 204, 163, 0.15)" : "transparent",
            color: "var(--accent)",
            fontWeight: 700,
            fontSize: 13,
            cursor: hintLoading ? "wait" : "pointer",
            opacity: hintLoading ? 0.6 : 1,
            transition: "all 0.15s",
          }}
          onClick={onHint}
          disabled={hintLoading}
        >
          {hintLoading ? "Thinking…" : showHint ? "Hint ✓" : "Hint"}
        </button>
      )}
    </div>
  );
}

export default ActionPanel;
