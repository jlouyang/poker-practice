/**
 * Post-hand AI coach chat sidebar.
 *
 * Sends questions to POST /coach/ask and displays responses in a chat UI.
 * The coach bot (LLMCoachBot on the backend) uses the Claude API to answer
 * questions about the last hand. Falls back to a generic message if the
 * session has no coach bot or the API call fails.
 *
 * Auto-scrolls to the latest message and uses aria-live for accessibility.
 */
import { useState, useCallback, useRef, useEffect } from "react";

import { API_URL } from "../config";

interface Message {
  id: number;
  role: "user" | "coach";
  text: string;
}

interface CoachChatProps {
  gameId: string;
  sessionToken: string | null;
  onClose: () => void;
}

let msgId = 0;

const CoachChat = ({ gameId, sessionToken, onClose }: CoachChatProps) => {
  const [messages, setMessages] = useState<Message[]>([
    { id: ++msgId, role: "coach", text: "Ask me about any decision in the last hand. For example: 'Why did you raise the turn?' or 'Should I have folded preflop?'" },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const messagesEnd = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEnd.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = useCallback(async () => {
    if (!input.trim() || loading) return;
    const question = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { id: ++msgId, role: "user", text: question }]);
    setLoading(true);

    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (sessionToken) headers["X-Session-Token"] = sessionToken;
      const res = await fetch(`${API_URL}/coach/ask`, {
        method: "POST",
        headers,
        body: JSON.stringify({ question, game_id: gameId }),
      });
      if (!res.ok) throw new Error("non-ok");
      const data = await res.json();
      setMessages((prev) => [...prev, { id: ++msgId, role: "coach", text: data.answer ?? "No response." }]);
    } catch {
      setMessages((prev) => [...prev, { id: ++msgId, role: "coach", text: "Sorry, I couldn't process that question." }]);
    }
    setLoading(false);
  }, [input, loading, gameId, sessionToken]);

  return (
    <div
      style={{ position: "fixed", bottom: 16, right: 16, width: 360, maxHeight: 480, background: "var(--bg-primary)", border: "1px solid var(--border-default)", borderRadius: "var(--radius-2xl)", display: "flex", flexDirection: "column", zIndex: "var(--z-coach)" as unknown as number, boxShadow: "var(--shadow-lg)" }}
      role="complementary"
      aria-label="Coach Q&A chat"
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "12px 16px", borderBottom: "1px solid var(--border-default)" }}>
        <span style={{ color: "var(--accent)", fontWeight: 700, fontSize: 14 }}>Coach Q&A</span>
        <button onClick={onClose} style={{ background: "none", border: "none", color: "var(--text-muted)", cursor: "pointer", fontSize: 18, padding: "4px 8px" }} aria-label="Close coach chat">
          ✕
        </button>
      </div>

      <div role="log" aria-live="polite" style={{ flex: 1, overflowY: "auto", padding: 12, display: "flex", flexDirection: "column", gap: 8, maxHeight: 340 }}>
        {messages.map((msg) => (
          <div
            key={msg.id}
            style={{
              alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
              background: msg.role === "user" ? "rgba(52, 152, 219, 0.2)" : "rgba(78, 204, 163, 0.1)",
              border: `1px solid ${msg.role === "user" ? "#34495e" : "var(--border-default)"}`,
              borderRadius: 10, padding: "8px 12px", maxWidth: "85%", fontSize: 13, color: "#ddd", lineHeight: 1.4,
            }}
          >
            {msg.text}
          </div>
        ))}
        {loading && <div style={{ color: "var(--text-muted)", fontSize: 12, fontStyle: "italic" }}>Thinking...</div>}
        <div ref={messagesEnd} />
      </div>

      <div style={{ display: "flex", gap: 8, padding: 12, borderTop: "1px solid var(--border-default)" }}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask about the hand..."
          aria-label="Ask the coach a question"
          style={{ flex: 1, padding: "8px 12px", borderRadius: 8, border: "1px solid var(--border-input)", background: "var(--bg-secondary)", color: "#fff", fontSize: 13, outline: "none" }}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          style={{ padding: "8px 16px", borderRadius: 8, border: "none", background: "var(--accent)", color: "#fff", fontWeight: 600, fontSize: 13, cursor: loading ? "not-allowed" : "pointer", opacity: loading ? 0.5 : 1 }}
        >
          Ask
        </button>
      </div>
    </div>
  );
};

export default CoachChat;
