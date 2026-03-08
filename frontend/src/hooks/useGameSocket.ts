/**
 * Central game state hook — manages WebSocket connection and all game state.
 *
 * Uses useReducer with a discriminated-union action type for predictable state
 * transitions. All server communication (WS messages, REST calls for hints /
 * replays) is encapsulated here; the App component only renders and dispatches.
 *
 * Returned object:
 *   state      — current GameStore snapshot
 *   startGame  — POST /game/create, then open WebSocket
 *   sendAction — send player action over WS
 *   nextHand   — send "continue" over WS
 *   fetchHint  — GET /game/{id}/hint
 *   loadReplay — GET /hand/{id}/replay
 *   closeReplay, exitGame, toggle — UI state helpers
 */
import { useReducer, useRef, useCallback } from "react";
import { soundManager } from "../audio/SoundManager";
import type {
  CreateGameRequest,
  CreateGameResponse,
  GameStateData,
  LegalAction,
  HandResult,
  AnalysisResult,
  PlayerStatsMap,
  HintData,
  WsMessage,
  BotActionData,
  GamePhase,
  HandReplayData,
} from "../types";
import type { HandStrengthData } from "../components/HandStrengthMeter";
import { API_URL, WS_URL } from "../config";

/* ── State ── */

export interface GameStore {
  phase: GamePhase;
  gameId: string | null;
  gameState: GameStateData | null;
  legalActions: LegalAction[];
  isMyTurn: boolean;
  handResult: HandResult | null;
  analysis: AnalysisResult[] | null;
  playerStats: PlayerStatsMap;
  bigBlind: number;
  hint: HintData | null;
  hintLoading: boolean;
  handStrength: HandStrengthData | null;

  showReview: boolean;
  showDashboard: boolean;
  showCoach: boolean;
  showLegend: boolean;
  showHintCalc: boolean;
  replayData: HandReplayData | null;
}

export const INITIAL_STATE: GameStore = {
  phase: "setup",
  gameId: null,
  gameState: null,
  legalActions: [],
  isMyTurn: false,
  handResult: null,
  analysis: null,
  playerStats: {},
  bigBlind: 10,
  hint: null,
  hintLoading: false,
  handStrength: null,
  showReview: false,
  showDashboard: false,
  showCoach: false,
  showLegend: false,
  showHintCalc: false,
  replayData: null,
};

/* ── Actions ── */

export type Action =
  | { type: "GAME_CREATED"; gameId: string; bigBlind: number }
  | { type: "WS_NEW_HAND"; data: GameStateData }
  | { type: "WS_ACTION_REQUIRED"; data: GameStateData }
  | { type: "WS_STATE_UPDATE"; data: GameStateData }
  | { type: "WS_HAND_COMPLETE"; data: GameStateData }
  | { type: "WS_GAME_OVER" }
  | { type: "ACTION_SENT" }
  | { type: "NEXT_HAND" }
  | { type: "HINT_LOADING" }
  | { type: "HINT_LOADED"; hint: HintData }
  | { type: "HINT_FAILED" }
  | { type: "HINT_DISMISSED" }
  | { type: "HAND_STRENGTH_LOADED"; data: HandStrengthData }
  | { type: "TOGGLE"; key: "showReview" | "showDashboard" | "showCoach" | "showLegend" | "showHintCalc"; value?: boolean }
  | { type: "REPLAY_LOADED"; data: HandReplayData }
  | { type: "REPLAY_CLOSED" }
  | { type: "EXIT_GAME" };

