import { useState, useCallback, useRef, useEffect } from "react";
import SetupScreen from "./components/SetupScreen";
import Table from "./components/Table";
import ActionPanel from "./components/ActionPanel";
import HandReview from "./components/HandReview";
import HandReplayer from "./components/HandReplayer";
import SessionDashboard from "./components/SessionDashboard";
import CoachChat from "./components/CoachChat";
import type {
  CreateGameRequest,
  GameStateData,
  LegalAction,
  WsMessage,
  GamePhase,
  HandResult,
} from "./types";
import "./App.css";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const WS_URL = API_URL.replace(/^http/, "ws");

interface AnalysisResult {
  player_id: string;
  street: string;
  equity: number;
  pot_odds?: number;
  score: string;
  optimal_action?: string;
  action_type?: string;
  amount?: number;
  reasoning?: string;
  recommendation?: string;
}

function App() {
  const [phase, setPhase] = useState<GamePhase>("setup");
  const [gameState, setGameState] = useState<GameStateData | null>(null);
  const [legalActions, setLegalActions] = useState<LegalAction[]>([]);
  const [isMyTurn, setIsMyTurn] = useState(false);
  const [handResult, setHandResult] = useState<HandResult | null>(null);
  const [bigBlind, setBigBlind] = useState(10);
  const [analysis, setAnalysis] = useState<AnalysisResult[] | null>(null);
  const [showReview, setShowReview] = useState(false);
  const [playerStats, setPlayerStats] = useState<Record<string, any>>({});
  const [showDashboard, setShowDashboard] = useState(false);
  const [replayData, setReplayData] = useState<any>(null);
  const [showCoach, setShowCoach] = useState(false);
  const [gameId, setGameId] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  const handleStart = useCallback(async (config: CreateGameRequest) => {
    setBigBlind(config.big_blind);

    const res = await fetch(`${API_URL}/game/create`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(config),
    });
    const data = await res.json();
    setGameId(data.game_id);
    setPhase("playing");

    const ws = new WebSocket(`${WS_URL}/game/${data.game_id}/ws`);
    wsRef.current = ws;

    ws.onmessage = (event) => {
      const msg: WsMessage = JSON.parse(event.data);
      handleWsMessage(msg);
    };

    ws.onclose = () => {
      console.log("WebSocket closed");
    };
  }, []);

  const handleWsMessage = useCallback((msg: WsMessage) => {
    const { type, data } = msg;

    if (!data || !data.players) {
      if (type === "game_over") {
        setPhase("setup");
      }
      return;
    }

    switch (type) {
      case "new_hand":
        setHandResult(null);
        setAnalysis(null);
        setShowReview(false);
        setGameState(data);
        setIsMyTurn(false);
        setLegalActions([]);
        break;

      case "action_required":
        setGameState(data);
        setLegalActions(data.legal_actions || []);
        setIsMyTurn(true);
        break;

      case "state_update":
      case "bot_action":
        setGameState(data);
        setIsMyTurn(false);
        setLegalActions([]);
        if ((data as any).player_stats) setPlayerStats((data as any).player_stats);
        break;

      case "hand_complete":
        setGameState(data);
        setHandResult(data.result || null);
        setAnalysis((data as any).analysis || null);
        if ((data as any).player_stats) setPlayerStats((data as any).player_stats);
        setIsMyTurn(false);
        setLegalActions([]);
        break;

      case "game_over":
        setPhase("setup");
        break;
    }
  }, []);

  const handleAction = useCallback(
    (action: string, amount: number) => {
      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        wsRef.current.send(JSON.stringify({ type: "action", action, amount }));
        setIsMyTurn(false);
        setLegalActions([]);
      }
    },
    []
  );

  const handleNextHand = useCallback(() => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "continue" }));
      setHandResult(null);
      setAnalysis(null);
      setShowReview(false);
    }
  }, []);

  const loadReplay = useCallback(async (handId: number) => {
    try {
      const res = await fetch(`${API_URL}/hand/${handId}/replay`);
      if (res.ok) {
        const data = await res.json();
        setReplayData(data);
        setShowDashboard(false);
      }
    } catch (e) {
      console.error("Failed to load replay", e);
    }
  }, []);

  // Keyboard shortcuts: F=fold, C=call/check, R=raise, Space/N=next hand
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const key = e.key.toLowerCase();

      if (handResult && (key === " " || key === "n") && !showReview) {
        e.preventDefault();
        handleNextHand();
        return;
      }

      if (!isMyTurn || showReview) return;
      const types = new Set(legalActions.map((a) => a.action_type));

      if (key === "f" && types.has("fold")) {
        handleAction("fold", 0);
      } else if (key === "c") {
        if (types.has("call")) {
          const callAction = legalActions.find((a) => a.action_type === "call");
          handleAction("call", callAction?.min_amount ?? 0);
        } else if (types.has("check")) {
          handleAction("check", 0);
        }
      } else if (key === "r") {
        const ra = legalActions.find(
          (a) => a.action_type === "raise" || a.action_type === "bet"
        );
        if (ra) handleAction(ra.action_type, ra.min_amount);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isMyTurn, legalActions, handleAction, handleNextHand, handResult, showReview]);

  useEffect(() => {
    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, []);

  if (phase === "setup") {
    return <SetupScreen onStart={handleStart} />;
  }

  if (!gameState) {
    return (
      <div className="app">
        <p>Connecting...</p>
      </div>
    );
  }

  return (
    <div className="app">
      <Table
        players={gameState.players}
        communityCards={gameState.community_cards}
        pot={gameState.pot}
        dealerSeat={gameState.dealer_seat}
        currentPlayerId={gameState.current_player_id}
        street={gameState.street}
        handNumber={gameState.hand_number}
        playerStats={playerStats}
      />

      {handResult && (
        <div
          style={{
            textAlign: "center",
            padding: "16px 24px",
            background: "rgba(46, 204, 113, 0.1)",
            borderRadius: 10,
            margin: "8px auto",
            maxWidth: 600,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 16,
          }}
        >
          <div>
            {handResult.winners &&
              Object.entries(handResult.winners).map(([pid, info]) => (
                <div key={pid} style={{ color: "#2ecc71", fontWeight: 600 }}>
                  {pid === "human" ? "You" : pid} wins {info.amount} with{" "}
                  {info.hand}
                </div>
              ))}
            {handResult.player_id && (
              <div style={{ color: "#2ecc71", fontWeight: 600 }}>
                {handResult.player_id === "human" ? "You" : handResult.player_id}{" "}
                wins {handResult.amount} (opponents folded)
              </div>
            )}
          </div>
          {analysis && analysis.length > 0 && (
            <button
              onClick={() => setShowReview(true)}
              style={{
                padding: "6px 16px",
                borderRadius: 8,
                border: "1px solid #4ecca3",
                background: "transparent",
                color: "#4ecca3",
                fontWeight: 600,
                fontSize: 13,
                cursor: "pointer",
              }}
            >
              Review Hand
            </button>
          )}
          <button
            onClick={handleNextHand}
            style={{
              padding: "8px 20px",
              borderRadius: 8,
              border: "none",
              background: "linear-gradient(135deg, #4ecca3, #36b58e)",
              color: "#fff",
              fontWeight: 700,
              fontSize: 14,
              cursor: "pointer",
              boxShadow: "0 2px 8px rgba(78, 204, 163, 0.3)",
            }}
          >
            Next Hand
          </button>
        </div>
      )}

      <ActionPanel
        legalActions={legalActions}
        onAction={handleAction}
        disabled={!isMyTurn}
        potSize={gameState.pot}
        bigBlind={bigBlind}
        myCurrentBet={gameState.players.find((p) => p.is_human)?.current_bet ?? 0}
      />

      {gameId && (
        <button
          onClick={() => setShowDashboard(true)}
          style={{
            position: "fixed",
            top: 16,
            left: 16,
            padding: "6px 14px",
            borderRadius: 8,
            border: "1px solid #4a6785",
            background: "rgba(0,0,0,0.5)",
            color: "#4ecca3",
            fontSize: 13,
            fontWeight: 600,
            cursor: "pointer",
            zIndex: 10,
          }}
        >
          Dashboard
        </button>
      )}

      {showReview && analysis && (
        <HandReview analysis={analysis} onClose={() => setShowReview(false)} />
      )}

      {showDashboard && gameId && (
        <SessionDashboard
          sessionId={gameId}
          onClose={() => setShowDashboard(false)}
          onReplayHand={loadReplay}
        />
      )}

      {replayData && (
        <HandReplayer
          handData={replayData}
          onClose={() => setReplayData(null)}
        />
      )}

      {gameId && handResult && (
        <button
          onClick={() => setShowCoach((v) => !v)}
          style={{
            position: "fixed",
            bottom: 16,
            right: showCoach ? 380 : 16,
            padding: "8px 16px",
            borderRadius: 20,
            border: "none",
            background: "#4ecca3",
            color: "#fff",
            fontWeight: 700,
            fontSize: 13,
            cursor: "pointer",
            boxShadow: "0 2px 10px rgba(78,204,163,0.3)",
            zIndex: 91,
          }}
        >
          {showCoach ? "Hide Coach" : "Ask Coach"}
        </button>
      )}

      {showCoach && gameId && (
        <CoachChat gameId={gameId} onClose={() => setShowCoach(false)} />
      )}
    </div>
  );
}

export default App;
