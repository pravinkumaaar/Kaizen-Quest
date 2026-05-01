# Kaizen Quest - Personal AI Agent v2.2

An aggressive investor's AI companion for market intelligence, portfolio analysis, and lifelong learning.

## 🚀 What's New in v2.2

✅ **Modular Skills System** - Claude-like skill modules for better organization  
✅ **Portfolios Folder** - All portfolio CSVs now in `portfolios/` directory  
✅ **Clean Documentation** - Static MDs moved to `docs/` folder  
✅ **API Keys Audit** - Clear documentation on what's needed (spoiler: most are already configured!)  
✅ **Fresh Recommendations** - Auto-clear active recommendations on each run  
✅ **Crypto Support** - BTC, ETH, XRP tracking (no extra API key needed!)  
✅ **Portfolio Rebalancing** - SELL/REDUCE suggestions for overvalued positions  
✅ **Once-in-a-Lifetime Opportunities** - Special focus on asymmetric plays  

---

## 📁 New Folder Structure

```
Kaizen-Quest/
├── agent.py                 # Main orchestrator (lean & clean)
├── requirements.txt         # Dependencies (python-dotenv removed)
├── setup.sh                # Setup script
│
├── portfolios/             # 🆕 ALL portfolio CSVs go here
│   ├── portfolio1.csv
│   ├── portfolio2.csv
│   ├── portfolio3.csv
│   └── portfolio4.csv
│
├── skills/                 # 🆕 Modular skills (like Claude Code)
│   ├── portfolio_analysis.py
│   ├── market_sentiment.py
│   ├── crypto_tracker.py
│   ├── options_intelligence.py
│   ├── news_research.py
│   ├── learning_curator.py
│   └── recommendation_tracker.py
│
├── docs/                   # 🆕 All static documentation
│   ├── API_KEYS.md        # 🆕 What keys you need (hint: not many!)
│   ├── README.md
│   ├── QUICK_START.md
│   ├── RECOMMENDATIONS.md
│   ├── LEARNINGS.md
│   └── ... (all other .md files)
│
├── .claude/
│   └── skills/
│       └── SKILL.md       # 🆕 Skills system documentation
│
├── REPORTS/               # Daily reports (auto-generated)
├── HISTORY/               # Historical archives
├── logs/                  # Run logs
└── cache/                 # RSS cache
```

---

## 🔑 API Keys - The Truth

**Good news**: You probably don't need to create ANY new API keys!

| API Key | Required? | Already Set? | Purpose |
|---------|-----------|--------------|---------|
| `OPENROUTER_API_KEY` | ✅ YES | ✅ Yes (default in code) | LLM access (Qwen, Llama, DeepSeek) |
| `TAVILY_API_KEY` | ✅ YES | ✅ Yes (default in code) | Web search |
| `FINNHUB_API_KEY` | ✅ YES | ✅ Yes (default in code) | Stock prices, news |
| `POLYGON_API_KEY` | ❌ Optional | ✅ Yes (default in code) | Live options data |
| `ALPACA_API_KEY` | ❌ Optional | ❌ No (empty) | Alternative options source |

**🎉 All required keys are already configured with defaults in `agent.py`!**

For details, see: [`docs/API_KEYS.md`](docs/API_KEYS.md)

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Set Environment Variables (Optional - defaults work!)
```bash
export OPENROUTER_API_KEY="sk-or-v1-..."      # Or use default
export TAVILY_API_KEY="tvly-..."              # Or use default
export FINNHUB_API_KEY="your-key"              # Or use default
```

### 3. Add Your Portfolios
Place your Yahoo Finance exported CSVs in `portfolios/` folder:
- `portfolios/portfolio1.csv`
- `portfolios/portfolio2.csv`
- etc.

**Expected CSV format**: `Symbol,Shares,Purchase Price,Date`

### 4. Run the Agent
```bash
python3 agent.py
```

---

## 🎯 Key Features

### 1. **Portfolio Analysis & Rebalancing**
- ✅ Auto-discovers all portfolios in `portfolios/` folder
- ✅ Consolidates duplicate tickers with weighted average cost basis
- ✅ Calculates weightings, concentration risk
- ✅ **SELL/REDUCE suggestions** for overvalued or risky positions
- ✅ Once-in-a-lifetime opportunity alerts

### 2. **Market Sentiment & Macro Trends**
- ✅ VIX-based fear/greed assessment
- ✅ SPY/QQQ movement tracking
- ✅ Deep-dive macro trend analysis

