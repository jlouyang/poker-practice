import React from "react";

interface AnalysisResult {
  player_id: string;
  street: string;
  equity: number;
  pot_odds?: number;
  score: string;
  optimal_action?: string;
  action_type?: string;
  amount?: number;
  reasoning?: string;
  recommendation?: string;
}

interface HandReviewProps {
  analysis: AnalysisResult[];
  onClose: () => void;
}

const SCORE_COLORS: Record<string, string> = {
  good: "#2ecc71",
  mistake: "#f39c12",
  blunder: "#e74c3c",
};

const SCORE_BG: Record<string, string> = {
  good: "rgba(46, 204, 113, 0.06)",
  mistake: "rgba(243, 156, 18, 0.06)",
  blunder: "rgba(231, 76, 60, 0.06)",
};

const HandReview: React.FC<HandReviewProps> = ({ analysis, onClose }) => {
  if (!analysis || analysis.length === 0) {
    return null;
  }

  const equityByStreet: Record<string, number> = {};
  for (const a of analysis) {
    equityByStreet[a.street] = a.equity;
  }

  const streets = ["preflop", "flop", "turn", "river"];
  const chartData = streets
    .filter((s) => equityByStreet[s] !== undefined)
    .map((s) => ({ street: s, equity: equityByStreet[s] }));

  const mistakes = analysis.filter((a) => a.score === "mistake").length;
  const blunders = analysis.filter((a) => a.score === "blunder").length;

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        background: "rgba(0,0,0,0.7)",
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
          maxWidth: 560,
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
            Hand Review
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
              fontSize: 14,
            }}
          >
            Close
          </button>
        </div>

        {/* Summary line */}
        {(mistakes > 0 || blunders > 0) && (
          <div style={{ marginBottom: 16, fontSize: 14, color: "#aaa" }}>
            {blunders > 0 && (
              <span style={{ color: SCORE_COLORS.blunder, fontWeight: 600 }}>
                {blunders} blunder{blunders > 1 ? "s" : ""}
              </span>
            )}
            {blunders > 0 && mistakes > 0 && <span> and </span>}
            {mistakes > 0 && (
              <span style={{ color: SCORE_COLORS.mistake, fontWeight: 600 }}>
                {mistakes} mistake{mistakes > 1 ? "s" : ""}
              </span>
            )}
            <span> found in this hand.</span>
          </div>
        )}
        {mistakes === 0 && blunders === 0 && (
          <div style={{ marginBottom: 16, fontSize: 14, color: SCORE_COLORS.good, fontWeight: 600 }}>
            Clean hand — all decisions were solid.
          </div>
        )}

        {/* Equity chart */}
        <div style={{ marginBottom: 24 }}>
          <div
            style={{
              fontSize: 13,
              color: "#888",
              marginBottom: 8,
              textTransform: "uppercase",
              letterSpacing: 1,
            }}
          >
            Equity by Street
          </div>
          <div style={{ display: "flex", gap: 12, alignItems: "flex-end", height: 100 }}>
            {chartData.map((d) => (
              <div
                key={d.street}
                style={{ display: "flex", flexDirection: "column", alignItems: "center", flex: 1 }}
              >
                <div style={{ fontSize: 12, color: "#4ecca3", marginBottom: 4 }}>
                  {Math.round(d.equity * 100)}%
                </div>
                <div
                  style={{
                    width: "100%",
                    height: `${d.equity * 80}px`,
                    background: "linear-gradient(to top, #4ecca3, #36b58e)",
                    borderRadius: "4px 4px 0 0",
                    minHeight: 4,
                  }}
                />
                <div
                  style={{
                    fontSize: 11,
                    color: "#888",
                    marginTop: 4,
                    textTransform: "capitalize",
                  }}
                >
                  {d.street}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Decision list */}
        <div>
          <div
            style={{
              fontSize: 13,
              color: "#888",
              marginBottom: 8,
              textTransform: "uppercase",
              letterSpacing: 1,
            }}
          >
            Decisions
          </div>
          {analysis.map((a, i) => (
            <div
              key={i}
              style={{
                padding: "10px 14px",
                background: SCORE_BG[a.score] || "rgba(255,255,255,0.03)",
                borderRadius: 8,
                marginBottom: 8,
                borderLeft: `3px solid ${SCORE_COLORS[a.score] || "#888"}`,
              }}
            >
              {/* Header row */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: a.reasoning ? 6 : 0,
                }}
              >
                <div>
                  <span
                    style={{
                      color: "#aaa",
                      fontSize: 12,
                      textTransform: "capitalize",
                    }}
                  >
                    {a.street}
                  </span>
                  <span style={{ color: "#fff", marginLeft: 8, fontSize: 14, fontWeight: 600 }}>
                    {a.action_type}
                    {a.amount ? ` ${a.amount}` : ""}
                  </span>
                </div>
                <div style={{ display: "flex", gap: 12, alignItems: "center" }}>
                  <span style={{ color: "#888", fontSize: 12 }}>
                    {Math.round(a.equity * 100)}% equity
                    {a.pot_odds ? ` · ${Math.round(a.pot_odds * 100)}% odds` : ""}
                  </span>
                  <span
                    style={{
                      color: SCORE_COLORS[a.score] || "#888",
                      fontWeight: 700,
                      fontSize: 13,
                      textTransform: "capitalize",
                    }}
                  >
                    {a.score}
                  </span>
                </div>
              </div>

              {/* Reasoning */}
              {a.reasoning && (
                <div style={{ fontSize: 13, color: "#bbb", lineHeight: 1.5, marginBottom: a.recommendation && a.score !== "good" ? 6 : 0 }}>
                  {a.reasoning}
                </div>
              )}

              {/* Recommendation (only for non-good decisions) */}
              {a.recommendation && a.score !== "good" && (
                <div
                  style={{
                    fontSize: 13,
                    color: "#4ecca3",
                    fontWeight: 600,
                    lineHeight: 1.5,
                    paddingTop: 4,
                    borderTop: "1px solid rgba(255,255,255,0.05)",
                  }}
                >
                  Suggestion: {a.recommendation}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default HandReview;
