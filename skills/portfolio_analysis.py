"""
Portfolio Analysis Skill

This module handles all portfolio-related analysis:
- Import and consolidate multiple portfolio CSVs
- Calculate weightings and concentration risk
- Suggest rebalancing opportunities
- Track unrealized gains/losses
- Generate portfolio-aware investment recommendations
"""

import sys
import csv
from pathlib import Path
from datetime import datetime
import requests
import yfinance as yf
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

def import_multiple_portfolios(portfolio_files: list = None) -> dict:
    """
    Import and consolidate holdings from multiple portfolio CSVs.
    Auto-discovers from portfolios/ folder.
    
    Returns: {
        'total': consolidated portfolio markdown,
        'holdings': list of {ticker, shares, cost_basis, purchase_price, sources}
    }
    """
    if portfolio_files is None:
        portfolio_files = []
        portfolios_dir = BASE_DIR / "portfolios"
        
        # Check portfolios/ folder first
        if portfolios_dir.exists():
            for i in range(1, 5):
                path = portfolios_dir / f"portfolio{i}.csv"
                if path.exists():
                    portfolio_files.append(str(path))
        
        # Fallback to root directory
        if not portfolio_files:
            for i in range(1, 5):
                path = BASE_DIR / f"portfolio{i}.csv"
                if path.exists():
                    portfolio_files.append(str(path))
        
        if not portfolio_files:
            return {"total": "[No portfolio CSV files found]", "holdings": []}
    
    # Consolidate holdings
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
                        # Support both 'Shares' and 'Quantity' column names
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
    
    # Convert to holdings list
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
    
    # Build markdown summary
    markdown = f"## Consolidated Holdings ({len(portfolio_files)} portfolios)\n\n"
    markdown += "| Ticker | Shares | Avg Price | Cost Basis | From |\n"
    markdown += "|--------|--------|-----------|-----------|------|\n"
    
    for h in holdings:
        markdown += f"| **{h['ticker']}** | {h['shares']:.2f} | ${h['purchase_price']:.2f} | ${h['cost_basis']:,.0f} | {h['sources']} portfolio(s) |\n"
    
    markdown += f"\n**Total Consolidated:**\n"
    markdown += f"- Unique Tickers: {len(holdings)}\n"
    markdown += f"- Total Cost Basis: ${total_cost_basis:,.0f}\n"
    
    return {"total": markdown, "holdings": holdings}