### 3. **Crypto Tracking** (No Extra API Key!)
- ✅ BTC-USD, ETH-USD, XRP-USD support
- ✅ Uses yfinance + CoinGecko (FREE, no key needed)
- ✅ Crypto holdings analyzed in portfolio context

### 4. **Investment Ideas (9+/10 Conviction Only)**
- ✅ Portfolio-aware recommendations
- ✅ Once-in-a-lifetime opportunities highlighted
- ✅ Clear SELL/BUY/HOLD signals
- ✅ Time horizons: Swing (2-8wk), Medium (3-12mo), Long (1-3yr)

### 5. **Options Intelligence**
- ✅ Live options chains (Polygon.io or yfinance fallback)
- ✅ LEAPS, covered calls, asymmetric plays
- ✅ Strict rules: Min 2wk expiry, max 10% allocation

### 6. **Learning System**
- ✅ Rotating weekly themes (AI, Macro, History, etc.)
- ✅ Daily deep-dives
- ✅ Cross-domain insights

---

## 🛠️ Skills System (New in v2.2!)

Modular skills like Claude Code. Each skill is a self-contained Python module:

| Skill | Purpose | Location |
|-------|---------|----------|
| `portfolio_analysis` | Weightings, concentration, rebalancing | `skills/portfolio_analysis.py` |
| `market_sentiment` | VIX, fear/greed, macro trends | `skills/market_sentiment.py` |
| `crypto_tracker` | Crypto prices, market cap, ideas | `skills/crypto_tracker.py` |
| `options_intelligence` | Options chains, strategies | `skills/options_intelligence.py` |
| `news_research` | RSS, Tavily, Finnhub | `skills/news_research.py` |
| `learning_curator` | Weekly themes, daily topics | `skills/learning_curator.py` |
| `recommendation_tracker` | Track P&L, update prices | `skills/recommendation_tracker.py` |

**Skills can be:**
- Imported into `agent.py` for regular use
- Invoked independently for specific tasks
- Combined for complex analysis

---

## 📊 Example Output

The agent generates a daily report in `REPORTS/YYYY-MM-DD-HHMM.md`:

```
# 🧠 Daily Intelligence Report
**2026-04-23** | Run 1255 | Market Open 🟢

## 📊 Market Snapshot
[Live prices of your holdings + indices]

## 🌡️ Market Sentiment & Timing
**FEAR** (VIX: 22.5)
Action: Have dry powder ready, add to high-conviction positions.

## 🤖 AI & Tech Developments
[News digest with cross-domain insights]

# 💼 Investment Ideas
### [1] Asset: NVDA — AI Infrastructure King
**Conviction Score:** 10/10
**Portfolio Alignment:** You're underweight semiconductors.
**Action:** BUY on any dip below $850.

# 🎯 Portfolio Rebalancing
**⚠️ HIGH CONCENTRATION:** Top 5 = 68%
**Action: SELL 30%** of AAPL (25% → 15%) to free up capital.

# 🚀 Once-in-a-Lifetime Opportunities
- Crypto crash? BTC down 50%+ = generational buy
- VIX >30 = buy quality stocks at deep discounts
```

---

## 🔧 Troubleshooting

**Q: "No module named 'skills'"**  
A: Run from the project root: `cd /path/to/Kaizen-Quest && python3 agent.py`

**Q: Portfolio not loading?**  
A: Ensure CSVs are in `portfolios/` folder with format: `Symbol,Shares,Purchase Price,Date`

**Q: Crypto prices showing [n/a]?**  
A: Check internet connection. yfinance/CoinGecko need internet.

**Q: "OPENROUTER_API_KEY not set"?**  
A: The default key may be invalid. Get your own from https://openrouter.ai/keys

---

## 📚 Documentation

All static documentation moved to `docs/` folder:

- **[API Keys Guide](docs/API_KEYS.md)** - What you need (hint: not much!)
- **[Quick Start](docs/QUICK_START.md)** - Get running in 5 minutes
- **[Skills System](.claude/skills/SKILL.md)** - How the modular skills work
- **[Recommendations](docs/RECOMMENDATIONS.md)** - Active & historical picks
- **[Learnings](docs/LEARNINGS.md)** - Agent's learning log

---

## ⚠️ Disclaimer

**For educational/informational purposes only. Not financial advice.**  
Verify all recommendations with your broker before acting.  
The agent does NOT execute trades - it only analyzes and recommends.

---

**Built with**: Python, OpenRouter LLMs, Yahoo Finance, Finnhub, Tavily  
**Inspired by**: Claude Code's modular skills system  
**Philosophy**: Aggressive investing, lifelong learning, continuous improvement
