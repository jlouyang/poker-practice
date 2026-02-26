import React from "react";

interface HUDStats {
  vpip: number;
  pfr: number;
  af: number;
  hands_played: number;
}

interface HUDProps {
  stats: HUDStats;
  playerName: string;
}

const HUD: React.FC<HUDProps> = ({ stats, playerName }) => {
  if (stats.hands_played < 1) return null;

  return (
    <div
      style={{
        background: "rgba(0, 0, 0, 0.75)",
        borderRadius: 6,
        padding: "4px 8px",
        fontSize: 11,
        fontFamily: "monospace",
        color: "#ccc",
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
      <span style={{ color: "#666" }}>({stats.hands_played}h)</span>
    </div>
  );
};

function getVpipColor(vpip: number): string {
  if (vpip > 40) return "#e74c3c"; // Too loose
  if (vpip > 25) return "#f39c12"; // Loose
  if (vpip > 15) return "#2ecc71"; // Normal
  return "#3498db"; // Tight
}

function getPfrColor(pfr: number): string {
  if (pfr > 30) return "#e74c3c";
  if (pfr > 18) return "#f39c12";
  if (pfr > 10) return "#2ecc71";
  return "#3498db";
}

function getAfColor(af: number): string {
  if (af > 3) return "#e74c3c";
  if (af > 1.5) return "#f39c12";
  if (af > 0.5) return "#2ecc71";
  return "#3498db";
}

export default HUD;
