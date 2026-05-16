# Kaizen Quest — Personal AI Investment Agent

An aggressive investor's AI companion for market intelligence, deep research, portfolio analysis, and lifelong learning. Built for an investor who chases multi-baggers — high-quality growth stocks with strong fundamentals, wide moats, and asymmetric upside.

## 🎯 Philosophy

- **Quality over safety:** We want exposure to the best companies in the world, even if volatile
- **Deep research:** Every investment decision is backed by comprehensive multi-source analysis
- **Continuous learning:** The agent runs 24/7, constantly researching and improving its knowledge
- **Defined risk only:** Options for leverage and hedging, never undefined risk
- **Generational wealth:** Focus on compounding through high-conviction, long-term positions

---

## 📁 Repository Structure

```
Kaizen-Quest/
├── agent.py                    # Main orchestrator (~5000 lines)
├── requirements.txt            # Python dependencies
├── setup.sh                    # Setup script
├── CLAUDE.md                   # Master instructions (owner profile, rules, strict guidelines)
├── README.md                   # This file
│
├── skills/                     # Modular skill system (28 modules)
│   ├── deep_research.py        # 🔬 7-layer deep research orchestrator
│   ├── research_memory.py      # 🧠 Per-ticker research journal with confidence decay
│   ├── dynamic_position_sizer.py # 📊 Kelly Criterion + quality-aware position sizing
│   ├── thesis_journal.py       # 📓 Investment thesis tracking and outcomes
│   ├── yfinance_utils.py       # 🔇 Safe yfinance wrappers with Polygon fallback
│   ├── youtube_parser.py       # 📺 YouTube channel parser (ZipTrader, Tom Nash)
│   ├── stock_analyzer.py       # 📈 Comprehensive stock analysis (DCF, comps, earnings)
│   ├── financial_data_providers.py # 🌐 25+ API wrapper functions (Finnhub, FMP)
│   ├── portfolio_manager.py    # 💼 Portfolio review, rebalancing, alerts
│   ├── portfolio_analysis.py   # 📊 Portfolio weightage and concentration analysis
│   ├── smart_money_tracker.py  # 🏦 Hedge fund, insider, congressional tracking
│   ├── sector_rotation.py      # 🔄 Sector momentum and macro rotation signals
│   ├── earnings_intelligence.py # 📅 Earnings calendar, estimates, surprises
│   ├── market_sentiment.py     # 🌡️ Fear/greed, VIX, macro trends
│   ├── market_foresight.py     # 🔮 Multi-signal market outlook predictor
│   ├── options_intelligence.py # 🎯 Options chain analysis and ideas
│   ├── options_strategies.py   # 📐 Advanced options strategy generation
│   ├── options_executor.py     # ⚡ Alpaca options order execution
│   ├── enhanced_trading.py     # 📐 Kelly Criterion, position sizing, options imbalances
│   ├── paper_trader.py         # 📝 Paper trade tracking and performance
│   ├── benchmark_tracker.py    # 📊 Portfolio vs SPY/QQQ/IWM/VTI/DIA comparison
│   ├── news_research.py        # 📰 RSS feeds, Tavily search, Finnhub news
│   ├── learning_curator.py     # 📚 Weekly learning themes with daily deep dives
│   ├── recommendation_tracker.py # 📋 Recommendation performance tracking
│   ├── crypto_tracker.py       # ₿ BTC, ETH, XRP tracking
│   ├── alpaca_trading.py       # 💹 Alpaca paper trading (stocks + options)
│   ├── telegram_bot.py         # 📱 Telegram report delivery and alerts
│   ├── clickup_integration.py  # ✅ ClickUp task creation for high-conviction picks
│   └── memory_manager.py       # 🧠 Tiered memory system (hot/warm/cold)
│
├── .claude/skills/             # Claude Code skill templates (reference)
│   ├── SKILL.md
│   ├── investment-analyst.SKILL.md
│   ├── news-researcher.SKILL.md
│   ├── options-intelligence.SKILL.md
│   ├── portfolio-analysis.SKILL.md
│   ├── learning-curator.SKILL.md
│   ├── market-sentiment.SKILL.md
│   ├── crypto-tracker.SKILL.md
│   └── recommendation-tracker.SKILL.md
│
├── .github/workflows/
│   └── daily-agent.yml         # ⏰ GitHub Actions scheduler (see schedule below)
│
├── docs/                       # 📖 Documentation
│   ├── API_KEYS.md             # API key setup guide
│   ├── ARCHITECTURE_GUIDE.md   # System architecture
│   ├── PORTFOLIO.md            # Portfolio setup guide
│   ├── RECOMMENDATIONS.md      # Active recommendations tracker
│   ├── LEARNINGS.md            # Auto-updated learnings from each run
│   ├── THESIS_JOURNAL.json     # Investment thesis tracking (auto-generated)
│   ├── BENCHMARKS.md           # Benchmark comparison log
│   ├── PERFORMANCE.json        # Performance history (JSON)
│   ├── PAPER_TRADES.md         # Paper trade log
│   ├── TRADE_JOURNAL.md        # Trade decision journal
│   ├── DECISION_JOURNAL.md     # Decision rationale log
│   ├── WEEKLY_THEMES.md        # Learning themes rotation
│   ├── MEMORY.md               # Agent memory summary
│   ├── CONTEXT.md              # Current goals and context
│   └── research/               # 🔬 Deep research state (auto-generated)
│       ├── tickers/            # Per-ticker research journals
│       ├── facts/              # Verified facts with timestamps
│       └── state.json          # Global research state
│
├── REPORTS/                    # 📊 Daily reports (auto-generated)
│   └── YYYY-MM-DD/
│       └── HHMM.md             # Individual run reports
│
├── HISTORY/                    # 📜 Daily archives
│   └── YYYY-MM-DD.md           # Full day archive
│
├── portfolios/                 # 💼 Portfolio CSV imports
│   ├── portfolio1.csv
│   ├── portfolio2.csv
│   ├── portfolio3.csv
│   └── portfolio4.csv
│
├── cache/                      # 💾 Cached data
│   ├── paper_portfolio.json
│   ├── rss_cache.json
│   ├── telegram_chat_ids.json
│   ├── trade_history.json
│   └── youtube_reviewed.json   # 📺 Tracked YouTube videos
│
└── logs/                       # 📝 Run logs
    ├── agent.log
    └── paper_trades.log
```

