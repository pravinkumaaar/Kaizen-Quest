# 📊 Dynamic Watchlist System - User Guide

## How the New Watchlist Works

Your agent now automatically creates a **personalized watchlist** based on YOUR actual holdings, plus key indices and crypto.

### The Watchlist Structure

Each report now shows:

```
## 📊 Market Snapshot

  [📊 Your Portfolio]        ← Your actual holdings from portfolio.csv
    NVDA       $202.50  ▲1.31%
    AAPL       $273.17  ▲2.63%
    MSFT       $432.92  ▲2.07%
    SPY        $450.00  ▲0.97%
    QQQ        $600.00  ▲1.67%
    BTC-USD    $65000.00  ▲2.5%
    GLD        $435.26  ▲1.32%
    TSLA       $180.00  ▲0.28%

  [Indices]               ← Market context
    SPY        $711.21  ▲1.01%
    QQQ        $655.11  ▲1.67%
    IWM        $276.48  ▲0.72%
    VTI        $351.22  ▲0.97%

  [Tech]                  ← Tech sector (for research)
    NVDA       $202.50  ▲1.31%
    MSFT       $432.92  ▲2.07%
    ... etc ...

  [Alt/Hedge]             ← Crypto and precious metals
    GLD        $435.26  ▲1.32%
    SLV        $70.37   ▲2.74%
    BTC-USD    $65000.00  [working now!]
    ETH-USD    $3500.00   [working now!]
```

---

## 📝 Customizing Your Portfolio

### Option 1: Manual `portfolio.csv` Update

**Edit:** `portfolio.csv`

Format:
```csv
Symbol,Shares,Purchase Price,Date,Notes
NVDA,50,200.00,2026-01-15,AI Infrastructure
AAPL,100,150.00,2026-02-01,Core Holdings
```

**Columns:**
- `Symbol` - Ticker (required)
- `Shares` - Number of shares (required)
- `Purchase Price` - Entry price in $/share (required)
- `Date` - When you bought (optional, for tracking)
- `Notes` - Why you own it (optional, helps context)

**Instructions:**
1. Export your portfolio from Yahoo Finance as CSV
2. Keep these columns: Symbol, Shares, Purchase Price
3. Paste into `portfolio.csv`
4. Run agent - it auto-loads on startup

### Option 2: Auto-Load from Yahoo Finance

(Coming soon: Direct Yahoo Finance API integration)

---

## 🔧 How the Agent Uses Your Portfolio

1. **On startup:** Loads `portfolio.csv` and displays holdings count
   ```
   ✓ Loaded portfolio: 8 holdings, $259,500 cost basis
   ```

2. **Market data fetch:** Creates dynamic watchlist section
   - Shows YOUR holdings with real-time prices
   - Includes % change from previous close
   - Falls back to multiple data sources (Finnhub → yfinance)

3. **Investment ideas:** Agent considers your holdings
   - Avoids suggesting something you already own (usually)
   - Analyzes performance of your positions
   - Suggests complementary moves

4. **Options ideas:** References your portfolio
   - Suggests covered calls on stocks you hold
   - Hedge strategies based on your exposure

---

## 🚀 Sample Portfolio (Included)

The agent comes with a sample `portfolio.csv`:

| Symbol | Shares | Price | Cost Basis | Purpose |
|--------|--------|-------|-----------|---------|
| NVDA | 50 | $200 | $10,000 | AI Infrastructure |
| AAPL | 100 | $150 | $15,000 | Core Tech |
| MSFT | 75 | $350 | $26,250 | AI & Cloud |
| SPY | 200 | $450 | $90,000 | Broad Market |
| QQQ | 100 | $600 | $60,000 | Tech-Heavy Index |
| BTC-USD | 0.5 | $65,000 | $32,500 | Crypto Allocation |
| GLD | 50 | $425 | $21,250 | Inflation Hedge |
| TSLA | 25 | $180 | $4,500 | EV & Energy |

**Total Cost Basis: $259,500**

---

## ✅ Watchlist Features

### Real-Time Updates
- Prices refresh on each agent run
- % change calculated from previous close
- Arrows show direction: ▲ green, ▼ red

### Multiple Data Sources (Fallback Chain)
1. **Finnhub** (if API key set) - Good for stocks, limited for crypto
2. **yFinance** (free fallback) - Works for everything including crypto
3. **Error handling** - Shows `[n/a - will retry]` instead of failing silently

### Crypto Support
- Now supports BTC-USD, ETH-USD, and any crypto ticker
- Falls back automatically if one source fails
- Shows real prices instead of just `[n/a]`

---

## 🎯 Investment Ideas Integration

After your agent generates investment ideas, it learns from your existing holdings:

**Example:** If you already hold NVDA, the agent might:
- Suggest a covered call for income generation
- Avoid recommending NVDA again
- Suggest complementary positions (ASML, TSMC, ARM)
- Analyze how NVDA is performing vs initial thesis

---

## 📈 Recommendation Tracking

The agent tracks your holdings vs recommendations:

File: `RECOMMENDATIONS.md`

```
- 2026-04-22 | NVDA | $200 | $300 | 9/10 | Active | $202.50 | +1.3%
- 2026-04-22 | SPY  | $450 | $520 | 8/10 | Active | $451.21 | +0.3%
```

Every run, the agent updates:
- Current price
- Performance % since recommendation
- Status (Active/Target Hit/Stop Loss)
- Helps you track ROI on agent ideas

---

## 💡 Pro Tips

1. **Use realistic holdings**: The more accurate your `portfolio.csv`, the better the agent's suggestions
2. **Update dates**: Include purchase dates so agent understands holding period
3. **Add notes**: Your "why" helps the agent give better ideas
4. **Regular rebalancing**: Let the agent see when you're adding/removing positions
5. **Cost basis matters**: Accurate cost basis helps calculate realized gains/losses

---

## 🔄 Next Steps

1. **Update `portfolio.csv`** with your actual holdings
2. **Run the agent**: `python3 agent.py`
3. **Check the Market Snapshot** - should show YOUR portfolio first
4. **Watch for crypto prices** - BTC-USD and ETH-USD should resolve now

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| `portfolio.csv: No such file` | File missing | Create it (see template above) |
| Holdings not showing | Wrong CSV format | Check Symbol, Shares, Purchase Price |
| `[n/a]` for crypto | Fallback failed | Agent will retry, check logs |
| Holdings showing but no prices | API rate limit | Wait, agent retries on next run |
| Cost basis wrong | CSV parsing error | Verify no extra spaces in numbers |

---

*Your portfolio is now the center of your personalized intelligence agent. The watchlist adapts to YOU, not the other way around.*
