"""
Portfolio Analysis Skill v2.0

This module handles all portfolio-related analysis:
- Import and consolidate multiple portfolio CSVs
- Calculate weightings and concentration risk
- Suggest rebalancing opportunities
- Track unrealized gains/losses
- Generate portfolio-aware investment recommendations

FIXED: Now properly fetches live/after-hours prices using multiple fallback sources.
Never falls back to purchase_price silently — clearly labels data freshness.
"""

import sys
import csv
import requests
import yfinance as yf
from pathlib import Path
from datetime import datetime
from io import StringIO

# These will be imported from agent.py or set during initialization
BASE_DIR = Path(__file__).parent.parent
FINNHUB_API_KEY = None

def init_skills(finnhub_key=None, base_dir=None):
    """Initialize skill with config from main agent."""
    global FINNHUB_API_KEY, BASE_DIR
    if finnhub_key:
        FINNHUB_API_KEY = finnhub_key
    if base_dir:
        BASE_DIR = Path(base_dir)


# ─────────────────────────────────────────────
# ROBUST PRICE FETCHING
# ─────────────────────────────────────────────

def get_current_price(ticker):
    """
    Get the most current price for a ticker using multiple fallback sources.
    
    Returns: {
        'price': float or None,
        'prev_close': float or None,
        'source': str,
        'is_live': bool,
        'is_stale': bool,
        'error': str or None
    }
    """
    result = {
        'price': None,
        'prev_close': None,
        'source': None,
        'is_live': False,
        'is_stale': False,
        'error': None
    }

    # SOURCE 1: Finnhub (most reliable — works after hours, gives both price and prev_close)
    if FINNHUB_API_KEY:
        try:
            r = requests.get(
                f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}",
                timeout=10
            )
            data = r.json()
            p = data.get("c", 0)
            pc = data.get("pc", 0)
            if p and float(p) > 0:
                result['price'] = float(p)
                result['prev_close'] = float(pc) if pc and float(pc) > 0 else None
                result['source'] = 'finnhub'
                result['is_live'] = True
        except Exception:
            pass

    # SOURCE 2: yfinance fast_info (fallback for when Finnhub unavailable)
    if result['price'] is None:
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            fi = t.fast_info
            p = fi.last_price
            pc = fi.previous_close
            if p and p > 0:
                result['price'] = float(p)
                result['prev_close'] = float(pc) if pc and pc > 0 else None
                result['source'] = 'yfinance-fast'
                if result['prev_close'] and abs(p - result['prev_close']) > 0.001:
                    result['is_live'] = True
        except Exception:
            pass
        finally:
            sys.stderr = old_stderr

    # SOURCE 3: yfinance info() — more detailed, includes postMarketPrice
    if result['price'] is None:
        sys.stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            info = t.info
            p = (info.get('postMarketPrice') or
                 info.get('currentPrice') or
                 info.get('regularMarketPrice') or
                 info.get('previousClose'))
            pc = (info.get('regularMarketPreviousClose') or
                  info.get('previousClose') or
                  info.get('postMarketPreviousClose'))
            if p and float(p) > 0:
                result['price'] = float(p)
                result['prev_close'] = float(pc) if pc and float(pc) > 0 else None
                result['source'] = 'yfinance-info'
                if info.get('postMarketPrice'):
                    result['is_live'] = True
        except Exception:
            pass
        finally:
            sys.stderr = old_stderr

    # SOURCE 4: If we have a price but no prev_close, try Finnhub for prev_close
    if result['price'] and not result['prev_close'] and FINNHUB_API_KEY:
        try:
            r = requests.get(
                f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}",
                timeout=10
            )
            data = r.json()
            pc = data.get("pc", 0)
            if pc and float(pc) > 0:
                result['prev_close'] = float(pc)
        except Exception:
            pass

    if result['price'] is None:
        result['error'] = f"All data sources failed for {ticker}"
        result['is_stale'] = True

    return result


