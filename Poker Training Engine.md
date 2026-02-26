# Product Requirements Document: Poker Training Engine

**An AI-powered poker practice platform with intelligent bot opponents**

| Field | Value |
|-------|-------|
| Document | Product Requirements Document |
| Product | Poker Training Engine |
| Version | 1.0 |
| Date | February 25, 2026 |
| Status | Draft |

---

## 1. Executive Summary

The Poker Training Engine is a self-contained, browser-based poker practice platform that allows users to play Texas Hold'em against AI-powered bot opponents of varying skill levels and playing styles. The product's core mission is to help players improve their poker skills through deliberate practice, real-time feedback, and post-hand analysis.

Unlike existing poker training tools that focus on solver outputs or video content, this product provides an interactive, game-based learning environment where every hand is an opportunity to practice decision-making against opponents that adapt and challenge the player at an appropriate level.

---

## 2. Problem Statement

Aspiring poker players face several barriers to improvement. Play-money sites are populated by players who don't take the game seriously, making it impossible to develop sound strategy. Real-money games carry financial risk that discourages experimentation. Solver tools like PioSOLVER are powerful but abstract, showing optimal strategies without letting players internalize them through repetition. Video training is passive.

Players need a risk-free environment where they can practice against realistic opponents, experiment with strategies, make mistakes, and receive immediate, actionable feedback on their decisions.

---

## 3. Target Users

- **Beginner players** who understand basic poker rules but need to develop fundamental strategy (position, hand selection, pot odds).
- **Intermediate players** who want to sharpen their postflop play, range construction, and opponent modeling.
- **Advanced players** who want a quick sparring partner to warm up or test specific lines against defined opponent types.
- **Poker content creators and coaches** looking for a tool to demonstrate concepts interactively.

---

## 4. Product Overview

The product consists of four major subsystems that work together to deliver the training experience:

| Subsystem | Responsibility | Key Technologies |
|-----------|---------------|-----------------|
| **Game Engine** | Manages game state, rules enforcement, card dealing, pot calculation, hand evaluation, and winner determination. | Python core with hand evaluator library (treys or phevaluator), WebSocket API layer. |
| **Bot Framework** | Pluggable AI opponents with configurable strategies, styles, and difficulty levels. | Strategy pattern architecture, Monte Carlo equity calculator, optional LLM integration via Claude API. |
| **User Interface** | Interactive poker table, HUD overlays, action controls, hand history viewer. | React + Canvas/SVG for table rendering, WebSocket client, responsive design. |
| **Analysis Engine** | Post-hand review, decision scoring, session statistics, and AI coaching commentary. | Equity calculator, EV computation, Claude API for natural-language coaching. |

---

## 5. Detailed Requirements

### 5.1 Game Engine

The game engine is the foundation of the platform. It must enforce all rules of No-Limit Texas Hold'em accurately and manage the complete lifecycle of each hand.

#### 5.1.1 Core Game Loop

| ID | Requirement | Priority | Phase |
|----|------------|----------|-------|
| GE-001 | Support 2–9 player tables with configurable seat count. | P0 | MVP |
| GE-002 | Implement complete betting rounds: preflop, flop, turn, river with proper action order. | P0 | MVP |
| GE-003 | Handle all bet types: fold, check, call, bet, raise, all-in. | P0 | MVP |
| GE-004 | Calculate and split main pot and side pots correctly for multi-way all-in scenarios. | P0 | MVP |
| GE-005 | Use a cryptographically secure random number generator for card shuffling. | P0 | MVP |
| GE-006 | Evaluate hand strength at showdown using a fast evaluator (sub-millisecond per hand). | P0 | MVP |
| GE-007 | Manage blinds, antes, and dealer button rotation automatically. | P0 | MVP |
| GE-008 | Enforce minimum raise rules (min-raise = previous raise size). | P0 | MVP |
| GE-009 | Support configurable blind structures for tournament-style play. | P1 | v1.1 |
| GE-010 | Emit structured events for every state change (deal, bet, fold, showdown) for UI and analysis consumption. | P0 | MVP |

#### 5.1.2 Hand Evaluation

The hand evaluator must rank all possible 5-card hands from a 7-card input (2 hole cards + 5 community cards) and correctly determine winners including split pots. It must support all standard hand rankings: Royal Flush, Straight Flush, Four of a Kind, Full House, Flush, Straight, Three of a Kind, Two Pair, One Pair, High Card. Kicker resolution must be exact.

