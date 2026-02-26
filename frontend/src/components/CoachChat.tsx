import React, { useState, useCallback } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

interface Message {
  role: "user" | "coach";
  text: string;
}

interface CoachChatProps {
  gameId: string;
  onClose: () => void;
}

const CoachChat: React.FC<CoachChatProps> = ({ gameId, onClose }) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: "coach",
      text: "Ask me about any decision in the last hand. For example: 'Why did you raise the turn?' or 'Should I have folded preflop?'",
    },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSend = useCallback(async () => {
    if (!input.trim() || loading) return;

    const question = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", text: question }]);
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/coach/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question, game_id: gameId }),
      });
      const data = await res.json();
      setMessages((prev) => [...prev, { role: "coach", text: data.answer }]);
    } catch {
      setMessages((prev) => [
        ...prev,
        { role: "coach", text: "Sorry, I couldn't process that question." },
      ]);
    }
    setLoading(false);
  }, [input, loading, gameId]);

  return (
    <div
      style={{
        position: "fixed",
        bottom: 16,
        right: 16,
        width: 360,
        maxHeight: 480,
        background: "#1a1a2e",
        border: "1px solid #2c3e50",
        borderRadius: 16,
        display: "flex",
        flexDirection: "column",
        zIndex: 90,
        boxShadow: "0 8px 32px rgba(0,0,0,0.5)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "12px 16px",
          borderBottom: "1px solid #2c3e50",
        }}
      >
        <span style={{ color: "#4ecca3", fontWeight: 700, fontSize: 14 }}>
          Coach Q&A
        </span>
        <button
          onClick={onClose}
          style={{
            background: "none",
            border: "none",
            color: "#888",
            cursor: "pointer",
            fontSize: 16,
          }}
        >
          x
        </button>
      </div>

      <div
        style={{
          flex: 1,
          overflowY: "auto",
          padding: 12,
          display: "flex",
          flexDirection: "column",
          gap: 8,
          maxHeight: 340,
        }}
      >
        {messages.map((msg, i) => (
          <div
            key={i}
            style={{
              alignSelf: msg.role === "user" ? "flex-end" : "flex-start",
              background:
                msg.role === "user"
                  ? "rgba(52, 152, 219, 0.2)"
                  : "rgba(78, 204, 163, 0.1)",
              border: `1px solid ${
                msg.role === "user" ? "#34495e" : "#2c3e50"
              }`,
              borderRadius: 10,
              padding: "8px 12px",
              maxWidth: "85%",
              fontSize: 13,
              color: "#ddd",
              lineHeight: 1.4,
            }}
          >
            {msg.text}
          </div>
        ))}
        {loading && (
          <div style={{ color: "#888", fontSize: 12, fontStyle: "italic" }}>
            Thinking...
          </div>
        )}
      </div>

      <div
        style={{
          display: "flex",
          gap: 8,
          padding: 12,
          borderTop: "1px solid #2c3e50",
        }}
      >
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask about the hand..."
          style={{
            flex: 1,
            padding: "8px 12px",
            borderRadius: 8,
            border: "1px solid #4a6785",
            background: "#16213e",
            color: "#fff",
            fontSize: 13,
            outline: "none",
          }}
        />
        <button
          onClick={handleSend}
          disabled={loading || !input.trim()}
          style={{
            padding: "8px 16px",
            borderRadius: 8,
            border: "none",
            background: "#4ecca3",
            color: "#fff",
            fontWeight: 600,
            fontSize: 13,
            cursor: loading ? "not-allowed" : "pointer",
            opacity: loading ? 0.5 : 1,
          }}
        >
          Ask
        </button>
      </div>
    </div>
  );
};

export default CoachChat;
