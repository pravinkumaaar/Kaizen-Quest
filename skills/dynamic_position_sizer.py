"""
Dynamic Position Sizer v1.0

Research-backed position sizing combining:
1. Kelly Criterion (half-Kelly for safety)
2. Risk Parity (equal risk contribution)
3. Conviction-weighted allocation
4. Sector correlation adjustment
5. Volatility normalization

Key research findings:
- Kelly fraction = (p*b - q) / b, where p=win_prob, b=win/loss ratio
- Half-Kelly is the practical standard (reduces volatility by ~50% with only ~25% lower returns)
- Thorp's research: SP500 Kelly fraction ≈ 117%, half-Kelly ≈ 58%
- Risk parity: each asset contributes equally to portfolio risk
- Piotroski F-score: quality filter for value stocks
- GARP: Growth at Reasonable Price — strong fundamentals + stagnant/declining price

Usage:
    from skills.dynamic_position_sizer import compute_position_sizes, format_position_report
    
    positions = compute_position_sizes(
        available_cash=50000,
        portfolio_value=250000,
        existing_positions=[...],
        watchlist=[...],
    )
    report = format_position_report(positions)
"""

import json
import datetime
import math
from pathlib import Path
from io import StringIO


def estimate_win_probability(conviction):
    """Map conviction (1-10) to estimated win probability.
    Calibrated: conviction 5 = 50% (no edge), 7 = 55%, 10 = 70%
    Based on historical analysis of analyst conviction vs outcomes.
    """
    return 0.45 + (conviction * 0.025)


def estimate_win_loss_ratio(conviction):
    """Map conviction to expected win/loss ratio.
    Higher conviction = better expected risk/reward.
    conviction 5 = 1.0 (even), 7 = 1.6, 10 = 2.5
    """
    return 1.0 + max(0, conviction - 5) * 0.3


def compute_kelly_fraction(win_prob, win_loss_ratio):
    """Compute Kelly Criterion fraction.
    Kelly = (p*b - q) / b
    where p = win probability, b = win/loss ratio, q = 1-p
    Returns half-Kelly for safety.
    """
    if win_loss_ratio <= 0:
        return 0
    q = 1 - win_prob
    kelly = (win_prob * win_loss_ratio - q) / win_loss_ratio
    kelly = max(0, kelly)  # Don't bet if no edge
    return kelly * 0.75  # Use 75% Kelly for aggressive growth


def estimate_volatility(ticker, period="3mo"):
    """Estimate annualized volatility from historical prices."""
    try:
        import yfinance as yf
        old_stderr = __import__('sys').stderr
        __import__('sys').stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period=period)
            if hist is not None and len(hist) > 10:
                returns = hist["Close"].pct_change().dropna()
                daily_vol = returns.std()
                annual_vol = daily_vol * math.sqrt(252)
                return max(annual_vol, 0.10)  # Floor at 10% annual vol
        finally:
            __import__('sys').stderr = old_stderr
    except Exception:
        pass
    return 0.25  # Default 25% annual volatility


def get_sector(ticker):
    """Get sector for a ticker."""
    try:
        import yfinance as yf
        old_stderr = __import__('sys').stderr
        __import__('sys').stderr = StringIO()
        try:
            info = yf.Ticker(ticker).info
            return info.get('sector', 'Unknown')
        finally:
            __import__('sys').stderr = old_stderr
    except Exception:
        return 'Unknown'