---

## ⏰ Schedule (GitHub Actions)

The agent runs automatically via GitHub Actions on a comprehensive schedule:

### Weekdays (Mon-Fri)

| Time (ET) | Mode | What It Does |
|-----------|------|-------------|
| 7:00 AM | 🔬 Research | Deep research, no trades/reports |
| 8:00 AM | 📊 **Full Report** | Research + trade + report + Telegram |
| 9:30 AM - 3:00 PM (hourly) | ⚡ Alerts | Research + trade, no report |
| 12:30 PM | 📊 **Full Report** | Research + trade + report + Telegram |
| 4:30 PM | 📊 **Full Report** | Research + trade + report + Telegram |
| 6 PM, 8 PM, 10 PM | 🔬 Research | Deep research, no trades/reports |

### Weekends (Sat-Sun)

| Time | Mode | What It Does |
|------|------|-------------|
| Every 2 hours (24/7) | 🔬 Research | Deep research dives, no trades/reports |

**Total: ~35 runs/week** — the agent never stops learning.

---

## 🔬 Deep Research System

Before making any investment decision, the agent runs a comprehensive 7-layer analysis:

1. **Quantitative Screen** — Price, ratios, valuation multiples (yfinance + Polygon fallback)
2. **Financial Deep-Dive** — Income statement, DCF, analyst estimates, earnings beat rate
3. **Competitive Landscape** — Peer comparison, moat assessment, supply chain analysis
4. **Management & Governance** — Insider trades, institutional ownership, ESG scores
5. **Macro & Sector Context** — Sector rotation, economic calendar, technical indicators
6. **Contrarian Analysis** — Short interest, bear case, risk deep-dive (quality-aware)
7. **Temporal Evolution** — Thesis history, change detection, fact freshness scoring

### Quality-Aware Position Sizing

The agent uses a comprehensive quality assessment (50+ data points) to determine position sizing:

- **Rule of 40** (revenue growth % + profit margin %) — gold standard for growth companies
- **PEG ratio** — P/E relative to growth rate
- **Earnings beat rate** — Consistency of beating estimates
- **Insider activity** — Are insiders buying or selling?
- **Institutional trend** — Are smart money increasing or decreasing positions?
- **Sector momentum** — Is the stock's sector outperforming?

**Key principle:** High-quality growth stocks are NOT penalized for volatility. Volatility is the price of admission for asymmetric upside.

### Research Memory

The agent tracks everything it researches across runs:
- **Per-ticker research journals** — Every fact, catalyst, and thesis evolution
- **Confidence decay** — Facts expire based on type (prices: 1 day, earnings: 90 days, moat: 90 days)
- **Change detection** — Only re-researches what has changed since last run
- **Video tracking** — YouTube videos are tracked to avoid reprocessing

---

## 📊 Position Sizing

Based on Kelly Criterion with quality-aware adjustments:

