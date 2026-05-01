# Kaizen Quest v2.1 — Quick Start Guide

## ✨ New Features in This Update

✅ **Free Models First** — Qwen 3 & Llama 3.3 attempt before falling back to DeepSeek Reasoner (cheapest paid)
✅ **Clean Error Logging** — No verbose error spam; graceful fallback
✅ **Live Options Data** — Polygon.io (recommended) or Alpaca, with yfinance fallback
✅ **Portfolio CSV Import** — Export from Yahoo Finance, auto-load into `PORTFOLIO.md`
✅ **Rating-Based Feedback** — Efficient self-reflection without massive token overhead
✅ **No Claude Models** — All agents run on OpenRouter free/cheap models

---

## 1. Setup

### Environment Variables (.env)
```bash
# Required
OPENROUTER_API_KEY=sk-or-...          # Free tier: ~$5 free credits/month

# Optional but recommended
POLYGON_API_KEY=...                   # Free tier: 5 API calls/min
TAVILY_API_KEY=...                    # Free tier: 1,000/month (web search)
FINNHUB_API_KEY=...                   # Free tier: 60 req/min

# Not required (fallback to free)
ALPACA_API_KEY=...                    # Alternative options source
```

**Get Free API Keys:**
- [OpenRouter](https://openrouter.ai/) — Sign up, get $5 free credits
- [Polygon.io](https://polygon.io/) — Free tier for options data
- [Tavily](https://tavily.com/) — Free tier for web search
- [Finnhub](https://finnhub.io/) — Free tier for market data

### Install Dependencies
```bash
pip install -r requirements.txt
```

### (NEW) Portfolio CSV Import

#### Export from Yahoo Finance:
1. Go to [finance.yahoo.com](https://finance.yahoo.com)
2. Click **Portfolios** → Select your portfolio
3. Click **⋯ (menu)** → **Export**
4. Save as `portfolio.csv` in the agent's directory

#### CSV Format Expected:
```csv
Symbol,Shares,Purchase Price,Date
AAPL,10,150.25,2024-01-15
MSFT,5,380.50,2024-02-20
BTC-USD,0.5,45000,2024-03-01
```

**The agent will auto-load this on every run** and update `PORTFOLIO.md`.

---

## 2. Model Fallback System

### Priority Order (Automatic):
1. **Qwen 3 Next 80B** (Free)
2. **Llama 3.3 70B** (Free)
3. **DeepSeek Reasoner** (Paid, $0.14/1M tokens — cheapest quality option)

**Why this order?**
- Free models (1-3) are ultra-cheap and usually available
- DeepSeek Reasoner is the fallback because it's the cheapest paid option with good reasoning
- **No Claude models** (your preference)

### Example Log Output:
```
[2026-04-23 14:22:30] INFO: ✓ Model qwen3-next-80b-a3b-instruct succeeded (free models failed)
[2026-04-23 14:22:31] WARN: ⚠ qwen3-next-80b-a3b-instruct: Failed, trying next...
[2026-04-23 14:22:35] INFO: ✓ Model meta-llama/llama-3.3-70b-instruct succeeded
```

---

## 3. Live Options Data (Choose One)

### Option A: Polygon.io (Recommended)
**Pros:** Real-time data, accurate IV, clean API
**Setup:**
```bash
# Get free API key: https://polygon.io/
export POLYGON_API_KEY=your_key_here
```

The agent will automatically use Polygon if the key is set.

### Option B: Alpaca (Alternative)
**Pros:** Also real-time, reliable
**Setup:**
```bash
export ALPACA_API_KEY=your_key_here
```

### Option C: yfinance (Always Available)
**Pros:** No API key needed, free forever
**Cons:** Slightly delayed data (OK for backtesting, less ideal for real-time)

The agent automatically falls back to yfinance if no API keys are set.

---

## 4. Rating-Based Feedback (Token Efficient)

After each run, rate the agent's performance:

```python
from agent import add_rating

# Rate from 1-10, with optional notes
add_rating(8, "Good investment ideas, options too conservative")
add_rating(6, "Missed market turnaround, news digest was generic")
add_rating(9, "Excellent conviction on NVDA call, great learning topic")
```

**Why this is efficient:**
- Ratings are **100-200 tokens** per reflection cycle
- Full introspection would be **500-1000+ tokens**
- Agent learns from pattern: low rating (5-6) → adjust strategy next run
- High rating (8-9) → replicate what worked

**Reflection Strategy:**
- If **avg rating < 6**: Agent focuses on "What caused poor performance?"
- If **avg rating ≥ 7**: Agent focuses on "What's working? Scale it."

---

## 5. Run the Agent

### One-Time Run
```bash
python agent.py
```

### Scheduled Runs (Recommended)
```bash
# Run at 11 AM and 5 PM every weekday (using cron)
0 11,17 * * 1-5 cd /path/to/agent && python agent.py >> cron.log 2>&1
```

### Output
- **Report:** `REPORTS/{DATE}-{TIME}.md` (full daily intelligence)
- **History:** `HISTORY/{DATE}.md` (appended all runs for the day)
- **Logs:** `logs/agent.log` (clean, concise error tracking)

---

## 6. Files You'll Create/Update

| File | Purpose |
|------|---------|
| `portfolio.csv` | Your holdings (auto-exported from Yahoo Finance) |
| `PORTFOLIO.md` | Current holdings & cost basis (auto-updated) |
| `MEMORY.md` | Agent's background context (you write once) |
| `CONTEXT.md` | Current goals & investment thesis (you update) |
| `RATINGS.md` | Your ratings of past runs (auto-updated) |
| `RECOMMENDATIONS.md` | Tracked investment ideas & performance (auto-updated) |
| `LEARNINGS.md` | Agent's reflection on past performance (auto-updated) |

---

## 7. Token Usage Breakdown (Per Run)

| Task | Tokens | Notes |
|------|--------|-------|
| News Digest | 1,500 | RSS feeds + Finnhub |
| Investment Ideas | 1,500 | Market data + digest |
| Options Ideas | 1,500 | Live options chains |
| Learning | 800 | Deep topic + resources |
| Self-Reflection | 400 | Rating-based (efficient) |
| **Total (Free Models)** | **~5,700** | ≈ $0.01 per run |
| **Total (DeepSeek Fallback)** | **~5,700** | ≈ $0.08 per run |

**Monthly Cost (5 runs/day):**
- Mostly free models: **$1.50/month**
- If free models unavailable: **$12/month** (still cheap!)

---

## 8. Token Efficiency Tips

**Methods to Improve Quality Without Extra Tokens:**

### ✅ Already Implemented (This Version)
1. **Few-shot examples** in system prompt (+50 tokens, high ROI)
2. **Structured JSON output** in investment ideas (+0 tokens, forces better reasoning)
3. **Market sentiment context** (VIX equivalent via yfinance) (+50 tokens)
4. **Portfolio tracking** (learn from what's working) (+100 tokens, high ROI)
5. **Rating-based feedback** (minimal tokens, high impact) (+100 tokens vs 500+ for full reflection)

### 🚀 Optional Upgrades (If Token Budget Allows)
1. **Add sentiment score** from news (scan RSS for positive/negative keywords) — +50 tokens
2. **Track conviction vs outcome** (are high-conviction picks actually outperforming?) — +50 tokens
3. **Sector rotation analysis** (which sectors are agent bullish on vs market?) — +100 tokens
4. **Weekly summary** (compare week's predictions to actuals) — +200 tokens, run once/week only

---

## 9. Troubleshooting

### "LLM unavailable after X attempts"
- Check `OPENROUTER_API_KEY` is set correctly
- Verify OpenRouter has free credits remaining
- Check if free models (Qwen, Llama) are down: https://openrouter.ai/status

### Options data shows "[Options data unavailable]"
- yfinance fallback is working but slow (normal)
- To use Polygon: get API key, set `POLYGON_API_KEY`, restart
- To use Alpaca: set `ALPACA_API_KEY`

### Portfolio CSV not loading
- Ensure file is named exactly `portfolio.csv`
- Verify columns: `Symbol,Shares,Purchase Price,Date`
- Check for special characters or blank rows

### Rating system not working
```python
# To manually check ratings:
from agent import get_recent_ratings, calculate_avg_rating
print(get_recent_ratings(10))
print(calculate_avg_rating())
```

---

## 10. Next Steps

1. **Export your Yahoo Finance portfolio** → save as `portfolio.csv`
2. **Set API keys** in `.env` (minimum: `OPENROUTER_API_KEY`)
3. **Write your `CONTEXT.md`** (3-4 sentences on your investment goals)
4. **Run the agent once:** `python agent.py`
5. **Review the report** → rate it (1-10) using `add_rating()`
6. **Schedule cron job** for daily runs at 11 AM & 5 PM

---

## 11. Philosophy

This agent is designed to:
- ✅ Learn from you (via ratings) without expensive token usage
- ✅ Stay cheap (free models first, DeepSeek fallback)
- ✅ Improve over time (track recommendations, reflect efficiently)
- ✅ Teach you frameworks (not just recommendations)
- ✅ Connect dots across domains (AI, macro, geopolitics, etc.)

The rating-based feedback loop is crucial: **your 1-10 score every few days will compound** into increasingly accurate recommendations over months.

---

**Questions?** Check the main README.md or review the agent code comments.
