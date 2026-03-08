# Poker Practice — Future Features

## Learning & Analysis
- [ ] **"What Would GTO Do?" Comparison** — Post-hand side-by-side showing your action vs GTO's action at each decision point
- [ ] **Common Mistake Pattern Detection** — Track recurring leaks across hands (e.g., "you fold to river bets 80% of the time", "you're not c-betting enough on dry boards")
- [ ] **Bot Personality & Tells** — Make bot tendencies visible and learnable during play (e.g., "Maniac Mike just min-raised for the 5th time")

## Game Modes
- [ ] **Structured Practice Scenarios** — Curated drills: short stack push/fold, blind defense, drawing hands, spot the bluff
- [ ] **Tournament / Sit & Go Mode** — Escalating blinds, bubble pressure, ICM considerations

## Persistence & Progression
- [ ] **Progress Tracking Over Time** — Persistent stats across sessions, trend charts, improvement curves (requires DB/login)
- [ ] **Achievements & Milestones** — Gamification: "First bluff that worked", "10 hands without a mistake", "Beat the Shark heads-up", skill level progression

## UI & Polish
- [ ] **Mobile Responsiveness** — Responsive table layout, touch-friendly controls
- [ ] **Custom Bot Selection** — Let players pick specific opponents from the setup screen (currently only difficulty slider)
- [ ] **Coach Bot Accessible from UI** — SetupScreen doesn't expose bot_configs, so Coach Claude can never be added from the UI
- [ ] **WebSocket Reconnection** — onclose handler is empty — no feedback or reconnect on disconnect
