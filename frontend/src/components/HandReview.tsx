/**
 * Post-hand review modal showing decision analysis.
 *
 * Displays:
 *   - Summary (blunder/mistake count or "clean hand")
 *   - Equity-by-street bar chart
 *   - Per-decision cards: street, action, equity, pot odds, score, reasoning
 *   - Expandable Monte Carlo equity breakdown for each decision
 */
import { useState } from "react";
import Modal from "./Modal";
import EquityBreakdown from "./EquityBreakdown";
import type { AnalysisResult } from "../types";
import { SCORE_COLORS, SCORE_BG } from "../types";

interface HandReviewProps {
  analysis: AnalysisResult[];
  onClose: () => void;
}

const HandReview = ({ analysis, onClose }: HandReviewProps) => {
  const [expandedCalc, setExpandedCalc] = useState<Set<number>>(new Set());

  const toggleCalc = (idx: number) => {
    setExpandedCalc((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  if (!analysis || analysis.length === 0) return null;

  const equityByStreet: Record<string, number> = {};
  for (const a of analysis) equityByStreet[a.street] = a.equity;

  const chartData = ["preflop", "flop", "turn", "river"]
    .filter((s) => equityByStreet[s] !== undefined)
    .map((s) => ({ street: s, equity: equityByStreet[s] }));

  const mistakes = analysis.filter((a) => a.score === "mistake").length;
  const blunders = analysis.filter((a) => a.score === "blunder").length;

  return (
    <Modal open onClose={onClose} title="Hand Review" maxWidth={560} titleId="review-title">
      {/* Summary */}
      {(mistakes > 0 || blunders > 0) ? (
        <div style={{ marginBottom: 16, fontSize: 14, color: "var(--text-secondary)" }}>
          {blunders > 0 && <span style={{ color: SCORE_COLORS.blunder, fontWeight: 600 }}>{blunders} blunder{blunders > 1 ? "s" : ""}</span>}
          {blunders > 0 && mistakes > 0 && <span> and </span>}
          {mistakes > 0 && <span style={{ color: SCORE_COLORS.mistake, fontWeight: 600 }}>{mistakes} mistake{mistakes > 1 ? "s" : ""}</span>}
          <span> found in this hand.</span>
        </div>
      ) : (
        <div style={{ marginBottom: 16, fontSize: 14, color: SCORE_COLORS.good, fontWeight: 600 }}>
          Clean hand — all decisions were solid.
        </div>
      )}

      {/* Equity chart */}
      <div style={{ marginBottom: 24 }}>
        <div className="section-label">Equity by Street</div>
        <div style={{ display: "flex", gap: 12, alignItems: "flex-end", height: 100 }}>
          {chartData.map((d) => (
            <div key={d.street} style={{ display: "flex", flexDirection: "column", alignItems: "center", flex: 1 }}>
              <div style={{ fontSize: 12, color: "var(--accent)", marginBottom: 4 }}>
                {Math.round(d.equity * 100)}%
              </div>
              <div style={{ width: "100%", height: `${d.equity * 80}px`, background: "linear-gradient(to top, var(--accent), var(--accent-hover))", borderRadius: "4px 4px 0 0", minHeight: 4 }} />
              <div style={{ fontSize: 11, color: "var(--text-muted)", marginTop: 4, textTransform: "capitalize" }}>{d.street}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Decisions */}
      <div>
        <div className="section-label">Decisions</div>
        {analysis.map((a, i) => (
          <div
            key={`${a.street}-${a.action_type}-${i}`}
            style={{ padding: "10px 14px", background: SCORE_BG[a.score] || "var(--bg-surface)", borderRadius: 8, marginBottom: 8, borderLeft: `3px solid ${SCORE_COLORS[a.score] || "var(--text-muted)"}` }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: a.reasoning ? 6 : 0 }}>
              <div>
                <span style={{ color: "var(--text-secondary)", fontSize: 12, textTransform: "capitalize" }}>{a.street}</span>
                <span style={{ color: "#fff", marginLeft: 8, fontSize: 14, fontWeight: 600 }}>{a.action_type}{a.amount ? ` ${a.amount}` : ""}</span>
              </div>
              <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                <span style={{ color: "var(--text-muted)", fontSize: 12 }}>
                  {Math.round(a.equity * 100)}% equity{a.pot_odds ? ` · ${Math.round(a.pot_odds * 100)}% odds` : ""}
                </span>
                <span style={{ color: SCORE_COLORS[a.score] || "var(--text-muted)", fontWeight: 700, fontSize: 13, textTransform: "capitalize" }}>{a.score}</span>
              </div>
            </div>

            {a.reasoning && (
              <div style={{ fontSize: 13, color: "#bbb", lineHeight: 1.5, marginBottom: a.recommendation && a.score !== "good" ? 6 : 0 }}>{a.reasoning}</div>
            )}

            {a.recommendation && a.score !== "good" && (
              <div style={{ fontSize: 13, color: "var(--accent)", fontWeight: 600, lineHeight: 1.5, paddingTop: 4, borderTop: "1px solid rgba(255,255,255,0.05)" }}>
                Suggestion: {a.recommendation}
              </div>
            )}

            {a.equity_details && (
              <>
                <button
                  onClick={() => toggleCalc(i)}
                  style={{ marginTop: 6, background: "none", border: "none", color: "var(--accent)", fontSize: 11, cursor: "pointer", textDecoration: "underline", opacity: 0.8, padding: 0 }}
                >
                  {expandedCalc.has(i) ? "Hide calculation" : "Show calculation"}
                </button>
                {expandedCalc.has(i) && <EquityBreakdown details={a.equity_details} compact />}
              </>
            )}
          </div>
        ))}
      </div>
    </Modal>
  );
};

export default HandReview;
