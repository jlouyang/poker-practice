import type { LegalAction } from "../types";

interface PotOddsDisplayProps {
  potSize: number;
  legalActions: LegalAction[];
  equity?: number | null;
}

function PotOddsDisplay({ potSize, legalActions, equity }: PotOddsDisplayProps) {
  const callAction = legalActions.find((a) => a.action_type === "call");
  if (!callAction) return null;

  const callAmount = callAction.min_amount;
  if (callAmount <= 0) return null;

  const potOdds = (callAmount / (potSize + callAmount)) * 100;
  const needEquity = potOdds;
  const hasGoodOdds = equity != null && equity * 100 >= needEquity;

  return (
    <div
      style={{
        background: "rgba(0, 0, 0, 0.75)",
        borderRadius: 8,
        padding: "8px 14px",
        display: "flex",
        flexDirection: "column",
        gap: 4,
        minWidth: 180,
        border: "1px solid var(--border-subtle)",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: 0.8 }}>
          Pot Odds
        </span>
        <span style={{ fontSize: 14, fontWeight: 700, color: "var(--color-info)" }}>
          {potOdds.toFixed(1)}%
        </span>
      </div>
      <div style={{ display: "flex", justifyContent: "space-between", fontSize: 11, color: "var(--text-secondary)" }}>
        <span>Call {callAmount} into {potSize}</span>
        <span>{(potSize / callAmount).toFixed(1)}:1</span>
      </div>
      <div
        style={{
          height: 4,
          borderRadius: 2,
          background: "rgba(255,255,255,0.1)",
          marginTop: 2,
          overflow: "hidden",
          position: "relative",
        }}
      >
        <div
          style={{
            position: "absolute",
            left: 0,
            top: 0,
            height: "100%",
            width: `${Math.min(potOdds, 100)}%`,
            background: "var(--color-info)",
            borderRadius: 2,
          }}
        />
        {equity != null && (
          <div
            style={{
              position: "absolute",
              left: `${Math.min(equity * 100, 100)}%`,
              top: -2,
              width: 2,
              height: 8,
              background: hasGoodOdds ? "var(--color-success)" : "var(--color-danger)",
              borderRadius: 1,
            }}
            title={`Your equity: ${(equity * 100).toFixed(0)}%`}
          />
        )}
      </div>
      <div style={{ fontSize: 10, color: "var(--text-dim)", lineHeight: 1.4 }}>
        {equity != null ? (
          hasGoodOdds ? (
            <span style={{ color: "var(--color-success)" }}>
              ✓ You need {needEquity.toFixed(0)}% equity to call — you have {(equity * 100).toFixed(0)}%
            </span>
          ) : (
            <span style={{ color: "var(--color-danger)" }}>
              ✗ You need {needEquity.toFixed(0)}% equity to call — you have {(equity * 100).toFixed(0)}%
            </span>
          )
        ) : (
          <span>You need at least {needEquity.toFixed(0)}% equity to call profitably</span>
        )}
      </div>
    </div>
  );
}

export default PotOddsDisplay;
