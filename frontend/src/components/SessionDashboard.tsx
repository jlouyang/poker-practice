/**
 * Session dashboard modal with aggregate statistics and hand history.
 *
 * Loads data from two endpoints on mount:
 *   GET /session/{id}/summary — aggregate stats (win rate, VPIP, mistakes, etc.)
 *   GET /session/{id}/hands   — list of hands with IDs for replay
 *
 * Displays stat boxes in a grid and a scrollable hand history list
 * with "Replay" buttons that load the hand replayer.
 */
import { useEffect, useState } from "react";
import Modal from "./Modal";
import type { SessionSummary, SessionHand } from "../types";

import { API_URL } from "../config";

interface SessionDashboardProps {
  sessionId: string;
  sessionToken: string | null;
  onClose: () => void;
  onReplayHand: (handId: number) => void;
}

const SessionDashboard = ({ sessionId, sessionToken, onClose, onReplayHand }: SessionDashboardProps) => {
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [hands, setHands] = useState<SessionHand[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        const headers: Record<string, string> = {};
        if (sessionToken) headers["X-Session-Token"] = sessionToken;
        const [summaryRes, handsRes] = await Promise.all([
          fetch(`${API_URL}/session/${sessionId}/summary`, { headers }),
          fetch(`${API_URL}/session/${sessionId}/hands`),
        ]);
        if (summaryRes.ok) setSummary(await summaryRes.json());
        else setError("Failed to load session summary");
        if (handsRes.ok) setHands(await handsRes.json());
      } catch {
        setError("Network error loading dashboard");
      }
      setLoading(false);
    };
    load();
  }, [sessionId, sessionToken]);

  return (
    <Modal open onClose={onClose} title="Session Dashboard" titleId="dashboard-title">
      {loading && <p style={{ color: "var(--text-muted)" }}>Loading...</p>}
      {error && <p style={{ color: "var(--color-danger)" }}>{error}</p>}

      {summary && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12, marginBottom: 24 }}>
          <StatBox label="Hands Played" value={summary.total_hands} />
          <StatBox label="Win Rate" value={`${summary.human_win_rate}%`} color="var(--color-success)" />
          <StatBox label="Biggest Pot" value={summary.biggest_pot} color="var(--color-gold)" />
          <StatBox label="Mistakes" value={summary.mistakes} color="var(--color-warning)" />
          <StatBox label="Blunders" value={summary.blunders} color="var(--color-danger)" />
          <StatBox label="Your VPIP" value={`${summary.player_stats?.human?.vpip ?? 0}%`} />
        </div>
      )}

      <div className="section-label">Hand History</div>
      <div style={{ maxHeight: 300, overflowY: "auto" }}>
        {hands.map((h) => (
          <div key={h.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "6px 10px", background: "var(--bg-surface)", borderRadius: 6, marginBottom: 4, fontSize: 13 }}>
            <span style={{ color: "#ccc" }}>Hand #{h.hand_number}</span>
            <span style={{ color: "var(--color-gold)" }}>Pot: {h.pot_size}</span>
            <span style={{ color: h.winner_ids.includes("human") ? "var(--color-success)" : "var(--color-danger)", fontWeight: 600 }}>
              {h.winner_ids.includes("human") ? "Won" : "Lost"}
            </span>
            <button
              onClick={() => onReplayHand(h.id)}
              style={{ padding: "2px 8px", borderRadius: 4, border: "1px solid var(--border-input)", background: "transparent", color: "var(--accent)", cursor: "pointer", fontSize: 12 }}
              aria-label={`Replay hand #${h.hand_number}`}
            >
              Replay
            </button>
          </div>
        ))}
      </div>
    </Modal>
  );
};

function StatBox({ label, value, color = "#fff" }: { label: string; value: string | number; color?: string }) {
  return (
    <div className="surface" style={{ padding: "12px 16px", textAlign: "center" }} aria-label={`${label}: ${value}`}>
      <div style={{ fontSize: 11, color: "var(--text-muted)", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 20, fontWeight: 700, color }}>{value}</div>
    </div>
  );
}

export default SessionDashboard;
