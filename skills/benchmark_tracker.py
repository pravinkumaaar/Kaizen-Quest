"""
Benchmark Tracker Skill v3.0 — Comprehensive Portfolio vs Market Analysis

Features:
  1. Key Performance Metrics (total return, Sharpe, Sortino, alpha, beta, max drawdown,
     win rate, profit factor, information ratio, Calmar ratio)
  2. Proper benchmark comparison (time-weighted vs money-weighted, cash handling,
     sector allocation)
  3. ASCII/text-based visualizations (cumulative returns, rolling beta, drawdown chart,
     sector allocation)
  4. Free data via yfinance + FRED API for risk-free rate
  5. Macro trend analysis (small-cap vs large-cap cycles, growth vs value rotations,
     sector leadership, leading economic indicators)

All data is fetched via yfinance (free) and optionally FRED (free API key).
All metrics are computed locally with pandas/numpy.

Formulas reference:
  - Sharpe = (Rp - Rf) / σp
  - Sortino = (Rp - Rf) / σ_downside
  - Alpha = Rp - [Rf + β(Rm - Rf)]  (Jensen's alpha)
  - Beta = Cov(Rp, Rm) / Var(Rm)
  - Information Ratio = (Rp - Rb) / Tracking Error
  - Calmar Ratio = Annualized Return / Max Drawdown
  - Profit Factor = Gross Profits / Gross Losses
"""

import json
import math
import warnings
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

import numpy as np
import pandas as pd
import yfinance as yf

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent
BENCHMARK_FILE = BASE_DIR / "docs" / "BENCHMARKS.md"
PERFORMANCE_FILE = BASE_DIR / "docs" / "PERFORMANCE.json"

# Benchmark indices with extended set
BENCHMARK_INDICES = {
    "SPY": "S&P 500",
    "QQQ": "Nasdaq 100",
    "IWM": "Russell 2000",
    "VTI": "Total Stock Market",
    "DIA": "Dow Jones",
}

# Sector ETFs for sector allocation comparison
SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLV": "Health Care",
    "XLE": "Energy",
    "XLI": "Industrials",
    "XLC": "Communication Services",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLU": "Utilities",
    "XLB": "Materials",
    "XLRE": "Real Estate",
}

# Growth vs Value benchmarks
STYLE_ETFS = {
    "VUG": "Growth",
    "VTV": "Value",
}

# Macro indicator ETFs
MACRO_ETFS = {
    "GLD": "Gold",
    "SLV": "Silver",
    "TLT": "20+ Year Treasury",
    "HYG": "High Yield Corp Bond",
    "UUP": "US Dollar",
    "EEM": "Emerging Markets",
}

# Risk-free rate proxy
RISK_FREE_TICKER = "^IRX"  # 13-week T-Bill rate

# Trading days per year
TRADING_DAYS = 252


# ─────────────────────────────────────────────
# DATA FETCHING
# ─────────────────────────────────────────────

def fetch_prices(tickers: list, period: str = "1y", interval: str = "1d") -> pd.DataFrame:
    """
    Fetch adjusted close prices for a list of tickers via yfinance.
    Returns DataFrame with dates as index and tickers as columns.
    """
    if not tickers:
        return pd.DataFrame()

    # Suppress yfinance stderr spam (e.g., "Failed to get ticker", "possibly delisted")
    import os, sys
    old_stderr = sys.stderr
    old_stdout = sys.stdout
    sys.stderr = open(os.devnull, 'w')
    sys.stdout = open(os.devnull, 'w')
    try:
        data = yf.download(
            tickers=" ".join(tickers),
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
            threads=True,
        )
    finally:
        sys.stderr = old_stderr
        sys.stdout = old_stdout

    if data.empty:
        return pd.DataFrame()

    # Handle single-ticker case (returns Series-like structure)
    if len(tickers) == 1:
        prices = data["Close"].to_frame(tickers[0])
    else:
        prices = data["Close"]

    # Forward-fill then drop remaining NaNs
    prices = prices.ffill().dropna()
    return prices


def fetch_risk_free_rate(ticker: str = RISK_FREE_TICKER) -> float:
    """
    Fetch the current risk-free rate (13-week T-Bill) as a decimal.
    Tries multiple sources: ^IRX, ^FVX (5Y Treasury), FRED API.
    Falls back to 0.05 (5%) if all unavailable.
    """
    # Try ^IRX first (13-week T-Bill)
    import os, sys
    old_stderr = sys.stderr
    old_stdout = sys.stdout
    sys.stderr = open(os.devnull, 'w')
    sys.stdout = open(os.devnull, 'w')
    try:
        data = yf.download(ticker, period="5d", interval="1d", progress=False)
        if not data.empty:
            rate = float(data["Close"].iloc[-1])
            if rate > 0:
                return rate / 100.0  # Convert from percentage
    except Exception:
        pass
    finally:
        sys.stderr = old_stderr
        sys.stdout = old_stdout

    # Try ^FVX (5-Year Treasury) as backup
    old_stderr = sys.stderr
    old_stdout = sys.stdout
    sys.stderr = open(os.devnull, 'w')
    sys.stdout = open(os.devnull, 'w')
    try:
        data = yf.download("^FVX", period="5d", interval="1d", progress=False)
        if not data.empty:
            rate = float(data["Close"].iloc[-1])
            if rate > 0:
                return rate / 100.0
    except Exception:
        pass
    finally:
        sys.stderr = old_stderr
        sys.stdout = old_stdout

    # Try FRED API if available
    import os
    fred_key = os.environ.get("FRED_API_KEY")
    if fred_key:
        try:
            import requests
            url = (f"https://api.stlouisfed.org/fred/series/observations"
                   f"?series_id=DGS3MO&api_key={fred_key}&file_type=json"
                   f"&sort_order=desc&limit=1")
            resp = requests.get(url, timeout=10)
            data = resp.json()
            obs = data.get("observations", [])
            if obs and obs[0].get("value", ".") != ".":
                return float(obs[0]["value"]) / 100.0
        except Exception:
            pass

    return 0.05  # Fallback: 5% annual


def fetch_fred_series(series_id: str, api_key: str = None) -> pd.Series:
    """
    Fetch a FRED economic series. Requires FRED_API_KEY env var or parameter.
    Common series:
      - DGS10: 10-Year Treasury yield
      - T10Y2Y: 10Y-2Y spread (yield curve)
      - UNRATE: Unemployment rate
      - CPIAUCSL: CPI
      - VIXCLS: VIX
    """
    if not api_key:
        import os
        api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        return pd.Series(dtype=float)

    try:
        url = (
            f"https://api.stlouisfed.org/fred/series/observations"
            f"?series_id={series_id}&api_key={api_key}&file_type=json"
            f"&sort_order=asc&observation_start=2020-01-01"
        )
        import requests
        resp = requests.get(url, timeout=15)
        data = resp.json()
        observations = data.get("observations", [])
        if observations:
            dates = [o["date"] for o in observations]
            values = [float(o["value"]) if o["value"] != "." else np.nan for o in observations]
            return pd.Series(values, index=pd.to_datetime(dates), name=series_id)
    except Exception:
        pass
    return pd.Series(dtype=float)


