# Architecture

This document describes the Poker Training Engine's architecture: how the pieces connect, how data flows through the system, and what each module is responsible for.

## System Overview

```
┌─────────────────────────────────────────────────────────────┐
│  Frontend  (React + TypeScript + Vite)                      │
│                                                             │
│  SetupScreen ──POST /game/create──▶ App.tsx                 │
│                                      │                      │
│                            useGameSocket hook                │
│                              │ (WebSocket)                   │
│                              ▼                               │
│  Table ◀── gameState ── useReducer ◀── WS messages          │
│  ActionPanel ──actions──▶ WS send                           │
│  HandReview / Dashboard / CoachChat / Replayer (modals)     │
└────────────────────────────┬────────────────────────────────┘
                             │ WebSocket + REST
                             ▼
┌─────────────────────────────────────────────────────────────┐
│  Backend  (Python 3.11+ / FastAPI)                          │
│                                                             │
│  ┌─── api/ ─────────────────────────────────────────────┐   │
│  │  routes.py    REST endpoints (create, hint, replay…) │   │
│  │  ws.py        WebSocket endpoint (/game/{id}/ws)     │   │
│  │  session.py   GameSession orchestrator + registry    │   │
│  │  schemas.py   Pydantic request/response models       │   │
│  └──────────────────────────────────────────────────────┘   │
│           │                                                  │
│           ▼                                                  │
│  ┌─── engine/ ──────────────────────────────────────────┐   │
│  │  game.py        GameEngine (start hand, apply action)│   │
│  │  game_state.py  GameState, PlayerState, Pot          │   │
│  │  validators.py  Legal action calculation             │   │
│  │  pot.py         Main pot / side pot splitting        │   │
│  └──────────────────────────────────────────────────────┘   │
│           │                                                  │
│     ┌─────┴──────┐                                          │
│     ▼            ▼                                          │
│  ┌─ models/ ─┐  ┌─ bots/ ──────────────────────────────┐   │
│  │ card.py   │  │ interface.py   BotStrategy ABC        │   │
│  │ hand.py   │  │ visible_state  Info-filtered state    │   │
│  │ types.py  │  │ fish.py        Tier 1 heuristic       │   │
│  └───────────┘  │ regular.py     Tier 2 chart-based     │   │
│                 │ shark.py       Tier 3 equity-based     │   │
│                 │ gto.py         Tier 4 balanced GTO     │   │
│                 │ llm_coach.py   Tier 4 Claude-powered   │   │
│                 │ profiles.py    Preset configurations   │   │
│                 └───────────────────────────────────────┘   │
│           │                                                  │
│           ▼                                                  │
│  ┌─── analysis/ ────────────────────────────────────────┐   │
│  │  equity.py    Monte Carlo equity calculator          │   │
│  │  ev.py        Expected value of actions              │   │
│  │  scoring.py   Decision scoring (good/mistake/blunder)│   │
│  │  stats.py     VPIP, PFR, AF session stats            │   │
│  │  ai_review.py Claude-powered session reviews         │   │
│  └──────────────────────────────────────────────────────┘   │
│           │                                                  │
│           ▼                                                  │
│  ┌─── db/ ──────────────────────────────────────────────┐   │
│  │  models.py      SQLAlchemy ORM models                │   │
│  │  repository.py  CRUD: save_hand, save_analysis, etc. │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

---

## Data Flows

### 1. Game Creation Flow

```
User clicks "Start Game"
  │
  ▼
Frontend: POST /game/create { num_players, starting_stack, blinds, difficulty }
  │
  ▼
routes.py: create_game()
  ├── session.py: create_game_session()
  │     ├── _pick_bots_for_difficulty()  →  selects BotProfiles weighted by difficulty
  │     ├── BotProfile.create_bot()     →  instantiates FishBot/RegularBot/SharkBot/etc.
  │     ├── GameEngine(player_ids, stacks, blinds)
  │     └── registers session in _sessions dict
  │
  ▼
Response: { game_id, player_seat, num_players }
  │
  ▼
Frontend: opens WebSocket to /game/{game_id}/ws
```

### 2. Hand Lifecycle (WebSocket)

```
ws.py: game_websocket()
  ├── creates asyncio task: session.run_game_loop()
  └── creates asyncio task: _send_loop() (session → WS → client)

