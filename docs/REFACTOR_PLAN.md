# 🔧 Agent Refactoring & Reorganization Plan

## Current Issues Identified

1. **Imports & Dependencies**
   - `yfinance` (yf): ✅ ACTIVELY USED - fetching stock/crypto prices, options data
   - `OpenAI`: ✅ ACTIVELY USED - creating LLM client for OpenRouter
   - `dotenv`: ✅ ACTIVELY USED - loading API keys from .env file
   - ✅ All three imports are necessary and being used correctly

2. **Repository Structure** (Too many .md files in root!)
   ```
   Current:  26 .md files in root directory (cluttered)
   Problem:  Hard to navigate, mixed docs/config/output
   
   Solution: Organize into:
   - docs/ → Documentation (README, guides)
   - config/ → Config & context files (MEMORY, CONTEXT, PORTFOLIO)
   - output/ → Runtime outputs (RECOMMENDATIONS, RATINGS, LEARNINGS)
   ```

3. **Portfolio Handling** ❌ NEEDS IMMEDIATE FIX
   - Portfolio4.csv has **CRYPTO** (XRP-USD, ETH-USD)
   - Current code only handles yfinance fallback
   - **Need**: Dedicated crypto data fetcher using CoinGecko (FREE) or Kraken API
   - **Missing**: Portfolio consolidation NOT including crypto properly for weightage analysis

4. **Skills System** ❌ MISSING
   - Suggested: `/skills/` folder with modular prompts/templates
   - Each skill = specific prompt template or analysis framework
   - Examples: portfolio-analysis.skill, macro-researcher.skill, once-in-lifetime-opportunities.skill

5. **Macro Data** ❌ MISSING
   - No integration of economic calendars
   - No Fed decision tracking
   - No CPI/employment data fetching
   - **Solution**: Add FRED API (Federal Reserve Economic Data - FREE)

6. **Once-in-a-Lifetime Opportunities** ❌ MISSING
   - Need specific LLM prompt for identifying "must-buy" asymmetric opportunities
   - Condition: Conviction 10/10, +50% upside min, clear catalyst, <20% downside

7. **Portfolio Restructuring Recommendations** ❌ MISSING
   - Agent should suggest SELLING positions if:
     - Overvalued (P/E vs sector average too high)
     - Risk profile changed (bankruptcy risk, regulatory)
     - Better alternatives found
   - Should suggest PORTFOLIO RESTRUCTURE if:
     - Concentration > 60%
     - Sector imbalance detected

---

## Refactoring Roadmap

### Phase 1: Repository Reorganization
- [x] Create `docs/` folder
- [x] Create `skills/` folder  
- [x] Create `config/` folder
- [ ] Move files:
  - `docs/`: README, QUICK_START, PORTFOLIO_SETUP, YAHOOFINANCE_GUIDE, etc.
  - `config/`: MEMORY, CONTEXT, PORTFOLIO, WEEKLY_THEMES
  - `output/`: RATINGS, RECOMMENDATIONS, LEARNINGS
  
### Phase 2: Crypto Tracking Integration
- [ ] Add CoinGecko API (FREE - no key needed for basic calls)
- [ ] Fix portfolio4.csv parsing (XRP-USD, ETH-USD)
- [ ] Update portfolio_weightage to include crypto with proper conversion
- [ ] Test with live prices

### Phase 3: Macro Data Integration
- [ ] Add FRED API integration (FREE)
- [ ] Fetch last 5 economic indicators: CPI, Employment, Fed Funds Rate, GDP
- [ ] Add to news digest as "Economic Context"
- [ ] Track Fed meeting dates

### Phase 4: Skills System
- [ ] Create SKILL_LOADER.md
- [ ] Build skills:
  - `portfolio-restructuring.skill` - portfolio analysis & recommendations
  - `macro-researcher.skill` - deep macro analysis
  - `once-lifetime-opportunities.skill` - extreme asymmetric plays
  - `market-technicals.skill` - charting/TA framework
  
### Phase 5: Once-in-a-Lifetime Opportunities
- [ ] New LLM task for identifying extreme asymmetry
- [ ] Criteria:
  - Conviction 10/10 only
  - Min 50% upside target
  - Clear binary catalyst
  - Max 20% downside defined
  - Max 3 opportunities per quarter (scarcity = quality)

### Phase 6: Portfolio Sell Recommendations
- [ ] Add SELL scoring for each position:
  - Valuation ranking vs peers
  - Fundamental deterioration signals
  - Better alternatives identified
- [ ] Flag for review if score > 7/10

---

## Quick Wins (Implement First)

