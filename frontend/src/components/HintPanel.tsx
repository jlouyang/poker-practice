/**
 * Displays the equity-based hint with optional calculation breakdown.
 */
import EquityBreakdown from "./EquityBreakdown";
import type { HintData } from "../types";

interface Props {
  hint: HintData;
  showCalc: boolean;
  onToggleCalc: () => void;
  onClose: () => void;
}

function HintPanel({ hint, showCalc, onToggleCalc, onClose }: Props) { return (
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
      Equity: {Math.round(hint.equity * 100)}% · Pot Odds: {Math.round(hint.pot_odds * 100)}%
    </div>
    <div style={{ color: "var(--text-secondary)", fontSize: 12, marginTop: 4, lineHeight: 1.4 }}>
      {hint.recommendation}
    </div>
    {hint.equity_details && (
      <>
        <button
          onClick={onToggleCalc}
          style={{
            marginTop: 6,
            background: "none",
            border: "none",
            color: "var(--accent)",
            fontSize: 11,
            cursor: "pointer",
            textDecoration: "underline",
            opacity: 0.8,
          }}
        >
          {showCalc ? "Hide calculation" : "Show calculation"}
        </button>
        {showCalc && <EquityBreakdown details={hint.equity_details} />}
      </>
    )}
  </div>
); }

export default HintPanel;
