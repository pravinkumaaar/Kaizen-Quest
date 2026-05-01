# 🤖 Personal AI Agent v2

Self-running intelligence system. Runs 5x/day in the cloud for **$0/month**.
Fetches news, generates long-term investment ideas, options opportunities,
and daily learning recommendations. Gets smarter over time via memory files.

**NEW FEATURES:**
- 📊 **Recommendation Tracking:** Agent tracks its best ideas over time, monitors performance
- 🎯 **Conviction Scoring:** High-confidence ideas get held through temporary dips  
- 📈 **Portfolio Integration:** Learns from your Yahoo Finance holdings
- ⭐ **Rating System:** Rate runs 1-10, agent learns to improve accuracy toward 90-95% win rate

---

## 💰 Cost Breakdown

| Component | Cost |
|---|---|
| GitHub repo + Actions (5x/day) | **FREE** |
| OpenRouter — Qwen 3 235B (primary LLM) | **FREE** |
| OpenRouter — Llama 3.3 70B (fallback LLM) | **FREE** |
| Tavily web search (1,000/month) | **FREE** |
| Finnhub market news (60/min) | **FREE** |
| yfinance stocks + options data | **FREE** |
| RSS feeds (50+ sources) | **FREE** |
| **Total** | **$0/month** |

**Upgrade when ready:** Add $5 to OpenRouter → set model to `deepseek/deepseek-chat`
for noticeably sharper analysis (~$1-2/month at 5 runs/day).

---

## 🚀 Quick Setup (Mac)

```bash
# 1. Clone your GitHub repo and enter it
git clone https://github.com/YOUR_USERNAME/my-ai-agent.git
cd my-ai-agent

# 2. Run the automated setup script
bash setup.sh

# 3. Add your API keys to .env
#    (setup.sh creates .env from the template)

# 4. Test it locally
python3 agent.py

# 5. Push to GitHub
git add . && git commit -m "Initial setup" && git push
```

---

## � Key Files

| File | Purpose |
|---|---|
| `agent.py` | Main orchestrator |
| `MEMORY.md` | Permanent owner profile & preferences |
| `CONTEXT.md` | Current goals & market thesis |
| `LEARNINGS.md` | Agent's self-improvements over time |
| `RECOMMENDATIONS.md` | **NEW:** Tracks recommendation performance |
| `PORTFOLIO.md` | **NEW:** Your Yahoo Finance holdings |
| `RATINGS.md` | **NEW:** Rate agent runs 1-10 for learning |
| `REPORTS/` | Daily intelligence reports |
| `HISTORY/` | Full run archives |

---

## 🎯 Using the New Features

### Portfolio Integration
1. Open `PORTFOLIO.md`
2. Add your current holdings from Yahoo Finance:
   ```
   AAPL | 100 | 150.00 | 175.00 | +$2,500
   NVDA | 50 | 200.00 | 220.00 | +$1,000
   ```
3. Agent will learn from your winners/losers

### Rating the Agent
After each run, rate the report in `RATINGS.md`:
```
2024-04-22-1808: 8/10 - Great analysis, but missed crypto trends
```
Agent analyzes patterns to improve.

### Recommendation Tracking
- Agent automatically tracks ideas marked "Track This: Yes"
- Monitors prices daily, calculates performance
- Learns from successes/failures for higher accuracy

---

| Key | Where to get it | Time |
|---|---|---|
| `OPENROUTER_API_KEY` | openrouter.ai → Sign up → Keys | 2 min |
| `TAVILY_API_KEY` | tavily.com → Sign up | 2 min |
| `FINNHUB_API_KEY` | finnhub.io → Sign up | 2 min |

**Add them in two places:**
1. Your local `.env` file (for running on your Mac)
2. GitHub repo → Settings → Secrets → Actions (for cloud runs)

---

## 📁 Project Structure