export function reducer(state: GameStore, action: Action): GameStore {
  switch (action.type) {
    case "GAME_CREATED":
      return { ...INITIAL_STATE, phase: "playing", gameId: action.gameId, bigBlind: action.bigBlind };

    case "WS_NEW_HAND":
      return {
        ...state,
        gameState: action.data,
        handResult: null,
        analysis: null,
        showReview: false,
        isMyTurn: false,
        legalActions: [],
        hint: null,
        handStrength: null,
      };

    case "WS_ACTION_REQUIRED":
      return {
        ...state,
        gameState: action.data,
        legalActions: action.data.legal_actions ?? [],
        isMyTurn: true,
      };

    case "WS_STATE_UPDATE":
      return {
        ...state,
        gameState: action.data,
        isMyTurn: false,
        legalActions: [],
        playerStats: action.data.player_stats ?? state.playerStats,
      };

    case "WS_HAND_COMPLETE":
      return {
        ...state,
        gameState: action.data,
        handResult: action.data.result ?? null,
        analysis: action.data.analysis ?? null,
        playerStats: action.data.player_stats ?? state.playerStats,
        isMyTurn: false,
        legalActions: [],
      };

    case "WS_GAME_OVER":
      return { ...INITIAL_STATE };

    case "ACTION_SENT":
      return { ...state, isMyTurn: false, legalActions: [], hint: null };

    case "NEXT_HAND":
      return { ...state, handResult: null, analysis: null, showReview: false, hint: null };

    case "HINT_LOADING":
      return { ...state, hintLoading: true };

    case "HINT_LOADED":
      return { ...state, hintLoading: false, hint: action.hint };

    case "HINT_FAILED":
      return { ...state, hintLoading: false };

    case "HINT_DISMISSED":
      return { ...state, hint: null, showHintCalc: false };

    case "HAND_STRENGTH_LOADED":
      return { ...state, handStrength: action.data };

    case "TOGGLE": {
      const key = action.key;
      return { ...state, [key]: action.value ?? !state[key] };
    }

    case "REPLAY_LOADED":
      return { ...state, replayData: action.data, showDashboard: false };

    case "REPLAY_CLOSED":
      return { ...state, replayData: null };

    case "EXIT_GAME":
      return { ...INITIAL_STATE };

    default:
      return state;
  }
}

/* ── Hook ── */

export interface ToastEmitter {
  error: (msg: string) => void;
  info: (msg: string) => void;
}

