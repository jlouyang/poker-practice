# Poker Training Engine

A full-stack poker training application where you play No-Limit Texas Hold'em against AI opponents of configurable difficulty, then review your decisions with equity analysis and AI coaching.

## Quick Start

### Local Development

**Backend** (Python 3.11+):
```bash
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
uvicorn app.main:app --port 8000 --reload
```

**Frontend** (Node 18+):
```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173.

### Docker
```bash
docker compose up
```

### Tests
```bash
cd backend && source .venv/bin/activate
pytest tests/ -v      # 138 tests
```

## How It Works

1. **Setup** — Configure table size (2-9 players), blinds, starting stacks, and difficulty.
2. **Play** — Take actions via buttons or keyboard shortcuts (F/C/R). Bots respond in real-time over WebSocket.
3. **Review** — After each hand, see equity-by-street charts, decision scores (good/mistake/blunder), and actionable suggestions.
4. **Coach** — Ask the AI coach questions about any decision ("Should I have folded preflop?").
5. **Dashboard** — Track session-wide stats: VPIP, PFR, AF, win rate, mistake/blunder counts.

## Project Structure

```
poker-practice/
├── backend/                  # Python / FastAPI
│   ├── app/
│   │   ├── api/              # REST + WebSocket endpoints
│   │   ├── engine/           # Core game logic (betting, pots, showdown)
│   │   ├── models/           # Card primitives, hand evaluation, enums
│   │   ├── bots/             # AI opponents (4 tiers) + coach
│   │   ├── analysis/         # Equity, EV, scoring, session stats
│   │   └── db/               # SQLAlchemy persistence
│   └── tests/                # 138 pytest tests
├── frontend/                 # React + TypeScript + Vite
│   └── src/
│       ├── hooks/            # useGameSocket (state + WS management)
│       ├── components/       # Table, ActionPanel, Modals, etc.
│       └── types.ts          # Shared TypeScript interfaces
├── ARCHITECTURE.md           # Detailed architecture & data flows
├── IMPLEMENTATION_PLAN.md    # Phase-by-phase build log
└── docker-compose.yml
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed data flow diagrams, type definitions, and module responsibilities.

## Bot Tiers

| Tier | Name | Strategy | Examples |
|------|------|----------|----------|
| 1 | Fish | Heuristic, loose | Calling Station Carl, Maniac Mike |
| 2 | Regular | Hand chart + position-aware | TAG Tommy, LAG Larry |
| 3 | Shark | Monte Carlo equity simulation | Shark Steve, Shark Samantha |
| 4 | GTO / Coach | Balanced mixed-strategy / LLM-powered | GTO Greg, Coach Claude |

Difficulty slider (0–100) controls the weighted mix of bot tiers at the table.

## Key API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/game/create` | Create a new game session |
| WS | `/game/{id}/ws` | Real-time game channel |
| GET | `/game/{id}/hint` | Get equity-based action recommendation |
| GET | `/session/{id}/summary` | Aggregate session statistics |
| GET | `/hand/{id}/replay` | Full hand data for step-by-step replay |
| POST | `/coach/ask` | Post-hand Q&A with AI coach |

## Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `ANTHROPIC_API_KEY` | No | Enables LLM coach bot and AI session reviews. Without it, falls back to equity-based strategy and template feedback. |
| `VITE_API_URL` | No | Frontend API base URL (default: `http://localhost:8000`) |

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| F | Fold |
| C | Call / Check |
| R | Raise (minimum) |
| Space / N | Next hand (after hand completes) |

## License

Private — not open source.