```
agent.py                      ← Main agent (runs everything)
setup.sh                      ← One-time Mac setup script
requirements.txt              ← Python packages
.env.example                  ← Copy to .env, add your keys
CLAUDE.md                     ← Agent brain + investment rules
MEMORY.md                     ← Your permanent profile (edit anytime)
CONTEXT.md                    ← Current goals (update periodically)
LEARNINGS.md                  ← Auto-updated by agent after each run

REPORTS/                      ← Daily reports (auto-generated)
HISTORY/                      ← Full archives by date
logs/                         ← Run logs

.claude/
  settings.json               ← Agent permissions config (optional)
  skills/
    news-researcher/          ← Deep web research skill
    investment-analyst/       ← Full ticker analysis skill
    options-scout/            ← Options opportunity scanner
    learning-curator/         ← Learning path builder
    self-improver/            ← Agent performance reviewer
    report-writer/            ← Custom report generator
    data-fetcher/             ← Data source debugger

.github/workflows/
  daily-agent.yml             ← Runs agent 5x/day automatically
```

---

## 📊 What Each Report Contains

Every run generates a report in `REPORTS/YYYY-MM-DD-HHMM.md`:

1. **Market Snapshot** — Live prices for SPY, QQQ, NVDA, BTC, GLD, and more
2. **News Digest** — AI/tech, markets, geopolitics, science — signal, not noise
3. **3 Investment Ideas** — Long-term/swing plays with entry, target, stop-loss, thesis
4. **2 Options Ideas** — LEAPS, asymmetric plays, covered calls (rules strictly enforced)
5. **Learning Topic** — Deep dive with books, videos, and a hands-on challenge
6. **Self-reflection** — Agent notes what worked and updates LEARNINGS.md

---

## ⚠️ Investment Rules (Hard-Coded, Never Violated)

- **No intraday trades** — minimum 2-week hold, prefer months to years
- **Options minimum expiry: 2 weeks** — prefer 30-90 days or LEAPS (6mo-2yr)
- **Options budget: max 10% of portfolio**
- **Defined risk only** — no naked options, no margin, no leverage
- **ALWAYS sell options before expiry** — never let ITM options expire
- **No position > 20% of portfolio**

---

## 🧠 Interactive Use (Optional — requires Claude Pro)

The `.claude/skills/` folder contains skill files that work with Claude Code,
which is a paid feature requiring Claude Pro ($20/month). **You don't need this
to run the agent** — it's a nice-to-have for when you want to chat with the
agent interactively on your laptop.

If you later subscribe to Claude Pro, you can install Claude Code with:
```bash
npm install -g @anthropic-ai/claude-code
claude  # log in with your Pro account
```

Then use it like: `Analyze NVDA` or `Find options opportunities on SPY`.

---

## 🔧 Customizing the Agent

**Change what stocks it watches:**
Edit `WATCHLIST` dict in `agent.py`

**Add a new news source:**
Edit `RSS_FEEDS` dict in `agent.py` — add any RSS URL

**Change run frequency:**
Edit `.github/workflows/daily-agent.yml` — adjust the cron lines

**Update your goals:**
Edit `CONTEXT.md` directly in GitHub (click file → pencil icon)

**Upgrade to DeepSeek (sharper analysis, ~$2/month):**
In GitHub Secrets, change `OPENROUTER_MODEL` to `deepseek/deepseek-chat`

---

## 🆘 Troubleshooting

| Problem | Fix |
|---|---|
| GitHub Actions failing | Actions tab → click failed run → read the log |
| "API key not set" error | Check GitHub Secrets — names must match exactly |
| RSS feed returning nothing | That URL changed — find new one or remove it |
| Options data empty | Weekend/holiday — normal, try weekday |
| LLM timeout | Free models have rate limits — wait a few minutes |
| `pip install` fails | Run `pip3 install -r requirements.txt` again |

---

## 📈 Upgrade Path

Once it's working and you want better output:

1. **$5 on OpenRouter** → switch to `deepseek/deepseek-chat` (best value paid model)
2. **Add email delivery** → get reports in your inbox each morning
3. **Add Discord webhook** → post summaries to your phone
4. **Add portfolio tracker** → log your actual trades, track vs recommendations
5. **Claude Max ($100/mo)** → use `claude-sonnet-4-5` for significantly better analysis

---

*Built with Python, OpenRouter (Qwen 3 free), Tavily, Finnhub, yfinance, GitHub Actions*
*Total cost: $0/month to start*