### 1. Crypto Tracking (5 mins)
Add to fetch_market_data():
```python
def fetch_crypto_prices(cryptos: list = ["BTC-USD", "ETH-USD", "XRP-USD"]) -> dict:
    """Fetch crypto prices from yfinance or CoinGecko"""
    import requests
    result = {}
    for crypto in cryptos:
        try:
            # Try yfinance first
            t = yf.Ticker(crypto)
            price = t.fast_info.last_price
            # Fallback to CoinGecko if yfinance fails
            if price is None:
                symbol = crypto.split('-')[0].lower()
                r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd")
                data = r.json()
                price = data.get(symbol, {}).get('usd')
            result[crypto] = price
        except:
            pass
    return result
```

### 2. Macro Data (10 mins)
Add FRED fetcher:
```python
def fetch_macro_data() -> str:
    """Fetch key economic indicators from FRED (FREE - no key needed)"""
    import requests
    indicators = {
        'CPIAUCSL': 'CPI (Consumer Price Index)',
        'PAYEMS': 'Employment (Total Non-Farm)',
        'DGS10': 'US 10Y Yield',
        'UNRATE': 'Unemployment Rate',
        'MORTGAGE30US': '30Y Mortgage Rate'
    }
    
    output = "## 📊 Key Economic Indicators\n\n"
    for fred_id, label in indicators.items():
        try:
            r = requests.get(f"https://api.stlouisfed.org/fred/series/observations?series_id={fred_id}&units=lin&limit=1")
            # Parse and display
        except:
            pass
    return output
```

### 3. Create Skills Folder Structure
```
skills/
  ├── portfolio-restructuring.skill
  ├── macro-researcher.skill
  ├── once-lifetime-opportunities.skill
  └── README.md
```

### 4. Once-in-a-Lifetime Opportunities Task
```python
def task_once_lifetime_opportunities(market_data, memory) -> str:
    """Identify extreme asymmetric opportunities"""
    # ONLY suggest max 3 per quarter
    # Conviction MUST be 10/10
    # Upside target >= 50%
    # Clear defined downside (stop loss)
```

---

## Import Verification

| Import | Used? | Where | Necessity |
|--------|-------|-------|-----------|
| os | ✅ | Loading env vars | CRITICAL |
| sys | ✅ | stderr suppression for yf | KEEP |
| json | ✅ | Cache handling, config | KEEP |
| time | ✅ | Rate limiting, sleep | KEEP |
| csv | ✅ | Portfolio CSV parsing | CRITICAL |
| datetime | ✅ | Timestamps, date logic | CRITICAL |
| feedparser | ✅ | RSS feed parsing | KEEP |
| requests | ✅ | API calls (Finnhub, Tavily, Polygon) | CRITICAL |
| yfinance (yf) | ✅ | Stock & crypto prices, options | CRITICAL |
| Path | ✅ | File path handling | KEEP |
| OpenAI | ✅ | LLM client creation | CRITICAL |
| dotenv | ✅ | .env file loading | CRITICAL |
| StringIO | ✅ | Suppress yfinance stderr | KEEP |

**Summary**: ✅ All imports are actively used and necessary. No cleanup needed here.

---

## Next Steps

1. **Today**: Implement crypto tracking fix + macro data
2. **This week**: Reorganize repository structure
3. **Next week**: Build skills system + once-in-lifetime opportunities
4. **Long-term**: Add portfolio sell recommendations, risk scoring

---

## Files to Move (After Structure Ready)

### To `docs/`
- README.md, README_v2.1.md
- QUICK_START.md, QUICK_START_v2.1.md
- QUICK_REFERENCE_v2.2.md
- PORTFOLIO_SETUP_5MIN.md
- PORTFOLIO_CONSOLIDATION_SUMMARY.md
- MULTIPLE_PORTFOLIOS_GUIDE.md
- MULTIPLE_PORTFOLIOS_IMPLEMENTATION.md
- YAHOO_FINANCE_GUIDE.md
- WATCHLIST_GUIDE.md
- LEARNING_THEMES_GUIDE.md
- TOKEN_EFFICIENCY_GUIDE.md
- HISTORY_README.md
- TLDR.md

### To `config/`
- MEMORY.md
- CONTEXT.md
- PORTFOLIO.md
- WEEKLY_THEMES.md
- CLAUDE.md

### To `output/` (auto-generated, don't move)
- RATINGS.md
- RECOMMENDATIONS.md
- LEARNINGS.md

### Archive (old versions, can delete)
- CHANGES_SUMMARY.md
- COMPARISON.md
- DELIVERY_SUMMARY.md
- FIXES_APPLIED_v2.2.md
- FIXES_SUMMARY.md
- IMPROVEMENTS_2023.md (recent but summary only)

---

**Status**: ✅ Plan Complete | Ready for Implementation