- **Max 90% of cash deployed** (10% reserve)
- **Max 15% in single position**
- **Max 40% of cash per trade**
- **Min $200 per trade** (for diversification)
- **75% of full Kelly** (aggressive but not reckless)
- **Quality score 7+:** Minimal volatility penalty
- **Quality score 5-7:** Moderate volatility penalty
- **Quality score <5:** Full volatility penalty

---

## 🎯 Investment Rules (Strict)

### Options Trading
1. **NEVER let options expire ITM** — always sell/close before expiry
2. **Minimum 2 weeks to expiration** (preference: 30-90 days or LEAPS)
3. **Max 10% of portfolio in options**
4. **Max 5 options underlyings** at a time
5. **Allowed strategies:** Buying calls/puts, selling covered calls, buying LEAPS, mispriced asymmetric options
6. **Conviction 8+** required for options strategies

### Stock/ETF Rules
- **Minimum hold horizon:** 2 weeks (swing), preferred: months to years
- **No penny stocks under $1**
- **No margin trading**
- **Max 20% concentration** in single position
- **Precious metals and crypto** are valid asset classes

---

## 📺 YouTube Integration

The agent parses YouTube channels for stock mentions:
- **ZipTrader** and **Tom Nash** (configurable)
- Extracts tickers from video titles, descriptions, and transcripts
- **Age-based confidence decay** — older videos get lower weight
- **Video tracking** — never reprocesses the same video twice
- Results are injected as **starting points for due diligence**, not recommendations

### Setting Up YouTube API Key

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project (or select existing)
3. Enable **YouTube Data API v3** (APIs & Services → Library)
4. Create an **API key** (APIs & Services → Credentials → Create Credentials → API Key)
5. Add to GitHub Secrets: `YOUTUBE_API_KEY`
6. Or set locally: `export YOUTUBE_API_KEY="your-key-here"`

**Without API key:** The parser falls back to web scraping (slower but functional).

---

## 🔑 API Keys

Required secrets for GitHub Actions (and/or `.env` file locally):

| Key | Required | Source |
|-----|----------|--------|
| `OPENROUTER_API_KEY` | ✅ Yes | [OpenRouter](https://openrouter.ai/keys) |
| `FINNHUB_API_KEY` | ✅ Yes | [Finnhub](https://finnhub.io/register) |
| `ALPACA_API_KEY` | ✅ Yes | [Alpaca](https://app.alpaca.markets) |
| `ALPACA_SECRET_KEY` | ✅ Yes | [Alpaca](https://app.alpaca.markets) |
| `TAVILY_API_KEY` | Optional | [Tavily](https://tavily.com) |
| `FMP_API_KEY` | Optional | [Financial Modeling Prep](https://site.financialmodelingprep.com/developer) |
| `TELEGRAM_BOT_TOKEN` | Optional | [@BotFather](https://t.me/BotFather) |
| `YOUTUBE_API_KEY` | Optional | [Google Cloud Console](https://console.cloud.google.com/) |
| `CLICKUP_API_KEY` | Optional | [ClickUp](https://clickup.com) |
| `PAT_TOKEN` | ✅ Yes | GitHub Personal Access Token (for git push) |

---

## 🚀 Quick Start

```bash
# 1. Clone and install
git clone https://github.com/pravinkumaaar/Kaizen-Quest.git
cd Kaizen-Quest
pip install -r requirements.txt

# 2. Set up environment variables
cp .env.example .env  # Edit with your API keys
# Or export directly:
export OPENROUTER_API_KEY="sk-or-v1-..."
export FINNHUB_API_KEY="your-key"
export ALPACA_API_KEY="your-key"
export ALPACA_SECRET_KEY="your-secret"

# 3. Run the agent
python3 agent.py

# 4. Run in specific modes
RUN_MODE=full python3 agent.py        # Full report + trade
RUN_MODE=alerts-only python3 agent.py # Trade only, no report
RUN_MODE=research python3 agent.py    # Deep research only
```

---

## 📖 Documentation

- **[CLAUDE.md](CLAUDE.md)** — Master instructions, owner profile, strict investment rules
- **[docs/API_KEYS.md](docs/API_KEYS.md)** — Detailed API key setup guide
- **[docs/ARCHITECTURE_GUIDE.md](docs/ARCHITECTURE_GUIDE.md)** — System architecture
- **[docs/PORTFOLIO.md](docs/PORTFOLIO.md)** — Portfolio setup and management
- **[docs/QUICK_START.md](docs/QUICK_START.md)** — Quick reference guide

---

## ⚠️ Disclaimer

**For educational/informational purposes only. Not financial advice. Verify with your broker before acting. The agent NEVER executes trades without human approval — it only RECOMMENDS. The human makes all final decisions.**

---

*Built with ❤️ for aggressive investors who believe in the power of compounding through high-quality growth.*