---

### 5.2 Bot Framework

The bot framework is the heart of the training product. Bots must feel like real opponents while providing pedagogical value. The architecture must support a spectrum from simple heuristic bots to sophisticated AI agents, all sharing a common interface.

#### 5.2.1 Bot Architecture

Every bot implements a common interface that receives a GameState object (containing visible information only — no peeking at other players' cards) and returns an Action. This allows bots to be swapped, combined, and composed freely.

| ID | Requirement | Priority | Phase |
|----|------------|----------|-------|
| BF-001 | All bots implement a common BotStrategy interface: `decide(game_state) → Action`. | P0 | MVP |
| BF-002 | Bots receive only information visible to their seat (hole cards, community cards, pot, bet sizes, position, stack sizes). No access to other players' hidden cards. | P0 | MVP |
| BF-003 | Bots must respond within 2 seconds to maintain game flow. Add configurable artificial delay (0.5–3s) for realism. | P0 | MVP |
| BF-004 | Support "thinking time" variation — bots pause longer on difficult decisions for realism. | P1 | v1.1 |
| BF-005 | Bot configurations are serializable as JSON profiles for sharing and reproducibility. | P1 | v1.1 |

#### 5.2.2 Bot Difficulty Tiers

The platform offers four tiers of bot difficulty, each corresponding to a fundamentally different decision-making approach. Players should be able to select the tier and customize parameters within each tier.

| Tier | Name | Strategy Approach | Target User |
|------|------|-------------------|-------------|
| **Tier 1** | Fish | Random/heuristic. Calls too much, rarely bluffs, plays too many hands. Loose-passive style with predictable patterns. | Complete beginners learning basic hand values and position. |
| **Tier 2** | Regular | Chart-based preflop + basic postflop heuristics. Plays a reasonable range, bets strong hands, folds weak ones. Some basic bet sizing. | Beginners ready to learn tight-aggressive fundamentals. |
| **Tier 3** | Shark | Equity-based decisions with Monte Carlo simulation. Considers pot odds, implied odds, opponent ranges. Balanced bet/bluff ratios. | Intermediate players working on range-based thinking. |
| **Tier 4** | GTO Bot | Near-optimal play using precomputed GTO solutions or real-time Nash equilibrium approximation. Mixed strategies with correct frequencies. | Advanced players studying game-theory-optimal strategy. |

#### 5.2.3 Bot Playing Styles (Personality System)

Beyond difficulty, bots are parameterized along two orthogonal axes that define their "personality." This creates a matrix of opponent types that mirrors the real poker ecosystem:

- **Tightness (0–100):** How selective the bot is with starting hands. 0 = plays every hand, 100 = plays only premium hands.
- **Aggression (0–100):** How often the bot bets/raises vs. checks/calls. 0 = pure passive, 100 = hyper-aggressive.

This produces four archetypal quadrants: Loose-Passive ("calling station"), Loose-Aggressive ("maniac"), Tight-Passive ("nit"), and Tight-Aggressive ("TAG"). Each named bot profile is a point in this 2D space, plus a difficulty tier.

#### 5.2.4 LLM-Powered Coach Bot (Stretch Goal)

A special bot variant that uses Claude's API to make decisions and, critically, can explain its reasoning after each hand. This bot serves dual purpose as opponent and coach. After showdown, the user can ask "Why did you raise the turn?" and get a strategic explanation grounded in the hand's context.

| ID | Requirement | Priority | Phase |
|----|------------|----------|-------|
| LLM-001 | Send structured game state (cards, pot, action history, stacks, position) to Claude API for decision-making. | P2 | v2.0 |
| LLM-002 | Parse Claude's response into a valid game Action with bet sizing. | P2 | v2.0 |
| LLM-003 | Cache hand context so the player can ask follow-up questions post-hand. | P2 | v2.0 |
| LLM-004 | Ground LLM decisions with equity calculation data passed in the prompt. | P2 | v2.0 |
| LLM-005 | Provide a "coach mode" toggle where the bot explains every decision as it plays. | P2 | v2.0 |

---

### 5.3 User Interface

#### 5.3.1 Poker Table View

| ID | Requirement | Priority | Phase |
|----|------------|----------|-------|
| UI-001 | Render a poker table with player seats, card areas, community cards, and pot display. | P0 | MVP |
| UI-002 | Display player's hole cards face-up; bot cards face-down (revealed at showdown). | P0 | MVP |
| UI-003 | Action panel with Fold, Check/Call, Bet/Raise buttons and a bet sizing slider. | P0 | MVP |
| UI-004 | Show pot size, current bet to call, and player stack sizes at all times. | P0 | MVP |
| UI-005 | Animate card dealing, chip movements, and player actions. | P1 | v1.1 |
| UI-006 | Display a mini HUD per bot showing VPIP, PFR, and Aggression Factor (updated in real time). | P1 | v1.1 |
| UI-007 | Responsive layout supporting desktop and tablet screen sizes. | P1 | v1.1 |
| UI-008 | Keyboard shortcuts for common actions (F=fold, C=call, R=raise). | P1 | v1.1 |

#### 5.3.2 Game Setup & Configuration

| ID | Requirement | Priority | Phase |
|----|------------|----------|-------|
| GS-001 | Allow user to select number of opponents (1–8 bots). | P0 | MVP |
| GS-002 | Allow user to choose bot difficulty tier for each seat independently. | P0 | MVP |
| GS-003 | Configurable starting stack sizes and blind levels. | P0 | MVP |
| GS-004 | Quick-start presets: "Heads-Up Practice," "6-Max Cash," "Full Ring," "Tournament." | P1 | v1.1 |
| GS-005 | Save and load custom table configurations. | P1 | v1.1 |

---

### 5.4 Analysis Engine

The analysis engine differentiates this product from a simple poker game. It transforms every session into a learning opportunity by evaluating the player's decisions against mathematically optimal play.

| ID | Requirement | Priority | Phase |
|----|------------|----------|-------|
| AN-001 | Store complete hand history for every hand played (all actions, cards, timing). | P0 | MVP |
| AN-002 | Post-hand equity graph: show the player's equity at each street (preflop, flop, turn, river). | P0 | MVP |
| AN-003 | Decision scoring: compare each player action to equity-optimal play and assign a score ("good," "mistake," "blunder"). | P0 | MVP |
| AN-004 | EV calculation: estimate the expected value gained or lost at each decision point. | P1 | v1.1 |
| AN-005 | Session summary dashboard: win rate, biggest pots won/lost, most common mistakes, positional stats. | P1 | v1.1 |
| AN-006 | Hand replayer: step through any past hand action-by-action with analysis overlay. | P1 | v1.1 |
| AN-007 | AI coaching commentary via Claude API: natural-language explanation of key mistakes and suggested improvements after each session. | P2 | v2.0 |
| AN-008 | Trend tracking across sessions: show improvement over time in key metrics. | P2 | v2.0 |

---

## 6. Technical Architecture

### 6.1 Recommended Stack

| Layer | Technology | Rationale |
|-------|-----------|-----------|
| **Backend / Engine** | Python 3.11+ | Rich poker library ecosystem (treys, phevaluator), fast prototyping, strong typing with dataclasses. |
| **API Layer** | FastAPI + WebSockets | Async-native, real-time bidirectional communication for game events. |
| **Frontend** | React + TypeScript | Component-based UI, strong typing, large ecosystem for canvas/SVG rendering. |
| **Hand Evaluator** | phevaluator or treys | Sub-microsecond hand evaluation, battle-tested. |
| **Equity Calculator** | Monte Carlo simulation | Flexible, supports any number of players and unknown cards. |
| **LLM Integration** | Claude API (Sonnet 4) | Strong reasoning, natural coaching voice, fast inference for real-time play. |
| **Persistence** | SQLite (local) / PostgreSQL (hosted) | Hand histories, session data, user progress. |
| **Deployment** | Docker Compose | Single-command local setup, portable. |

### 6.2 Data Model (Key Entities)

- **GameSession:** id, table_config, players[], start_time, status.
- **Hand:** id, session_id, hand_number, dealer_seat, community_cards[], pot_size, winner_id.
- **PlayerState:** player_id, hand_id, seat, stack, hole_cards[], is_active, is_all_in.
- **Action:** id, hand_id, player_id, street, action_type, amount, timestamp.
- **BotProfile:** id, name, tier, tightness, aggression, description, config_json.
- **AnalysisResult:** id, hand_id, action_id, equity_at_decision, ev_of_action, optimal_action, score.

---

## 7. Phased Delivery Plan

### 7.1 MVP (Phase 1) — 8–10 weeks

**Goal:** A playable heads-up or multi-way poker game against Tier 1 and Tier 2 bots, with basic post-hand equity review.

- Complete game engine with rules enforcement and hand evaluation.
- Tier 1 (Fish) and Tier 2 (Regular) bots with configurable tightness/aggression.
- Functional poker table UI with card display, action buttons, and pot tracking.
- Basic hand history storage and post-hand equity display.
- Simple decision scoring (good / mistake / blunder).

### 7.2 Version 1.1 (Phase 2) — 6–8 weeks

**Goal:** Add challenging opponents and rich analysis to deepen the training value.

- Tier 3 (Shark) bot with Monte Carlo equity-based decision engine.
- HUD overlay with real-time bot stats (VPIP, PFR, AF).
- Hand replayer with action-by-action stepping and analysis.
- Session summary dashboard with aggregate statistics.
- Quick-start presets and tournament blind structures.
- Card and chip animations for game feel.

### 7.3 Version 2.0 (Phase 3) — 8–12 weeks

**Goal:** Introduce AI coaching and near-optimal play for advanced training.

- Tier 4 (GTO Bot) with precomputed or approximated equilibrium strategies.
- LLM Coach Bot powered by Claude API with post-hand Q&A.
- AI-generated session reviews with personalized improvement suggestions.
- Trend tracking and progress visualization across sessions.
- Exportable hand histories in standard poker formats.

---

## 8. Success Metrics

| Metric | Target (MVP) | Target (v2.0) |
|--------|-------------|---------------|
| Hands per session (avg) | 50+ | 100+ |
| Session duration (avg) | 20+ minutes | 30+ minutes |
| Analysis review rate | 30% of hands reviewed | 60% of hands reviewed |
| Return sessions per week | 3+ per user | 5+ per user |
| User-reported skill improvement | N/A (qualitative) | 70% report improvement |
| Game engine accuracy | 100% rules correctness | 100% rules correctness |
| Bot response latency | < 2 seconds | < 2 seconds (< 5s for LLM bot) |

---

## 9. Risks and Mitigations

| Risk | Impact | Likelihood | Mitigation |
|------|--------|-----------|------------|
| Bots feel too predictable at lower tiers | Users get bored, stop practicing | Medium | Add randomization noise, vary styles per session, track and shuffle bot profiles. |
| LLM coaching advice is inaccurate | Users learn bad strategy | Medium | Ground LLM with equity data, validate advice against solver outputs, allow user flagging. |
| Game engine has edge-case bugs (side pots, all-in) | Loss of trust in the platform | High initially | Extensive test suite with known hand scenarios, community bug reporting. |
| Claude API latency disrupts gameplay | Frustrating UX for LLM bot hands | Low-Medium | Async decision pipeline, pre-fetch common spots, fallback to equity bot if timeout. |
| Scope creep into multiplayer / real money | Delays MVP, regulatory issues | Low | Strict scope to single-player training. No real money, no multiplayer networking. |

---

## 10. Open Questions

1. Should the MVP support only heads-up (1v1) or also multi-way tables? Multi-way is more realistic but adds complexity to bot interactions and side pot logic.
2. What is the preferred hosting model: fully local (desktop app / Docker), browser-based with a cloud backend, or both?
3. Should bot profiles be fixed or should bots adapt to the player's tendencies over time (exploitative play)?
4. How much Claude API usage budget is acceptable for the LLM coaching features? This determines how often the coach bot can be used.
5. Should hand histories be exportable to standard formats (PokerStars HH format) for use with external analysis tools?

---

## 11. Appendix: Bot Decision Pseudocode

The following illustrates the decision flow for a Tier 3 (Shark) bot to demonstrate the equity-based approach:

```
1. Receive game state (hole cards, community cards, pot, bet to call, position, stacks).
2. Estimate hand equity via Monte Carlo: simulate 1,000–10,000 random runouts
   against a modeled opponent range.
3. Calculate pot odds: call_amount / (pot + call_amount).
4. If equity > pot_odds * 1.2: RAISE (size proportional to equity strength).
5. If equity > pot_odds: CALL.
6. If equity < pot_odds but bluff_frequency check passes:
   BLUFF RAISE (with semi-bluff hands preferred).
7. Otherwise: FOLD.
8. Add noise: ±5% randomization to all thresholds to prevent exploitability.
```