Game Loop (session.py):
  │
  ├── engine.start_hand()
  │     ├── Deck.shuffle(), deal hole cards
  │     ├── Post blinds (SB/BB)
  │     └── Set current_player_idx to UTG
  │
  ├── send "new_hand" message to client
  │
  ├── while not hand_complete:
  │     ├── If current player is human:
  │     │     ├── send "action_required" + legal_actions
  │     │     └── await action from _action_queue
  │     │
  │     ├── If current player is bot:
  │     │     ├── make_visible_state() → filter to bot's view
  │     │     ├── bot.decide(state) → BotAction
  │     │     ├── engine.apply_action(bot_id, action_type, amount)
  │     │     └── send "bot_action" message
  │     │
  │     └── engine.apply_action() internally:
  │           ├── validators.validate_action()
  │           ├── Update PlayerState (stack, bet, is_active)
  │           ├── Check if betting round complete → advance_street()
  │           │     ├── calculate_pots() → main/side pots
  │           │     ├── Deal community cards (flop 3, turn 1, river 1)
  │           │     └── Reset bets, set new current_player_idx
  │           └── If all-in runout or single player → complete hand
  │
  ├── Showdown / win_uncontested
  │     ├── evaluate_hand() via phevaluator for each active player
  │     ├── compare_hands() → rank players, handle ties
  │     └── Distribute pot(s) to winner(s)
  │
  ├── _record_stats() → VPIP/PFR/AF tracking
  ├── _save_hand_history() → DB insert (HandRecord, PlayerStateRecord, ActionRecord)
  ├── _run_analysis() → score each human decision
  │     ├── Replay action history to reconstruct state at each decision point
  │     ├── score_decision() → equity, pot odds, optimal action, grade
  │     └── save_analysis() → DB insert (AnalysisRecord)
  │
  ├── send "hand_complete" + result + analysis
  │
  └── await continue_event (user clicks "Next Hand")
```

### 3. Analysis / Scoring Flow

```
score_decision(hole_cards, community, action, amount, pot, to_call, num_opponents)
  │
  ├── calculate_equity(hole_cards, community, num_opponents, num_simulations=1000)
  │     └── Monte Carlo: deal random opponent hands, complete board, evaluate
  │
  ├── Compute pot_odds = to_call / (pot + to_call)
  │
  ├── Determine optimal_action:
  │     ├── equity > pot_odds + margin  →  raise/bet
  │     ├── equity > pot_odds           →  call/check
  │     └── equity < pot_odds           →  fold/check
  │
  ├── Compare player's actual action vs optimal
  │     ├── Match or close  →  "good"
  │     ├── Suboptimal      →  "mistake"
  │     └── Costly error    →  "blunder"
  │
  └── Return { score, equity, pot_odds, optimal_action, reasoning, recommendation }
```

### 4. Bot Decision Flow (Shark example)

```
SharkBot.decide(visible_state):
  │
  ├── calculate_equity(my_hole_cards, community, num_opponents, num_simulations=1500)
  │
  ├── pot_odds = to_call / (pot + to_call)
  │
  ├── If equity > threshold  →  raise/bet (size based on equity strength)
  ├── If equity > pot_odds   →  call
  ├── Random bluff check     →  occasional bluff raise
  └── Otherwise              →  fold (or check if free)
```

### 5. Frontend State Management

```
App.tsx
  │
  ├── useGameSocket(toast) hook
  │     ├── useReducer(reducer, INITIAL_STATE)  →  single GameStore object
  │     ├── WebSocket ref (wsRef)
  │     │
  │     ├── Dispatched actions:
  │     │   GAME_CREATED → set gameId, phase="playing"
  │     │   WS_NEW_HAND  → reset hand state, set gameState
  │     │   WS_ACTION_REQUIRED → set legalActions, isMyTurn=true
  │     │   WS_STATE_UPDATE → update gameState, clear turn
  │     │   WS_HAND_COMPLETE → set handResult, analysis
  │     │   ACTION_SENT → clear turn, clear hint
  │     │   TOGGLE → flip UI panel visibility
  │     │
  │     └── Exposed functions:
  │         startGame(), sendAction(), nextHand(), fetchHint(),
  │         loadReplay(), closeReplay(), exitGame(), toggle()
  │
  ├── ToastContainer  →  error/info notifications
  │
  └── Rendering:
      ├── SetupScreen (phase="setup")
      ├── Table → Player (×N), CommunityCards, Pot, ChipStack
      ├── ActionPanel → Fold/Check/Call/Raise + slider + hint
      └── Modals (all use <Modal> with focus trap + Escape):
          ├── HandReview (analysis decisions + equity chart)
          ├── HandReplayer (step-through action replay)
          ├── SessionDashboard (aggregate stats + hand list)
          ├── Legend (abbreviation definitions)
          └── CoachChat (post-hand Q&A sidebar)
