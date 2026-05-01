# Market Sentiment Skill

## Description
Analyzes market conditions using VIX (fear/greed index), market breadth, and macro trends.

## When to Use
- Assessing market timing (buy/sell/hold)
- Generating macro context for investment ideas
- Deep-dive macroeconomic research
- Understanding Fed policy impacts

## Instructions

### 1. VIX Fear/Greed Assessment
Get VIX (^VIX) from yfinance:
- **<12**: EXTREME GREED → Take profits, trim positions, add hedges
- **12-16**: GREED → Steady accumulation, buy dips
- **16-20**: NEUTRAL → Stick to high-conviction ideas
- **20-30**: FEAR → Have dry powder, add on weakness
- **>30**: EXTREME FEAR → Contrarian buying opportunity

### 2. Market Breadth
Track major indices:
- SPY (S&P 500) - broad market
- QQQ (NASDAQ) - tech-heavy
- Calculate daily moves and trends

### 3. Macro Trends Deep-Dive
Current key themes to monitor:
1. **Federal Reserve Policy** - Rate cuts/pauses, inflation trajectory
2. **AI Infrastructure Boom** - Data centers, energy demand, chip race
3. **Geopolitical Tensions** - Trade wars, sanctions, supply chains
4. **Energy Transition** - Renewables vs fossil fuels, grid upgrades
5. **Demographic Shifts** - Aging populations, labor shortages

### 4. Investment Timing Context
Based on sentiment:
- **EXTREME GREED**: "Markets pricing in near-perfect outcomes. Complacency high. Action: Take profits, trim concentrated positions."
- **FEAR/EXTREME FEAR**: "Markets pricing in significant downside. Action: Contrarian positions for aggressive investors, have cash ready."

## Output Format

```markdown
## 🌡️ Market Sentiment & Timing

**VIX: 22.5 (FEAR)**

**Today's Market:**
- SPY: -1.2% @ $485.20
- QQQ: -1.8% @ $425.50

**Assessment:** Investors nervous but not panicked. Often creates opportunities for disciplined buyers.

**Action:** Have dry powder ready, add to high-conviction positions on weakness.

## 🌍 Macro Trends Deep-Dive

### Key Themes:
1. **Fed Policy**: Rate pause likely, inflation cooling
2. **AI Boom**: Infrastructure spending accelerating
3. **Geopolitics**: Trade tensions with China escalating

### Investment Implications:
- Buy dips in AI infrastructure (NVDA, SMCI)
- Avoid rate-sensitive sectors (real estate)
- Watch for China-exposed companies missing earnings
```

## Key Reminders
- Always include VIX number and category
- Connect sentiment to actionable investment advice
- Mention specific indices and their moves
- Link macro trends to portfolio implications
- Use emojis: 🌡️ for sentiment, 🌍 for macro
