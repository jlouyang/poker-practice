/**
 * Shared TypeScript type definitions for the poker training app.
 *
 * All server↔client data shapes are defined here to avoid duplication
 * across components. Grouped by domain:
 *   - Core game types (PlayerInfo, GameStateData, LegalAction, etc.)
 *   - Analysis types (EquityDetails, AnalysisResult, HintData)
 *   - Player stats (PlayerStats, PlayerStatsMap)
 *   - Replay types (ReplayAction, ReplayPlayer, HandReplayData)
 *   - Session dashboard (SessionSummary, SessionHand)
 *   - UI constants (SCORE_COLORS, SCORE_BG)
 */

/* ── Core game types ── */

export interface PlayerInfo {
  player_id: string;
  seat: number;
  stack: number;
  current_bet: number;
  is_active: boolean;
  is_all_in: boolean;
  is_human: boolean;
  hole_cards?: string[];
}

export interface LegalAction {
  action_type: string;
  min_amount: number;
  max_amount: number;
}

export interface GameStateData {
  hand_number: number;
  street: string;
  pot: number;
  community_cards: string[];
  players: PlayerInfo[];
  current_player_id: string | null;
  dealer_seat: number;
  is_complete: boolean;
  legal_actions?: LegalAction[];
  result?: HandResult;
  player_stats?: PlayerStatsMap;
  analysis?: AnalysisResult[];
  hand_db_id?: number;
}

export interface HandResult {
  winners?: Record<string, { amount: number; hand: string }>;
  hands?: Record<string, { cards: string[]; result: string }>;
  player_id?: string;
  amount?: number;
}

export interface WsErrorData {
  message: string;
}

export interface BotActionData extends GameStateData {
  last_action?: { player_id: string; action: string; amount: number };
}

export type WsMessage =
  | { type: "new_hand"; data: GameStateData }
  | { type: "action_required"; data: GameStateData }
  | { type: "state_update"; data: GameStateData }
  | { type: "bot_action"; data: BotActionData }
  | { type: "hand_complete"; data: GameStateData }
  | { type: "game_over"; data: Record<string, never> }
  | { type: "error"; data: WsErrorData };

export interface CreateGameRequest {
  num_players: number;
  starting_stack: number;
  small_blind: number;
  big_blind: number;
  difficulty: number;
}

export interface CreateGameResponse {
  game_id: string;
  session_token: string;
  player_seat: number;
  num_players: number;
}

export type GamePhase = "setup" | "playing" | "review";

/* ── Analysis types ── */

export interface EquityDetails {
  simulations: number;
  wins: number;
  ties: number;
  losses: number;
  current_hand: string | null;
  hand_distribution: { hand: string; pct: number }[];
  hole_cards: string[];
  community_cards: string[];
  num_opponents: number;
  pot: number;
  to_call: number;
  decision_steps: string[];
}

export interface AnalysisResult {
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
  equity_details?: EquityDetails;
  /** Equity vs random hands (shown when decision used range-based equity) */
  equity_vs_random?: number;
}

export interface HintData {
  optimal_action: string;
  equity: number;
  pot_odds: number;
  recommendation: string;
  equity_details?: EquityDetails;
  /** When hint is based on inferred opponent range */
  opponent_range_pct?: number;
  opponent_range_description?: string;
  /** Equity vs random hands (shown when hint used range-based equity) */
  equity_vs_random?: number;
}

/* ── Player stats types ── */

export interface PlayerStats {
  vpip: number;
  pfr: number;
  af: number;
  hands_played: number;
  pots_won: number;
  total_winnings: number;
}

export type HUDStats = Pick<PlayerStats, "vpip" | "pfr" | "af" | "hands_played">;

export type PlayerStatsMap = Record<string, PlayerStats>;

/* ── Replay types ── */

export interface ReplayAction {
  player_id: string;
  street: string;
  action_type: string;
  amount: number;
  sequence: number;
}

export interface ReplayPlayer {
  player_id: string;
  seat: number;
  starting_stack: number;
  ending_stack: number;
  hole_cards: string[];
  is_human: boolean;
}

export interface ReplayAnalysis {
  player_id: string;
  street: string;
  equity: number;
  score: string;
}

export interface HandReplayData {
  hand_number: number;
  community_cards: string[];
  pot_size: number;
  winner_ids: string[];
  players: ReplayPlayer[];
  actions: ReplayAction[];
  analysis: ReplayAnalysis[];
}

/* ── Session dashboard types ── */

export interface SessionSummary {
  session_id: string;
  total_hands: number;
  human_win_rate: number;
  biggest_pot: number;
  mistakes: number;
  blunders: number;
  player_stats: PlayerStatsMap;
}

export interface SessionHand {
  id: number;
  hand_number: number;
  pot_size: number;
  winner_ids: string[];
}

/* ── Score constants ── */

export const SCORE_COLORS: Record<string, string> = {
  good: "var(--color-success)",
  mistake: "var(--color-warning)",
  blunder: "var(--color-danger)",
};

export const SCORE_BG: Record<string, string> = {
  good: "rgba(46, 204, 113, 0.06)",
  mistake: "rgba(243, 156, 18, 0.06)",
  blunder: "rgba(231, 76, 60, 0.06)",
};