def get_batch_prices(tickers):
    """
    Fetch prices for multiple tickers efficiently using yfinance batch download.
    More reliable than individual API calls.
    Returns dict of ticker -> price_result
    """
    results = {}

    # Try batch download via yfinance
    old_stderr = sys.stderr
    sys.stderr = StringIO()
    try:
        # Use download for batch price fetching
        import pandas as pd
        data = yf.download(tickers, period="5d", progress=False, threads=True)
        if not data.empty:
            # Get the last available close price for each ticker
            if len(tickers) == 1:
                ticker = tickers[0]
                if 'Close' in data.columns:
                    last_close = data['Close'].dropna().iloc[-1]
                    prev_close = data['Close'].dropna().iloc[-2] if len(data['Close'].dropna()) > 1 else None
                    results[ticker] = {
                        'price': float(last_close),
                        'prev_close': float(prev_close) if prev_close is not None else None,
                        'source': 'yfinance-batch',
                        'is_live': False,
                        'is_stale': False,
                        'error': None
                    }
            else:
                for ticker in tickers:
                    try:
                        if ('Close', ticker) in data.columns:
                            closes = data['Close'][ticker].dropna()
                            if len(closes) > 0:
                                last_close = closes.iloc[-1]
                                prev_close = closes.iloc[-2] if len(closes) > 1 else None
                                results[ticker] = {
                                    'price': float(last_close),
                                    'prev_close': float(prev_close) if prev_close is not None else None,
                                    'source': 'yfinance-batch',
                                    'is_live': False,
                                    'is_stale': False,
                                    'error': None
                                }
                    except Exception:
                        continue
    except Exception:
        pass
    finally:
        sys.stderr = old_stderr

    # For tickers not found in batch, try individual fetches
    for ticker in tickers:
        if ticker not in results:
            results[ticker] = get_current_price(ticker)

    return results


# ─────────────────────────────────────────────
# PORTFOLIO IMPORT
# ─────────────────────────────────────────────

