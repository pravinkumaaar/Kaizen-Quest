# 🔑 API Keys Setup Guide

## Required Keys (Free Tiers)

### OpenRouter (LLM Models)
- **URL**: https://openrouter.ai/keys
- **Free credits**: $5-10 free credit on signup
- **Env vars**: `OPENROUTER_API_KEY`
- **Used for**: All LLM calls (news, analysis, recommendations)

### Finnhub (Market Data)
- **URL**: https://finnhub.io/register
- **Free tier**: 60 calls/min, 10,000 calls/month
- **Env vars**: `FINNHUB_API_KEY`
- **Used for**: Stock quotes, market news, earnings data

### Tavily (Web Search)
- **URL**: https://app.tavily.com
- **Free tier**: 1,000 searches/month
- **Env vars**: `TAVILY_API_KEY`
- **Used for**: Deep web research, news analysis

## Optional Keys (Free Tiers)

### Alpaca (Paper Trading)
- **URL**: https://alpaca.markets (create paper trading account)
- **Free tier**: Unlimited paper trading
- **Env vars**: `ALPACA_API_KEY`, `ALPACA_SECRET_KEY`
- **Used for**: Executing paper trades, tracking performance

### ClickUp (Task Management & UI)
- **URL**: https://clickup.com (free tier)
- **Free tier**: Unlimited tasks, 100MB storage
- **Env vars**: `CLICKUP_API_KEY`, `CLICKUP_LIST_ID`
- **Used for**: Recommendation tracking, notifications, dashboard UI

### Polygon.io (Options Data) - Optional
- **URL**: https://polygon.io/dashboard/signup
- **Free tier**: 5 API calls/min
- **Env vars**: `POLYGON_API_KEY`
- **Used for**: Live options chain data

## How to Set Environment Variables

### Option 1: Export in terminal (temporary)
```bash
export OPENROUTER_API_KEY="sk-or-v1-..."
export FINNHUB_API_KEY="..."
export TAVILY_API_KEY="tvly-dev-..."
export ALPACA_API_KEY="..."
export ALPACA_SECRET_KEY="..."
export CLICKUP_API_KEY="..."
export CLICKUP_LIST_ID="..."
```

### Option 2: Add to ~/.zshrc (permanent)
```bash
echo 'export OPENROUTER_API_KEY="sk-or-v1-..."' >> ~/.zshrc
echo 'export FINNHUB_API_KEY="..."' >> ~/.zshrc
# ... etc for each key
source ~/.zshrc
```

### Option 3: Use .env file (recommended)
Create a `.env` file in the project root:
```
OPENROUTER_API_KEY=sk-or-v1-...
FINNHUB_API_KEY=...
TAVILY_API_KEY=tvly-dev-...
ALPACA_API_KEY=...
ALPACA_SECRET_KEY=...
CLICKUP_API_KEY=...
CLICKUP_LIST_ID=...
```

## Key Rotation Schedule

- **OpenRouter**: Check balance monthly at https://openrouter.ai/credits
- **Tavily**: Resets monthly (1,000 searches)
- **Finnhub**: Resets monthly (10,000 calls)
- **Alpaca**: No limits on paper trading
- **ClickUp**: No limits on free tier