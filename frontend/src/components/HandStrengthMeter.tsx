export interface HandStrengthData {
  hand_name: string;
  category: string;
  percentile: number;
  description: string;
}

interface HandStrengthMeterProps {
  data: HandStrengthData;
}

function getBarColor(percentile: number): string {
  if (percentile >= 80) return "var(--color-success)";
  if (percentile >= 60) return "#4ecca3";
  if (percentile >= 40) return "var(--color-warning)";
  if (percentile >= 20) return "var(--color-orange)";
  return "var(--color-danger)";
}

function getCategoryColor(category: string): string {
  switch (category) {
    case "premium": return "var(--color-success)";
    case "strong": return "#4ecca3";
    case "good": return "var(--color-warning)";
    case "playable": return "var(--color-orange)";
    case "speculative": return "var(--color-danger)";
    default: return "var(--text-dim)";
  }
}

function HandStrengthMeter({ data }: HandStrengthMeterProps) {
  const barColor = getBarColor(data.percentile);
  const catColor = getCategoryColor(data.category);

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
          Hand Strength
        </span>
        <span style={{ fontSize: 11, fontWeight: 700, color: catColor, textTransform: "capitalize" }}>
          {data.category}
        </span>
      </div>
      <div style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)" }}>
        {data.hand_name}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        <div
          style={{
            flex: 1,
            height: 6,
            borderRadius: 3,
            background: "rgba(255,255,255,0.1)",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${data.percentile}%`,
              background: `linear-gradient(90deg, ${barColor}aa, ${barColor})`,
              borderRadius: 3,
              transition: "width 0.3s ease",
            }}
          />
        </div>
        <span style={{ fontSize: 12, fontWeight: 700, color: barColor, minWidth: 36, textAlign: "right" }}>
          {data.percentile}%
        </span>
      </div>
      <div style={{ fontSize: 10, color: "var(--text-dim)", lineHeight: 1.4 }}>
        {data.description}
      </div>
    </div>
  );
}

export default HandStrengthMeter;