```

---

## Core Data Structures

### Backend

| Structure | Location | Purpose |
|-----------|----------|---------|
| `Card(rank, suit)` | `models/card.py` | Immutable card primitive. `from_str("Ah")` parser. |
| `Deck` | `models/card.py` | 52-card deck with secure shuffle (`secrets.randbelow`). |
| `HandResult(rank, hand_ranking, hand_name)` | `models/hand.py` | Result of hand evaluation via `phevaluator`. Lower rank = stronger. |
| `PlayerState` | `engine/game_state.py` | Per-player mutable state: stack, hole cards, bets, active/all-in flags. |
| `GameState` | `engine/game_state.py` | Full game state: players, community cards, pots, street, action history. |
| `Pot(amount, eligible_players)` | `engine/game_state.py` | A single pot (main or side) with its eligible player IDs. |
| `LegalAction(action_type, min, max)` | `engine/validators.py` | An action a player may take, with chip amount bounds. |
| `GameEngine` | `engine/game.py` | Stateful engine: `start_hand()`, `apply_action()`, `rotate_dealer()`. |
| `VisibleGameState` | `bots/visible_state.py` | Information-filtered game state (hides opponent hole cards). |
| `BotAction(action_type, amount)` | `bots/interface.py` | A bot's decided action. |
| `BotStrategy` (ABC) | `bots/interface.py` | Abstract base: `decide(state) → BotAction`, `name`, `tier`. |
| `BotProfile` | `bots/profiles.py` | Configuration record. `create_bot()` factory dispatches to correct tier class. |
| `GameSession` | `api/session.py` | Orchestrator: game loop, bot turns, human input queue, WS send queue, stats. |

### Frontend

| Type | Location | Purpose |
|------|----------|---------|
| `GameStore` | `hooks/useGameSocket.ts` | Reducer state: phase, gameState, legalActions, isMyTurn, hints, UI toggles. |
| `GameStateData` | `types.ts` | Server game state payload (players, community cards, pot, street). |
| `PlayerInfo` | `types.ts` | Per-player data: stack, seat, cards, active/all-in/human flags. |
| `AnalysisResult` | `types.ts` | Per-decision analysis: equity, pot_odds, score, reasoning. |
| `EquityDetails` | `types.ts` | Monte Carlo breakdown: win/tie/loss counts, hand distribution. |
| `HintData` | `types.ts` | Hint response: optimal action, equity, pot odds, recommendation. |
| `HandReplayData` | `types.ts` | Full hand for step-by-step replay: players, actions, analysis. |

---

## Session Lifecycle & Cleanup

1. `POST /game/create` → `create_game_session()` → stored in `_sessions` dict
2. Every user interaction (`submit_action`, `continue_to_next_hand`, `get_session`) calls `session.touch()` to update `_last_active`
3. WebSocket disconnect → `remove_session()` stops game loop and removes session
4. Background `_cleanup_loop` (started at app boot via lifespan) runs every 5 minutes and removes sessions idle for >1 hour (`SESSION_TTL_SECONDS`)

---

## WebSocket Protocol

All messages are JSON with `{ type, data }` shape.

### Client → Server

| type | Fields | Effect |
|------|--------|--------|
| `action` | `action`: string, `amount`: int | Submit player action |
| `continue` | — | Advance to next hand |
| `quit` | — | Disconnect gracefully |

### Server → Client

| type | data contains | When |
|------|---------------|------|
| `new_hand` | Full game state | Hand starts, cards dealt |
| `action_required` | Game state + `legal_actions[]` | It's the human's turn |
| `state_update` | Game state | After any state change |
| `bot_action` | Game state + `last_action` | Bot took an action |
| `hand_complete` | Game state + `result` + `analysis[]` | Hand finished |
| `game_over` | `{}` | Fewer than 2 players remain |
| `error` | `{ message }` | Unrecoverable error |

---

## Scoring System

Decisions are graded by comparing the player's action against the equity-optimal play:

| Grade | Meaning | Criteria |
|-------|---------|----------|
| **good** | Correct or close to optimal | Action matches optimal, or EV difference is small |
| **mistake** | Suboptimal but not catastrophic | Wrong action category but with some justification |
| **blunder** | Clearly wrong, significant EV loss | Folding with strong equity, calling with none, etc. |

The scoring logic lives in `analysis/scoring.py`. Each decision also gets:
- `equity` — Monte Carlo win probability
- `pot_odds` — required equity to call profitably
- `optimal_action` — what the player should have done
- `reasoning` — human-readable explanation
- `recommendation` — specific suggestion for improvement
