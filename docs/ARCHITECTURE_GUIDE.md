# Kaizen Quest Agent - Complete Architecture Guide

## How It All Works

### Current Architecture
GitHub Actions (free) runs agent.py twice daily (9:30 AM & 4:30 PM ET):
- Uses free LLM models (OpenRouter)
- Fetches news, market data, options data
- Generates investment ideas with reasoning
- Tracks recommendations in docs/
- Sends daily summary to ClickUp
- Commits reports back to GitHub
- Costs: $0/month

### What the Agent Does Each Run
1. Collects data - RSS feeds, market prices, news, options chains
2. Analyzes portfolio - Weightage, rebalancing needs, benchmark comparison
3. Generates ideas - News digest, investment ideas, options plays, learning topics
4. Tracks recommendations - Stores in RECOMMENDATIONS.md, DECISION_JOURNAL.md, ClickUp
5. Self-reflects - Updates LEARNINGS.md with patterns and mistakes
6. Updates memory - Tiered hot/warm/cold memory system
7. Commits results - All reports saved to GitHub

### What the Agent Does NOT Do Yet
- Live trading - Currently only generates recommendations (no auto-execution)
- Real-time monitoring - Only runs at scheduled times, not continuously
- Chat interface - No way to ask questions or get ad-hoc reports

---

## GitHub Actions Setup - Step by Step

### What is GitHub Actions?
GitHub Actions is a free automation service built into GitHub. It runs code on GitHub's servers whenever you tell you to. Think of it as a free cloud computer that runs your agent automatically.

### How to Add Secrets (Step by Step)

1. Go to your GitHub repo: https://github.com/pravinkumaaar/Kaizen-Quest
2. Click "Settings" (top right tab)
3. Click "Secrets and variables" in the left sidebar
4. Click "Actions"
5. Click "New repository secret"
6. For each key below, enter the name and value:

Secret Name: OPENROUTER_API_KEY
Value: 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

Secret Name: FINNHUB_API_KEY
Value: d7kj3h9r01qiqbcuk1ugd7kj3h9r01qiqbcuk1v0

Secret Name: TAVILY_API_KEY
Value: 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

Secret Name: ALPACA_API_KEY
Value: PKQPPHGBKHMRBLDY6HKSXKXA3Y

Secret Name: ALPACA_SECRET_KEY
Value: 7vq32opSfSvDhwp5qttV6o7SePyfrfTfVffS7zTKiDZp

Secret Name: CLICKUP_API_KEY
Value: pk_210064579_GKJGK3ZL7YXS46SKMB4GZ7UBDR61JRLE

Secret Name: CLICKUP_LIST_ID
Value: 901416047336

7. Verify: Go to Actions tab, click "Daily Agent Run", click "Run workflow" to test

### What Happens When It Runs
1. GitHub spins up a fresh Ubuntu virtual machine
2. Checks out your code
3. Installs Python and dependencies
4. Runs python3 agent.py with your secrets as environment variables
5. Commits any new reports back to the repo
6. Shuts down (free up to 2,000 minutes/month)

---

## Trading Strategy

### Structured Trade Thesis Framework
Every recommendation will include:
- Thesis: One-sentence investment logic
- Bull Case (3 points): Why this could go up significantly
- Bear Case (3 points): Why this could go wrong
- Risk/Reward Ratio: Minimum 3:1 upside vs downside
- Position Size: Based on conviction and Kelly Criterion
- Entry Criteria: Exact price levels to enter
- Exit Criteria: Stop-loss and profit-taking levels
- Pre-Mortem: "This trade will fail if X, Y, or Z happens"
- Time Horizon: Expected holding period

### Kelly Criterion Position Sizing
Kelly % = (Win Probability * Average Win - Loss Probability * Average Loss) / Average Win
Conservative Kelly = Kelly % * 0.5 (half-Kelly for safety)
Max position size = Portfolio Value * Conservative Kelly

Rules:
- Never more than 10% of portfolio in one position
- Never more than 25% in one sector
- Minimum conviction of 7/10 for any trade
- Risk/reward must be at least 3:1

### Options Strategy
The agent will look for:
- Pricing imbalances: Options where implied volatility differs from historical
- Asymmetric plays: Trades where upside is 5x+ the downside
- High probability: Selling premium on overpriced options (high IV rank)
- LEAPS: Long-term calls on high-conviction growth stocks
- Covered calls: On existing positions to generate income

---

## UI & Chat Interface

### ClickUp as UI (Already Integrated)
Each recommendation is a task with full thesis, price levels, exit criteria.
Daily summaries appear as new tasks. Mobile app available (iOS/Android).
Dashboard view of all active trades.

Limitations: Cannot chat or ask questions. Read-only dashboard.

### Telegram Bot (Recommended)
Chat with your agent naturally. Ask "Why OKLO?", "How is paper trading?",
"Show me all recommendations", "What's the market looking like?"

Setup: Message @BotFather on Telegram, send /newbot, get token.

---

## Schedule & Timing

### Current: 9:30 AM and 4:30 PM ET, Mon-Fri
For research and recommendations, this is enough.
For active trading, it is not - the market moves continuously.

### Options for More Frequent Runs
1. More GitHub Actions runs (still free) - every hour from 9 AM to 5 PM
2. Always-on cloud server ($5-20/month) - continuous monitoring
3. Hybrid - GitHub Actions for research + lightweight server for monitoring

---

## Roadmap

Phase 1: Foundation (Done)
- Agent generates recommendations
- Tracks in RECOMMENDATIONS.md and DECISION_JOURNAL.md
- GitHub Actions automation
- ClickUp integration
- Alpaca paper trading connected
- Tiered memory system

Phase 2: Intelligence (Next)
- Enhanced trade thesis framework
- Kelly Criterion position sizing
- Options pricing imbalance detection
- Scheduled re-evaluation of positions
- More frequent GitHub Actions runs

Phase 3: Interface (Next)
- Telegram bot for chatting
- Web dashboard (Streamlit)
- ClickUp automation

Phase 4: Trading (Future)
- Automated paper trading execution
- Real-time position monitoring
- Stop-loss and profit-taking automation
- Performance analytics
- Transition to live trading