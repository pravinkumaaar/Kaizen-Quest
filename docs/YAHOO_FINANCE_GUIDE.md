# 📊 Yahoo Finance Portfolio Integration Guide

This guide explains how to link your Yahoo Finance portfolio to your AI agent so it learns from your trading history and makes personalized recommendations.

---

## 🔗 Step 1: Get Your Portfolio Data from Yahoo Finance

### Manual Export Method
1. Go to [Yahoo Finance](https://finance.yahoo.com)
2. Click on your **Portfolio** section
3. For each holding, you'll see:
   - **Symbol** (ticker): AAPL, NVDA, SPY, etc.
   - **Shares/Units**: How many shares you own
   - **Avg Cost**: Your average purchase price
   - **Current Value**: Market value today
   - **Gain/Loss**: Unrealized P&L

### What You Need to Record
- **Ticker**: The stock symbol
- **Shares**: Number of shares owned
- **Avg Cost**: Average cost per share (price you paid)
- **Current Value**: Today's market value
- **Unrealized P/L**: Your gain or loss (can calculate as: Current Value - (Shares × Avg Cost))

---

## ✏️ Step 2: Update Your PORTFOLIO.md File

Open `PORTFOLIO.md` in your workspace and fill it out. The format is simple:

### Example Portfolio (update with YOUR holdings):

```
# 📈 My Yahoo Finance Portfolio
# Update this file with your current holdings from Yahoo Finance
# Format: Ticker | Shares | Avg Cost | Current Value | Unrealized P/L

## Current Holdings
AAPL | 100 | 150.00 | 175.00 | +$2,500
NVDA | 50 | 200.00 | 220.00 | +$1,000
SPY | 200 | 450.00 | 510.00 | +$12,000
MSFT | 25 | 300.00 | 380.00 | +$2,000
BTC-USD | 0.5 | 45000.00 | 52000.00 | +$3,500

## Recent Trades
- 2026-04-20: Bought 50 NVDA @ $200
- 2026-04-15: Sold 100 SPY @ $508 (+3.5%)
- 2026-04-10: Bought 25 MSFT @ $300

## Portfolio Goals
- Growth-focused with 70% equities, 20% crypto, 10% cash
- Risk tolerance: Aggressive (hold through -20% dips if thesis intact)
- Target allocation: 40% Tech, 30% Indices, 20% Crypto, 10% Metals
```

### Key Tips:
- **Keep it updated**: After every trade, add the transaction
- **Be accurate**: Avg Cost affects performance calculations
- **Include all positions**: Every holding, crypto, metals, etc.
- **Use actual values**: Don't approximate

---

## ⭐ Step 3: Rate the Agent's Recommendations

After each agent run, rate how good the recommendations were in `RATINGS.md`:

### How to Rate (1-10 scale):

**10 = Excellent** 
- Insights were novel and actionable
- Good mix of deep dives and quick hits  
- Recommendations align with your portfolio
- Learned from past performance

**7-9 = Good**
- Solid analysis, some areas could be deeper
- Options ideas had good setups
- Learning section was useful

**4-6 = Average**
- Basic but nothing special
- Some useful intel, but repetitive
- Recommendations felt generic

**1-3 = Poor**
- Missed obvious signals
- Data was old/inaccurate
- Options ideas were risky or unworkable

### Example Ratings Entry:

```markdown
## Recent Ratings

- 2026-04-22-1736: 8/10 - Great market analysis, good conviction scores, but options data was 2 years old
- 2026-04-21-1630: 7/10 - Solid investment ideas, learning section was weak
- 2026-04-20-1515: 9/10 - Nailed the AI infrastructure theme, perfect entry points suggested
- 2026-04-19-1445: 5/10 - Generic recommendations, didn't use portfolio context

## Average Rating: 7.3/10

## Agent's Self-Improvement Notes
- Agent analyzes these ratings to learn patterns
- If options consistently score low, agent improves that section
- If portfolio-aware suggestions score high, agent uses more portfolio context
- Tracks which recommendation themes perform best
```

---

## 🎯 Step 4: Track Recommendations Over Time

The agent automatically logs its "best ideas" in `RECOMMENDATIONS.md`. This file tracks:

### What Gets Tracked
- **Conviction Score** (1-10): How confident the agent is
- **Entry Price**: What price it recommended at
- **Target**: Where the agent thinks it's going
- **Current Price**: Updated daily by the agent
- **Performance**: Gain/loss since recommendation
- **Status**: Active, Target Hit, Stopped Out, or Archived

### Example Tracking:

```markdown
## Active Recommendations
- 2026-04-22 | NVDA | $202.50 | $300 | 9/10 | Active | $202.50 | 0%
- 2026-04-22 | SMCI | $85 | $150 | 8/10 | Active | $85 | 0%
- 2026-04-20 | QQQ | $640 | $700 | 7/10 | Active | $655 | +2.3%

## Historical Performance
- 2026-04-15 | TSLA | $180 | $250 | 6/10 | Stopped | $165 | -8.3%
- 2026-04-10 | AAPL | $270 | $320 | 8/10 | Target Hit | $320 | +18.5%
```

---

## 🧠 How the Agent Learns

### From Your Portfolio:
1. Agent sees your holdings (PORTFOLIO.md)
2. Identifies which recommendations YOU acted on
3. Tracks their performance
4. Learns your winners vs. losers
5. Adjusts conviction scores based on patterns

### From Your Ratings:
1. You rate each report 1-10 (RATINGS.md)
2. Agent sees patterns: "High ratings when I focus on X"
3. Agent learns to repeat what works
4. Agent drops what doesn't resonate

### From Recommendation Tracking:
1. Agent makes predictions (RECOMMENDATIONS.md)
2. Market moves daily
3. Agent tracks performance automatically
4. Agent learns: "My 9/10 calls hit 85% of the time, my 5/10 calls only 40%"
5. Agent uses this to improve conviction scores

---

## 📊 Real Example: How Learning Works

### Day 1: Agent makes recommendation
```
NVDA @ $200 | Target $300 | Conviction 9/10 | "AI infrastructure leader, high conviction"
```

### Days 2-10: Market moves
```
Day 2: NVDA $202 | Day 5: NVDA $215 | Day 10: NVDA $220 (↑10%)
```

### You rate the recommendation
```
RATINGS.md: 9/10 - "Great call, conviction score was right. Held through the dips"
```

### Next run: Agent learns
- "My 9/10 conviction calls had 85% accuracy last month"
- "Portfolio holder followed this recommendation and is +18% YTD"
- "Focus on infrastructure theme = high satisfaction"

### Next recommendation:
```
SMCI @ $85 | Target $150 | Conviction 9/10 | "Similar infrastructure theme, similar pattern recognition"
```

---

## 🔄 Update Frequency

### Update PORTFOLIO.md:
- **After every trade** (buy/sell)
- **Weekly** at minimum (even if no trades)
- **Monthly** for rebalancing tracking

### Rate RATINGS.md:
- **After each agent run** (daily if you run it daily)
- Takes 30 seconds: just the score + 1-line comment
- Don't overthink it - gut feeling is fine

### RECOMMENDATIONS.md:
- **Agent updates automatically daily**
- You don't need to touch it
- But review it weekly to understand patterns

---

## ⚙️ Advanced: Linking to Yahoo Finance API (Optional)

If you want to automate portfolio pulling (advanced):

1. Yahoo Finance stopped providing public API access
2. Alternative: Use `yfinance` library (already installed)
3. Could write a script to auto-fetch your holdings
4. For now: Manual updates are fine and give you control

---

## ❓ Troubleshooting

### Problem: Agent not using my portfolio?
- **Check**: Is PORTFOLIO.md in the right place?
- **Check**: Is the format correct (Ticker | Shares | Avg Cost | Current | P/L)?
- **Solution**: Run agent again, should see portfolio in memory

### Problem: Ratings not affecting recommendations?
- **Normal**: Takes 5-10 runs to see patterns
- **Check**: Are you rating consistently? (scale of 1-10?)
- **Solution**: Rate 5 reports, then agent will adjust

### Problem: Recommendations tracking not working?
- **Check**: Are you marking recommendations "Track This: Yes" in reports?
- **Check**: Do recommendations have tickers (NVDA, AAPL, etc.)?
- **Solution**: Agent should auto-track high-conviction ideas

---

## 💡 Pro Tips

1. **Be consistent with ratings**: If you rate 8/10 for good analysis, don't rate 5/10 later for the same thing
2. **Add context in ratings**: "8/10 - loved the AI thesis, but options data felt stale"
3. **Update portfolio weekly**: Helps agent track your actual performance
4. **Trust conviction scores**: If agent says 9/10, it usually means "hold through dips"
5. **Review recommendations monthly**: See which themes actually worked for you
6. **Keep recent trades in portfolio**: Helps agent learn your recent thinking

---

## 📚 Related Files

- `PORTFOLIO.md` - Your holdings (update manually)
- `RATINGS.md` - Rate each run (takes 30 seconds)
- `RECOMMENDATIONS.md` - Agent tracks predictions (updates automatically)
- `LEARNINGS.md` - Agent's insights from ratings + portfolio (auto-updated)
