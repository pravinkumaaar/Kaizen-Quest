# Recommendation Tracker Skill#

## Description#
Manages investment recommendations: parsing, tracking performance (P&L), updating prices, and clearing/resetting.#

## When to Use#
- Storing high-conviction ideas (9+/10) in RECOMMENDATIONS.md#
- Updating prices and performance of tracked recommendations#
- Clearing active recommendations for fresh runs#
- Analyzing recommendation accuracy (win/loss ratio)#

## Instructions#

### 1. Parse and Store Recommendations#
**Trigger**: After generating investment ideas#

**Criteria for tracking**:#
- Conviction score ≥9/10 OR explicit "Track This: Yes"#
- Parse from investment ideas text#
- Extract: ticker, entry price, target, conviction, thesis#

**Store in RECOMMENDATIONS.md**:#
```markdown#
## Active Recommendations#

- 2026-04-23 | NVDA | $875.50 | $1,200 | 10/10 | Active | $890.20 | +1.7%#
- 2026-04-23 | SMCI | $750.20 | $950 | 9/10 | Active | $745.80 | -0.6%#
- 2026-04-22 | BTC-USD | $42,500 | $75,000 | 9/10 | Active | $43,200 | +1.6%#
```

### 2. Update Performance (P&L)#
**When**: Every run, BEFORE generating new ideas#

**Process**:#
1. Read RECOMMENDATIONS.md#
2. For each "Active" recommendation:#
   - Get current price (Finnhub → yfinance fallback)#
   - Calculate: `((current - entry) / entry) * 100`#
   - Update current price and performance#
   - If target hit (within 5%): Mark "Target Hit"#
   - If stop-loss triggered: Mark "Stop Loss"#

**Output**: Updated RECOMMENDATIONS.md with fresh P&L#

### 3. Clear Active Recommendations#
**When**: Start of EVERY run (fresh list each time)#

**Process**:#
1. Read RECOMMENDATIONS.md#
2. Keep file header/intro#
3. Replace "## Active Recommendations" section with fresh placeholder#
4. New ideas will be added after generation#

**Why**: Owner wants fresh list each run (no stale ideas)#

### 4. Analyze Accuracy#
**From memory/ratings**:#
- Calculate win rate (target: 90-95%)#
- Identify patterns in failed ideas#
- Learn: What made successful picks work?#
- Adjust: What should be avoided next time?#

## Output Format#

### Active Recommendations Section#
```markdown#
## Active Recommendations#

- 2026-04-23 | NVDA | $875.50 | $1,200 | 10/10 | Active | $890.20 | +1.7%#
- 2026-04-23 | SMCI | $750.20 | $950 | 9/10 | Active | $745.80 | -0.6%#
- 2026-04-22 | BTC-USD | $42,500 | $75,000 | 9/10 | Active | $43,200 | +1.6%#

*Updated: 2026-04-23 14:30 UTC*#
```

### Performance Summary (in LEARNINGS.md)#
```markdown#
## Recommendation Tracking Performance#

**Total Active**: 3#
**Winners**: 2 (+5% or more)#
**Losers**: 1 (-5% or more)#
**Win Rate**: 66.7% (target: 90-95%)#

**Lessons Learned**:#
- Crypto picks need wider stop-losses (volatility)#
- Tech stocks: Wait for earnings dip before adding#
- Conviction 10/10 ideas performing better than 9/10#
```

## Key Reminders#
- Only track 9+/10 conviction OR explicit "Track This: Yes"#
- Update prices BEFORE generating new ideas (avoid double-counting)#
- Clear active list EVERY run (fresh start)#
- Mark "Target Hit" when within 5% of target#
- Include in report: "Updated: [timestamp]"#
- Connect failures to learning (improve win rate)#
