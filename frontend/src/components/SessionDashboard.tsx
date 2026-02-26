import React, { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface SessionSummary {
  session_id: string;
  total_hands: number;
  human_win_rate: number;
  biggest_pot: number;
  mistakes: number;
  blunders: number;
  player_stats: Record<
    string,
    {
      vpip: number;
      pfr: number;
      af: number;
      hands_played: number;
      pots_won: number;
      total_winnings: number;
    }
  >;
}

interface SessionDashboardProps {
  sessionId: string;
  onClose: () => void;
  onReplayHand: (handId: number) => void;
}

const SessionDashboard: React.FC<SessionDashboardProps> = ({
  sessionId,
  onClose,
  onReplayHand,
}) => {
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [hands, setHands] = useState<
    { id: number; hand_number: number; pot_size: number; winner_ids: string[] }[]
  >([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [summaryRes, handsRes] = await Promise.all([
          fetch(`${API_URL}/session/${sessionId}/summary`),
          fetch(`${API_URL}/session/${sessionId}/hands`),
        ]);
        if (summaryRes.ok) setSummary(await summaryRes.json());
        if (handsRes.ok) setHands(await handsRes.json());
      } catch (e) {
        console.error("Failed to load dashboard", e);
      }
      setLoading(false);
    };
    load();
  }, [sessionId]);

  if (loading) {
    return (
      <div style={overlayStyle}>
        <div style={panelStyle}>
          <p style={{ color: "#888" }}>Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div style={overlayStyle}>
      <div style={panelStyle}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: 20,
          }}
        >
          <h2 style={{ color: "#4ecca3", margin: 0, fontSize: 20 }}>
            Session Dashboard
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
            }}
          >
            Close
          </button>
        </div>

        {summary && (
          <>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "repeat(3, 1fr)",
                gap: 12,
                marginBottom: 24,
              }}
            >
              <StatBox label="Hands Played" value={summary.total_hands} />
              <StatBox
                label="Win Rate"
                value={`${summary.human_win_rate}%`}
                color="#2ecc71"
              />
              <StatBox
                label="Biggest Pot"
                value={summary.biggest_pot}
                color="#f1c40f"
              />
              <StatBox
                label="Mistakes"
                value={summary.mistakes}
                color="#f39c12"
              />
              <StatBox
                label="Blunders"
                value={summary.blunders}
                color="#e74c3c"
              />
              <StatBox
                label="Your VPIP"
                value={`${summary.player_stats?.human?.vpip ?? 0}%`}
              />
            </div>
          </>
        )}

        <div
          style={{
            fontSize: 13,
            color: "#888",
            marginBottom: 8,
            textTransform: "uppercase",
            letterSpacing: 1,
          }}
        >
          Hand History
        </div>
        <div style={{ maxHeight: 300, overflowY: "auto" }}>
          {hands.map((h) => (
            <div
              key={h.id}
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "6px 10px",
                background: "rgba(255,255,255,0.03)",
                borderRadius: 6,
                marginBottom: 4,
                fontSize: 13,
              }}
            >
              <span style={{ color: "#ccc" }}>Hand #{h.hand_number}</span>
              <span style={{ color: "#f1c40f" }}>Pot: {h.pot_size}</span>
              <span
                style={{
                  color: h.winner_ids.includes("human") ? "#2ecc71" : "#e74c3c",
                  fontWeight: 600,
                }}
              >
                {h.winner_ids.includes("human") ? "Won" : "Lost"}
              </span>
              <button
                onClick={() => onReplayHand(h.id)}
                style={{
                  padding: "2px 8px",
                  borderRadius: 4,
                  border: "1px solid #4a6785",
                  background: "transparent",
                  color: "#4ecca3",
                  cursor: "pointer",
                  fontSize: 12,
                }}
              >
                Replay
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const StatBox: React.FC<{
  label: string;
  value: string | number;
  color?: string;
}> = ({ label, value, color = "#fff" }) => (
  <div
    style={{
      background: "rgba(255,255,255,0.03)",
      borderRadius: 10,
      padding: "12px 16px",
      textAlign: "center",
    }}
  >
    <div style={{ fontSize: 11, color: "#888", marginBottom: 4 }}>{label}</div>
    <div style={{ fontSize: 20, fontWeight: 700, color }}>{value}</div>
  </div>
);

const overlayStyle: React.CSSProperties = {
  position: "fixed",
  inset: 0,
  background: "rgba(0,0,0,0.7)",
  display: "flex",
  alignItems: "center",
  justifyContent: "center",
  zIndex: 100,
};

const panelStyle: React.CSSProperties = {
  background: "#1a1a2e",
  border: "1px solid #2c3e50",
  borderRadius: 16,
  padding: 32,
  maxWidth: 600,
  width: "90%",
  maxHeight: "85vh",
  overflowY: "auto",
};

export default SessionDashboard;
