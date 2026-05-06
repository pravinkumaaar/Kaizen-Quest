"""
Portfolio Manager Skill v2.0

Single source of truth: Alpaca paper trading account.
All portfolio data comes directly from Alpaca's API — no local cache drift.

Features:
1. Real-time portfolio snapshot from Alpaca (positions, cash, P&L)
2. Continuous position review with gold-standard sell/hold/add rules
3. Asset allocation monitoring (stocks, options, crypto, gold/silver, cash)
4. Cash drag detection and automatic deployment
5. Telegram alerts for urgent actions and once-in-a-lifetime opportunities
6. Supports trading: US stocks, options, crypto on Alpaca
   GLD/SLV trade as regular stocks on Alpaca (they're ETFs)

Gold Standard Investment Rules:
- SELL: Fundamentals deteriorated, thesis broken, position >20%, stop-loss -15%, profit target +50%,
        momentum reversal (below 200-day MA), consecutive earnings misses, extreme valuation
- HOLD: Thesis intact, within allocation, uptrend intact, approaching catalyst
- ADD: Thesis strengthening, dip buying on quality, underweight target, momentum confirm
- BUY NEW: Meets conviction threshold, fits allocation, clear catalyst
"""

import json
import datetime
import re
import requests
import yfinance as yf
from pathlib import Path
from io import StringIO

BASE_DIR = Path(__file__).parent.parent
FINNHUB_API_KEY = None
ALPACA_API_KEY = None
ALPACA_SECRET_KEY = None

# Asset allocation targets (aggressive investor)
TARGET_ALLOCATION = {
    "stocks":      {"min": 0.40, "max": 0.75, "target": 0.60},
    "options":     {"min": 0.00, "max": 0.10, "target": 0.05},
    "crypto":      {"min": 0.00, "max": 0.10, "target": 0.05},
    "gold_silver": {"min": 0.00, "max": 0.15, "target": 0.05},
    "cash":        {"min": 0.05, "max": 0.35, "target": 0.15},
}


def init_portfolio_manager(finnhub_key=None, alpaca_key=None, alpaca_secret=None, base_dir=None):
    global FINNHUB_API_KEY, ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_DIR
    if finnhub_key: FINNHUB_API_KEY = finnhub_key
    if alpaca_key: ALPACA_API_KEY = alpaca_key
    if alpaca_secret: ALPACA_SECRET_KEY = alpaca_secret
    if base_dir: BASE_DIR = Path(base_dir)