# ─────────────────────────────────────────────
# CORE METRIC CALCULATIONS
# ─────────────────────────────────────────────

def calculate_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """Calculate daily percentage returns from price data."""
    return prices.pct_change().dropna()


def total_return(prices: pd.Series) -> float:
    """Total return over the entire period as a percentage."""
    if prices.empty or prices.iloc[0] == 0:
        return 0.0
    return float((prices.iloc[-1] / prices.iloc[0] - 1) * 100)


def annualized_return(prices: pd.Series, trading_days: int = TRADING_DAYS) -> float:
    """Annualized return from daily price series."""
    if len(prices) < 2:
        return 0.0
    total = prices.iloc[-1] / prices.iloc[0]
    n_years = len(prices) / trading_days
    if n_years <= 0:
        return 0.0
    return float((total ** (1 / n_years) - 1) * 100)


def annualized_volatility(returns: pd.Series, trading_days: int = TRADING_DAYS) -> float:
    """Annualized standard deviation of returns."""
    if returns.empty:
        return 0.0
    return float(returns.std() * math.sqrt(trading_days) * 100)


def downside_deviation(returns: pd.Series, trading_days: int = TRADING_DAYS) -> float:
    """Annualized downside deviation (only negative returns)."""
    neg_returns = returns[returns < 0]
    if neg_returns.empty:
        return 0.0
    return float(neg_returns.std() * math.sqrt(trading_days) * 100)


def sharpe_ratio(returns: pd.Series, risk_free_rate: float = None) -> float:
    """
    Sharpe Ratio = (Rp - Rf) / σp
    Where Rp = annualized return, Rf = risk-free rate, σp = annualized volatility
    """
    if returns.empty:
        return 0.0
    if risk_free_rate is None:
        risk_free_rate = fetch_risk_free_rate()
    ann_ret = float(returns.mean() * TRADING_DAYS * 100)
    ann_vol = annualized_volatility(returns)
    if ann_vol == 0:
        return 0.0
    return float((ann_ret / 100 - risk_free_rate) / (ann_vol / 100))


def sortino_ratio(returns: pd.Series, risk_free_rate: float = None) -> float:
    """
    Sortino Ratio = (Rp - Rf) / σ_downside
    Like Sharpe but only penalizes downside volatility.
    """
    if returns.empty:
        return 0.0
    if risk_free_rate is None:
        risk_free_rate = fetch_risk_free_rate()
    ann_ret = float(returns.mean() * TRADING_DAYS * 100)
    dd = downside_deviation(returns)
    if dd == 0:
        return 0.0
    return float((ann_ret / 100 - risk_free_rate) / (dd / 100))


