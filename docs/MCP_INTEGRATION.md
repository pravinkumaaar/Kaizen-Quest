# MCP Financial Data Integration

## Overview

Our agent now integrates with multiple financial data providers through MCP-style tool wrappers, replacing the need for paid Anthropic MCP servers with free/affordable alternatives.

## Data Sources & MCP Equivalents

| Anthropic MCP Server | Our Implementation | Cost | Status |
|---------------------|-------------------|------|--------|
| **Fiscal AI** | FMP Advanced DCF + Finnhub real-time fundamentals | Free tier | ✅ Active |
| **Financial Modeling Prep** | Direct FMP API integration | Free tier (300 calls/min) | ✅ Active |
| **IBISWorld** | FMP Industry PE + Sector Performance + Finnhub Basic Financials | Free tier | ✅ Active |
| **Third Bridge** | Finnhub Earnings Transcripts + FMP Transcript Search | Free tier | ✅ Active |
| **Daloopa** | FMP Financial Statements As-Reported | Free tier | ✅ Active |
| **Morningstar** | FMP Analyst Estimates + Ratings | Free tier | ✅ Active |
| **FactSet** | FMP Bulk Data + Finnhub Real-time | Free tier | ✅ Active |
| **Moody's** | FMP Financial Scores (Altman Z, Piotroski) | Free tier | ✅ Active |
| **Aiera** | Finnhub News Sentiment + Social Sentiment | Free tier | ✅ Active |
| **LSEG** | FMP Global Filings + Finnhub International | Free tier | ✅ Active |
| **PitchBook** | FMP M&A Data + Institutional Ownership | Free tier | ✅ Active |
| **SS&C Intralinks** | Not available (deal room subscription required) | N/A | ❌ |
| **Chronograph** | Not available (PE-specific) | N/A | ❌ |
| **Egnyte** | Not available (document management) | N/A | ❌ |
| **MT Newswires** | Finnhub Market News + Company News | Free tier | ✅ Active |
| **Dun & Bradstreet** | FMP Company Profile + SEC Filings | Free tier | ✅ Active |
| **Guidepoint** | Not available (expert network) | N/A | ❌ |
| **Verisk** | Not available (insurance-specific) | N/A | ❌ |

## API Keys Required

### Already Configured
- **Finnhub**: `FINNHUB_API_KEY` — Already in .env (free tier: 60 calls/min)

### Recommended to Add
- **Financial Modeling Prep**: `FMP_API_KEY` — Get free key at https://site.financialmodelingprep.com/developer (300 calls/min free)

## Module Structure

```
skills/
├── stock_analyzer.py              # Core analysis (2,846 lines)
│   ├── analyze_stock()            # Basic single-stock analysis
│   ├── build_comps_analysis()     # Comparable company analysis
│   ├── build_dcf_valuation()      # DCF valuation model
│   ├── analyze_earnings_event()   # Earnings analysis
│   ├── analyze_competitive_landscape()  # Moat assessment
│   ├── sector_overview()          # Industry analysis
│   ├── valuation_football_field() # Multi-method valuation
│   └── full_financial_analysis()  # Complete analysis
│
└── financial_data_providers.py    # MCP-style API wrappers (1,200+ lines)
    ├── get_company_profile()      # Multi-source company profile
    ├── get_financial_statements() # Income, Balance Sheet, Cash Flow
    ├── get_financial_ratios()     # Profitability, liquidity, leverage
    ├── get_dcf_valuation()        # FMP DCF valuation
    ├── get_analyst_estimates()    # Price targets, recommendations
    ├── get_institutional_ownership()  # 13F filings, fund ownership
    ├── get_insider_trades()       # Insider transactions + sentiment
    ├── get_earnings_history()     # Historical earnings + surprises
    ├── get_earnings_transcripts() # Earnings call transcripts
    ├── get_sector_performance()   # Sector performance data
    ├── get_industry_pe()          # Industry P/E ratios
    ├── get_news_sentiment()       # News sentiment analysis
    ├── get_social_sentiment()     # Reddit + Twitter sentiment
    ├── get_supply_chain()         # Customer/supplier relationships
    ├── get_esg_scores()           # ESG ratings
    ├── get_congressional_trading() # Congressional trades
    ├── get_forex_rates()          # Currency exchange rates
    ├── get_crypto_quotes()        # Cryptocurrency prices
    ├── get_commodity_quotes()     # Commodity prices
    ├── get_economic_calendar()    # Economic events
    ├── get_treasury_rates()        # US Treasury yield curve
    ├── get_technical_indicators() # SMA, EMA, RSI, MACD, etc.
    ├── get_aggregate_indicators() # Buy/sell/neutral signals
    ├── get_bulk_financials()      # Multi-ticker financials
    └── get_comprehensive_analysis() # All-in-one analysis
```

## Usage Examples

```python
from skills.financial_data_providers import *

# Comprehensive single-stock analysis
analysis = get_comprehensive_analysis("AAPL")

# Individual data points
profile = get_company_profile("MSFT")
dcf = get_dcf_valuation("GOOGL", method="levered")
estimates = get_analyst_estimates("TSLA")
insider = get_insider_trades("NVDA")
transcripts = get_earnings_transcripts("AMZN", year=2024, quarter=4)
sentiment = get_news_sentiment("META")
esg = get_esg_scores("JPM")
supply_chain = get_supply_chain("AAPL")

# Market data
sectors = get_sector_performance()
industry_pe = get_industry_pe()
forex = get_forex_rates("USD")
crypto = get_crypto_quotes(["BTCUSD", "ETHUSD"])
commodities = get_commodity_quotes()
economic = get_economic_calendar(days_forward=14)
treasury = get_treasury_rates()

# Bulk analysis
bulk = get_bulk_financials(["AAPL", "MSFT", "GOOGL", "AMZN", "META"])
```

## Rate Limits

| Provider | Free Tier Limit | Strategy |
|----------|----------------|----------|
| Finnhub | 60 calls/min | Built-in rate limiter |
| FMP | 300 calls/min | Built-in rate limiter |
| yfinance | ~10 calls/min | Conservative throttling |

## Data Flow

```
Agent Request
     │
     ▼
┌─────────────────────┐
│ financial_data_      │
│ providers.py         │
│ (MCP-style wrapper)  │
└─────────┬───────────┘
          │
    ┌─────┼─────┬──────────┐
    ▼     ▼     ▼          ▼
Finnhub  FMP   yfinance  Web Search
(API)   API    (library)  (fallback)
```

## Key Features

1. **Multi-source fallback**: If one provider fails, others are tried automatically
2. **Rate limiting**: Built-in rate limiters prevent API throttling
3. **Unified interface**: Same function signature regardless of data source
4. **Comprehensive coverage**: 25+ functions covering all major financial data needs
5. **Free tier optimized**: Works entirely with free API tiers
6. **Extensible**: Easy to add new data providers or endpoints

## Adding FMP API Key

1. Go to https://site.financialmodelingprep.com/developer
2. Sign up for a free account
3. Get your API key
4. Add to `.env`:
   ```
   FMP_API_KEY=your_key_here
   ```
