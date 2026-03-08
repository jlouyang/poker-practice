import { useState, useRef, useEffect } from "react";

export interface TrainingToolsState {
  preflopChart: boolean;
  positionGuide: boolean;
  potOdds: boolean;
  handStrength: boolean;
  sizingTips: boolean;
  rangeViz: boolean;
}

const TOOL_LABELS: { key: keyof TrainingToolsState; label: string; desc: string }[] = [
  { key: "positionGuide", label: "Position Guide", desc: "Show seat positions and advantage" },
  { key: "potOdds", label: "Pot Odds", desc: "Display live pot odds during your turn" },
  { key: "handStrength", label: "Hand Strength", desc: "Show your current hand strength" },
  { key: "sizingTips", label: "Sizing Tips", desc: "Bet sizing guidance on presets" },
  { key: "rangeViz", label: "Opponent Ranges", desc: "Estimate opponent hand ranges from their actions" },
];

interface TrainingToolsProps {
  tools: TrainingToolsState;
  onToggle: (key: keyof TrainingToolsState) => void;
}

function TrainingTools({ tools, onToggle }: TrainingToolsProps) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    if (open) document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  const activeCount = Object.values(tools).filter(Boolean).length;

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        className="btn btn-outline"
        style={{
          color: activeCount > 0 ? "var(--accent)" : "var(--text-subtle)",
          borderColor: activeCount > 0 ? "var(--accent)" : undefined,
          display: "flex",
          alignItems: "center",
          gap: 6,
          fontSize: 13,
        }}
        onClick={() => setOpen((v) => !v)}
      >
        <span style={{ fontSize: 15 }}>🎓</span>
        Training
        {activeCount > 0 && (
          <span
            style={{
              background: "var(--accent)",
              color: "#fff",
              borderRadius: "var(--radius-full)",
              width: 18,
              height: 18,
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 10,
              fontWeight: 800,
            }}
          >
            {activeCount}
          </span>
        )}
      </button>

      {open && (
        <div
          style={{
            position: "absolute",
            top: "calc(100% + 8px)",
            left: 0,
            background: "var(--bg-primary)",
            border: "1px solid var(--border-default)",
            borderRadius: "var(--radius-xl)",
            padding: 16,
            minWidth: 260,
            zIndex: 50,
            boxShadow: "var(--shadow-lg)",
          }}
        >
          <div
            style={{
              fontSize: 13,
              color: "var(--accent)",
              fontWeight: 700,
              marginBottom: 12,
              textTransform: "uppercase",
              letterSpacing: 1,
            }}
          >
            Training Tools
          </div>
          {TOOL_LABELS.map(({ key, label, desc }) => (
            <label
              key={key}
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 10,
                padding: "8px 0",
                borderBottom: "1px solid var(--border-subtle)",
                cursor: "pointer",
              }}
            >
              <input
                type="checkbox"
                checked={tools[key]}
                onChange={() => onToggle(key)}
                style={{ marginTop: 2, accentColor: "var(--accent)" }}
              />
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: "var(--text-primary)" }}>
                  {label}
                </div>
                <div style={{ fontSize: 11, color: "var(--text-muted)", lineHeight: 1.4 }}>
                  {desc}
                </div>
              </div>
            </label>
          ))}
          <div style={{ fontSize: 10, color: "var(--text-dim)", marginTop: 10, lineHeight: 1.4 }}>
            Toggle tools on/off to customize your learning experience. Settings are saved automatically.
          </div>
        </div>
      )}
    </div>
  );
}

export default TrainingTools;
