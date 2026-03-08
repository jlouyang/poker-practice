/**
 * Root application component.
 *
 * Phases:
 *   "setup"   — SetupScreen (configure table and start)
 *   "playing" — Table + ActionPanel + modals (review, dashboard, coach, etc.)
 *
 * All game state lives in the useGameSocket hook. This component handles:
 *   - Rendering the appropriate phase UI
 *   - Toast notifications for errors
 */
import { useState, useCallback, useEffect, useRef } from "react";
import SetupScreen from "./components/SetupScreen";
import Table from "./components/Table";
import ActionPanel from "./components/ActionPanel";
import HandReview from "./components/HandReview";
import HandReplayer from "./components/HandReplayer";
import SessionDashboard from "./components/SessionDashboard";
import CoachChat from "./components/CoachChat";
import Modal from "./components/Modal";
import ToastContainer, { type ToastMessage } from "./components/Toast";
import HandResultBar from "./components/HandResultBar";
import HintPanel from "./components/HintPanel";
import TrainingTools, { type TrainingToolsState } from "./components/TrainingTools";
import PreflopChart, { type Position } from "./components/PreflopChart";
import PotOddsDisplay from "./components/PotOddsDisplay";
import HandStrengthMeter from "./components/HandStrengthMeter";
import RangeVisualization, { type ActionEntry } from "./components/RangeVisualization";
import { useGameSocket, type ToastEmitter } from "./hooks/useGameSocket";
import { useKeyboardShortcuts } from "./hooks/useKeyboardShortcuts";
import { soundManager } from "./audio/SoundManager";
import type { PlayerInfo } from "./types";
import "./App.css";

const TRAINING_TOOLS_KEY = "poker-training-tools";

function loadTrainingTools(): TrainingToolsState {
  try {
    const stored = localStorage.getItem(TRAINING_TOOLS_KEY);
    if (stored) return JSON.parse(stored);
  } catch { /* use defaults */ }
  return { preflopChart: false, positionGuide: false, potOdds: false, handStrength: false, sizingTips: false, rangeViz: false };
}

function computeHumanPosition(
  players: PlayerInfo[],
  dealerSeat: number,
): Position | null {
  const activeSeats = players.filter((p) => p.is_active || p.stack > 0).map((p) => p.seat).sort((a, b) => a - b);
  const n = activeSeats.length;
  if (n < 2) return null;

  const nextActive = (from: number): number => {
    for (let i = 1; i <= players.length; i++) {
      const s = (from + i) % players.length;
      if (activeSeats.includes(s)) return s;
    }
    return -1;
  };

  const ordered: number[] = [];
  let current = dealerSeat;
  for (let i = 0; i < n; i++) {
    if (i === 0) ordered.push(current);
    else { current = nextActive(current); ordered.push(current); }
  }

  const human = players.find((p) => p.is_human);
  if (!human) return null;
  const humanIdx = ordered.indexOf(human.seat);
  if (humanIdx === -1) return null;

  if (n <= 3) {
    const names: Position[] = n === 2 ? ["BTN", "BB"] : ["BTN", "SB", "BB"];
    return names[humanIdx] ?? null;
  }

  if (humanIdx === 0) return "BTN";
  if (humanIdx === 1) return "SB";
  if (humanIdx === 2) return "BB";

  const remaining = n - 3;
  const posInRemaining = humanIdx - 3;
  if (remaining <= 1) return "UTG";
  if (remaining <= 2) return posInRemaining === 0 ? "UTG" : "CO";
  if (remaining <= 3) return (["UTG", "MP", "CO"] as Position[])[posInRemaining] ?? "MP";
  if (remaining <= 4) return (["UTG", "MP", "MP", "CO"] as Position[])[posInRemaining] ?? "MP";
  return (["UTG", "UTG", "MP", "MP", "CO"] as Position[])[posInRemaining] ?? "MP";
}

const LEGEND_ITEMS = [
  ["VPIP", "Voluntarily Put $ In Pot", "% of hands a player voluntarily puts money in preflop (excludes posting blinds)"],
  ["PFR", "Preflop Raise", "% of hands a player raises preflop — a subset of VPIP"],
  ["AF", "Aggression Factor", "Ratio of (bets + raises) to calls — higher means more aggressive"],
  ["BB", "Big Blind", "The larger of the two forced bets, used as a unit of measurement"],
  ["SB", "Small Blind", "The smaller forced bet, typically half of the big blind"],
  ["Pot Odds", "Pot Odds", "The ratio of the current pot to the cost of a call, expressed as %"],
  ["Equity", "Hand Equity", "Your estimated chance of winning the hand at showdown"],
] as const;

let toastId = 0;

