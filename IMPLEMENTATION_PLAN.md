# Poker Training Engine -- Implementation Plan

## Status: All 11 Phases Complete

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | Project scaffolding -- monorepo, deps, Docker | Done |
| 2 | Card/Deck primitives and hand evaluation | Done |
| 3 | Game engine core -- betting, side pots, showdown | Done |
| 4 | Bot framework + Tier 1 (Fish) and Tier 2 (Regular) bots | Done |
| 5 | FastAPI + WebSocket API layer | Done |
| 6 | Frontend poker table UI | Done |
| 7 | Frontend-backend WebSocket integration | Done |
| 8 | Analysis engine -- hand history, equity, scoring (MVP) | Done |
| 9 | Tier 3 Shark bot, HUD, keyboard shortcuts (v1.1) | Done |
| 10 | Hand replayer, session dashboard, EV calc (v1.1) | Done |
| 11 | LLM Coach bot, GTO bot, AI reviews (v2.0) | Done |

---

## Architecture

```
poker-practice/
├── backend/                    # Python 3.11+ / FastAPI
│   ├── app/
│   │   ├── api/               # REST + WebSocket endpoints
│   │   │   ├── routes.py      # Game create, profiles, analysis, replay, coach
│   │   │   ├── ws.py          # WebSocket game endpoint
│   │   │   ├── session.py     # GameSession orchestrator
│   │   │   └── schemas.py     # Pydantic request/response models
│   │   ├── engine/            # Core game logic
│   │   │   ├── game.py        # GameEngine class
│   │   │   ├── game_state.py  # GameState, PlayerState, Pot dataclasses
│   │   │   ├── pot.py         # Side pot calculation
│   │   │   └── validators.py  # Legal action validation
│   │   ├── models/            # Card primitives
│   │   │   ├── card.py        # Card, Deck
│   │   │   ├── hand.py        # Hand evaluation (phevaluator wrapper)
│   │   │   └── types.py       # Enums: Rank, Suit, Street, ActionType
│   │   ├── bots/              # AI opponents
│   │   │   ├── interface.py   # BotStrategy ABC
│   │   │   ├── visible_state.py # Information-filtered game state
│   │   │   ├── fish.py        # Tier 1: loose-passive
│   │   │   ├── regular.py     # Tier 2: chart-based TAG
│   │   │   ├── shark.py       # Tier 3: Monte Carlo equity-based
│   │   │   ├── gto.py         # Tier 4: balanced GTO approximation
│   │   │   ├── llm_coach.py   # Tier 4: Claude-powered coach + Q&A
│   │   │   └── profiles.py    # Preset bot configurations
│   │   ├── analysis/          # Training analytics
│   │   │   ├── equity.py      # Monte Carlo equity calculator
│   │   │   ├── scoring.py     # Decision scoring (good/mistake/blunder)
│   │   │   ├── ev.py          # Expected value calculation
│   │   │   ├── stats.py       # Session stats (VPIP, PFR, AF)
│   │   │   └── ai_review.py   # Claude-powered session reviews
│   │   ├── db/                # Persistence
│   │   │   ├── models.py      # SQLAlchemy models
│   │   │   └── repository.py  # CRUD operations
│   │   └── main.py            # FastAPI app entry point
│   ├── tests/                 # 138 passing tests
│   │   ├── test_hand_eval.py  # 29 tests: card, deck, hand evaluation
│   │   ├── test_game_engine.py # 20 tests: betting, pots, showdown
│   │   ├── test_bots.py       # 7 tests: bot legality, 100-hand stress test
│   │   ├── test_analysis.py   # Analysis, equity, scoring, EV tests
│   │   ├── test_advanced_bots.py # Shark, GTO, LLM coach bot tests
│   │   └── test_edge_cases.py # Card parsing, pot logic, engine edge cases
│   ├── pyproject.toml
│   └── Dockerfile
├── frontend/                   # React 18 + TypeScript + Vite
│   ├── src/
│   │   ├── components/
│   │   │   ├── Table.tsx       # Poker table with oval seat layout
│   │   │   ├── Card.tsx        # Playing card (face-up / face-down)
│   │   │   ├── Player.tsx      # Player seat with stack, cards, HUD
│   │   │   ├── Pot.tsx         # Center pot display
│   │   │   ├── CommunityCards.tsx
│   │   │   ├── ActionPanel.tsx # Fold/Check/Call/Raise + slider
│   │   │   ├── SetupScreen.tsx # Game configuration
│   │   │   ├── HandReview.tsx  # Post-hand equity + decision scores
│   │   │   ├── HandReplayer.tsx # Step-through replay
│   │   │   ├── SessionDashboard.tsx # Aggregate session stats
│   │   │   ├── HUD.tsx        # Per-player VPIP/PFR/AF overlay
│   │   │   ├── CoachChat.tsx  # Post-hand Q&A with AI coach
│   │   │   ├── Modal.tsx      # Accessible dialog (focus trap, Escape, aria)
│   │   │   ├── Toast.tsx      # Error/info toast notifications
│   │   │   ├── EquityBreakdown.tsx # Monte Carlo equity display
│   │   │   └── ChipStack.tsx  # Visual chip stack decomposition
│   │   ├── hooks/
│   │   │   └── useGameSocket.ts # Central state + WS hook (useReducer)
│   │   ├── types.ts           # Shared TypeScript type definitions
│   │   ├── App.tsx            # Root component (keyboard shortcuts, layout)
│   │   ├── App.css            # App-level styles
│   │   └── index.css          # CSS design system (custom properties)
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── README.md                   # Quick start and overview
├── ARCHITECTURE.md             # Detailed architecture, data flows, protocols
└── IMPLEMENTATION_PLAN.md      # This file (build phases and reference)

```