def analyze_portfolio_weightage() -> dict:
    """
    Analyze portfolio by weightage, current value, and P&L.
    
    Returns: {
        'total_holdings': int,
        'weighted_summary': str (markdown),
        'top_positions': list,
        'concentration_ratio': float,
        'total_value': float
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
            'total_value': 0
        }
    
    total_cost = sum(h['cost_basis'] for h in holdings)
    
    # PASS 1: Fetch all current prices and calculate current values
    weighted_holdings = []
    for h in holdings:
        try:
            current_price = None
            prev_close = None
            
            if FINNHUB_API_KEY and h['ticker'] not in ['BTC-USD', 'ETH-USD']:
                try:
                    r = requests.get(
                        f"https://finnhub.io/api/v1/quote?symbol={h['ticker']}&token={FINNHUB_API_KEY}",
                        timeout=10
                    )
                    data = r.json()
                    current_price = data.get("c", 0)
                    prev_close = data.get("pc", None)
                except Exception:
                    pass
            
            if current_price is None or current_price == 0:
                old_stderr = sys.stderr
                sys.stderr = StringIO()
                try:
                    t = yf.Ticker(h['ticker'])
                    current_price = t.fast_info.last_price
                    prev_close = t.fast_info.previous_close
                except Exception:
                    current_price = h['purchase_price']
                    prev_close = h['purchase_price']
                finally:
                    sys.stderr = old_stderr
            
            # Skip if we got no valid price
            if current_price is None or current_price == 0:
                current_price = h['purchase_price']
                prev_close = h['purchase_price']
            
            current_value = h['shares'] * current_price
            
            weighted_holdings.append({
                'ticker': h['ticker'],
                'shares': h['shares'],
                'cost_basis': h['cost_basis'],
                'purchase_price': h['purchase_price'],
                'current_price': current_price,
                'current_value': current_value,
                'prev_close': prev_close if prev_close else h['purchase_price'],
                'sources': h.get('sources', 1)
            })
        except Exception:
            continue
    
    # Calculate total current value across all holdings
    total_current_value = sum(wh['current_value'] for wh in weighted_holdings)
    
    # PASS 2: Calculate percentages and gains
    for wh in weighted_holdings:
        # % of portfolio based on current value (not cost basis)
        wh['portfolio_pct'] = (wh['current_value'] / total_current_value * 100) if total_current_value > 0 else 0
        # Unrealized gain: how much current price vs purchase price
        wh['unrealized_gain'] = ((wh['current_price'] - wh['purchase_price']) / wh['purchase_price'] * 100) if wh['purchase_price'] > 0 else 0
        # Day change: how much current price vs previous close
        wh['day_change'] = ((wh['current_price'] - wh['prev_close']) / wh['prev_close'] * 100) if wh['prev_close'] > 0 else 0
    
    # Sort by portfolio % descending
    weighted_holdings.sort(key=lambda x: x['portfolio_pct'], reverse=True)
    
    top_5 = weighted_holdings[:5]
    top_5_pct = sum(h['portfolio_pct'] for h in top_5)
    
    summary = f"**Portfolio Analysis ({len(weighted_holdings)} holdings):**\n"
    summary += f"- Total Cost Basis: ${total_cost:,.0f}\n"
    summary += f"- Top 5 positions: {top_5_pct:.1f}% of portfolio\n"
    summary += f"- Concentration risk: {'HIGH' if top_5_pct > 60 else 'MODERATE' if top_5_pct > 40 else 'LOW'}\n\n"
    summary += "| Ticker | % of Portfolio | Current Price | Today's Move | Unrealized P&L |\n"
    summary += "|--------|----------------|---------------|--------------|----------------|\n"
    for h in weighted_holdings[:10]:
        summary += f"| {h['ticker']} | {h['portfolio_pct']:.1f}% | ${h['current_price']:.2f} | {h['day_change']:+.2f}% | {h['unrealized_gain']:+.1f}% |\n"
    
    return {
        'total_holdings': len(weighted_holdings),
        'weighted_summary': summary,
        'top_positions': weighted_holdings,
        'concentration_ratio': top_5_pct,
        'total_value': sum(h['current_value'] for h in weighted_holdings)
    }

def suggest_rebalancing(portfolio_analysis: dict) -> str:
    """
    Suggest rebalancing based on concentration, losers, and winners.
    Includes 'SELL' recommendations for overvalued/risky positions.
    """
    top_pos = portfolio_analysis.get('top_positions', [])
    concentration = portfolio_analysis.get('concentration_ratio', 0)
    
    if not top_pos:
        return "[No rebalancing analysis available]"
    
    suggestions = "## 🎯 Portfolio Rebalancing Assessment\n\n"
    
    # Concentration check
    if concentration > 65:
        suggestions += f"**⚠️ HIGH CONCENTRATION RISK:** Top 5 = {concentration:.1f}%\n"
        suggestions += "**Action: SELL/REDUCE** the following overweighed positions:\n"
        for p in top_pos[:3]:
            if p['portfolio_pct'] > 20:
                suggestion = "🔴 **SELL 50%**" if p['portfolio_pct'] > 30 else "🟡 **REDUCE 30%**"
                suggestions += f"- {p['ticker']}: {p['portfolio_pct']:.1f}% → Target: 15-20%\n"
                suggestions += f"  {suggestion} to free up capital for diversification\n"
        suggestions += "\n"
    elif concentration > 45:
        suggestions += f"**MODERATE CONCENTRATION:** Top 5 = {concentration:.1f}%\n"
        suggestions += "Monitor for excessive single-position risk.\n\n"
    else:
        suggestions += f"**✅ HEALTHY DIVERSIFICATION:** Top 5 = {concentration:.1f}%\n\n"
    
    # Losers (suggest SELL if fundamentals broken)
    losers = [p for p in top_pos if p['unrealized_gain'] < -10]
    if losers:
        suggestions += f"**🔴 LOSING POSITIONS ({len(losers)}):**\n"
        suggestions += "Consider SELLING if thesis is broken:\n"
        for p in losers[:3]:
            reason = " (deep value?)" if p['unrealized_gain'] < -20 else " (reassess thesis)"
            suggestions += f"- {p['ticker']}: {p['unrealized_gain']:+.1f}% | {p['portfolio_pct']:.1f}% of portfolio{reason}\n"
        suggestions += "\n"
    
    # Winners (suggest taking profits)
    winners = [p for p in top_pos if p['unrealized_gain'] > 30]
    if winners:
        suggestions += f"**🟢 TOP PERFORMERS ({len(winners)}):**\n"
        suggestions += "Consider TAKING PROFITS on overweight winners:\n"
        for p in winners[:3]:
            if p['portfolio_pct'] > 15:
                suggestions += f"- {p['ticker']}: {p['unrealized_gain']:+.1f}% | {p['portfolio_pct']:.1f}% → SELL 30-50%\n"
            else:
                suggestions += f"- {p['ticker']}: {p['unrealized_gain']:+.1f}% | Great performer, hold\n"
        suggestions += "\n"
    
    # Once-in-a-lifetime opportunities
    suggestions += "\n## 🚀 ONCE-IN-A-LIFETIME OPPORTUNITIES\n\n"
    suggestions += "Look for these asymmetric opportunities:\n"
    suggestions += "- Extreme fear (VIX >30): Buy quality stocks at deep discounts\n"
    suggestions += "- Sector rotation: When a sector is down 30%+ but fundamentals intact\n"
    suggestions += "- Crypto crashes: BTC/ETH down 50%+ can be generational buys\n"
    suggestions += "- Spin-offs and special situations with clear catalysts\n"
    
    return suggestions

# Export main functions
__all__ = [
    'init_skills',
    'import_multiple_portfolios',
    'analyze_portfolio_weightage',
    'suggest_rebalancing'
]