function App() {
  const [toasts, setToasts] = useState<ToastMessage[]>([]);
  const [trainingTools, setTrainingTools] = useState<TrainingToolsState>(loadTrainingTools);
  const [showPreflopChart, setShowPreflopChart] = useState(false);
  const [showRangeViz, setShowRangeViz] = useState(false);
  const [soundEnabled, setSoundEnabled] = useState(soundManager.enabled);
  const actionLogRef = useRef<ActionEntry[]>([]);

  const toggleTool = useCallback((key: keyof TrainingToolsState) => {
    setTrainingTools((prev) => {
      const next = { ...prev, [key]: !prev[key] };
      localStorage.setItem(TRAINING_TOOLS_KEY, JSON.stringify(next));
      return next;
    });
  }, []);

  const toast = useRef<ToastEmitter>({
    error: (text: string) => setToasts((prev) => [...prev, { id: ++toastId, text, type: "error" }]),
    info: (text: string) => setToasts((prev) => [...prev, { id: ++toastId, text, type: "info" }]),
  }).current;

  const dismissToast = useCallback((id: number) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const {
    state: g,
    startGame,
    sendAction,
    nextHand,
    fetchHint,
    fetchHandStrength,
    dismissHint,
    loadReplay,
    closeReplay,
    exitGame,
    toggle,
    wsRef,
    sessionTokenRef,
  } = useGameSocket(toast);

  const toggleSound = useCallback(() => {
    const next = !soundEnabled;
    setSoundEnabled(next);
    soundManager.setEnabled(next);
  }, [soundEnabled]);

  // Track actions for range visualization
  const prevStreetRef = useRef<string | null>(null);
  useEffect(() => {
    if (!g.gameState) return;
    const gs = g.gameState;

    // Reset on new hand
    const lastAction = (gs as unknown as Record<string, unknown>).last_action as
      | { player_id?: string; action?: string; amount?: number } | undefined;
    if (lastAction?.player_id && lastAction.action) {
      actionLogRef.current.push({
        player_id: lastAction.player_id,
        action: lastAction.action,
        amount: lastAction.amount ?? 0,
        street: gs.street,
      });
    }
    prevStreetRef.current = `${gs.hand_number}:${gs.street}`;
  }, [g.gameState]);

  // Clear action log on new hand
  useEffect(() => {
    if (g.gameState?.hand_number) {
      actionLogRef.current = [];
    }
  }, [g.gameState?.hand_number]);

  useKeyboardShortcuts({
    isMyTurn: g.isMyTurn,
    legalActions: g.legalActions,
    handResult: g.handResult,
    showReview: g.showReview,
    sendAction,
    nextHand,
  });

  useEffect(() => {
    if (g.isMyTurn && trainingTools.handStrength && !g.handStrength) {
      fetchHandStrength();
    }
  }, [g.isMyTurn, trainingTools.handStrength, g.handStrength, fetchHandStrength]);

  useEffect(() => () => { wsRef.current?.close(); }, [wsRef]);

  if (g.phase === "setup") {
    return (
      <>
        <SetupScreen onStart={startGame} />
        <ToastContainer toasts={toasts} onDismiss={dismissToast} />
      </>
    );
  }

  if (!g.gameState) {
    return (
      <div className="app">
        <p style={{ color: "var(--text-muted)" }}>Connecting...</p>
        <ToastContainer toasts={toasts} onDismiss={dismissToast} />
      </div>
    );
  }

  return (
    <div className="app">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      {/* ── Header ── */}
      {g.gameId && (
        <div className="app-header">
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button className="btn btn-outline" style={{ color: "var(--accent)" }} onClick={() => toggle("showDashboard", true)}>
              Dashboard
            </button>
            <button
              className="btn btn-outline"
              style={{ color: "var(--color-warning)", borderColor: "rgba(241, 196, 15, 0.4)", fontSize: 13 }}
              onClick={() => setShowPreflopChart(true)}
            >
              📊 Hand Chart
            </button>
            <TrainingTools tools={trainingTools} onToggle={toggleTool} />
            {trainingTools.rangeViz && (
              <button
                className="btn btn-outline"
                style={{ color: "var(--color-danger)", borderColor: "rgba(231, 76, 60, 0.4)", fontSize: 13 }}
                onClick={() => setShowRangeViz(true)}
              >
                🎯 Ranges
              </button>
            )}
            <button className="btn btn-outline" style={{ color: "var(--color-danger)", borderColor: "var(--color-danger-dark)" }} onClick={exitGame}>
              Exit
            </button>
          </div>
          <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
            <button
              className="btn btn-outline"
              style={{
                width: 32, height: 32, borderRadius: "var(--radius-full)",
                display: "flex", alignItems: "center", justifyContent: "center",
                color: soundEnabled ? "var(--accent)" : "var(--text-dim)",
                fontSize: 16, fontWeight: 700,
              }}
              onClick={toggleSound}
              aria-label={soundEnabled ? "Mute sounds" : "Unmute sounds"}
              title={soundEnabled ? "Sound on" : "Sound off"}
            >
              {soundEnabled ? "🔊" : "🔇"}
            </button>
            <button
              className="btn btn-outline"
              style={{ width: 32, height: 32, borderRadius: "var(--radius-full)", display: "flex", alignItems: "center", justifyContent: "center", color: "var(--accent)", fontSize: 16, fontWeight: 700 }}
              onClick={() => toggle("showLegend")}
              aria-label="Show abbreviation legend"
            >
              ?
            </button>
          </div>
        </div>
      )}

      {/* ── Scrollable main: table + controls (no overlap when viewport is short) ── */}
      <main className="app-main" aria-label="Table and controls">
        <div className="app-table">
          <Table
          players={g.gameState.players}
          communityCards={g.gameState.community_cards}
          pot={g.gameState.pot}
          dealerSeat={g.gameState.dealer_seat}
          currentPlayerId={g.gameState.current_player_id}
          street={g.gameState.street}
          handNumber={g.gameState.hand_number}
          playerStats={g.playerStats}
          showPositionGuide={trainingTools.positionGuide}
          />
        </div>

        <div className="app-controls">
        {g.handResult && (
          <HandResultBar
            handResult={g.handResult}
            analysis={g.analysis}
            onReviewHand={() => toggle("showReview", true)}
            onNextHand={nextHand}
          />
        )}

        {g.isMyTurn && g.hint && (
          <HintPanel
            hint={g.hint}
            showCalc={g.showHintCalc}
            onToggleCalc={() => toggle("showHintCalc")}
            onClose={dismissHint}
          />
        )}

        {g.isMyTurn && (trainingTools.potOdds || trainingTools.handStrength) && (
          <div className="training-tools-bar">
            {trainingTools.potOdds && (
              <PotOddsDisplay
                potSize={g.gameState.pot}
                legalActions={g.legalActions}
                equity={g.hint?.equity ?? null}
              />
            )}
            {trainingTools.handStrength && g.handStrength && (
              <HandStrengthMeter data={g.handStrength} />
            )}
          </div>
        )}

        <ActionPanel
          legalActions={g.legalActions}
          onAction={sendAction}
          onError={(msg) => toast.error(msg)}
          disabled={!g.isMyTurn}
          potSize={g.gameState.pot}
          bigBlind={g.bigBlind}
          myCurrentBet={g.gameState.players.find((p) => p.is_human)?.current_bet ?? 0}
          onHint={fetchHint}
          hintLoading={g.hintLoading}
          showHint={!!g.hint}
          showSizingTips={trainingTools.sizingTips}
        />
        </div>
      </main>

      {/* ── Modals ── */}
      <Modal open={g.showLegend} onClose={() => toggle("showLegend", false)} title="Abbreviation Legend" maxWidth={380} titleId="legend-title">
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {LEGEND_ITEMS.map(([abbr, full, desc]) => (
            <div key={abbr} style={{ borderBottom: "1px solid var(--border-subtle)", paddingBottom: 8 }}>
              <div>
                <span style={{ color: "var(--accent)", fontWeight: 700, fontSize: 13 }}>{abbr}</span>
                <span style={{ color: "var(--text-subtle)", fontSize: 12, marginLeft: 8 }}>{full}</span>
              </div>
              <div style={{ color: "var(--text-secondary)", fontSize: 11, marginTop: 2, lineHeight: 1.4 }}>{desc}</div>
            </div>
          ))}
        </div>
      </Modal>

      {g.showReview && g.analysis && (
        <HandReview analysis={g.analysis} onClose={() => toggle("showReview", false)} />
      )}

      {g.showDashboard && g.gameId && (
        <SessionDashboard
          sessionId={g.gameId}
          sessionToken={sessionTokenRef.current}
          onClose={() => toggle("showDashboard", false)}
          onReplayHand={loadReplay}
        />
      )}

      {g.replayData && (
        <HandReplayer handData={g.replayData} onClose={closeReplay} />
      )}

      {showRangeViz && g.gameState && (
        <RangeVisualization
          open={showRangeViz}
          onClose={() => setShowRangeViz(false)}
          gameState={g.gameState}
          actionLog={actionLogRef.current}
        />
      )}

      {showPreflopChart && (
        <PreflopChart
          open={showPreflopChart}
          onClose={() => setShowPreflopChart(false)}
          holeCards={g.gameState?.players.find((p) => p.is_human)?.hole_cards}
          playerPosition={g.gameState ? computeHumanPosition(g.gameState.players, g.gameState.dealer_seat) : null}
        />
      )}

      {g.gameId && g.handResult && (
        <button
          onClick={() => toggle("showCoach")}
          className="coach-toggle-btn"
          style={{ right: g.showCoach ? 380 : 16 }}
        >
          {g.showCoach ? "Hide Coach" : "Ask Coach"}
        </button>
      )}

      {g.showCoach && g.gameId && (
        <CoachChat gameId={g.gameId} sessionToken={sessionTokenRef.current} onClose={() => toggle("showCoach", false)} />
      )}
    </div>
  );
}

export default App;