def calculate_beta(returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """
    Beta = Cov(Rp, Rm) / Var(Rm)
    Measures systematic risk relative to the benchmark.
    """
    aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
    if aligned.shape[0] < 10:
        return 1.0
    cov = aligned.cov().iloc[0, 1]
    var = aligned.iloc[:, 1].var()
    if var == 0:
        return 1.0
    return float(cov / var)


def calculate_alpha(returns: pd.Series, benchmark_returns: pd.Series,
                    risk_free_rate: float = None) -> float:
    """
    Jensen's Alpha = Rp - [Rf + β(Rm - Rf)]
    Annualized excess return above what CAPM predicts.
    """
    if returns.empty or benchmark_returns.empty:
        return 0.0
    if risk_free_rate is None:
        risk_free_rate = fetch_risk_free_rate()
    beta = calculate_beta(returns, benchmark_returns)
    rp = float(returns.mean() * TRADING_DAYS * 100)
    rm = float(benchmark_returns.mean() * TRADING_DAYS * 100)
    alpha = rp / 100 - (risk_free_rate + beta * (rm / 100 - risk_free_rate))
    return float(alpha * 100)


def max_drawdown(prices: pd.Series) -> float:
    """
    Maximum drawdown as a negative percentage.
    MDD = min((Peak - Trough) / Peak) over the period.
    """
    if prices.empty:
        return 0.0
    cumulative = (1 + prices.pct_change().fillna(0)).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max
    return float(drawdown.min() * 100)


def max_drawdown_duration(prices: pd.Series) -> int:
    """Maximum drawdown duration in trading days."""
    if prices.empty:
        return 0
    cumulative = (1 + prices.pct_change().fillna(0)).cumprod()
    running_max = cumulative.cummax()
    is_drawdown = cumulative < running_max
    if not is_drawdown.any():
        return 0
    groups = (~is_drawdown).cumsum()
    drawdown_groups = groups[is_drawdown]
    if drawdown_groups.empty:
        return 0
    return int(drawdown_groups.value_counts().max())


def calmar_ratio(prices: pd.Series) -> float:
    """
    Calmar Ratio = Annualized Return / |Max Drawdown|
    Higher is better. Undefined if no drawdown.
    """
    ann_ret = annualized_return(prices)
    mdd = abs(max_drawdown(prices))
    if mdd == 0:
        return float("inf") if ann_ret > 0 else 0.0
    return float(ann_ret / mdd)


def information_ratio(returns: pd.Series, benchmark_returns: pd.Series) -> float:
    """
    Information Ratio = (Rp - Rb) / Tracking Error
    Where Tracking Error = std(Rp - Rb) * sqrt(252)
    Measures consistency of outperformance.
    """
    aligned = pd.concat([returns, benchmark_returns], axis=1).dropna()
    if aligned.shape[0] < 10:
        return 0.0
    active_returns = aligned.iloc[:, 0] - aligned.iloc[:, 1]
    te = float(active_returns.std() * math.sqrt(TRADING_DAYS) * 100)
    if te == 0:
        return 0.0
    ann_active = float(active_returns.mean() * TRADING_DAYS * 100)
    return float(ann_active / te)


def win_rate(trades: list) -> float:
    """
    Win rate from a list of trade P&L values.
    Win rate = number of winning trades / total trades
    """
    if not trades:
        return 0.0
    wins = sum(1 for t in trades if t > 0)
    return float(wins / len(trades) * 100)


def profit_factor(trades: list) -> float:
    """
    Profit Factor = Gross Profits / |Gross Losses|
    > 1.0 means profitable. > 2.0 is excellent.
    """
    if not trades:
        return 0.0
    gross_profits = sum(t for t in trades if t > 0)
    gross_losses = abs(sum(t for t in trades if t < 0))
    if gross_losses == 0:
        return float("inf") if gross_profits > 0 else 0.0
    return float(gross_profits / gross_losses)


def avg_win_loss_ratio(trades: list) -> float:
    """Average win size / average loss size."""
    wins = [t for t in trades if t > 0]
    losses = [t for t in trades if t < 0]
    if not wins or not losses:
        return 0.0
    return float(np.mean(wins) / abs(np.mean(losses)))


# ─────────────────────────────────────────────
# TIME-WEIGHTED vs MONEY-WEIGHTED RETURNS
# ─────────────────────────────────────────────

def time_weighted_return(prices: pd.Series) -> float:
    """
    Time-Weighted Return (TWR) — geometric mean of period returns.
    Eliminates the effect of cash flows. Best for comparing to benchmarks.
    """
    if prices.empty or len(prices) < 2:
        return 0.0
    daily_returns = prices.pct_change().dropna()
    twr = float((1 + daily_returns).prod() - 1) * 100
    return twr


def money_weighted_return(cash_flows: list, dates: list, current_value: float,
                          current_date: str = None) -> float:
    """
    Money-Weighted Return (MWR) / IRR — accounts for timing of cash flows.
    Uses Newton's method to solve for the rate that makes NPV = 0.

    cash_flows: list of amounts (positive = deposit, negative = withdrawal)
    dates: list of date strings matching cash_flows
    current_value: current portfolio value (treated as final cash inflow)
    current_date: date string for current_value (default: today)
    """
    if not cash_flows:
        return 0.0

    if current_date is None:
        current_date = datetime.now().strftime("%Y-%m-%d")

    all_flows = list(cash_flows) + [current_value]
    all_dates = list(dates) + [current_date]

    # Convert to days from first date
    base = datetime.strptime(all_dates[0], "%Y-%m-%d")
    days = [(datetime.strptime(d, "%Y-%m-%d") - base).days for d in all_dates]

    # Newton's method to find IRR
    rate = 0.01  # Initial guess (daily rate)
    for _ in range(100):
        npv = sum(f / (1 + rate) ** d for f, d in zip(all_flows, days))
        dnpv = sum(-f * d / (1 + rate) ** (d + 1) for f, d in zip(all_flows, days))
        if abs(dnpv) < 1e-12:
            break
        new_rate = rate - npv / dnpv
        if abs(new_rate - rate) < 1e-10:
            rate = new_rate
            break
        rate = new_rate

    # Annualize
    if rate <= -1:
        return -100.0
    annual = (1 + rate) ** TRADING_DAYS - 1
    return float(annual * 100)


# ─────────────────────────────────────────────
# COMPREHENSIVE METRICS COMPUTATION
# ─────────────────────────────────────────────

def compute_all_metrics(portfolio_prices: pd.Series,
                        benchmark_prices: dict = None,
                        trades: list = None,
                        risk_free_rate: float = None) -> dict:
    """
    Compute all performance metrics for a portfolio.

    Args:
        portfolio_prices: Daily portfolio value (or price series)
        benchmark_prices: Dict of {symbol: price_series} for comparison
        trades: Optional list of trade P&L values for win rate/profit factor
        risk_free_rate: Annual risk-free rate as decimal (fetched if None)

    Returns:
        Dictionary with all computed metrics
    """
    if risk_free_rate is None:
        risk_free_rate = fetch_risk_free_rate()

    returns = calculate_returns(portfolio_prices)
    if returns.empty:
        return {"error": "Insufficient price data"}

    metrics = {
        "period": {
            "start": str(portfolio_prices.index[0])[:10],
            "end": str(portfolio_prices.index[-1])[:10],
            "trading_days": len(portfolio_prices),
            "years": round(len(portfolio_prices) / TRADING_DAYS, 2),
        },
        "returns": {
            "total_return_pct": round(total_return(portfolio_prices), 2),
            "annualized_return_pct": round(annualized_return(portfolio_prices), 2),
            "time_weighted_return_pct": round(time_weighted_return(portfolio_prices), 2),
        },
        "risk": {
            "annualized_volatility_pct": round(annualized_volatility(returns), 2),
            "downside_deviation_pct": round(downside_deviation(returns), 2),
            "max_drawdown_pct": round(max_drawdown(portfolio_prices), 2),
            "max_drawdown_duration_days": max_drawdown_duration(portfolio_prices),
        },
        "risk_adjusted": {
            "sharpe_ratio": round(sharpe_ratio(returns, risk_free_rate), 3),
            "sortino_ratio": round(sortino_ratio(returns, risk_free_rate), 3),
            "calmar_ratio": round(calmar_ratio(portfolio_prices), 3),
        },
        "risk_free_rate_used": round(risk_free_rate * 100, 2),
    }

    # Trade-level metrics
    if trades:
        metrics["trades"] = {
            "total_trades": len(trades),
            "win_rate_pct": round(win_rate(trades), 1),
            "profit_factor": round(profit_factor(trades), 2),
            "avg_win_loss_ratio": round(avg_win_loss_ratio(trades), 2),
            "total_pnl": round(sum(trades), 2),
            "avg_trade_pnl": round(np.mean(trades), 2),
        }

    # Benchmark-relative metrics
    if benchmark_prices:
        benchmark_metrics = {}
        for symbol, b_prices in benchmark_prices.items():
            if b_prices.empty:
                continue
            b_returns = calculate_returns(b_prices)
            if b_returns.empty:
                continue

            bm = {
                "total_return_pct": round(total_return(b_prices), 2),
                "annualized_return_pct": round(annualized_return(b_prices), 2),
                "annualized_volatility_pct": round(annualized_volatility(b_returns), 2),
                "max_drawdown_pct": round(max_drawdown(b_prices), 2),
                "sharpe_ratio": round(sharpe_ratio(b_returns, risk_free_rate), 3),
            }

            # Alpha, Beta, Information Ratio (need aligned returns)
            aligned = pd.concat([returns, b_returns], axis=1).dropna()
            if aligned.shape[0] > 10:
                bm["beta"] = round(calculate_beta(aligned.iloc[:, 0], aligned.iloc[:, 1]), 3)
                bm["alpha_annualized_pct"] = round(
                    calculate_alpha(aligned.iloc[:, 0], aligned.iloc[:, 1], risk_free_rate), 2
                )
                bm["information_ratio"] = round(
                    information_ratio(aligned.iloc[:, 0], aligned.iloc[:, 1]), 3
                )
                bm["correlation"] = round(
                    float(aligned.iloc[:, 0].corr(aligned.iloc[:, 1])), 3
                )

            benchmark_metrics[symbol] = bm

        metrics["benchmarks"] = benchmark_metrics

    return metrics


# ─────────────────────────────────────────────
# PORTFOLIO VALUE FROM CSV + LIVE PRICES
# ─────────────────────────────────────────────

def build_portfolio_value_series(portfolio_csv: str = None,
                                 portfolio_dir: str = None) -> pd.Series:
    """
    Build a daily portfolio value time series from CSV trade history + live prices.

    If portfolio_csv is provided, reads that file.
    Otherwise reads all CSVs in portfolio_dir.
    Returns a pd.Series of daily portfolio values.
    """
    import csv

    if portfolio_dir is None:
        portfolio_dir = BASE_DIR / "portfolios"

    holdings = {}  # ticker -> quantity
    cash = 0.0

    csv_files = []
    if portfolio_csv:
        csv_files = [Path(portfolio_csv)]
    else:
        csv_files = sorted(Path(portfolio_dir).glob("*.csv"))

    for csv_file in csv_files:
        if not csv_file.exists():
            continue
        with open(csv_file, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row.get("Symbol", "").strip()
                qty = float(row.get("Quantity", 0) or 0)
                price = float(row.get("Purchase Price", 0) or 0)
                txn_type = row.get("Transaction Type", "BUY").strip().upper()

                if not ticker or qty <= 0:
                    continue

                if txn_type == "BUY":
                    holdings[ticker] = holdings.get(ticker, 0) + qty
                    cash -= qty * price
                elif txn_type == "SELL":
                    holdings[ticker] = holdings.get(ticker, 0) - qty
                    cash += qty * price

    # Remove zero/negative holdings
    holdings = {t: q for t, q in holdings.items() if q > 0.01}
    if not holdings:
        return pd.Series(dtype=float)

    # Fetch price history for all holdings
    tickers = list(holdings.keys())
    prices = fetch_prices(tickers, period="2y")
    if prices.empty:
        return pd.Series(dtype=float)

    # Calculate daily portfolio value
    portfolio_value = pd.Series(0.0, index=prices.index)
    for ticker, qty in holdings.items():
        if ticker in prices.columns:
            portfolio_value += prices[ticker] * qty
    portfolio_value += cash  # Add cash balance

    return portfolio_value.dropna()


# ─────────────────────────────────────────────
# ASCII / TEXT-BASED VISUALIZATIONS
# ─────────────────────────────────────────────

def ascii_bar(value: float, max_val: float, width: int = 40, char: str = "█") -> str:
    """Create an ASCII bar for a value scaled to max_val."""
    if max_val == 0:
        return ""
    filled = int(abs(value) / abs(max_val) * width)
    filled = min(filled, width)
    bar = char * filled
    if value < 0:
        return f"-{bar}"
    return bar


def cumulative_return_chart(portfolio_prices: pd.Series,
                            benchmark_prices: dict = None,
                            width: int = 60, height: int = 20) -> str:
    """
    Generate an ASCII cumulative return chart.
    Shows portfolio vs benchmarks over time.
    """
    if portfolio_prices.empty:
        return "[No data for chart]"

    # Calculate cumulative returns (normalized to 0%)
    cum_returns = (portfolio_prices / portfolio_prices.iloc[0] - 1) * 100

    lines = ["📈 Cumulative Return Comparison", "=" * (width + 20), ""]

    # Downsample for display
    n_points = min(len(cum_returns), width)
    if len(cum_returns) > width:
        indices = np.linspace(0, len(cum_returns) - 1, n_points, dtype=int)
        display_returns = cum_returns.iloc[indices]
    else:
        display_returns = cum_returns

    # Build chart
    all_values = list(display_returns.values)
    if benchmark_prices:
        for sym, bp in benchmark_prices.items():
            if not bp.empty:
                br = (bp / bp.iloc[0] - 1) * 100
                if len(br) > width:
                    indices = np.linspace(0, len(br) - 1, n_points, dtype=int)
                    br = br.iloc[indices]
                all_values.extend(br.values)

    min_val = min(all_values) if all_values else -10
    max_val = max(all_values) if all_values else 10
    val_range = max_val - min_val if max_val != min_val else 1

    # Create grid
    chart = []
    for row in range(height, -1, -1):
        threshold = min_val + (row / height) * val_range
        if row == 0:
            line = f"{threshold:7.1f}% │"
        elif row == height:
            line = f"{threshold:7.1f}% │"
        elif row == height // 2:
            line = f"{threshold:7.1f}% │"
        else:
            line = f"        │"

        for val in display_returns.values:
            normalized = (val - min_val) / val_range * height
            if abs(normalized - row) < 0.5:
                line += "●"
            elif row == 0 and val >= 0:
                line += "─"
            else:
                line += " "
        chart.append(line)

    # X-axis
    chart.append("        └" + "─" * len(display_returns))

    # Date labels
    start_date = str(display_returns.index[0])[:10]
    end_date = str(display_returns.index[-1])[:10]
    chart.append(f"         {start_date}{' ' * max(0, len(display_returns) - 22)}{end_date}")

    lines.extend(chart)
    lines.append("")
    lines.append("  ● = Portfolio  |  SPY/QQQ/IWM shown if available")

    # Summary table
    lines.append("")
    lines.append(f"  {'Metric':<25} {'Portfolio':>12}")
    lines.append(f"  {'─' * 38}")
    lines.append(f"  {'Total Return':<25} {total_return(portfolio_prices):>11.2f}%")

    if benchmark_prices:
        for sym, bp in benchmark_prices.items():
            if not bp.empty:
                lines.append(f"  {sym + ' Return':<25} {total_return(bp):>11.2f}%")

    return "\n".join(lines)


def drawdown_chart(prices: pd.Series, width: int = 60, height: int = 12) -> str:
    """
    Generate an ASCII drawdown chart.
    Shows the drawdown from peak over time.
    """
    if prices.empty:
        return "[No data for drawdown chart]"

    cumulative = (1 + prices.pct_change().fillna(0)).cumprod()
    running_max = cumulative.cummax()
    drawdown = (cumulative - running_max) / running_max * 100

    # Downsample
    n_points = min(len(drawdown), width)
    if len(drawdown) > width:
        indices = np.linspace(0, len(drawdown) - 1, n_points, dtype=int)
        dd_display = drawdown.iloc[indices]
    else:
        dd_display = drawdown

    lines = ["📉 Drawdown Chart", "=" * (width + 10), ""]

    min_dd = dd_display.min()

    for row in range(0, -height - 1, -1):
        threshold = (row / height) * abs(min_dd) if min_dd != 0 else 0
        if row == 0:
            label = "   0% │"
        elif row == -height:
            label = f"{min_dd:5.1f}% │"
        else:
            label = "      │"

        line = label
        for val in dd_display.values:
            normalized = val / min_dd * height if min_dd != 0 else 0
            if normalized <= row:
                line += "▓"
            else:
                line += " "
        lines.append(line)

    lines.append("      └" + "─" * len(dd_display))
    return "\n".join(lines)


def rolling_beta_chart(portfolio_returns: pd.Series,
                       benchmark_returns: pd.Series,
                       window: int = 60, width: int = 60) -> str:
    """
    Generate an ASCII rolling beta chart.
    Shows how beta changes over time.
    """
    aligned = pd.concat([portfolio_returns, benchmark_returns], axis=1).dropna()
    if aligned.shape[0] < window:
        return "[Insufficient data for rolling beta]"

    rolling_cov = aligned.iloc[:, 0].rolling(window).cov(aligned.iloc[:, 1])
    rolling_var = aligned.iloc[:, 1].rolling(window).var()
    rolling_beta = rolling_cov / rolling_var

    rb = rolling_beta.dropna()
    if rb.empty:
        return "[Could not compute rolling beta]"

    # Downsample
    n_points = min(len(rb), width)
    if len(rb) > width:
        indices = np.linspace(0, len(rb) - 1, n_points, dtype=int)
        rb_display = rb.iloc[indices]
    else:
        rb_display = rb

    min_val = max(rb_display.min(), -1)
    max_val = min(rb_display.max(), 3)
    val_range = max_val - min_val if max_val != min_val else 1

    lines = [f"📊 Rolling Beta ({window}-day) vs Benchmark", "=" * (width + 10), ""]

    height = 10
    for row in range(height, -1, -1):
        threshold = min_val + (row / height) * val_range
        if row == 0:
            label = f"{threshold:5.2f} │"
        elif row == height:
            label = f"{threshold:5.2f} │"
        elif row == height // 2:
            label = f"{threshold:5.2f} │"
        else:
            label = "      │"

        line = label
        for val in rb_display.values:
            normalized = (val - min_val) / val_range * height
            if abs(normalized - row) < 0.5:
                line += "●"
            elif abs(row - (1 - min_val) / val_range * height) < 0.3:
                line += "─"  # Beta = 1 reference line
            else:
                line += " "
        lines.append(line)

    lines.append("      └" + "─" * len(rb_display))
    lines.append("       ─── = Beta 1.0 reference")
    return "\n".join(lines)


def sector_allocation_chart(portfolio_holdings: dict, width: int = 50) -> str:
    """
    Generate an ASCII sector allocation chart.
    portfolio_holdings: {ticker: {"quantity": q, "value": v, "sector": s}}
    """
    if not portfolio_holdings:
        return "[No holdings data]"

    # Aggregate by sector
    sectors = defaultdict(float)
    total_value = 0
    for ticker, info in portfolio_holdings.items():
        value = info.get("value", 0)
        sector = info.get("sector", "Unknown")
        sectors[sector] += value
        total_value += value

    if total_value == 0:
        return "[Zero portfolio value]"

    # Sort by allocation
    sorted_sectors = sorted(sectors.items(), key=lambda x: -x[1])

    lines = ["📊 Sector Allocation", "=" * (width + 25), ""]

    for sector, value in sorted_sectors:
        pct = value / total_value * 100
        bar = ascii_bar(pct, 100, width=width, char="█")
        lines.append(f"  {sector:<22} {bar} {pct:5.1f}%  ${value:>10,.0f}")

    lines.append("")
    lines.append(f"  {'Total':<22} {'':>{width}} {'100.0%':>6}  ${total_value:>10,.0f}")
    return "\n".join(lines)


def metrics_comparison_table(metrics: dict) -> str:
    """
    Generate a formatted comparison table of all metrics vs benchmarks.
    """
    lines = [
        "📊 Portfolio vs Benchmarks — Full Metrics Comparison",
        "=" * 80,
        "",
    ]

    # Header
    header = f"  {'Metric':<30}"
    header += f" {'Portfolio':>12}"
    if "benchmarks" in metrics:
        for sym in metrics["benchmarks"]:
            header += f" {sym:>10}"
    lines.append(header)
    lines.append("  " + "─" * (30 + 12 + 10 * len(metrics.get("benchmarks", {}))))

    # Return metrics
    row_metrics = [
        ("Total Return (%)", "returns", "total_return_pct"),
        ("Annualized Return (%)", "returns", "annualized_return_pct"),
        ("Annualized Volatility (%)", "risk", "annualized_volatility_pct"),
        ("Max Drawdown (%)", "risk", "max_drawdown_pct"),
        ("Sharpe Ratio", "risk_adjusted", "sharpe_ratio"),
        ("Sortino Ratio", "risk_adjusted", "sortino_ratio"),
        ("Calmar Ratio", "risk_adjusted", "calmar_ratio"),
    ]

    for label, section, key in row_metrics:
        row = f"  {label:<30}"
        val = metrics.get(section, {}).get(key, 0)
        row += f" {val:>12}"
        if "benchmarks" in metrics:
            for sym, bm in metrics["benchmarks"].items():
                bval = bm.get(key, "-")
                row += f" {bval:>10}"
        lines.append(row)

    # Benchmark-specific metrics
    if "benchmarks" in metrics:
        lines.append("")
        lines.append("  " + "─" * (30 + 12 + 10 * len(metrics["benchmarks"])))

        for label, key in [("Beta", "beta"), ("Alpha (%)", "alpha_annualized_pct"),
                           ("Information Ratio", "information_ratio"), ("Correlation", "correlation")]:
            row = f"  {label:<30}"
            row += f" {'—':>12}"
            for sym, bm in metrics["benchmarks"].items():
                val = bm.get(key, "—")
                row += f" {val:>10}"
            lines.append(row)

    # Trade metrics
    if "trades" in metrics:
        lines.append("")
        lines.append("  " + "─" * 50)
        t = metrics["trades"]
        lines.append(f"  {'Total Trades':<30} {t['total_trades']:>12}")
        lines.append(f"  {'Win Rate (%)':<30} {t['win_rate_pct']:>12}")
        lines.append(f"  {'Profit Factor':<30} {t['profit_factor']:>12}")
        lines.append(f"  {'Avg Win/Loss Ratio':<30} {t['avg_win_loss_ratio']:>12}")
        lines.append(f"  {'Total P&L ($)':<30} {t['total_pnl']:>12,.2f}")

    return "\n".join(lines)


# ─────────────────────────────────────────────
# MACRO TREND ANALYSIS
# ─────────────────────────────────────────────

def analyze_small_cap_cycle(iwm_prices: pd.Series = None,
                            spy_prices: pd.Series = None) -> dict:
    """
    Analyze small-cap vs large-cap cycle using IWM/SPY ratio.
    Rising ratio = small caps outperforming (risk-on, early cycle)
    Falling ratio = large caps outperforming (risk-off, late cycle)

    Cycle phases:
      - Early Cycle: Small caps start outperforming (IWM/SPY rising from bottom)
      - Mid Cycle: Small caps outperforming strongly
      - Late Cycle: Large caps start outperforming (IWM/SPY falling)
      - Recession: Large caps dominate, small caps underperform severely
    """
    if iwm_prices is None or spy_prices is None:
        prices = fetch_prices(["IWM", "SPY"], period="2y")
        if prices.empty or "IWM" not in prices.columns or "SPY" not in prices.columns:
            return {"error": "Could not fetch IWM/SPY data"}
        iwm_prices = prices["IWM"]
        spy_prices = prices["SPY"]

    # Calculate ratio
    ratio = iwm_prices / spy_prices
    ratio_ma20 = ratio.rolling(20).mean()
    ratio_ma50 = ratio.rolling(50).mean()

    current_ratio = float(ratio.iloc[-1])
    ma20_val = float(ratio_ma20.iloc[-1]) if not ratio_ma20.empty else current_ratio
    ma50_val = float(ratio_ma50.iloc[-1]) if not ratio_ma50.empty else current_ratio

    # Determine trend
    if ma20_val > ma50_val * 1.02:
        trend = "RISING"
        phase = "Small caps outperforming — risk-on environment"
    elif ma20_val < ma50_val * 0.98:
        trend = "FALLING"
        phase = "Large caps outperforming — risk-off / late cycle"
    else:
        trend = "NEUTRAL"
        phase = "No clear leadership — transition period"

    # Percentile rank (where is current ratio vs 2-year range?)
    ratio_pctile = float((current_ratio - ratio.min()) / (ratio.max() - ratio.min()) * 100) \
        if ratio.max() != ratio.min() else 50

    return {
        "iwm_spy_ratio": round(current_ratio, 4),
        "ratio_ma20": round(ma20_val, 4),
        "ratio_ma50": round(ma50_val, 4),
        "trend": trend,
        "phase": phase,
        "percentile_2y": round(ratio_pctile, 1),
        "interpretation": (
            f"IWM/SPY at {current_ratio:.4f} ({ratio_pctile:.0f}th percentile of 2y range). "
            f"Trend: {trend}. {phase}"
        ),
    }


def analyze_growth_value_rotation(vug_prices: pd.Series = None,
                                  vtv_prices: pd.Series = None) -> dict:
    """
    Analyze growth vs value rotation using VUG/VTV ratio.
    Rising ratio = Growth outperforming (tech/innovation leadership)
    Falling ratio = Value outperforming (defensive/cyclical rotation)
    """
    if vug_prices is None or vtv_prices is None:
        prices = fetch_prices(["VUG", "VTV"], period="2y")
        if prices.empty or "VUG" not in prices.columns or "VTV" not in prices.columns:
            return {"error": "Could not fetch VUG/VTV data"}
        vug_prices = prices["VUG"]
        vtv_prices = prices["VTV"]

    ratio = vug_prices / vtv_prices
    ma20 = ratio.rolling(20).mean()
    ma50 = ratio.rolling(50).mean()

    current = float(ratio.iloc[-1])
    ma20_val = float(ma20.iloc[-1]) if not ma20.empty else current
    ma50_val = float(ma50.iloc[-1]) if not ma50.empty else current

    if ma20_val > ma50_val * 1.02:
        trend = "GROWTH_LEADING"
        phase = "Growth stocks outperforming — favor tech, innovation, high-PE names"
    elif ma20_val < ma50_val * 0.98:
        trend = "VALUE_LEADING"
        phase = "Value stocks outperforming — favor dividends, low-PE, cyclicals"
    else:
        trend = "NEUTRAL"
        phase = "No clear style leadership"

    pctile = float((current - ratio.min()) / (ratio.max() - ratio.min()) * 100) \
        if ratio.max() != ratio.min() else 50

    return {
        "vug_vtv_ratio": round(current, 4),
        "trend": trend,
        "phase": phase,
        "percentile_2y": round(pctile, 1),
        "interpretation": (
            f"VUG/VTV at {current:.4f} ({pctile:.0f}th percentile). "
            f"Trend: {trend}. {phase}"
        ),
    }


def analyze_sector_leadership(top_n: int = 3) -> dict:
    """
    Analyze which sectors are leading using sector ETF momentum.
    Ranks sectors by 1-month and 3-month returns.
    """
    symbols = list(SECTOR_ETFS.keys())
    prices = fetch_prices(symbols, period="6mo")
    if prices.empty:
        return {"error": "Could not fetch sector data"}

    rankings = {}
    for symbol in symbols:
        if symbol not in prices.columns:
            continue
        p = prices[symbol].dropna()
        if len(p) < 20:
            continue

        ret_1m = float(p.iloc[-1] / p.iloc[-21] - 1) * 100 if len(p) >= 21 else 0
        ret_3m = float(p.iloc[-1] / p.iloc[-63] - 1) * 100 if len(p) >= 63 else 0

        rankings[symbol] = {
            "name": SECTOR_ETFS.get(symbol, symbol),
            "return_1m_pct": round(ret_1m, 2),
            "return_3m_pct": round(ret_3m, 2),
            "momentum_score": round(ret_1m * 0.6 + ret_3m * 0.4, 2),
        }

    # Sort by momentum score
    sorted_rankings = dict(
        sorted(rankings.items(), key=lambda x: -x[1]["momentum_score"])
    )

    return {
        "rankings": sorted_rankings,
        "top_sectors": list(sorted_rankings.keys())[:top_n],
        "bottom_sectors": list(sorted_rankings.keys())[-top_n:],
    }


def analyze_macro_indicators() -> dict:
    """
    Analyze key macro indicators using free ETF proxies:
      - TLT (bonds) → interest rate environment
      - GLD (gold) → safe haven demand
      - HYG (high yield) → credit risk appetite
      - UUP (dollar) → dollar strength
      - EEM (emerging markets) → global risk appetite
    """
    symbols = ["TLT", "GLD", "HYG", "UUP", "EEM"]
    prices = fetch_prices(symbols, period="3mo")
    if prices.empty:
        return {"error": "Could not fetch macro indicator data"}

    indicators = {}
    for symbol in symbols:
        if symbol not in prices.columns:
            continue
        p = prices[symbol].dropna()
        if len(p) < 10:
            continue

        ret_1m = float(p.iloc[-1] / p.iloc[-21] - 1) * 100 if len(p) >= 21 else 0

        indicators[symbol] = {
            "return_1m_pct": round(ret_1m, 2),
            "current_price": round(float(p.iloc[-1]), 2),
        }

    # Interpret signals
    signals = []
    if "TLT" in indicators:
        if indicators["TLT"]["return_1m_pct"] > 2:
            signals.append("📈 Bonds rallying → rates falling / risk-off")
        elif indicators["TLT"]["return_1m_pct"] < -2:
            signals.append("📉 Bonds falling → rates rising / risk-on")

    if "GLD" in indicators:
        if indicators["GLD"]["return_1m_pct"] > 3:
            signals.append("🥇 Gold surging → safe haven demand / inflation hedge")
        elif indicators["GLD"]["return_1m_pct"] < -3:
            signals.append("🥇 Gold falling → risk-on / strong dollar")

    if "HYG" in indicators:
        if indicators["HYG"]["return_1m_pct"] > 1:
            signals.append("💳 Credit spreads tightening → risk appetite healthy")
        elif indicators["HYG"]["return_1m_pct"] < -2:
            signals.append("💳 Credit spreads widening → stress in high yield")

    if "UUP" in indicators:
        if indicators["UUP"]["return_1m_pct"] > 2:
            signals.append("💵 Dollar strengthening → headwind for commodities/emerging markets")
        elif indicators["UUP"]["return_1m_pct"] < -2:
            signals.append("💵 Dollar weakening → tailwind for international assets")

    if "EEM" in indicators:
        if indicators["EEM"]["return_1m_pct"] > 3:
            signals.append("🌍 Emerging markets rallying → global risk-on")
        elif indicators["EEM"]["return_1m_pct"] < -3:
            signals.append("🌍 EM falling → global risk-off / dollar strength")

    return {
        "indicators": indicators,
        "signals": signals,
        "summary": " | ".join(signals) if signals else "No strong macro signals detected",
    }


def detect_yield_curve(fred_api_key: str = None) -> dict:
    """
    Detect yield curve shape using FRED data (T10Y2Y spread).
    Inverted curve (negative spread) has predicted every recession since 1969.
    """
    spread = fetch_fred_series("T10Y2Y", api_key=fred_api_key)
    if spread.empty:
        return {"note": "FRED API key not set. Set FRED_API_KEY env var for yield curve data."}

    current = float(spread.iloc[-1])
    inverted = current < 0

    return {
        "ten_two_spread": round(current, 2),
        "inverted": inverted,
        "interpretation": (
            f"10Y-2Y spread: {current:.2f}%. "
            + ("⚠️ INVERTED — recession risk elevated" if inverted else "✅ Positive — normal curve")
        ),
    }


# ─────────────────────────────────────────────
# HIGH-LEVEL REPORTING FUNCTIONS
# ─────────────────────────────────────────────

def get_index_prices(symbols: list = None) -> dict:
    """Get current prices for benchmark indices (backward compatible)."""
    if symbols is None:
        symbols = list(BENCHMARK_INDICES.keys())

    prices = {}
    for symbol in symbols:
        try:
            t = yf.Ticker(symbol)
            info = t.fast_info
            prices[symbol] = {
                "price": round(float(info.last_price), 2),
                "prev_close": round(float(info.previous_close), 2) if info.previous_close else None,
                "change_pct": round(
                    float((info.last_price - info.previous_close) / info.previous_close * 100), 2
                ) if info.previous_close else 0,
            }
        except Exception:
            prices[symbol] = {"price": 0, "change_pct": 0}

    return prices


def calculate_portfolio_performance(portfolio_value: float, cost_basis: float) -> dict:
    """Calculate portfolio performance metrics (backward compatible)."""
    if cost_basis <= 0:
        return {"total_return_pct": 0, "total_return_dollar": 0}

    total_return_dollar = portfolio_value - cost_basis
    total_return_pct = (total_return_dollar / cost_basis) * 100

    return {
        "total_return_pct": round(total_return_pct, 2),
        "total_return_dollar": round(total_return_dollar, 2),
        "portfolio_value": round(portfolio_value, 2),
        "cost_basis": round(cost_basis, 2),
    }


def compare_to_benchmarks(portfolio_return_pct: float, period: str = "1D") -> dict:
    """Compare portfolio return to benchmark indices (backward compatible)."""
    index_prices = get_index_prices()

    comparison = {
        "portfolio_return": portfolio_return_pct,
        "indices": {},
        "outperformed": [],
        "period": period,
    }

    for symbol, name in BENCHMARK_INDICES.items():
        index_data = index_prices.get(symbol, {})
        index_return = index_data.get("change_pct", 0)

        comparison["indices"][symbol] = {
            "name": name,
            "return": round(index_return, 2),
            "diff": round(portfolio_return_pct - index_return, 2),
        }

        if portfolio_return_pct > index_return:
            comparison["outperformed"].append(symbol)

    return comparison


def update_benchmark_log(portfolio_value: float, cost_basis: float,
                         recommendations: list) -> str:
    """Update benchmark tracking log (backward compatible)."""
    perf = calculate_portfolio_performance(portfolio_value, cost_basis)
    comparison = compare_to_benchmarks(perf["total_return_pct"])

    today = datetime.now().strftime("%Y-%m-%d")

    summary = f"\n| {today} | {perf['total_return_pct']:+.2f}% | "
    summary += " | ".join(
        [f"{data['return']:+.2f}%" for data in comparison["indices"].values()]
    )
    summary += f" | {', '.join(comparison['outperformed']) if comparison['outperformed'] else 'None'} |"

    if not BENCHMARK_FILE.exists():
        BENCHMARK_FILE.write_text(
            """# 📊 Benchmark Tracking

| Date | Portfolio | SPY | QQQ | IWM | Outperformed |
|------|-----------|-----|-----|-----|--------------|
"""
        )

    with open(BENCHMARK_FILE, "a") as f:
        f.write(summary)

    # Save JSON data
    perf_data = {
        "date": today,
        "portfolio": perf,
        "benchmarks": comparison,
        "recommendations_count": len(recommendations),
    }

    history = []
    if PERFORMANCE_FILE.exists():
        history = json.loads(PERFORMANCE_FILE.read_text())

    history.append(perf_data)
    PERFORMANCE_FILE.write_text(json.dumps(history, indent=2))

    return summary


def get_performance_summary() -> str:
    """Get a human-readable performance summary (backward compatible)."""
    if not PERFORMANCE_FILE.exists():
        return "[No performance data yet]"

    history = json.loads(PERFORMANCE_FILE.read_text())

    if not history:
        return "[No performance data yet]"

    latest = history[-1]
    portfolio = latest.get("portfolio", {})
    benchmarks = latest.get("benchmarks", {})

    summary = "**Portfolio Performance**\n"
    summary += f"- Total Return: {portfolio.get('total_return_pct', 0):+.2f}%\n"
    summary += f"- Value: ${portfolio.get('portfolio_value', 0):,.0f} (Cost: ${portfolio.get('cost_basis', 0):,.0f})\n\n"

    summary += "**vs Benchmarks**\n"
    for symbol, data in benchmarks.get("indices", {}).items():
        diff = data.get("diff", 0)
        emoji = "✅" if diff > 0 else "❌"
        summary += f"- {symbol}: {data['return']:+.2f}% ({diff:+.2f}% vs portfolio) {emoji}\n"

    return summary


# ─────────────────────────────────────────────
# FULL ANALYSIS REPORT
# ─────────────────────────────────────────────

def generate_full_report(portfolio_csv: str = None,
                         portfolio_dir: str = None,
                         trades: list = None,
                         fred_api_key: str = None) -> str:
    """
    Generate a comprehensive benchmark comparison report.
    This is the main entry point for the full analysis.

    Args:
        portfolio_csv: Path to a single portfolio CSV file
        portfolio_dir: Directory containing portfolio CSVs
        trades: Optional list of trade P&L values
        fred_api_key: Optional FRED API key for economic data

    Returns:
        Full markdown report string
    """
    lines = [
        "# 📊 Portfolio Benchmark Analysis Report",
        f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    # ── 1. Build portfolio value series ──
    portfolio_value = build_portfolio_value_series(portfolio_csv, portfolio_dir)
    if portfolio_value.empty:
        lines.append("⚠️ Could not build portfolio value series. Check portfolio CSV files.")
        return "\n".join(lines)

    # ── 2. Fetch benchmark data ──
    bench_symbols = ["SPY", "QQQ", "IWM"]
    bench_prices_raw = fetch_prices(bench_symbols, period="2y")
    benchmark_prices = {}
    if not bench_prices_raw.empty:
        for sym in bench_symbols:
            if sym in bench_prices_raw.columns:
                benchmark_prices[sym] = bench_prices_raw[sym]

    # ── 3. Compute all metrics ──
    metrics = compute_all_metrics(
        portfolio_value,
        benchmark_prices=benchmark_prices,
        trades=trades,
    )

    # ── 4. Metrics comparison table ──
    lines.append(metrics_comparison_table(metrics))
    lines.append("")

    # ── 5. Cumulative return chart ──
    lines.append(cumulative_return_chart(portfolio_value, benchmark_prices))
    lines.append("")

    # ── 6. Drawdown chart ──
    lines.append(drawdown_chart(portfolio_value))
    lines.append("")

    # ── 7. Rolling beta (vs SPY) ──
    if "SPY" in benchmark_prices:
        port_returns = calculate_returns(portfolio_value)
        spy_returns = calculate_returns(benchmark_prices["SPY"])
        lines.append(rolling_beta_chart(port_returns, spy_returns))
        lines.append("")

    # ── 8. Macro trend analysis ──
    lines.append("## 🌐 Macro Trend Analysis")
    lines.append("=" * 60)
    lines.append("")

    # Small cap vs large cap
    if "IWM" in benchmark_prices and "SPY" in benchmark_prices:
        sc = analyze_small_cap_cycle(benchmark_prices["IWM"], benchmark_prices["SPY"])
        lines.append(f"**Small-Cap vs Large-Cap Cycle:**")
        lines.append(f"  {sc.get('interpretation', 'N/A')}")
        lines.append("")

    # Growth vs value
    gv = analyze_growth_value_rotation()
    if "interpretation" in gv:
        lines.append(f"**Growth vs Value Rotation:**")
        lines.append(f"  {gv['interpretation']}")
        lines.append("")

    # Sector leadership
    sl = analyze_sector_leadership()
    if "rankings" in sl:
        lines.append("**Sector Leadership (Momentum Ranking):**")
        for i, (sym, data) in enumerate(sl["rankings"].items()):
            emoji = "🥇" if i == 0 else "🥈" if i == 1 else "🥉" if i == 2 else "  "
            lines.append(
                f"  {emoji} {sym} ({data['name']}): "
                f"1M={data['return_1m_pct']:+.1f}% 3M={data['return_3m_pct']:+.1f}% "
                f"Score={data['momentum_score']:+.1f}"
            )
        lines.append("")

    # Macro indicators
    mi = analyze_macro_indicators()
    if "signals" in mi:
        lines.append("**Macro Indicator Signals:**")
        for signal in mi["signals"]:
            lines.append(f"  {signal}")
        if not mi["signals"]:
            lines.append("  No strong macro signals detected")
        lines.append("")

    # Yield curve
    yc = detect_yield_curve(fred_api_key)
    if "interpretation" in yc:
        lines.append(f"**Yield Curve:** {yc['interpretation']}")
    elif "note" in yc:
        lines.append(f"**Yield Curve:** {yc['note']}")
    lines.append("")

    # ── 9. Key takeaways ──
    lines.append("## 🎯 Key Takeaways")
    lines.append("")

    if "benchmarks" in metrics:
        for sym, bm in metrics["benchmarks"].items():
            port_ret = metrics["returns"]["total_return_pct"]
            bench_ret = bm.get("total_return_pct", 0)
            diff = port_ret - bench_ret
            emoji = "✅" if diff > 0 else "❌"
            lines.append(
                f"- {emoji} Portfolio {'beat' if diff > 0 else 'underperformed'} "
                f"{sym} by {abs(diff):.2f}% total return"
            )

        # Risk-adjusted comparison
        lines.append("")
        lines.append("**Risk-Adjusted Comparison:**")
        port_sharpe = metrics["risk_adjusted"]["sharpe_ratio"]
        for sym, bm in metrics["benchmarks"].items():
            bench_sharpe = bm.get("sharpe_ratio", 0)
            diff = port_sharpe - bench_sharpe
            emoji = "✅" if diff > 0 else "❌"
            lines.append(
                f"- {emoji} Sharpe: Portfolio={port_sharpe:.2f} vs {sym}={bench_sharpe:.2f} "
                f"({diff:+.2f})"
            )

    lines.append("")
    lines.append("---")
    lines.append("*For educational/informational purposes only. Not financial advice.*")

    return "\n".join(lines)


# ─────────────────────────────────────────────
# CLI ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Portfolio Benchmark Analysis")
    parser.add_argument("--portfolio-csv", help="Path to portfolio CSV file")
    parser.add_argument("--portfolio-dir", help="Directory with portfolio CSVs")
    parser.add_argument("--output", help="Output file path (default: print to stdout)")
    parser.add_argument("--fred-key", help="FRED API key for economic data")
    args = parser.parse_args()

    report = generate_full_report(
        portfolio_csv=args.portfolio_csv,
        portfolio_dir=args.portfolio_dir,
        fred_api_key=args.fred_key,
    )

    if args.output:
        Path(args.output).write_text(report)
        print(f"Report saved to {args.output}")
    else:
        print(report)