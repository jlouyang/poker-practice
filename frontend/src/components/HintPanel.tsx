/**
 * Displays the equity-based hint with optional calculation breakdown.
 * Labels: weighted equity (vs range) when available, equity (vs random), pot odds.
 */
import EquityBreakdown from "./EquityBreakdown";
import type { HintData } from "../types";

interface Props {
  hint: HintData;
  showCalc: boolean;
  onToggleCalc: () => void;
  onClose: () => void;
  onOpenHowCalculations?: () => void;
}

function HintPanel({ hint, showCalc, onToggleCalc, onClose, onOpenHowCalculations }: Props) { return (
  <div className="hint-panel" style={{ position: "relative" }}>
    <button
      onClick={onClose}
      style={{
        position: "absolute",
        top: 4,
        right: 4,
        background: "none",
        border: "none",
        color: "var(--text-muted)",
        fontSize: 16,
        cursor: "pointer",
        lineHeight: 1,
        padding: "2px 6px",
      }}
      aria-label="Close hint"
    >
      ×
    </button>
    <div style={{ color: "var(--accent)", fontWeight: 700, fontSize: 15, marginBottom: 4 }}>
      Hint: {hint.optimal_action.toUpperCase()}
    </div>
    <div style={{ color: "var(--text-secondary)", fontSize: 12, lineHeight: 1.4 }}>
      {hint.equity_vs_random != null ? (
        <>
          Weighted equity: {Math.round(hint.equity * 100)}% · Equity (vs random): {Math.round(hint.equity_vs_random * 100)}%
        </>
      ) : (
        <>Equity: {Math.round(hint.equity * 100)}%</>
      )}
      {" · "}
      Pot odds: {Math.round(hint.pot_odds * 100)}%
    </div>
    {hint.opponent_range_pct != null && hint.opponent_range_description && (
      <div style={{ color: "var(--text-muted)", fontSize: 11, marginTop: 2, lineHeight: 1.3 }}>
        vs ~{hint.opponent_range_pct}% range — {hint.opponent_range_description}
      </div>
    )}
    <div style={{ color: "var(--text-secondary)", fontSize: 12, marginTop: 4, lineHeight: 1.4 }}>
      {hint.recommendation}
    </div>
    <div style={{ marginTop: 6, display: "flex", flexWrap: "wrap", gap: "8px 12px", alignItems: "center" }}>
      {onOpenHowCalculations && (
        <button
          type="button"
          onClick={onOpenHowCalculations}
          style={{
            background: "none",
            border: "none",
            color: "var(--text-muted)",
            fontSize: 11,
            cursor: "pointer",
            textDecoration: "underline",
            padding: 0,
          }}
        >
          How are these calculated?
        </button>
      )}
      {hint.equity_details && (
        <button
          onClick={onToggleCalc}
          style={{
            background: "none",
            border: "none",
            color: "var(--accent)",
            fontSize: 11,
            cursor: "pointer",
            textDecoration: "underline",
            opacity: 0.8,
            padding: 0,
          }}
        >
          {showCalc ? "Hide calculation" : "Show calculation"}
        </button>
      )}
    </div>
    {showCalc && hint.equity_details && <EquityBreakdown details={hint.equity_details} />}
  </div>
); }

export default HintPanel;