---

## Running the Project

### Local Development

**Backend:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --port 8000 --reload
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173 in your browser.

### Docker
```bash
docker compose up
```

### Running Tests
```bash
cd backend
source .venv/bin/activate
pytest tests/ -v
```

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check (includes active session count) |
| POST | `/game/create` | Create new game session |
| GET | `/game/{id}/hint` | Get equity-based action recommendation |
| GET | `/profiles` | List available bot profiles |
| WS | `/game/{id}/ws` | WebSocket game channel |
| GET | `/hand/{id}/analysis` | Get hand analysis results |
| GET | `/hand/{id}/replay` | Get full hand replay data |
| GET | `/session/{id}/hands` | List hands in a session |
| GET | `/session/{id}/summary` | Session aggregate stats |
| GET | `/session/{id}/review` | AI-generated session review |
| POST | `/coach/ask` | Ask coach bot a question |

---

## Bot Profiles

| Profile | Tier | Style | Description |
|---------|------|-------|-------------|
| Calling Station Carl | 1 (Fish) | Loose-Passive | Calls everything |
| Passive Pete | 1 (Fish) | Loose-Passive | Slightly selective |
| Maniac Mike | 1 (Fish) | Loose-Aggressive | Wild and unpredictable |
| Nitty Nancy | 2 (Regular) | Tight-Passive | Only plays premiums |
| TAG Tommy | 2 (Regular) | Tight-Aggressive | Solid fundamentals |
| LAG Larry | 2 (Regular) | Loose-Aggressive | Pressures constantly |
| Shark Steve | 3 (Shark) | Balanced | Monte Carlo equity-based |
| Shark Samantha | 3 (Shark) | Aggressive | High bluff frequency |
| Shark Simon | 3 (Shark) | Tight | Maximizes value |
| GTO Greg | 4 (GTO) | Balanced | Near-optimal mixed strategies |
| Coach Claude | 4 (Coach) | Balanced | Explains decisions, Q&A |

---

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| F | Fold |
| C | Call / Check |
| R | Raise (minimum) |
| Space / N | Next hand (after hand completes) |

---

## LLM Integration

The Coach bot and AI session reviews use the Claude API. Set the `ANTHROPIC_API_KEY` environment variable to enable LLM features. Without it, the coach bot falls back to the Shark equity-based strategy, and session reviews use template-based feedback.

```bash
export ANTHROPIC_API_KEY=your-key-here
```