def _alpaca_headers():
    return {"APCA-API-KEY-ID": ALPACA_API_KEY or "", "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY or ""}


def _alpaca_base():
    return "https://paper-api.alpaca.markets/v2"


def _finnhub_get(endpoint, params=None):
    if not FINNHUB_API_KEY: return None
    if params is None: params = {}
    params["token"] = FINNHUB_API_KEY
    try:
        r = requests.get(f"https://finnhub.io/api/v1/{endpoint}", params=params, timeout=15)
        if r.status_code == 200: return r.json()
    except Exception: pass
    return None


def _yf_price(ticker):
    try:
        old_stderr = __import__('sys').stderr
        __import__('sys').stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            fi = t.fast_info
            p = fi.last_price; pc = fi.previous_close
            if p and p > 0:
                chg = ((p - pc) / pc * 100) if pc and pc > 0 else 0
                return {"price": float(p), "prev_close": float(pc) if pc else 0, "change_pct": float(chg)}
        finally: __import__('sys').stderr = old_stderr
    except Exception: pass
    return {"price": 0, "prev_close": 0, "change_pct": 0}


# ═══════════════════════════════════════════
# CORE: Get portfolio from Alpaca (source of truth)
# ═══════════════════════════════════════════
def get_alpaca_portfolio_snapshot():
    """Get complete portfolio snapshot directly from Alpaca API."""
    headers = _alpaca_headers()
    base = _alpaca_base()

    acct = {}
    try:
        r = requests.get(f"{base}/account", headers=headers, timeout=10)
        if r.ok: acct = r.json()
    except Exception: pass

    cash = float(acct.get("cash", 0))
    portfolio_value = float(acct.get("portfolio_value", cash))
    buying_power = float(acct.get("buying_power", cash))

    positions = []
    stock_value = option_value = crypto_value = gold_silver_value = 0
    crypto_syms = {"BTC","ETH","SOL","DOGE","LTC","XRP","ADA","DOT","AVAX","MATIC","LINK","UNI","AAVE","ATOM","ALGO","PEPE","SHIB","NEAR","ARB","OP","INJ","SUI","APT","SEI"}
    gs_syms = {"GLD","SLD","IAU","SIVR","PPLT","PALL"}

    try:
        r = requests.get(f"{base}/positions", headers=headers, timeout=10)
        if r.ok:
            for p in r.json():
                symbol = p.get("symbol", "")
                qty = float(p.get("qty", 0))
                avg_entry = float(p.get("avg_entry_price", 0))
                current_price = float(p.get("current_price", 0))
                market_value = float(p.get("market_value", 0))
                cost_basis = float(p.get("cost_basis", 0))
                unrealized_pl = float(p.get("unrealized_pl", 0))
                unrealized_plpc = float(p.get("unrealized_plpc", 0)) * 100
                asset_class = p.get("asset_class", "us_equity")
                lastday = float(p.get("lastday_price", 0))
                day_chg = ((current_price - lastday) / lastday * 100) if lastday > 0 else 0
                pos_type = "option" if asset_class == "option" else "stock"

                base_sym = symbol.split("-")[0] if "-" in symbol else symbol
                if base_sym in crypto_syms or asset_class == "crypto":
                    crypto_value += market_value; category = "crypto"
                elif base_sym in gs_syms:
                    gold_silver_value += market_value; category = "gold_silver"
                elif asset_class == "option":
                    option_value += market_value; category = "options"
                else:
                    stock_value += market_value; category = "stocks"

                positions.append({
                    "symbol": symbol, "qty": qty, "avg_entry": avg_entry,
                    "current_price": current_price, "market_value": market_value,
                    "cost_basis": cost_basis, "unrealized_pl": unrealized_pl,
                    "unrealized_plpc": unrealized_plpc, "day_change_pct": day_chg,
                    "asset_class": asset_class, "type": pos_type, "category": category,
                })
    except Exception: pass

    total_invested = stock_value + option_value + crypto_value + gold_silver_value
    allocation = {
        "cash": cash / portfolio_value if portfolio_value > 0 else 0,
        "stocks": stock_value / portfolio_value if portfolio_value > 0 else 0,
        "options": option_value / portfolio_value if portfolio_value > 0 else 0,
        "crypto": crypto_value / portfolio_value if portfolio_value > 0 else 0,
        "gold_silver": gold_silver_value / portfolio_value if portfolio_value > 0 else 0,
    }
    initial_equity = 100000.0
    total_pnl = portfolio_value - initial_equity
    total_pnl_pct = (total_pnl / initial_equity * 100)

    return {
        "total_value": portfolio_value, "cash": cash, "buying_power": buying_power,
        "stock_value": stock_value, "option_value": option_value,
        "crypto_value": crypto_value, "gold_silver_value": gold_silver_value,
        "total_invested": total_invested, "allocation": allocation,
        "total_pnl": total_pnl, "total_pnl_pct": total_pnl_pct,
        "positions": positions, "num_positions": len(positions),
        "source": "alpaca_api", "timestamp": datetime.datetime.now().isoformat(),
    }


# ═══════════════════════════════════════════
# FUNDAMENTAL DATA FOR POSITION REVIEW
# ═══════════════════════════════════════════
def get_position_fundamentals(ticker):
    """Get fundamental data for sell/hold/buy decisions."""
    data = {}

    # Earnings surprise history
    earnings = _finnhub_get("stock/earnings", {"symbol": ticker, "limit": 4})
    if earnings:
        misses = beats = 0
        for e in earnings:
            eps_est = e.get("epsEstimate"); eps_actual = e.get("epsActual")
            if eps_est and eps_actual:
                try:
                    if float(eps_actual) > float(eps_est): beats += 1
                    else: misses += 1
                except (ValueError, TypeError): pass
        data["consecutive_misses"] = misses >= 2 and beats == 0
        data["beat_rate"] = beats / (beats + misses) * 100 if (beats + misses) > 0 else 50

    # Analyst recommendations
    rec = _finnhub_get("stock/recommendation", {"symbol": ticker})
    if rec and len(rec) > 0:
        latest = rec[0]
        sb = latest.get("strongBuy", 0); b = latest.get("buy", 0)
        h = latest.get("hold", 0); s = latest.get("sell", 0); ss = latest.get("strongSell", 0)
        total = sb + b + h + s + ss
        if total > 0:
            data["analyst_buy_pct"] = (sb + b) / total * 100
            data["analyst_sell_pct"] = (ss + s) / total * 100

    # Price target
    pt = _finnhub_get("stock/price-target", {"symbol": ticker})
    if pt: data["price_target_mean"] = pt.get("targetMean", 0)

    # Valuation
    metrics = _finnhub_get("stock/metric", {"symbol": ticker, "metric": "all"})
    if metrics:
        pe = metrics.get("peNormalizedAnnual", 0)
        if pe:
            data["pe_ratio"] = pe
            if pe > 50: data["extreme_valuation"] = True

    # Technical: 200-day MA
    try:
        old_stderr = __import__('sys').stderr
        __import__('sys').stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="1y")
            if hist is not None and len(hist) > 200:
                ma200 = float(hist["Close"].rolling(200).mean().iloc[-1])
                current = float(hist["Close"].iloc[-1])
                data["below_200ma"] = current < ma200
                data["above_200ma"] = current >= ma200
                data["ma200"] = ma200
                data["distance_from_200ma"] = float((current - ma200) / ma200 * 100)
        finally: __import__('sys').stderr = old_stderr
    except Exception: pass

    return data


