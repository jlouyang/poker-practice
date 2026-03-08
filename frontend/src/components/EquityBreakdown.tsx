/**
 * Monte Carlo equity breakdown display.
 *
 * Shared by the hint panel (in App) and hand review (per-decision).
 * Shows win/tie/loss percentages, a colored bar, likely hands at showdown,
 * and numbered decision logic steps. Supports compact mode for inline use.
 */
import type { EquityDetails } from "../types";

interface EquityBreakdownProps {
  details: EquityDetails;
  compact?: boolean;
}

export default function EquityBreakdown({ details, compact = false }: EquityBreakdownProps) {
  const total = details.wins + details.ties + details.losses;
  const winPct = total > 0 ? ((details.wins / total) * 100).toFixed(1) : "0";
  const tiePct = total > 0 ? ((details.ties / total) * 100).toFixed(1) : "0";
  const lossPct = total > 0 ? ((details.losses / total) * 100).toFixed(1) : "0";
  const fontSize = compact ? 11 : 12;

  return (
    <div style={{ textAlign: "left", marginTop: 8, fontSize, lineHeight: 1.6, padding: compact ? "8px 10px" : 0, background: compact ? "rgba(0,0,0,0.2)" : "transparent", borderRadius: 6 }}>
      {details.current_hand && (
        <div style={{ color: "var(--color-gold)", fontWeight: 600, marginBottom: 4 }}>
          Current hand: {details.current_hand}
        </div>
      )}

      <div style={{ color: "var(--text-subtle)", marginBottom: compact ? 4 : 6 }}>
        {compact ? `${details.simulations.toLocaleString()} sims` : `Monte Carlo: ${details.simulations.toLocaleString()} simulations`} vs {details.num_opponents} opponent{details.num_opponents > 1 ? "s" : ""}
        {compact && details.pot > 0 && <> &middot; Pot: {details.pot}</>}
        {compact && details.to_call > 0 && <> &middot; To call: {details.to_call}</>}
      </div>

      <div style={{ display: "flex", gap: 12, marginBottom: compact ? 6 : 8 }}>
        <span style={{ color: "var(--color-success)" }}>Win {winPct}%</span>
        <span style={{ color: "var(--color-warning)" }}>Tie {tiePct}%</span>
        <span style={{ color: "var(--color-danger)" }}>Lose {lossPct}%</span>
      </div>

      <div style={{ display: "flex", height: compact ? 5 : 6, borderRadius: 3, overflow: "hidden", marginBottom: compact ? 6 : 8 }}>
        <div style={{ width: `${winPct}%`, background: "var(--color-success)" }} />
        <div style={{ width: `${tiePct}%`, background: "var(--color-warning)" }} />
        <div style={{ width: `${lossPct}%`, background: "var(--color-danger)" }} />
      </div>

      {details.hand_distribution.length > 0 && (
        <div style={{ marginBottom: compact ? 6 : 8 }}>
          <div style={{ color: "var(--text-subtle)", fontSize: fontSize - 1, marginBottom: compact ? 2 : 4 }}>Likely hands{compact ? ":" : " at showdown:"}</div>
          {details.hand_distribution.map((h) => (
            <div key={h.hand} style={{ display: "flex", justifyContent: "space-between", color: "#ccc", fontSize: compact ? 11 : 12 }}>
              <span>{h.hand}</span>
              <span style={{ color: "var(--text-subtle)" }}>{h.pct}%</span>
            </div>
          ))}
        </div>
      )}

      <div style={{ borderTop: "1px solid var(--border-subtle)", paddingTop: compact ? 4 : 6 }}>
        <div style={{ color: "var(--text-subtle)", fontSize: fontSize - 1, marginBottom: compact ? 2 : 4 }}>Decision logic:</div>
        {details.decision_steps.map((step, i) => (
          <div key={i} style={{ color: "#bbb", paddingLeft: compact ? 0 : 8, position: "relative", fontSize: compact ? 11 : 12 }}>
            <span style={{ color: "var(--border-input)", marginRight: 4 }}>{i + 1}.</span>
            {step}
          </div>
        ))}
      </div>
    </div>
  );
}
