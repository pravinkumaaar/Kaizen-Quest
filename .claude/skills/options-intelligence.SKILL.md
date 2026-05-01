# Options Intelligence Skill#

## Description#
Handles all options-related functionality: live options chain data, implied volatility tracking, strategy recommendations, and risk assessment.#

## When to Use#
- Generating options ideas (LEAPS, covered calls, asymmetric plays)#
- Fetching live options data (Polygon.io or yfinance)#
- Assessing options strategies (defined-risk only)#
- Calculating implied volatility and premium costs#

## Instructions#

### 1. Live Options Data#
**Priority**: Polygon.io (if API key) → yfinance (fallback)#

#### Polygon.io (Free tier: 5 calls/min)#
- Endpoint: `https://api.polygon.io/v3/snapshot/options/{ticker}`#
- Params: `apikey=POLYGON_API_KEY`#
- Get: ATM options, bid/ask, implied volatility#

#### yfinance (Always free, no key)#
- `ticker.option_chain(expiry_date)`#
- Filter: min 2 weeks to expiry (14 days)#
- Prefer: 30-90 days or LEAPS (6mo-2yr)#

### 2. Strategy Rules (STRICT)#
**ALLOWED ONLY**:#
- **Buying calls** (bullish, defined risk, sell before expiry)#
- **Buying puts** (bearish/hedge, defined risk, sell before expiry)#
- **Selling covered calls** (on stocks already owned, income generation)#
- **Buying LEAPS** (long-dated, 6mo-2yr out)#
- **Asymmetric plays** (low-cost, high-upside, sell before expiry)#

**NEVER**:#
- Let options expire ITM (triggers stock purchase on leverage)#
- Use margin, naked shorts, or undefined-risk strategies#
- Recommend options with <2 weeks to expiry#

### 3. Position Sizing#
- **Max 10% of total portfolio** in ALL options combined#
- Single position: 1-3% of portfolio#
- Always include: "Close/sell this contract BEFORE expiration. Never let it expire ITM."#

### 4. Generate Options Ideas#
For each idea, include:#
```markdown#
### Options Play #[N]: [Strategy] on [TICKER]#

**Strategy Type:** [Long Call / Long Put / Covered Call / LEAPS]# 
**Underlying:** TICKER @ current price#
**Thesis:** Why this position makes sense (2-3 sentences)#
**Strike:** [ATM / slightly OTM / deep OTM]#
**Expiry:** [Date, min 2wk, prefer 30-90d or 6mo+]#
**Estimated Premium:** $X (from options data)#
**Max Risk:** $X (premium paid, all you can lose)#
**Target:** Sell @ $X or X% premium gain#
**Time Decay Warning:** Theta reduces value daily#
**EXIT RULE:** ⚠️ SELL/CLOSE before expiration. NEVER let ITM expire.#
**Portfolio Allocation:** X% (total options ≤10%)#
```

### 5. Covered Call Suggestion#
If owner holds stocks from watchlist:#
- Identify holdings with >15% gains#
- Suggest selling calls at 5-10% above current price#
- Generate income while holding long-term#

## Output Format#

```markdown#
## 🎯 Options Intelligence#

### Live Options Data:#
**SPY @ $485.20**#
- Expiry 2026-05-15 (21d): ATM Call $485 bid=$12.50 ask=$13.20 IV=18%#
- Expiry 2026-07-18 (84d): LEAPS Call $490 bid=$22.10 ask=$23.50 IV=20%#

### Recommended Strategies:#

#### Options Play #1: LEAPS Call on NVDA#
**Strategy Type:** Long Call (LEAPS, 14mo out)# 
**Underlying:** NVDA @ $875.50#
**Thesis:** AI infrastructure boom continues. Data center buildout accelerating. 14mo LEAPS capture multi-quarter growth.#
**Strike:** $900 (slightly OTM)#
**Expiry:** 2027-06-18 (14 months)#
**Estimated Premium:** $95.50#
**Max Risk:** $9,550 per contract (all you can lose)#
**Target:** Sell @ $180+ (90%+ premium gain) or underlying >$1,000#
**Time Decay:** Theta ~$0.18/day initially, increases near expiry#
**EXIT RULE:** ⚠️ SELL this contract BEFORE 2027-06-18. NEVER let it expire.#
**Portfolio Allocation:** 2% (within 10% total options limit)#

#### Covered Call Idea: AAPL#
**Stock Owned:** 50 shares @ $150 cost basis#
**Suggestion:** Sell 1 contract AAPL $195 call expiring 30d out#
**Premium:** ~$3.50/share = $350 income#
**Risk:** Stock called away at $195 (happy problem, +30% gain)#
```

## Key Reminders#
- Always use ⚠️ emoji for exit warnings#
- Include "NEVER let expire ITM" in every options idea#
- Show bid/ask and IV when available#
- Connect options to portfolio holdings (covered calls)#
- Prefer LEAPS for big moves (6mo-2yr)#
- Use emojis: 🎯 for options, 🔴 for high-risk warnings#