def import_multiple_portfolios(portfolio_files=None):
    """
    Import and consolidate holdings from multiple portfolio CSVs.
    Auto-discovers from portfolios/ folder.
    """
    if portfolio_files is None:
        portfolio_files = []
        portfolios_dir = BASE_DIR / "portfolios"

        if portfolios_dir.exists():
            for i in range(1, 5):
                path = portfolios_dir / f"portfolio{i}.csv"
                if path.exists():
                    portfolio_files.append(str(path))

        if not portfolio_files:
            for i in range(1, 5):
                path = BASE_DIR / f"portfolio{i}.csv"
                if path.exists():
                    portfolio_files.append(str(path))

        if not portfolio_files:
            return {"total": "[No portfolio CSV files found]", "holdings": []}

    consolidated = {}

    for filepath in portfolio_files:
        portfolio_path = Path(filepath)
        if not portfolio_path.exists():
            continue

        try:
            with open(portfolio_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ticker = row.get('Symbol', '').strip().upper()
                    try:
                        shares_raw = row.get('Shares') or row.get('Quantity') or '0'
                        shares = float(shares_raw)
                        price_raw = row.get('Purchase Price') or row.get('Cost Basis') or '0'
                        price = float(price_raw)
                        if ticker and shares and price:
                            cost_basis = shares * price

                            if ticker not in consolidated:
                                consolidated[ticker] = {
                                    'shares': 0,
                                    'total_cost_basis': 0,
                                    'sources': 0,
                                    'prices_list': []
                                }

                            consolidated[ticker]['shares'] += shares
                            consolidated[ticker]['total_cost_basis'] += cost_basis
                            consolidated[ticker]['sources'] += 1
                            consolidated[ticker]['prices_list'].append(price)
                    except ValueError:
                        continue
        except Exception:
            continue

    if not consolidated:
        return {"total": "[No holdings found]", "holdings": []}

    holdings = []
    total_cost_basis = 0

    for ticker in sorted(consolidated.keys()):
        data = consolidated[ticker]
        shares = data['shares']
        total_cb = data['total_cost_basis']
        avg_price = total_cb / shares if shares > 0 else 0
        total_cost_basis += total_cb

        holdings.append({
            'ticker': ticker,
            'shares': shares,
            'purchase_price': avg_price,
            'cost_basis': total_cb,
            'sources': data['sources']
        })

    markdown = f"## Consolidated Holdings ({len(portfolio_files)} portfolios)\n\n"
    markdown += "| Ticker | Shares | Avg Cost | Cost Basis | From |\n"
    markdown += "|--------|--------|----------|-----------|------|\n"

    for h in holdings:
        markdown += f"| **{h['ticker']}** | {h['shares']:.2f} | ${h['purchase_price']:.2f} | ${h['cost_basis']:,.0f} | {h['sources']} portfolio(s) |\n"

    markdown += f"\n**Total Consolidated:**\n"
    markdown += f"- Unique Tickers: {len(holdings)}\n"
    markdown += f"- Total Cost Basis: ${total_cost_basis:,.0f}\n"

    return {"total": markdown, "holdings": holdings}


# ─────────────────────────────────────────────
# PORTFOLIO ANALYSIS WITH LIVE PRICES
# ─────────────────────────────────────────────

def analyze_portfolio_weightage():
    """
    Analyze portfolio by weightage, current value, and P&L.
    Uses LIVE current prices — never falls back to purchase price.
    
    Returns: {
        'total_holdings': int,
        'weighted_summary': str (markdown),
        'top_positions': list,
        'concentration_ratio': float,
        'total_value': float,
        'total_cost_basis': float,
        'total_unrealized_pnl': float,
        'total_unrealized_pnl_pct': float,
        'data_quality': str,
    }
    """
    portfolio_data = import_multiple_portfolios()
    holdings = portfolio_data.get('holdings', [])

    if not holdings:
        return {
            'total_holdings': 0,
            'weighted_summary': 'No portfolio data',
            'top_positions': [],
            'concentration_ratio': 0,
            'total_value': 0,
            'total_cost_basis': 0,
            'total_unrealized_pnl': 0,
            'total_unrealized_pnl_pct': 0,
            'data_quality': 'no_data'
        }

    total_cost = sum(h['cost_basis'] for h in holdings)
    tickers = [h['ticker'] for h in holdings]

    # Filter out crypto for batch stock fetch
    stock_tickers = [t for t in tickers if not t.endswith("-USD")]
    crypto_tickers = [t for t in tickers if t.endswith("-USD")]

    # Fetch all prices using batch + individual fallbacks
    price_map = {}
    if stock_tickers:
        price_map.update(get_batch_prices(stock_tickers))

    # Fetch crypto individually
    for ct in crypto_tickers:
        price_map[ct] = get_current_price(ct)

    # Build weighted holdings with LIVE prices
    weighted_holdings = []
    stale_count = 0
    live_count = 0
    error_count = 0

    for h in holdings:
        ticker = h['ticker']
        pr = price_map.get(ticker, {})

        current_price = pr.get('price')
        prev_close = pr.get('prev_close')
        source = pr.get('source', 'unknown')
        is_stale = pr.get('is_stale', False)
        error = pr.get('error')

        if error:
            error_count += 1

        if is_stale or current_price is None:
            stale_count += 1

        if pr.get('is_live'):
            live_count += 1

        # CRITICAL: If we got no price at all, use the CSV's "Current Price" column
        # as a last resort (it's the most recent price in the export), NOT purchase_price
        if current_price is None:
            # Try to get from the CSV data itself
            csv_price = _get_csv_current_price(ticker)
            if csv_price:
                current_price = csv_price
                source = 'csv-fallback'
            else:
                # Absolute last resort: mark as unavailable, don't fake it
                current_price = None
                source = 'UNAVAILABLE'

        if current_price is not None:
            current_value = h['shares'] * current_price

            # Calculate day change
            if prev_close and prev_close > 0:
                day_change = ((current_price - prev_close) / prev_close) * 100
            else:
                day_change = None  # Unknown, don't fake 0%

            # Calculate unrealized P&L
            unrealized_pnl = current_value - h['cost_basis']
            unrealized_pnl_pct = ((current_price - h['purchase_price']) / h['purchase_price'] * 100) if h['purchase_price'] > 0 else 0

            weighted_holdings.append({
                'ticker': ticker,
                'shares': h['shares'],
                'cost_basis': h['cost_basis'],
                'purchase_price': h['purchase_price'],
                'current_price': current_price,
                'current_value': current_value,
                'prev_close': prev_close,
                'day_change': day_change,
                'unrealized_pnl': unrealized_pnl,
                'unrealized_pnl_pct': unrealized_pnl_pct,
                'source': source,
                'sources': h.get('sources', 1)
            })

    if not weighted_holdings:
        return {
            'total_holdings': 0,
            'weighted_summary': 'No price data available for any holdings',
            'top_positions': [],
            'concentration_ratio': 0,
            'total_value': 0,
            'total_cost_basis': total_cost,
            'total_unrealized_pnl': 0,
            'total_unrealized_pnl_pct': 0,
            'data_quality': 'all_failed'
        }

    # Calculate total current value
    total_current_value = sum(wh['current_value'] for wh in weighted_holdings)

    # Calculate portfolio percentages based on CURRENT value
    for wh in weighted_holdings:
        wh['portfolio_pct'] = (wh['current_value'] / total_current_value * 100) if total_current_value > 0 else 0

    # Sort by portfolio % descending
    weighted_holdings.sort(key=lambda x: x['portfolio_pct'], reverse=True)

    top_5 = weighted_holdings[:5]
    top_5_pct = sum(h['portfolio_pct'] for h in top_5)

    total_unrealized_pnl = total_current_value - total_cost
    total_unrealized_pnl_pct = ((total_current_value - total_cost) / total_cost * 100) if total_cost > 0 else 0

    # Data quality indicator
    data_quality = f"Live: {live_count}, Stale: {stale_count}, Errors: {error_count} (of {len(holdings)} tickers)"

    # Build summary
    summary = f"**Portfolio Analysis ({len(weighted_holdings)} holdings):**\n"
    summary += f"- Total Cost Basis: ${total_cost:,.0f}\n"
    summary += f"- Total Current Value: ${total_current_value:,.0f}\n"
    summary += f"- Total Unrealized P&L: ${total_unrealized_pnl:+,.0f} ({total_unrealized_pnl_pct:+.1f}%)\n"
    summary += f"- Top 5 positions: {top_5_pct:.1f}% of portfolio\n"
    summary += f"- Concentration risk: {'HIGH' if top_5_pct > 60 else 'MODERATE' if top_5_pct > 40 else 'LOW'}\n"
    summary += f"- Data quality: {data_quality}\n\n"

    summary += "| Ticker | % Portfolio | Current Price | Today's Move | Unrealized P&L | Source |\n"
    summary += "|--------|-------------|---------------|--------------|----------------|--------|\n"
    for h in weighted_holdings[:15]:
        day_str = f"{h['day_change']:+.2f}%" if h['day_change'] is not None else "N/A"
        summary += (f"| {h['ticker']} | {h['portfolio_pct']:.1f}% "
                    f"| ${h['current_price']:.2f} "
                    f"| {day_str} "
                    f"| ${h['unrealized_pnl']:+,.0f} ({h['unrealized_pnl_pct']:+.1f}%) "
                    f"| {h['source']} |\n")

    return {
        'total_holdings': len(weighted_holdings),
        'weighted_summary': summary,
        'top_positions': weighted_holdings,
        'concentration_ratio': top_5_pct,
        'total_value': total_current_value,
        'total_cost_basis': total_cost,
        'total_unrealized_pnl': total_unrealized_pnl,
        'total_unrealized_pnl_pct': total_unrealized_pnl_pct,
        'data_quality': data_quality
    }


def _get_csv_current_price(ticker):
    """Try to get the most recent price from the CSV files as a last resort."""
    portfolios_dir = BASE_DIR / "portfolios"
    search_dirs = [portfolios_dir, BASE_DIR]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for i in range(1, 5):
            csv_path = search_dir / f"portfolio{i}.csv"
            if not csv_path.exists():
                continue
            try:
                with open(csv_path, 'r') as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get('Symbol', '').strip().upper() == ticker:
                            cp = row.get('Current Price', '')
                            if cp:
                                val = float(cp)
                                if val > 0:
                                    return val
            except Exception:
                continue
    return None


def suggest_rebalancing(portfolio_analysis):
    """Suggest rebalancing based on portfolio weightage."""
    try:
        top_pos = portfolio_analysis.get('top_positions', [])
        concentration = portfolio_analysis.get('concentration_ratio', 0)

        if not top_pos:
            return "[No rebalancing analysis available]"

        suggestions = "## 🎯 Portfolio Rebalancing Assessment\n\n"

        if concentration > 65:
            suggestions += f"**⚠️ HIGH CONCENTRATION RISK:** Top 5 positions = {concentration:.1f}%\n"
            suggestions += "Recommendation: Consider reducing largest positions to 15-20% each.\n\n"
        elif concentration > 45:
            suggestions += f"**MODERATE CONCENTRATION:** Top 5 = {concentration:.1f}%\n"
            suggestions += "This is reasonable but monitor for excessive single-position risk.\n\n"
        else:
            suggestions += f"**✅ HEALTHY DIVERSIFICATION:** Top 5 = {concentration:.1f}%\n"
            suggestions += "Portfolio is well-balanced.\n\n"

        # Identify underperforming positions
        losers = [p for p in top_pos if p.get('unrealized_pnl_pct', 0) < -10]
        if losers:
            suggestions += f"**Losing Positions ({len(losers)}):**\n"
            for p in losers[:5]:
                suggestions += f"- {p['ticker']}: {p['unrealized_pnl_pct']:+.1f}% | {p['portfolio_pct']:.1f}% of portfolio\n"
            suggestions += "Decision points: Are fundamentals intact? Or cut losses?\n\n"

        # Identify strong performers
        winners = [p for p in top_pos if p.get('unrealized_pnl_pct', 0) > 20]
        if winners:
            suggestions += f"**Top Performers ({len(winners)}):**\n"
            for p in winners[:5]:
                suggestions += f"- {p['ticker']}: {p['unrealized_pnl_pct']:+.1f}% | {p['portfolio_pct']:.1f}% of portfolio\n"
            suggestions += "Consider: Lock in profits on winners > 50% if they've become too large?\n\n"

        return suggestions

    except Exception:
        return "[Rebalancing analysis unavailable]"


__all__ = [
    'init_skills',
    'import_multiple_portfolios',
    'analyze_portfolio_weightage',
    'suggest_rebalancing',
    'get_current_price',
    'get_batch_prices',
]