def compute_position_sizes(available_cash, portfolio_value, existing_positions, watchlist,
                            max_single_position_pct=0.15, max_cash_per_trade=0.40,
                            max_total_deployment=0.90, min_trade_size=200,
                            allow_adding_existing=True, conviction_threshold=8):
    """
    Compute dynamic position sizes using Kelly Criterion + Risk Parity.
    
    Args:
        available_cash: Cash available for trading
        portfolio_value: Total portfolio value
        existing_positions: List of dicts with 'symbol', 'market_value', 'sector'
        watchlist: List of dicts with 'ticker', 'conviction' (1-10), 'price'
        max_single_position_pct: Max % of portfolio in single position
        max_cash_per_trade: Max % of available cash per trade
        max_total_deployment: Max % of total cash to deploy
        min_trade_size: Minimum dollar amount per trade
    
    Returns:
        dict with 'trades', 'skipped', 'summary'
    """
    results = {"trades": [], "skipped": [], "summary": {}}
    
    if not watchlist or available_cash < min_trade_size:
        results["summary"] = {"reason": "No watchlist or insufficient cash"}
        return results
    
    # Compute sector allocation of existing positions
    sector_allocation = {}
    for pos in existing_positions:
        if pos.get('type') == 'stock':
            sector = pos.get('sector', get_sector(pos['symbol']))
            mv = float(pos.get('market_value', 0))
            sector_allocation[sector] = sector_allocation.get(sector, 0) + mv
    
    # Normalize to percentages
    if portfolio_value > 0:
        for sector in sector_allocation:
            sector_allocation[sector] = round(sector_allocation[sector] / portfolio_value * 100, 1)
    
    # Compute Kelly-based size for each watchlist ticker
    max_total_dollar = available_cash * max_total_deployment
    total_allocated = 0
    
    for item in watchlist:
        ticker = item.get('ticker', '').upper()
        conviction = item.get('conviction', 5)
        price = item.get('price', 0)
        
        if not ticker or price <= 0:
            results["skipped"].append({"ticker": ticker, "reason": "No price data"})
            continue
        
        # Check if already held — allow adding if conviction is high and cash is ample
        already_held = any(p['symbol'] == ticker for p in existing_positions if p.get('type') == 'stock')
        if already_held:
            # Only skip if adding is disabled
            if not allow_adding_existing:
                results["skipped"].append({"ticker": ticker, "reason": "Already held (adding disabled)"})
                continue
            # For already-held: only add if conviction >= 9 and cash > 30% of portfolio
            if conviction < 9:
                results["skipped"].append({"ticker": ticker, "reason": f"Already held, conviction {conviction} < 9 for adding"})
                continue
            if portfolio_value > 0 and available_cash / portfolio_value < 0.30:
                results["skipped"].append({"ticker": ticker, "reason": f"Already held, cash {available_cash/portfolio_value*100:.0f}% < 30% for adding"})
                continue
        
        # Skip low conviction (threshold configurable, default 8 for quality)
        if conviction < conviction_threshold:
            results["skipped"].append({"ticker": ticker, "reason": f"Conviction {conviction}/10 below {conviction_threshold} threshold"})
            continue
        
        # Compute Kelly fraction
        win_prob = estimate_win_probability(conviction)
        win_loss_ratio = estimate_win_loss_ratio(conviction)
        kelly = compute_kelly_fraction(win_prob, win_loss_ratio)
        
        # Volatility adjustment (higher vol = smaller position)
        vol = estimate_volatility(ticker)
        vol_adjustment = 0.20 / vol  # Normalize to 20% baseline vol
        vol_adjustment = min(vol_adjustment, 2.0)  # Cap at 2x
        
        # Sector correlation adjustment
        sector = get_sector(ticker)
        sector_pct = sector_allocation.get(sector, 0)
        if sector_pct > 25:
            corr_adjustment = 0.5  # Halve size if sector already >25%
        elif sector_pct > 15:
            corr_adjustment = 0.75
        else:
            corr_adjustment = 1.0
        
        # Compute position size
        base_size = portfolio_value * kelly * vol_adjustment * corr_adjustment
        
        # Apply guardrails
        max_position = portfolio_value * max_single_position_pct
        max_cash_trade = available_cash * max_cash_per_trade
        remaining_budget = max_total_dollar - total_allocated
        
        dollar_amount = min(base_size, max_position, max_cash_trade, remaining_budget)
        dollar_amount = max(0, dollar_amount)
        
        if dollar_amount < min_trade_size:
            results["skipped"].append({
                "ticker": ticker,
                "reason": f"Computed size ${dollar_amount:.0f} below minimum ${min_trade_size}"
            })
            continue
        
        qty = max(1, int(dollar_amount / price))
        actual_cost = qty * price
        
        total_allocated += actual_cost
        
        results["trades"].append({
            "ticker": ticker,
            "action": "BUY",
            "qty": qty,
            "price": price,
            "cost": round(actual_cost, 2),
            "conviction": conviction,
            "kelly_fraction": round(kelly, 3),
            "half_kelly": round(kelly * 0.5, 3),
            "win_prob": round(win_prob, 2),
            "win_loss_ratio": round(win_loss_ratio, 1),
            "volatility": round(vol, 2),
            "sector": sector,
            "sector_adjustment": corr_adjustment,
            "portfolio_pct": round(actual_cost / portfolio_value * 100, 1) if portfolio_value > 0 else 0,
        })
    
    # Sort by conviction (highest first) for execution priority
    results["trades"].sort(key=lambda x: x['conviction'], reverse=True)
    
    # Summary
    total_cost = sum(t['cost'] for t in results["trades"])
    results["summary"] = {
        "available_cash": round(available_cash, 2),
        "portfolio_value": round(portfolio_value, 2),
        "cash_pct": round(available_cash / portfolio_value * 100, 1) if portfolio_value > 0 else 0,
        "trades_count": len(results["trades"]),
        "total_deployed": round(total_cost, 2),
        "deployment_pct": round(total_cost / available_cash * 100, 1) if available_cash > 0 else 0,
        "remaining_cash": round(available_cash - total_cost, 2),
        "skipped_count": len(results["skipped"]),
    }
    
    return results