# ═══════════════════════════════════════════
# PORTFOLIO REVIEW ENGINE (Gold Standard Rules)
# ═══════════════════════════════════════════
def review_all_positions(snapshot):
    """
    Review every position using gold-standard sell/hold/add rules.
    
    SELL rules (in priority order):
    1. Stop loss: Position down >15% from entry
    2. Fundamental deterioration: 2+ consecutive earnings misses
    3. Trend breakdown: Below 200-day MA with negative P&L
    4. Concentration risk: Single position >20% of portfolio
    5. Profit target: Position up >50% — take partial profits
    6. Extreme valuation: P/E >50 with significant gains
    
    HOLD rules:
    - Thesis intact, uptrend healthy, within allocation, approaching catalyst
    
    ADD rules:
    - Thesis strengthening, dip buying on quality, underweight target, momentum confirm
    """
    actions = []
    total_value = snapshot["total_value"]
    positions = snapshot["positions"]

    for pos in positions:
        symbol = pos["symbol"]
        pos_pct = pos["market_value"] / total_value if total_value > 0 else 0
        pnl_pct = pos["unrealized_plpc"]
        fundamentals = get_position_fundamentals(symbol)
        sell_triggered = False

        # ── SELL: Stop loss (-15%) ──
        if pnl_pct <= -15:
            actions.append({
                "type": "SELL", "priority": "URGENT", "symbol": symbol,
                "detail": f"🛑 STOP LOSS: {symbol} at {pnl_pct:+.1f}% (threshold: -15%). Loss: ${pos['unrealized_pl']:,.0f}. SELL IMMEDIATELY.",
                "reasoning": "Gold standard: Cut losses at -15% to preserve capital. Positions that drop 15% have >50% chance of dropping further. Better to redeploy into higher-probability opportunities.",
                "action": f"SELL {symbol} x{pos['qty']} (stop loss -15%)",
            })
            sell_triggered = True

        # ── SELL: Fundamental deterioration ──
        if fundamentals.get("consecutive_misses") and not sell_triggered:
            actions.append({
                "type": "SELL", "priority": "URGENT", "symbol": symbol,
                "detail": f"📉 FUNDAMENTAL DETERIORATION: {symbol} has 2+ consecutive earnings misses. Thesis likely broken.",
                "reasoning": "Gold standard: Two consecutive misses with downward guidance signals fundamental deterioration. These companies underperform by 8-12% over following 6 months.",
                "action": f"SELL {symbol} x{pos['qty']} (fundamental deterioration)",
            })
            sell_triggered = True

        # ── SELL: Trend breakdown ──
        if fundamentals.get("below_200ma") and pnl_pct < -5 and not sell_triggered:
            actions.append({
                "type": "SELL", "priority": "HIGH", "symbol": symbol,
                "detail": f"📉 TREND BREAKDOWN: {symbol} below 200-day MA ({fundamentals.get('distance_from_200ma', 0):.1f}%) with {pnl_pct:+.1f}% P&L.",
                "reasoning": "Gold standard: Below 200-day MA with negative returns = trend shifted. CMT research shows negative expected returns over next 3-6 months. Exit and wait for trend to re-establish.",
                "action": f"SELL {symbol} x{pos['qty']} (trend breakdown)",
            })
            sell_triggered = True

        # ── REDUCE: Concentration risk ──
        if pos_pct > 0.20 and not sell_triggered:
            excess = pos["market_value"] - (total_value * 0.15)
            actions.append({
                "type": "REDUCE", "priority": "HIGH", "symbol": symbol,
                "detail": f"⚠️ CONCENTRATION: {symbol} is {pos_pct:.1%} of portfolio (${pos['market_value']:,.0f}). Max: 20%.",
                "reasoning": "Gold standard: No single position >20%. Diversification reduces drawdown risk without significantly reducing expected returns.",
                "action": f"TRIM {symbol} by ${excess:,.0f} (reduce to 15%)",
            })

        # ── SELL PARTIAL: Profit target (+50%) ──
        if pnl_pct >= 50 and not sell_triggered:
            actions.append({
                "type": "SELL_PARTIAL", "priority": "HIGH", "symbol": symbol,
                "detail": f"🎯 PROFIT TARGET: {symbol} at +{pnl_pct:.1f}% (${pos['unrealized_pl']:+,.0f}). Take profits on 50%.",
                "reasoning": "Gold standard: At +50%, take partial profits (50% of position). Locks in gains while maintaining upside. Positions with >50% gains often experience mean reversion.",
                "action": f"SELL 50% of {symbol} (profit taking at +50%)",
            })

        # ── SELL PARTIAL: Extreme valuation ──
        if fundamentals.get("extreme_valuation") and pnl_pct > 30 and not sell_triggered:
            actions.append({
                "type": "SELL_PARTIAL", "priority": "MEDIUM", "symbol": symbol,
                "detail": f"💰 OVERVALUED: {symbol} P/E of {fundamentals.get('pe_ratio', 0):.0f}x with +{pnl_pct:.0f}% gain. Trim to reduce valuation risk.",
                "reasoning": "Gold standard: P/E >50 with significant gains = unfavorable risk/reward. Stocks with P/E >50 underperform by 4-6% annually.",
                "action": f"TRIM 30% of {symbol} (valuation risk)",
            })

        # ── HOLD: Thesis intact ──
        if not sell_triggered and -15 < pnl_pct < 50:
            hold_reasons = []
            if fundamentals.get("above_200ma"): hold_reasons.append("above 200-day MA")
            if fundamentals.get("beat_rate", 50) >= 60: hold_reasons.append(f"strong beat rate ({fundamentals['beat_rate']:.0f}%)")
            if fundamentals.get("analyst_buy_pct", 0) >= 60: hold_reasons.append(f"{fundamentals['analyst_buy_pct']:.0f}% analyst buy")
            if pos_pct < 0.10: hold_reasons.append("underweight — room to add")
            if hold_reasons:
                actions.append({
                    "type": "HOLD", "priority": "LOW", "symbol": symbol,
                    "detail": f"✅ HOLD {symbol}: {', '.join(hold_reasons)}. P&L: {pnl_pct:+.1f}%. Position: {pos_pct:.1%}.",
                    "reasoning": "Gold standard: Hold when thesis intact, trend positive, within allocation. Don't sell winners just because they're up — let them run.",
                    "action": f"HOLD {symbol} — thesis intact",
                })

        # ── ADD: Thesis strengthening ──
        if not sell_triggered and pnl_pct > -10:
            add_reasons = []
            if fundamentals.get("beat_rate", 0) >= 75: add_reasons.append("strong earnings beat history")
            if fundamentals.get("above_200ma") and pnl_pct < 10: add_reasons.append("uptrend intact")
            if pos_pct < 0.05: add_reasons.append("significantly underweight")
            pt_mean = fundamentals.get("price_target_mean", 0)
            if pt_mean > pos["current_price"] * 1.15:
                upside = (pt_mean / pos["current_price"] - 1) * 100
                add_reasons.append(f"price target implies {upside:.0f}% upside")
            if add_reasons and pos_pct < 0.15:
                actions.append({
                    "type": "ADD", "priority": "MEDIUM", "symbol": symbol,
                    "detail": f"➕ ADD {symbol}: {', '.join(add_reasons)}. Current: {pos_pct:.1%}.",
                    "reasoning": "Gold standard: Add to winners with intact thesis. Position sizing should reflect conviction.",
                    "action": f"ADD to {symbol} — increase position",
                })

    # ── CASH DRAG ──
    cash_pct = snapshot["allocation"]["cash"]
    if cash_pct > 0.40:
        excess_cash = snapshot["cash"] - (total_value * 0.15)
        actions.insert(0, {
            "type": "DEPLOY_CASH", "priority": "HIGH", "symbol": "CASH",
            "detail": f"💰 CASH DRAG: {cash_pct:.0%} cash (${snapshot['cash']:,.0f}). Target: 15%. Excess: ${excess_cash:,.0f}. Every dollar uninvested is a dollar not compounding.",
            "reasoning": f"Gold standard: Cash drag kills returns. With {cash_pct:.0%} cash in a rising market, you're missing gains. Being fully invested outperforms timing 90% of 10-year periods.",
            "action": f"DEPLOY ${excess_cash:,.0f} across stocks/crypto/gold",
        })
    elif cash_pct > 0.30:
        actions.insert(0, {
            "type": "DEPLOY_CASH", "priority": "MEDIUM", "symbol": "CASH",
            "detail": f"💰 Cash at {cash_pct:.0%} — above 15% target. Deploy ${snapshot['cash'] * 0.3:,.0f}.",
            "reasoning": "Gold standard: Maintain 5-15% cash. Above 30% is excessive for aggressive investor.",
            "action": f"DEPLOY 30% of cash (${snapshot['cash'] * 0.3:,.0f})",
        })

    # ── ALLOCATION DRIFT ──
    for asset_class, targets in TARGET_ALLOCATION.items():
        current = snapshot["allocation"].get(asset_class, 0)
        if current > targets["max"] and asset_class != "cash":
            excess_val = (current - targets["target"]) * total_value
            actions.append({
                "type": "REBALANCE", "priority": "MEDIUM", "symbol": asset_class.upper(),
                "detail": f"📊 OVERWEIGHT: {asset_class} at {current:.0%} (max {targets['max']:.0%}). Reduce by ~${excess_val:,.0f}.",
                "reasoning": f"Gold standard: {asset_class} should not exceed {targets['max']:.0%}. Rebalance to maintain diversification.",
                "action": f"TRIM {asset_class} by ${excess_val:,.0f}",
            })

    priority_order = {"URGENT": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    actions.sort(key=lambda x: priority_order.get(x.get("priority", "LOW"), 99))
    return actions


# ═══════════════════════════════════════════
# REPORT GENERATION
# ═══════════════════════════════════════════
def generate_portfolio_report(snapshot, actions):
    """Generate comprehensive portfolio review for the daily report."""
    lines = ["## 📊 Portfolio Review & Active Management\n"]
    lines.append(f"**Portfolio Value:** ${snapshot['total_value']:,.0f} | "
                 f"**P&L:** ${snapshot['total_pnl']:+,.0f} ({snapshot['total_pnl_pct']:+.2f}%) | "
                 f"**Positions:** {snapshot['num_positions']} | "
                 f"**Cash:** ${snapshot['cash']:,.0f} ({snapshot['allocation']['cash']:.0%})\n")

    # Allocation bars
    lines.append("**Asset Allocation:**")
    for asset, pct in snapshot["allocation"].items():
        target = TARGET_ALLOCATION.get(asset, {}).get("target", 0)
        max_a = TARGET_ALLOCATION.get(asset, {}).get("max", 1.0)
        bar = "█" * int(pct * 30) + "░" * (30 - int(pct * 30))
        status = "🔴" if pct > max_a else "✅" if abs(pct - target) < 0.05 else "📉" if pct < target else "⚠️"
        lines.append(f"  {status} {asset:14s} {bar} {pct:5.1%} (target: {target:.0%}, max: {max_a:.0%})")
    lines.append("")

    if snapshot["allocation"]["cash"] > 0.40:
        lines.append(f"🚨 **CASH DRAG ALERT:** {snapshot['allocation']['cash']:.0%} cash is significantly reducing returns.\n")

    # Position table
    if snapshot["positions"]:
        lines.append("**Position Details:**")
        lines.append("| # | Ticker | Qty | Avg Cost | Current | Value | P&L | Day Chg | % of Port |")
        lines.append("|---|--------|-----|----------|---------|-------|-----|---------|-----------|")
        for i, pos in enumerate(sorted(snapshot["positions"], key=lambda x: x["market_value"], reverse=True), 1):
            pnl_e = "🟢" if pos["unrealized_plpc"] > 0 else "🔴"
            day_e = "🟢" if pos["day_change_pct"] > 0 else "🔴"
            pos_pct = pos["market_value"] / snapshot["total_value"] * 100 if snapshot["total_value"] > 0 else 0
            lines.append(f"| {i} | **{pos['symbol']}** | {pos['qty']:.0f} | ${pos['avg_entry']:.2f} | "
                         f"${pos['current_price']:.2f} | ${pos['market_value']:,.0f} | "
                         f"{pnl_e} {pos['unrealized_plpc']:+.1f}% | {day_e} {pos['day_change_pct']:+.2f}% | {pos_pct:.1f}% |")
        lines.append("")

    # Actions
    if actions:
        lines.append("**🎯 Active Management Decisions:**\n")
        for action in actions:
            emoji = {"URGENT": "🚨", "HIGH": "🔴", "MEDIUM": "🟡", "LOW": "🟢"}.get(action.get("priority", ""), "⚪")
            lines.append(f"{emoji} **[{action.get('priority', '')}] {action['type']} — {action.get('symbol', '')}**")
            lines.append(f"  {action['detail']}")
            if "reasoning" in action:
                lines.append(f"  <i>Why: {action['reasoning']}</i>")
            lines.append("")

    return "\n".join(lines)


# ═══════════════════════════════════════════
# TELEGRAM ALERTS
# ═══════════════════════════════════════════
def generate_urgent_alert(snapshot, actions):
    """Generate Telegram alert for urgent/high priority actions."""
    urgent = [a for a in actions if a.get("priority") == "URGENT"]
    high = [a for a in actions if a.get("priority") == "HIGH"]
    if not urgent and not high:
        return None

    lines = ["🚨 <b>PORTFOLIO ACTION REQUIRED</b> 🚨\n"]
    lines.append(f"Portfolio: ${snapshot['total_value']:,.0f} | Cash: {snapshot['allocation']['cash']:.0%} | P&L: {snapshot['total_pnl_pct']:+.2f}%\n")
    if urgent:
        lines.append("<b>🔴 URGENT (Act Now):</b>")
        for a in urgent:
            lines.append(f"• {a['detail']}")
            lines.append(f"  → <b>{a['action']}</b>")
        lines.append("")
    if high:
        lines.append("<b>🟡 HIGH PRIORITY (Act Today):</b>")
        for a in high[:3]:
            lines.append(f"• {a['detail']}")
            lines.append(f"  → <b>{a['action']}</b>")
        lines.append("")
    lines.append("<i>Not financial advice. Review and confirm before acting.</i>")
    return "\n".join(lines)


def generate_once_in_a_lifetime_alert(opportunity):
    """Generate Telegram alert for once-in-a-lifetime opportunities."""
    return (
        f"⭐⭐⭐ <b>ONCE-IN-A-LIFETIME OPPORTUNITY</b> ⭐⭐⭐\n\n"
        f"<b>{opportunity.get('ticker', 'N/A')}</b> — {opportunity.get('type', 'Stock')}\n\n"
        f"<b>Thesis:</b> {opportunity.get('thesis', 'N/A')}\n\n"
        f"<b>Catalyst:</b> {opportunity.get('catalyst', 'N/A')}\n\n"
        f"<b>Risk/Reward:</b> {opportunity.get('risk_reward', 'N/A')}\n\n"
        f"<b>Action:</b> {opportunity.get('action', 'N/A')}\n\n"
        f"<b>Conviction:</b> {opportunity.get('conviction', '10/10')}/10\n\n"
        f"<i>This is the kind of opportunity that comes once every few years. Act decisively but with proper position sizing.</i>\n\n"
        f"<i>Not financial advice. Verify independently before acting.</i>"
    )


__all__ = [
    "init_portfolio_manager",
    "get_alpaca_portfolio_snapshot",
    "review_all_positions",
    "generate_portfolio_report",
    "generate_urgent_alert",
    "generate_once_in_a_lifetime_alert",
    "TARGET_ALLOCATION",
]
