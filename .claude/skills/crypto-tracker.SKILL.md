# Crypto Tracker Skill

## Description
Handles all cryptocurrency-related functionality: price tracking, market cap analysis, and crypto-specific investment ideas.

## When to Use
- Tracking BTC-USD, ETH-USD, XRP-USD in portfolio
- Getting crypto prices (yfinance + CoinGecko fallback)
- Analyzing crypto holdings in portfolio
- Generating crypto investment ideas

## Instructions

### 1. Fetch Crypto Prices
**NO API KEY NEEDED!** Both sources are free:
- **yfinance**: Primary source (BTC-USD, ETH-USD, XRP-USD)
- **CoinGecko API**: Fallback (no key required): `https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd`

### 2. Analyze Crypto Holdings
If portfolio contains crypto (BTC-USD, ETH-USD, etc.):
- Calculate current value and unrealized P&L
- Show in separate "🪙 Crypto Holdings Analysis" section
- Flag large positions (>10% of portfolio)

### 3. Crypto Investment Ideas
Generate crypto-specific ideas:
- **Bitcoin (BTC)**: Digital gold, institutional adoption
- **Ethereum (ETH)**: Smart contract king, DeFi backbone
- **Crypto crashes (50%+ drops)**: Generational buying opportunities
- **Bitcoin ETF approvals**: Institutional inflows catalyst

### 4. Once-in-a-Lifetime Crypto Plays
When market crashes:
- BTC down 50%+ = generational buy signal
- ETH down 60%+ = smart contract dominance play
- Market cap analysis: Compare to all-time highs

## Output Format

```markdown
## 🪙 Crypto Holdings Analysis

| Crypto | Shares | Cost Basis | Current Price | P&L |
|--------|--------|-----------|---------------|-----|
| BTC-USD | 0.5000 | $25,000 | $42,500 | +70.0% |
| ETH-USD | 5.0000 | $8,000 | $2,200 | -72.5% |

## 🚀 Crypto Opportunities

### Current Prices:
- BTC-USD: $42,500
- ETH-USD: $2,200
- XRP-USD: $0.52

### Once-in-a-Lifetime Plays:
1. **Bitcoin (BTC-USD)** - Digital gold, institutional adoption accelerating
2. **Ethereum (ETH-USD)** - Smart contract king, DeFi backbone
3. **Crypto crashes (50%+ drops)** - Generational buying opportunities
4. **Bitcoin ETF approvals** - Institutional inflows catalyst
```

## Key Reminders
- NO API key needed for crypto tracking!
- Always use -USD suffix (BTC-USD, not BTC)
- Flag crypto crashes as opportunities with 🚀
- Connect crypto trends to macro (inflation hedge, digital gold)
- Include in portfolio analysis if present