export function useGameSocket(toast: ToastEmitter) {
  const [state, dispatch] = useReducer(reducer, INITIAL_STATE);
  const wsRef = useRef<WebSocket | null>(null);
  const sessionTokenRef = useRef<string | null>(null);

  const handleWsMessage = useCallback((msg: WsMessage) => {
    switch (msg.type) {
      case "new_hand":
        dispatch({ type: "WS_NEW_HAND", data: msg.data });
        soundManager.play("deal");
        break;
      case "action_required":
        dispatch({ type: "WS_ACTION_REQUIRED", data: msg.data });
        soundManager.play("yourTurn");
        break;
      case "state_update":
        dispatch({ type: "WS_STATE_UPDATE", data: msg.data });
        break;
      case "bot_action": {
        dispatch({ type: "WS_STATE_UPDATE", data: msg.data });
        const lastAction = (msg.data as BotActionData).last_action;
        if (lastAction?.action) {
          const a = lastAction.action;
          if (a === "fold") soundManager.play("fold");
          else if (a === "check") soundManager.play("check");
          else if (a === "call") soundManager.play("call");
          else if (a === "all_in") soundManager.play("allIn");
          else if (a === "bet" || a === "raise") soundManager.play("bet");
        }
        break;
      }
      case "hand_complete": {
        dispatch({ type: "WS_HAND_COMPLETE", data: msg.data });
        const result = msg.data.result;
        const humanWon = result?.winners?.["human"] || result?.player_id === "human";
        soundManager.play(humanWon ? "win" : "lose");
        break;
      }
      case "game_over":
        dispatch({ type: "WS_GAME_OVER" });
        break;
      case "error":
        toast.error(msg.data.message ?? "Game error");
        break;
    }
  }, [toast]);

  const startGame = useCallback(async (config: CreateGameRequest) => {
    try {
      const res = await fetch(`${API_URL}/game/create`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (!res.ok) {
        toast.error(`Failed to create game (${res.status})`);
        return;
      }
      const data: CreateGameResponse = await res.json();
      sessionTokenRef.current = data.session_token;
      dispatch({ type: "GAME_CREATED", gameId: data.game_id, bigBlind: config.big_blind });

      const ws = new WebSocket(
        `${WS_URL}/game/${data.game_id}/ws?token=${encodeURIComponent(data.session_token)}`
      );
      wsRef.current = ws;
      ws.onmessage = (event) => {
        try {
          handleWsMessage(JSON.parse(event.data));
        } catch {
          toast.error("Received invalid data from server");
        }
      };
      ws.onclose = (e) => {
        if (e.code !== 1000) {
          toast.error("Connection lost — please restart the game");
        }
      };
      ws.onerror = () => toast.error("WebSocket connection failed");
    } catch {
      toast.error("Network error — could not reach server");
    }
  }, [handleWsMessage, toast]);

  const sendAction = useCallback((action: string, amount: number) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "action", action, amount }));
      dispatch({ type: "ACTION_SENT" });
      if (action === "fold") soundManager.play("fold");
      else if (action === "check") soundManager.play("check");
      else if (action === "call") soundManager.play("call");
      else if (action === "all_in") soundManager.play("allIn");
      else if (action === "bet" || action === "raise") soundManager.play("bet");
    }
  }, []);

  const nextHand = useCallback(() => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ type: "continue" }));
      dispatch({ type: "NEXT_HAND" });
    }
  }, []);

  const authHeaders = useCallback((): Record<string, string> => {
    const headers: Record<string, string> = {};
    if (sessionTokenRef.current) {
      headers["X-Session-Token"] = sessionTokenRef.current;
    }
    return headers;
  }, []);

  const fetchHint = useCallback(async () => {
    if (!state.gameId || state.hintLoading) return;
    dispatch({ type: "HINT_LOADING" });
    try {
      const res = await fetch(`${API_URL}/game/${state.gameId}/hint`, {
        headers: authHeaders(),
      });
      if (res.ok) {
        dispatch({ type: "HINT_LOADED", hint: await res.json() });
      } else {
        dispatch({ type: "HINT_FAILED" });
        toast.error("Could not load hint");
      }
    } catch {
      dispatch({ type: "HINT_FAILED" });
      toast.error("Network error loading hint");
    }
  }, [state.gameId, state.hintLoading, toast, authHeaders]);

  const fetchHandStrength = useCallback(async () => {
    if (!state.gameId) return;
    try {
      const res = await fetch(`${API_URL}/game/${state.gameId}/hand-strength`, {
        headers: authHeaders(),
      });
      if (res.ok) {
        dispatch({ type: "HAND_STRENGTH_LOADED", data: await res.json() });
      }
    } catch {
      // silently fail — training tool is optional
    }
  }, [state.gameId, authHeaders]);

  const loadReplay = useCallback(async (handId: number) => {
    try {
      const res = await fetch(`${API_URL}/hand/${handId}/replay`);
      if (res.ok) {
        dispatch({ type: "REPLAY_LOADED", data: await res.json() });
      } else {
        toast.error("Could not load replay");
      }
    } catch {
      toast.error("Network error loading replay");
    }
  }, [toast]);

  const exitGame = useCallback(() => {
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    sessionTokenRef.current = null;
    dispatch({ type: "EXIT_GAME" });
  }, []);

  const toggle = useCallback((key: "showReview" | "showDashboard" | "showCoach" | "showLegend" | "showHintCalc", value?: boolean) => {
    dispatch({ type: "TOGGLE", key, value });
  }, []);

  const closeReplay = useCallback(() => {
    dispatch({ type: "REPLAY_CLOSED" });
  }, []);

  const dismissHint = useCallback(() => {
    dispatch({ type: "HINT_DISMISSED" });
  }, []);

  return {
    state,
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
  };
}