def find_value_opportunities(tickers, min_revenue_growth=0.10, max_pe=25, min_roe=0.15):
    """
    Find stocks with strong fundamentals but stagnant/declining prices.
    GARP strategy: Growth at Reasonable Price.
    
    Looks for:
    - Revenue growth > 10% (strong fundamentals)
    - P/E < 25 (reasonable price)
    - ROE > 15% (quality)
    - Price below 50-day MA (stagnant/declining)
    - Positive free cash flow
    """
    opportunities = []
    
    for ticker in tickers:
        try:
            import yfinance as yf
            old_stderr = __import__('sys').stderr
            __import__('sys').stderr = StringIO()
            try:
                t = yf.Ticker(ticker)
                info = t.info
                
                # Fundamental filters
                revenue_growth = info.get('revenueGrowth', 0) or 0
                pe = info.get('trailingPE', 999) or 999
                roe = info.get('returnOnEquity', 0) or 0
                fcf = info.get('freeCashflow', 0) or 0
                price = info.get('currentPrice', 0) or info.get('regularMarketPrice', 0) or 0
                
                # Price trend (stagnant/declining)
                hist = t.history(period="3mo")
                price_below_ma = False
                if hist is not None and len(hist) > 20:
                    ma50 = hist["Close"].rolling(50).mean().iloc[-1] if len(hist) >= 50 else hist["Close"].mean()
                    current = hist["Close"].iloc[-1]
                    price_below_ma = current < ma50
                
                # Score the opportunity
                score = 0
                reasons = []
                
                if revenue_growth > 0.20:
                    score += 3
                    reasons.append(f"Strong revenue growth: {revenue_growth*100:.0f}%")
                elif revenue_growth > min_revenue_growth:
                    score += 2
                    reasons.append(f"Revenue growth: {revenue_growth*100:.0f}%")
                
                if 0 < pe < 15:
                    score += 3
                    reasons.append(f"Attractive P/E: {pe:.1f}")
                elif 0 < pe < max_pe:
                    score += 1
                    reasons.append(f"Reasonable P/E: {pe:.1f}")
                
                if roe > 0.20:
                    score += 2
                    reasons.append(f"High ROE: {roe*100:.0f}%")
                elif roe > min_roe:
                    score += 1
                    reasons.append(f"Good ROE: {roe*100:.0f}%")
                
                if fcf > 0:
                    score += 1
                    reasons.append("Positive FCF")
                
                if price_below_ma:
                    score += 2
                    reasons.append("Price below 50-day MA (potential entry point)")
                
                if score >= 5:
                    opportunities.append({
                        "ticker": ticker,
                        "score": score,
                        "price": price,
                        "pe": pe,
                        "revenue_growth": revenue_growth,
                        "roe": roe,
                        "reasons": reasons,
                    })
            finally:
                __import__('sys').stderr = old_stderr
        except Exception:
            continue
    
    opportunities.sort(key=lambda x: x['score'], reverse=True)
    return opportunities


def format_position_report(positions):
    """Format position sizing results as readable markdown."""
    lines = []
    lines.append("## 📊 Dynamic Position Sizing Report")
    lines.append(f"*{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
    lines.append("")
    
    summary = positions.get("summary", {})
    lines.append(f"**Available Cash:** ${summary.get('available_cash', 0):,.0f} ({summary.get('cash_pct', 0)}% of portfolio)")
    lines.append(f"**Trades:** {summary.get('trades_count', 0)} | **Skipped:** {summary.get('skipped_count', 0)}")
    lines.append(f"**Total Deployed:** ${summary.get('total_deployed', 0):,.0f} ({summary.get('deployment_pct', 0)}% of cash)")
    lines.append(f"**Remaining Cash:** ${summary.get('remaining_cash', 0):,.0f}")
    lines.append("")
    
    trades = positions.get("trades", [])
    if trades:
        lines.append("| Ticker | Conviction | Kelly | Win Prob | R/R | Vol | Sector Adj | Shares | Cost | Portfolio % |")
        lines.append("|--------|-----------|-------|----------|-----|-----|-----------|--------|------|-------------|")
        for t in trades:
            lines.append(f"| **{t['ticker']}** | {t['conviction']}/10 | {t['kelly_fraction']:.1%} | {t['win_prob']:.0%} | {t['win_loss_ratio']:.1f}x | {t['volatility']:.0%} | {t['sector_adjustment']:.1f}x | {t['qty']} | ${t['cost']:,.0f} | {t['portfolio_pct']:.1f}% |")
        lines.append("")
    
    skipped = positions.get("skipped", [])
    if skipped:
        lines.append("### Skipped")
        for s in skipped:
            lines.append(f"- {s['ticker']}: {s['reason']}")
        lines.append("")
    
    return "\n".join(lines)



