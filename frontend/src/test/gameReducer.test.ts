import { describe, it, expect } from "vitest";
import { reducer, INITIAL_STATE } from "../hooks/useGameSocket";
import type { GameStateData } from "../types";

function makeGameState(overrides: Partial<GameStateData> = {}): GameStateData {
  return {
    hand_number: 1,
    street: "preflop",
    pot: 30,
    community_cards: [],
    players: [
      { player_id: "human", seat: 0, stack: 1000, current_bet: 10, is_active: true, is_all_in: false, is_human: true, hole_cards: ["Ah", "Kd"] },
      { player_id: "bot_1", seat: 1, stack: 990, current_bet: 20, is_active: true, is_all_in: false, is_human: false },
    ],
    current_player_id: "human",
    dealer_seat: 0,
    is_complete: false,
    ...overrides,
  };
}

describe("gameReducer", () => {
  describe("GAME_CREATED", () => {
    it("transitions to playing phase", () => {
      const state = reducer(INITIAL_STATE, { type: "GAME_CREATED", gameId: "abc123", bigBlind: 20 });
      expect(state.phase).toBe("playing");
      expect(state.gameId).toBe("abc123");
      expect(state.bigBlind).toBe(20);
    });

    it("resets state from a previous game", () => {
      const prev = { ...INITIAL_STATE, hint: { optimal_action: "fold", equity: 0.5, pot_odds: 0.3, recommendation: "fold" } as never };
      const state = reducer(prev, { type: "GAME_CREATED", gameId: "new", bigBlind: 10 });
      expect(state.hint).toBeNull();
      expect(state.phase).toBe("playing");
    });
  });

  describe("WS_NEW_HAND", () => {
    it("sets game state and clears hand result", () => {
      const gs = makeGameState();
      const prev = { ...INITIAL_STATE, phase: "playing" as const, handResult: { winners: {} } as never, analysis: [{}] as never };
      const state = reducer(prev, { type: "WS_NEW_HAND", data: gs });
      expect(state.gameState).toBe(gs);
      expect(state.handResult).toBeNull();
      expect(state.analysis).toBeNull();
      expect(state.isMyTurn).toBe(false);
      expect(state.hint).toBeNull();
      expect(state.handStrength).toBeNull();
    });
  });

  describe("WS_ACTION_REQUIRED", () => {
    it("sets isMyTurn and legal actions", () => {
      const gs = makeGameState({
        legal_actions: [
          { action_type: "fold", min_amount: 0, max_amount: 0 },
          { action_type: "call", min_amount: 10, max_amount: 10 },
        ],
      } as never);
      const state = reducer(INITIAL_STATE, { type: "WS_ACTION_REQUIRED", data: gs });
      expect(state.isMyTurn).toBe(true);
      expect(state.legalActions).toHaveLength(2);
      expect(state.legalActions[0].action_type).toBe("fold");
    });
  });

  describe("WS_STATE_UPDATE", () => {
    it("clears turn and updates player stats", () => {
      const gs = makeGameState({ player_stats: { human: { vpip: 25, pfr: 18, af: 1.5, hands_played: 10, pots_won: 3, total_winnings: 200 } } } as never);
      const prev = { ...INITIAL_STATE, isMyTurn: true, legalActions: [{ action_type: "fold", min_amount: 0, max_amount: 0 }] };
      const state = reducer(prev, { type: "WS_STATE_UPDATE", data: gs });
      expect(state.isMyTurn).toBe(false);
      expect(state.legalActions).toHaveLength(0);
      expect(state.playerStats).toHaveProperty("human");
    });
  });

  describe("WS_HAND_COMPLETE", () => {
    it("sets hand result and analysis", () => {
      const gs = makeGameState({
        is_complete: true,
        result: { winners: { human: { amount: 100, hand: "Two Pair" } } },
        analysis: [{ player_id: "human", street: "preflop", equity: 0.6, score: "good" }],
      } as never);
      const state = reducer(INITIAL_STATE, { type: "WS_HAND_COMPLETE", data: gs });
      expect(state.handResult).toBeTruthy();
      expect(state.analysis).toHaveLength(1);
      expect(state.isMyTurn).toBe(false);
    });
  });

  describe("WS_GAME_OVER", () => {
    it("resets to initial state", () => {
      const prev = { ...INITIAL_STATE, phase: "playing" as const, gameId: "abc" };
      const state = reducer(prev, { type: "WS_GAME_OVER" });
      expect(state.phase).toBe("setup");
      expect(state.gameId).toBeNull();
    });
  });

  describe("ACTION_SENT", () => {
    it("clears turn and hint", () => {
      const prev = { ...INITIAL_STATE, isMyTurn: true, hint: {} as never, legalActions: [{ action_type: "fold", min_amount: 0, max_amount: 0 }] };
      const state = reducer(prev, { type: "ACTION_SENT" });
      expect(state.isMyTurn).toBe(false);
      expect(state.legalActions).toHaveLength(0);
      expect(state.hint).toBeNull();
    });
  });

  describe("NEXT_HAND", () => {
    it("clears hand result and review state", () => {
      const prev = { ...INITIAL_STATE, handResult: {} as never, analysis: [{}] as never, showReview: true, hint: {} as never };
      const state = reducer(prev, { type: "NEXT_HAND" });
      expect(state.handResult).toBeNull();
      expect(state.analysis).toBeNull();
      expect(state.showReview).toBe(false);
      expect(state.hint).toBeNull();
    });
  });

  describe("HINT_LOADING / HINT_LOADED / HINT_FAILED", () => {
    it("tracks hint loading lifecycle", () => {
      let state = reducer(INITIAL_STATE, { type: "HINT_LOADING" });
      expect(state.hintLoading).toBe(true);

      const hint = { optimal_action: "call", equity: 0.55, pot_odds: 0.33, recommendation: "Call" };
      state = reducer(state, { type: "HINT_LOADED", hint });
      expect(state.hintLoading).toBe(false);
      expect(state.hint?.optimal_action).toBe("call");
    });

    it("clears loading on failure", () => {
      let state = reducer(INITIAL_STATE, { type: "HINT_LOADING" });
      state = reducer(state, { type: "HINT_FAILED" });
      expect(state.hintLoading).toBe(false);
      expect(state.hint).toBeNull();
    });
  });

  describe("TOGGLE", () => {
    it("toggles boolean flags", () => {
      let state = reducer(INITIAL_STATE, { type: "TOGGLE", key: "showDashboard" });
      expect(state.showDashboard).toBe(true);
      state = reducer(state, { type: "TOGGLE", key: "showDashboard" });
      expect(state.showDashboard).toBe(false);
    });

    it("sets explicit values", () => {
      const state = reducer(INITIAL_STATE, { type: "TOGGLE", key: "showCoach", value: true });
      expect(state.showCoach).toBe(true);
    });
  });

  describe("REPLAY_LOADED / REPLAY_CLOSED", () => {
    it("loads replay and closes dashboard", () => {
      const prev = { ...INITIAL_STATE, showDashboard: true };
      const replayData = { hand_id: 1, hand_number: 1 } as never;
      const state = reducer(prev, { type: "REPLAY_LOADED", data: replayData });
      expect(state.replayData).toBeTruthy();
      expect(state.showDashboard).toBe(false);
    });

    it("clears replay on close", () => {
      const prev = { ...INITIAL_STATE, replayData: {} as never };
      const state = reducer(prev, { type: "REPLAY_CLOSED" });
      expect(state.replayData).toBeNull();
    });
  });

  describe("EXIT_GAME", () => {
    it("fully resets state", () => {
      const prev = { ...INITIAL_STATE, phase: "playing" as const, gameId: "abc", gameState: makeGameState() };
      const state = reducer(prev, { type: "EXIT_GAME" });
      expect(state).toEqual(INITIAL_STATE);
    });
  });
});
