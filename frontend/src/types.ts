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
}

export interface HandResult {
  winners?: Record<string, { amount: number; hand: string }>;
  hands?: Record<string, { cards: string[]; result: string }>;
  player_id?: string;
  amount?: number;
}

export interface WsMessage {
  type: string;
  data: GameStateData;
}

export interface CreateGameRequest {
  num_players: number;
  starting_stack: number;
  small_blind: number;
  big_blind: number;
}

export interface CreateGameResponse {
  game_id: string;
  player_seat: number;
  num_players: number;
}

export type GamePhase = "setup" | "playing" | "review";
