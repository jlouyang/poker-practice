/**
 * Heads-up display overlay for bot player stats.
 *
 * Shows VPIP, PFR, AF, and hands played in a compact monospace bar.
 * Stats are color-coded by range (e.g., VPIP >40% = red/loose,
 * 15-25% = green/normal). Only appears on hover over bot players
 * after at least 1 hand has been played.
 */
import type { HUDStats } from "../types";

interface HUDProps {
  stats: HUDStats;
}

function HUD({ stats }: HUDProps) {
  if (stats.hands_played < 1) return null;

  return (
    <div
      style={{
        background: "rgba(0, 0, 0, 0.75)",
        borderRadius: 6,
        padding: "4px 8px",
        fontSize: 11,
        fontFamily: "monospace",
        color: "var(--text-light)",
        display: "flex",
        gap: 8,
        whiteSpace: "nowrap",
      }}
    >
      <span>
        VPIP: <span style={{ color: getVpipColor(stats.vpip) }}>{stats.vpip}%</span>
      </span>
      <span>
        PFR: <span style={{ color: getPfrColor(stats.pfr) }}>{stats.pfr}%</span>
      </span>
      <span>
        AF: <span style={{ color: getAfColor(stats.af) }}>{stats.af}</span>
      </span>
      <span style={{ color: "var(--text-dim)" }}>({stats.hands_played}h)</span>
    </div>
  );
}

function getVpipColor(vpip: number): string {
  if (vpip > 40) return "var(--color-danger)";
  if (vpip > 25) return "var(--color-warning)";
  if (vpip > 15) return "var(--color-success)";
  return "var(--color-info)";
}

function getPfrColor(pfr: number): string {
  if (pfr > 30) return "var(--color-danger)";
  if (pfr > 18) return "var(--color-warning)";
  if (pfr > 10) return "var(--color-success)";
  return "var(--color-info)";
}

function getAfColor(af: number): string {
  if (af > 3) return "var(--color-danger)";
  if (af > 1.5) return "var(--color-warning)";
  if (af > 0.5) return "var(--color-success)";
  return "var(--color-info)";
}

export default HUD;
