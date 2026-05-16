# Portfolio Analysis Skill

## Description
Deep analysis of portfolio holdings, weightings, concentration risk, and rebalancing suggestions.

## When to Use
- Analyzing current portfolio positions
- Calculating weightings and concentration risk
- Suggesting rebalancing opportunities
- Generating SELL/REDUCE/HOLD recommendations
- Finding once-in-a-lifetime opportunities

## Instructions

### 1. Import and Consolidate Portfolios
- Read all CSVs from `portfolios/` folder (portfolio1-4.csv)
- Auto-discover files if not specified
- Consolidate duplicate tickers with weighted average cost basis
- Calculate total cost basis and unique tickers

### 2. Analyze Weightings
- Calculate each holding's % of total portfolio
- Sort by portfolio % (descending)
- Identify top 5 positions and their concentration ratio
- Assess risk: HIGH (>60%), MODERATE (40-60%), LOW (<40%)

### 3. Get Current Prices & P&L
- Use Finnhub API for stocks (if key available)
- Fallback to yfinance for all assets (including crypto)
- Calculate unrealized gains/losses
- Track day-to-day movements

### 4. Generate Rebalancing Suggestions
**SELL Recommendations** (for overvalued/risky):
- Positions >25% of portfolio → Reduce to 15-20%
- Losers with broken thesis → SELL completely
- Winners >50% gain AND >15% portfolio → Take partial profits

**BUY Recommendations** (for underweight sectors):
- Identify sectors missing from portfolio
- Suggest additions to balance exposure
- Look for once-in-a-lifetime opportunities:
  - VIX >30 (extreme fear) = generational buys
  - Crypto crashes (50%+ drops)
  - Sector rotations (30%+ declines with intact fundamentals)

### 5. Portfolio-Aware Investment Ideas
When generating investment ideas:
- Analyze underweight sectors in current holdings
- Suggest additions to weak areas
- Recommend taking profits on overweight positions
- Include at least ONE once-in-a-lifetime opportunity if portfolio concentration >60%

## Output Format

### Portfolio Analysis Summary
```markdown
**Portfolio Analysis (N holdings):**

- Total Cost Basis: $XXX,XXX
- Top 5 positions: XX.X% of portfolio
- Concentration risk: HIGH/MODERATE/LOW

| Ticker | % of Portfolio | Current Price | Today's Move | Unrealized P&L |
|--------|----------------|---------------|--------------|----------------|
| AAPL   | 25.3%          | $185.20        | +1.2%         | +15.3%          |
...

## 🎯 Portfolio Rebalancing Assessment

**⚠️ HIGH CONCENTRATION RISK:** Top 5 = 68%
**Action: SELL/REDUCE** the following:
- AAPL: 25.3% → Target 15% (SELL 40% of position)
- MSFT: 18.7% → Target 15% (SELL 20% of position)

**🔴 LOSING POSITIONS (3):**
- XYZ: -22.5% | 8% of portfolio → Reassess thesis, consider SELL
...

## 🚀 ONCE-IN-A-LIFETIME OPPORTUNITIES
- Extreme fear (VIX >30): Buy quality stocks at deep discounts
- Sector rotation: When a sector is down 30%+ but fundamentals intact
- Crypto crashes: BTC/ETH down 50%+ = generational buys
```

## Key Reminders
- Always include specific tickers and percentages
- Explain WHY a position should be sold/reduced
- Connect rebalancing to investment thesis
- Flag extreme opportunities with 🚀
- Be direct: use SELL/BUY/HOLD explicitly
