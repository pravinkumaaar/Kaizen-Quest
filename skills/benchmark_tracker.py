"""
Benchmark Tracker Skill

Tracks portfolio performance vs indices (SPY, QQQ, IWM).
Compares agent recommendations against benchmarks.
"""

import json
import yfinance as yf
from pathlib import Path
from datetime import datetime

BASE_DIR = Path(__file__).parent.parent
BENCHMARK_FILE = BASE_DIR / "docs" / "BENCHMARKS.md"
PERFORMANCE_FILE = BASE_DIR / "docs" / "PERFORMANCE.json"

BENCHMARK_INDICES = {
    "SPY": "S&P 500",
    "QQQ": "Nasdaq 100",
    "IWM": "Russell 2000"
}

def get_index_prices(symbols: list = None) -> dict:
    """Get current prices for benchmark indices."""
    if symbols is None:
        symbols = list(BENCHMARK_INDICES.keys())
    
    prices = {}
    for symbol in symbols:
        try:
            t = yf.Ticker(symbol)
            info = t.fast_info
            prices[symbol] = {
                "price": info.last_price,
                "prev_close": info.previous_change,
                "change_pct": ((info.last_price - info.previous_close) / info.previous_close * 100) if info.previous_close else 0
            }
        except Exception:
            prices[symbol] = {"price": 0, "change_pct": 0}
    
    return prices

def calculate_portfolio_performance(portfolio_value: float, cost_basis: float) -> dict:
    """Calculate portfolio performance metrics."""
    if cost_basis <= 0:
        return {"total_return_pct": 0, "total_return_dollar": 0}
    
    total_return_dollar = portfolio_value - cost_basis
    total_return_pct = (total_return_dollar / cost_basis) * 100
    
    return {
        "total_return_pct": round(total_return_pct, 2),
        "total_return_dollar": round(total_return_dollar, 2),
        "portfolio_value": round(portfolio_value, 2),
        "cost_basis": round(cost_basis, 2)
    }

def compare_to_benchmarks(portfolio_return_pct: float, period: str = "1D") -> dict:
    """Compare portfolio return to benchmark indices."""
    index_prices = get_index_prices()
    
    comparison = {
        "portfolio_return": portfolio_return_pct,
        "indices": {},
        "outperformed": []
    }
    
    for symbol, name in BENCHMARK_INDICES.items():
        index_data = index_prices.get(symbol, {})
        index_return = index_data.get("change_pct", 0)
        
        comparison["indices"][symbol] = {
            "name": name,
            "return": round(index_return, 2),
            "diff": round(portfolio_return_pct - index_return, 2)
        }
        
        if portfolio_return_pct > index_return:
            comparison["outperformed"].append(symbol)
    
    return comparison

def update_benchmark_log(portfolio_value: float, cost_basis: float, 
                         recommendations: list) -> str:
    """
    Update benchmark tracking log.
    Returns markdown summary.
    """
    perf = calculate_portfolio_performance(portfolio_value, cost_basis)
    comparison = compare_to_benchmarks(perf["total_return_pct"])
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Build markdown summary
    summary = f"\n| {today} | {perf['total_return_pct']:+.2f}% | "
    summary += " | ".join([
        f"{data['return']:+.2f}%" 
        for data in comparison["indices"].values()
    ])
    summary += f" | {', '.join(comparison['outperformed']) if comparison['outperformed'] else 'None'} |"
    
    # Update file
    if not BENCHMARK_FILE.exists():
        BENCHMARK_FILE.write_text("""# 📊 Benchmark Tracking

| Date | Portfolio | SPY | QQQ | IWM | Outperformed |
|------|-----------|-----|-----|-----|--------------|
""")
    
    with open(BENCHMARK_FILE, "a") as f:
        f.write(summary)
    
    # Save JSON data
    perf_data = {
        "date": today,
        "portfolio": perf,
        "benchmarks": comparison,
        "recommendations_count": len(recommendations)
    }
    
    # Append to performance history
    history = []
    if PERFORMANCE_FILE.exists():
        history = json.loads(PERFORMANCE_FILE.read_text())
    
    history.append(perf_data)
    PERFORMANCE_FILE.write_text(json.dumps(history, indent=2))
    
    return summary

def get_performance_summary() -> str:
    """Get a human-readable performance summary."""
    if not PERFORMANCE_FILE.exists():
        return "[No performance data yet]"
    
    history = json.loads(PERFORMANCE_FILE.read_text())
    
    if not history:
        return "[No performance data yet]"
    
    latest = history[-1]
    portfolio = latest.get("portfolio", {})
    benchmarks = latest.get("benchmarks", {})
    
    summary = f"**Portfolio Performance**\n"
    summary += f"- Total Return: {portfolio.get('total_return_pct', 0):+.2f}%\n"
    summary += f"- Value: ${portfolio.get('portfolio_value', 0):,.0f} (Cost: ${portfolio.get('cost_basis', 0):,.0f})\n\n"
    
    summary += f"**vs Benchmarks**\n"
    for symbol, data in benchmarks.get("indices", {}).items():
        diff = data.get("diff", 0)
        emoji = "✅" if diff > 0 else "❌"
        summary += f"- {symbol}: {data['return']:+.2f}% ({diff:+.2f}% vs portfolio) {emoji}\n"
    
    return summary

__all__ = [
    'get_index_prices',
    'calculate_portfolio_performance',
    'compare_to_benchmarks',
    'update_benchmark_log',
    'get_performance_summary'
]