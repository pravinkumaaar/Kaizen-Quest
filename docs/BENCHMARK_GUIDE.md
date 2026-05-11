# 📊 Portfolio Benchmark Comparison — Complete Guide

## Table of Contents
1. [Key Performance Metrics](#1-key-performance-metrics)
2. [Benchmark Comparison Methods](#2-benchmark-comparison-methods)
3. [Visualization Methods](#3-visualization-methods)
4. [Free Data Sources](#4-free-data-sources)
5. [Macro Trend Analysis](#5-macro-trend-analysis)
6. [Usage Examples](#6-usage-examples)

---

## 1. Key Performance Metrics

### Total Return
```
Total Return (%) = (End Value / Start Value - 1) × 100
```
The simplest measure. Shows total gain/loss over the period.

**Python:**
```python
def total_return(prices):
    return (prices.iloc[-1] / prices.iloc[0] - 1) * 100
```

### Annualized Return (CAGR)
```
CAGR = (End Value / Start Value)^(1/years) - 1
```
Normalizes returns to a yearly rate for fair comparison across different time periods.

**Python:**
```python
def annualized_return(prices, trading_days=252):
    total = prices.iloc[-1] / prices.iloc[0]
    n_years = len(prices) / trading_days
    return (total ** (1 / n_years) - 1) * 100
```

### Sharpe Ratio
```
Sharpe = (Rp - Rf) / σp
```
Where:
- Rp = annualized portfolio return
- Rf = risk-free rate (T-Bill yield)
- σp = annualized standard deviation of returns

**Interpretation:**
- < 0: Worse than risk-free
- 0 – 1.0: Sub-optimal
- 1.0 – 2.0: Good
- 2.0 – 3.0: Very good
- > 3.0: Excellent (may indicate overfitting or short period)

**Python:**
```python
def sharpe_ratio(returns, risk_free_rate=0.05):
    ann_ret = returns.mean() * 252 * 100
    ann_vol = returns.std() * math.sqrt(252) * 100
    return (ann_ret / 100 - risk_free_rate) / (ann_vol / 100)
```

### Sortino Ratio
```
Sortino = (Rp - Rf) / σ_downside
```
Like Sharpe but only penalizes **downside** volatility (negative returns). More appropriate for asymmetric return distributions.

**Python:**
```python
def sortino_ratio(returns, risk_free_rate=0.05):
    ann_ret = returns.mean() * 252 * 100
    neg_returns = returns[returns < 0]
    downside_vol = neg_returns.std() * math.sqrt(252) * 100
    return (ann_ret / 100 - risk_free_rate) / (downside_vol / 100)
```

### Alpha (Jensen's Alpha)
```
α = Rp - [Rf + β(Rm - Rf)]
```
The excess return above what the CAPM model predicts. Positive alpha = stock-picking skill.

**Interpretation:**
- α > 0: Outperformed on risk-adjusted basis
- α = 0: Performed exactly as expected
- α < 0: Underperformed on risk-adjusted basis

**Python:**
```python
def calculate_alpha(port_returns, bench_returns, risk_free_rate=0.05):
    beta = calculate_beta(port_returns, bench_returns)
    rp = port_returns.mean() * 252 * 100
    rm = bench_returns.mean() * 252 * 100
    alpha = rp/100 - (risk_free_rate + beta * (rm/100 - risk_free_rate))
    return alpha * 100
```

### Beta
```
β = Cov(Rp, Rm) / Var(Rm)
```
Measures systematic risk relative to the benchmark.

**Interpretation:**
- β = 1.0: Moves with the market
- β > 1.0: More volatile than market (aggressive)
- β < 1.0: Less volatile than market (defensive)
- β < 0: Moves opposite to market (rare)

**Python:**
```python
def calculate_beta(port_returns, bench_returns):
    aligned = pd.concat([port_returns, bench_returns], axis=1).dropna()
    cov = aligned.cov().iloc[0, 1]
    var = aligned.iloc[:, 1].var()
    return cov / var
```

### Maximum Drawdown
```
MDD = min((Peak - Trough) / Peak)
```
The largest peak-to-trough decline. Critical for understanding worst-case scenarios.

**Python:**
```python
def max_drawdown(prices):
    cumulative = (1 + prices.pct_change().fillna(0)).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    return drawdown.min() * 100  # Negative percentage
```

### Calmar Ratio
```
Calmar = Annualized Return / |Max Drawdown|
```
Measures return per unit of drawdown risk. Higher is better.

### Information Ratio
```
IR = (Rp - Rb) / Tracking Error
```
Where Tracking Error = std(Rp - Rb) × √252

Measures consistency of outperformance. > 0.5 is good, > 1.0 is excellent.

**Python:**
```python
def information_ratio(port_returns, bench_returns):
    aligned = pd.concat([port_returns, bench_returns], axis=1).dropna()
    active_returns = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    te = active_returns.std() * math.sqrt(252) * 100
    ann_active = active_returns.mean() * 252 * 100
    return ann_active / te
```

### Win Rate
```
Win Rate = Winning Trades / Total Trades × 100
```

### Profit Factor
```
Profit Factor = Gross Profits / |Gross Losses|
```
- > 1.0: Profitable
- > 1.5: Good
- > 2.0: Excellent
- < 1.0: Losing strategy

**Python:**
```python
def profit_factor(trades):
    gross_profits = sum(t for t in trades if t > 0)
    gross_losses = abs(sum(t for t in trades if t < 0))
    return gross_profits / gross_losses
```

---

## 2. Benchmark Comparison Methods

### Concentrated Portfolio vs Diversified Index

A concentrated portfolio (5-15 stocks) will naturally have:
- **Higher volatility** → expect higher standard deviation
- **Higher beta variance** → beta may be misleading with few holdings
- **Higher alpha potential** → stock selection matters more
- **Higher max drawdown** → less diversification = larger drawdowns

**Best practices:**
1. Compare to **multiple benchmarks** (SPY for large-cap, QQQ for growth, IWM for small-cap)
2. Use **time-weighted returns** to eliminate cash flow effects
3. Focus on **risk-adjusted metrics** (Sharpe, Sortino, Information Ratio) rather than raw returns
4. Consider **tracking error** — a concentrated portfolio will naturally deviate from indices

### Time-Weighted vs Money-Weighted Returns

**Time-Weighted Return (TWR):**
- Eliminates the effect of cash flows (deposits/withdrawals)
- Best for comparing to benchmarks
- Formula: TWR = ∏(1 + Ri) - 1 (geometric linking of period returns)

**Money-Weighted Return (MWR / IRR):**
- Accounts for timing and size of cash flows
- Best for measuring personal performance
- Formula: Solve for r where NPV = Σ(CFt / (1+r)^t) = 0

**When to use which:**
- Use TWR when comparing to SPY/QQQ (benchmarks don't have cash flows)
- Use MWR when measuring your actual dollar experience
- If you deposit money before good performance, MWR > TWR
- If you deposit money before poor performance, MWR < TWR

### Handling Cash Positions

Cash drag affects comparison:
- A portfolio with 20% cash will underperform in rising markets
- Solution: Compare **invested portion only** to benchmarks
- Or: Include cash as a "position" returning the risk-free rate

### Sector Allocation Comparison

Compare your sector weights to SPY's sector breakdown:
- **Overweight** a sector → making a bet on that sector
- **Underweight** a sector → avoiding or reducing exposure
- Use sector ETFs (XLK, XLF, XLV, etc.) to measure sector contribution

---

## 3. Visualization Methods

### Cumulative Return Chart (ASCII)

```
📈 Cumulative Return Comparison
============================================================

  80.0% │
  60.0% │              ●
  40.0% │           ●     ●
  20.0% │        ●           ●  ●
   0.0% │─────●──────────────────────●──●──●──●──●──●──
 -20.0% │  ●
        └──────────────────────────────────────────────
         2024-05-11                    2025-05-11
```

**Implementation:** See `cumulative_return_chart()` in `benchmark_tracker.py`

### Drawdown Chart (ASCII)

```
📉 Drawdown Chart
============================================================

   0% │
  -5% │▓▓
 -10% │▓▓▓▓▓▓
 -15% │▓▓▓▓▓▓▓▓▓▓▓▓
 -20% │▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓
      └──────────────────────────────
```

**Implementation:** See `drawdown_chart()` in `benchmark_tracker.py`

### Rolling Beta Chart (ASCII)

```
📊 Rolling Beta (60-day) vs Benchmark
============================================================

  2.50 │
  2.00 │         ●●●
  1.50 │      ●●●   ●●●●
  1.00 │────●──────────────●●●●●●●●●●●●●●●●●●●●●●●●●●●●
  0.50 │  ●●
  0.00 │●●
      └──────────────────────────────
       ─── = Beta 1.0 reference
```

**Implementation:** See `rolling_beta_chart()` in `benchmark_tracker.py`

### Sector Allocation (ASCII)

```
📊 Sector Allocation
============================================================

  Technology         ████████████████████████  35.2%  $83,450
  Health Care        ██████████████            18.7%  $44,320
  Financials         ██████████                14.1%  $33,420
  Energy             ██████                     8.3%  $19,670
  Industrials        █████                      6.9%  $16,350
  ...
```

**Implementation:** See `sector_allocation_chart()` in `benchmark_tracker.py`

---

## 4. Free Data Sources

### yfinance (Free, No API Key)

```python
import yfinance as yf
import pandas as pd

# Fetch benchmark prices
benchmarks = yf.download("SPY QQQ IWM", period="2y", auto_adjust=True)
prices = benchmarks["Close"]

# Fetch individual stock
ticker = yf.Ticker("AAPL")
info = ticker.fast_info
current_price = info.last_price
prev_close = info.previous_close

# Fetch risk-free rate (13-week T-Bill)
tbill = yf.download("^IRX", period="5d")
risk_free_rate = float(tbill["Close"].iloc[-1]) / 100  # Convert from percentage
```

### FRED API (Free, Requires API Key)

Get a free key at: https://fred.stlouisfed.org/docs/api/api_key.html

```python
import requests
import pandas as pd

FRED_API_KEY = "your-key-here"

def fetch_fred_series(series_id):
    url = (f"https://api.stlouisfed.org/fred/series/observations"
           f"?series_id={series_id}&api_key={FRED_API_KEY}"
           f"&file_type=json&sort_order=asc")
    resp = requests.get(url)
    data = resp.json()
    observations = data.get("observations", [])
    dates = [o["date"] for o in observations]
    values = [float(o["value"]) if o["value"] != "." else None for o in observations]
    return pd.Series(values, index=pd.to_datetime(dates))

# Key series:
# T10Y2Y  — 10Y-2Y Treasury spread (yield curve)
# DGS10   — 10-Year Treasury yield
# UNRATE  — Unemployment rate
# CPIAUCSL — Consumer Price Index
# VIXCLS  — VIX (volatility index)
# DTWEXB  — Trade Weighted US Dollar Index
```

### Complete Metric Calculation Example

```python
import yfinance as yf
import pandas as pd
import numpy as np
import math

# 1. Fetch data
portfolio = yf.download("AAPL MSFT GOOGL", period="1y")["Close"]
spy = yf.download("SPY", period="1y")["Close"]

# 2. Calculate returns
port_returns = portfolio.sum(axis=1).pct_change().dropna()
spy_returns = spy.pct_change().dropna()

# 3. Compute metrics
total_ret = (portfolio.sum(axis=1).iloc[-1] / portfolio.sum(axis=1).iloc[0] - 1) * 100
ann_ret = port_returns.mean() * 252 * 100
ann_vol = port_returns.std() * math.sqrt(252) * 100
sharpe = (ann_ret/100 - 0.05) / (ann_vol/100)

# 4. Benchmark comparison
spy_total = (spy.iloc[-1] / spy.iloc[0] - 1) * 100
alpha = total_ret - spy_total  # Simplified

print(f"Total Return: {total_ret:.2f}% (SPY: {spy_total:.2f}%)")
print(f"Sharpe Ratio: {sharpe:.2f}")
print(f"Alpha: {alpha:.2f}%")
```

---

## 5. Macro Trend Analysis

### Small-Cap vs Large-Cap Cycles (IWM/SPY Ratio)

The IWM/SPY ratio reveals market risk appetite:

| Phase | IWM/SPY Behavior | Market Implication |
|-------|------------------|-------------------|
| Early Cycle | Rising from bottom | Risk-on, recovery beginning |
| Mid Cycle | Strongly rising | Small caps leading, broad participation |
| Late Cycle | Falling | Risk-off, flight to quality |
| Recession | Falling sharply | Large caps dominate, small caps crushed |

**Python:**
```python
iwm = yf.download("IWM", period="2y")["Close"]
spy = yf.download("SPY", period="2y")["Close"]
ratio = iwm / spy
ma20 = ratio.rolling(20).mean()
ma50 = ratio.rolling(50).mean()

if ma20.iloc[-1] > ma50.iloc[-1] * 1.02:
    print("Small caps outperforming — risk-on")
elif ma20.iloc[-1] < ma50.iloc[-1] * 0.98:
    print("Large caps outperforming — risk-off")
```

### Growth vs Value Rotations (VUG/VTV Ratio)

| VUG/VTV Trend | Implication |
|---------------|-------------|
| Rising | Growth leading — favor tech, innovation, high-PE |
| Falling | Value leading — favor dividends, low-PE, cyclicals |
| Neutral | No clear style leadership |

**Python:**
```python
vug = yf.download("VUG", period="2y")["Close"]
vtv = yf.download("VTV", period="2y")["Close"]
ratio = vug / vtv
ma20 = ratio.rolling(20).mean()
ma50 = ratio.rolling(50).mean()

if ma20.iloc[-1] > ma50.iloc[-1] * 1.02:
    print("Growth outperforming")
elif ma20.iloc[-1] < ma50.iloc[-1] * 0.98:
    print("Value outperforming")
```

### Sector Leadership Detection

Rank sector ETFs by momentum (weighted 1M + 3M returns):

```python
sectors = ["XLK", "XLF", "XLV", "XLE", "XLI", "XLC", "XLY", "XLP", "XLU", "XLB", "XLRE"]
prices = yf.download(" ".join(sectors), period="6mo")["Close"]

rankings = {}
for sym in sectors:
    p = prices[sym].dropna()
    ret_1m = (p.iloc[-1] / p.iloc[-21] - 1) * 100
    ret_3m = (p.iloc[-1] / p.iloc[-63] - 1) * 100
    rankings[sym] = ret_1m * 0.6 + ret_3m * 0.4

sorted_rankings = sorted(rankings.items(), key=lambda x: -x[1])
```

### Leading Economic Indicators

| Indicator | ETF Proxy | Signal |
|-----------|-----------|--------|
| Interest Rates | TLT | Rising TLT = falling rates = risk-off |
| Safe Haven | GLD | Rising GLD = fear/inflation hedge |
| Credit Risk | HYG | Falling HYG = credit stress |
| Dollar | UUP | Rising UUP = strong dollar = EM headwind |
| Global Risk | EEM | Rising EEM = global risk-on |
| Yield Curve | FRED T10Y2Y | Inverted = recession warning |

---

## 6. Usage Examples

### Generate Full Report

```python
from skills.benchmark_tracker import generate_full_report

# From portfolio CSVs in default directory
report = generate_full_report()
print(report)

# From specific CSV
report = generate_full_report(portfolio_csv="portfolios/portfolio1.csv")

# With FRED data for yield curve
report = generate_full_report(fred_api_key="your-key")

# Save to file
from pathlib import Path
Path("REPORTS/benchmark_report.md").write_text(report)
```

### CLI Usage

```bash
# Full report from portfolio CSVs
python -m skills.benchmark_tracker --output REPORTS/benchmark.md

# Specific portfolio file
python -m skills.benchmark_tracker --portfolio-csv portfolios/portfolio1.csv

# With FRED data
python -m skills.benchmark_tracker --fred-key YOUR_KEY --output report.md
```

### Individual Functions

```python
from skills.benchmark_tracker import (
    compute_all_metrics,
    analyze_small_cap_cycle,
    analyze_growth_value_rotation,
    analyze_sector_leadership,
    analyze_macro_indicators,
)

# Compute all metrics
metrics = compute_all_metrics(portfolio_prices, benchmark_prices={"SPY": spy_prices})
print(f"Sharpe: {metrics['risk_adjusted']['sharpe_ratio']}")
print(f"Alpha: {metrics['benchmarks']['SPY']['alpha_annualized_pct']}%")

# Macro analysis
sc_cycle = analyze_small_cap_cycle()
print(sc_cycle["interpretation"])

gv_rotation = analyze_growth_value_rotation()
print(gv_rotation["interpretation"])

sectors = analyze_sector_leadership()
print(f"Top sectors: {sectors['top_sectors']}")

macro = analyze_macro_indicators()
for signal in macro["signals"]:
    print(signal)
```

---

## Quick Reference Card

| Metric | Formula | Good | Great |
|--------|---------|------|-------|
| Sharpe | (Rp-Rf)/σp | > 1.0 | > 2.0 |
| Sortino | (Rp-Rf)/σ_down | > 1.5 | > 2.5 |
| Alpha | Rp-[Rf+β(Rm-Rf)] | > 0% | > 3% |
| Beta | Cov(Rp,Rm)/Var(Rm) | 0.8-1.2 | Context-dependent |
| Max Drawdown | min(Peak-Trough)/Peak | > -20% | > -10% |
| Information Ratio | (Rp-Rb)/TE | > 0.5 | > 1.0 |
| Calmar | Ann Return / |MDD| | > 1.0 | > 2.0 |
| Profit Factor | Gross Profits/|Losses| | > 1.5 | > 2.0 |
| Win Rate | Wins/Total | > 50% | > 60% |

---

*For educational/informational purposes only. Not financial advice.*
