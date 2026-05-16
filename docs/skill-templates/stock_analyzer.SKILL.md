# Stock Analyzer Skill v2.0

Institutional-grade financial analysis for evaluating companies, comparing peers, and making informed investment decisions.

Based on Anthropic's [financial-services](https://github.com/anthropics/financial-services) framework, adapted for free data sources (yfinance, Finnhub).

## Capabilities

### 1. Comparable Company Analysis (`build_comps_analysis`)
Institutional-grade comps with operating metrics, valuation multiples, and statistical benchmarking (Max, 75th, Median, 25th, Min).

- Auto-detects peer group by sector or accepts custom peers
- Operating statistics: Revenue, Growth, Gross/EBITDA/FCF Margins, Rule of 40
- Valuation multiples: P/E, EV/EBITDA, EV/Revenue, P/S, P/B, FCF Yield
- Statistical summary with outlier detection
- Industry-specific metric selection (SaaS, Financials, Retail, etc.)

### 2. DCF Valuation (`build_dcf_valuation`)
Discounted Cash Flow model with CAPM-based WACC, scenario analysis, and sensitivity tables.

- Historical financial analysis
- Revenue projections with growth decay
- WACC calculation via CAPM (risk-free rate, beta, equity risk premium)
- Terminal value (perpetuity growth + exit multiple methods)
- Bear/Base/Bull scenario analysis
- WACC vs Terminal Growth sensitivity table (5x5)
- Sanity checks (TV < WACC, TV proportion, growth reasonableness)

### 3. Earnings Reviewer (`analyze_earnings_event`)
Post-earnings analysis with beat/miss, guidance, and quality assessment.

- EPS and Revenue beat/miss vs estimates
- Margin analysis (gross, operating, net, EBITDA, FCF)
- Growth analysis (YoY, quarterly)
- Estimate revision impact
- Quality scoring

### 4. Competitive Landscape (`analyze_competitive_landscape`)
Market positioning and moat assessment.

- Moat analysis across 4 dimensions:
  - Network Effects
  - Switching Costs
  - Scale Economies
  - Intangible Assets
- Competitor comparison table
- Market share estimation
- Bull/Base/Bear scenario analysis

### 5. Sector Overview (`sector_overview`)
Industry landscape and market structure analysis.

- Top companies by market cap
- Sector statistics (median P/E, EV/EBITDA, growth, margins)
- Market concentration (top 5)
- Industry structure assessment

### 6. Valuation Football Field (`valuation_football_field`)
Multi-method valuation summary.

- P/E-based (trailing + forward)
- EV/EBITDA-based
- EV/Revenue-based
- Analyst consensus
- Overall valuation range

### 7. Full Financial Analysis (`full_financial_analysis`)
Combines all modules into a single comprehensive report.

## Usage

```python
from skills.stock_analyzer import (
    analyze_stock,              # Basic single-stock analysis
    build_comps_analysis,       # Comparable company analysis
    build_dcf_valuation,        # DCF valuation model
    analyze_earnings_event,     # Earnings analysis
    analyze_competitive_landscape,  # Competitive analysis
    sector_overview,            # Sector analysis
    valuation_football_field,   # Multi-method valuation
    full_financial_analysis,    # Complete analysis
)

# Quick analysis
result = analyze_stock("AAPL")

# Full institutional-grade analysis
result = full_financial_analysis("MSFT", depth="comprehensive")

# Individual modules
comps = build_comps_analysis("NVDA", peer_tickers=["AMD", "INTC", "AVGO"])
dcf = build_dcf_valuation("GOOGL", scenario="base")
earnings = analyze_earnings_event("TSLA")
competitive = analyze_competitive_landscape("AMZN")
sector = sector_overview("Technology")
football = valuation_football_field("MSFT")

# Format reports
from skills.stock_analyzer import (
    format_analysis_report, format_comps_report, format_dcf_report,
    format_earnings_report, format_competitive_report, format_football_field_report,
)
print(format_comps_report(comps))
print(format_dcf_report(dcf))
```

## Data Sources

- **yfinance**: Company profiles, financials, estimates, analyst data
- **Finnhub** (optional): Earnings calendar, recommendations
- **Free tier only** — no paid MCP connectors required

## Disclaimer

For educational/informational purposes only. Not financial advice. Verify with your broker before acting.
