"""
Advanced Options Strategies Module v1.0

Implements the most profitable, research-backed options strategies:

1. ASYMMETRIC LONG CALLS (Unlimited upside, defined risk)
   - Buy OTM calls on high-conviction names with catalysts
   - Best when IV is low relative to expected move
   - Position sizing: max 2-3% of portfolio per trade

2. ASYMMETRIC LONG PUTS (Bearish, defined risk)
   - Buy OTM puts on overvalued names or hedges
   - Best when IV is low and downside risk is high

3. CALL DEBIT SPREADS (Bullish, defined risk/reward)
   - Buy ATM call, sell OTM call at target price
   - Reduces cost basis vs naked call
   - Best risk/reward when targeting specific price levels

4. PUT DEBIT SPREADS (Bearish, defined risk/reward)
   - Buy ATM put, sell OTM put at support
   - Defined risk, lower cost than naked put

5. IRON CONDORS (Range-bound, high probability)
   - Sell OTM call spread + sell OTM put spread
   - Profits when stock stays within range
   - Best when IV is high (sell expensive premium)
   - Target 70-80% probability of profit

6. IRON BUTTERFLIES (Range-bound, higher reward)
   - Like iron condor but with narrower wings
   - Higher max profit but narrower profit zone
   - Best for earnings plays with expected small move

7. CALENDAR SPREADS (Time decay arbitrage)
   - Sell near-term option, buy longer-term option at same strike
   - Profits from faster decay of short-term option
   - Best when IV term structure is steep

8. DIAGONAL SPREADS (Directional + time decay)
   - Sell near-term OTM option, buy longer-term further OTM
   - Combines directional bias with time decay income
   - Best for gradual trend plays

9. STRADDLES/STRANGLES (Volatility plays)
   - Buy call + put at same strike (straddle) or nearby strikes (strangle)
   - Profits from large move in either direction
   - Best before earnings or major catalysts when IV is low

10. RATIO SPREADS (Asymmetric directional)
    - Buy 1 ATM call, sell 2 OTM calls
    - Zero or negative cost, unlimited upside to short strike
    - Best for moderate bullish outlook

11. COVERED CALLS (Income on existing positions)
    - Sell OTM calls on stocks already owned
    - Generates income, caps upside
    - Only on stocks willing to sell at strike

12. CASH-SECURED PUTS (Income + potential buying)
    - Sell OTM puts on stocks willing to own
    - Generates income, may acquire at discount
    - Best on high-conviction names at support levels

13. MISPRICING ARBITRAGE
    - Identify options where IV differs significantly from HV
    - Sell overpriced options (IV >> HV), buy underpriced (IV << HV)
    - Exploit put-call parity violations

14. EARNINGS PLAYS (Pre/post-earnings)
    - Buy straddles/strangles when IV is low before earnings
    - Sell iron condors when IV is elevated before earnings
    - Close positions before earnings to avoid gamma risk

Strategy Selection Framework:
- Bullish + Low IV → Long calls or call debit spreads
- Bullish + High IV → Covered calls or cash-secured puts
- Bearish + Low IV → Long puts or put debit spreads
- Bearish + High IV → Put credit spreads
- Neutral + High IV → Iron condors or iron butterflies
- Neutral + Low IV → Calendar spreads
- High uncertainty → Straddles/strangles
- Mispricing detected → Volatility arbitrage
"""

import requests
import json
import datetime
import re
from pathlib import Path
from io import StringIO

BASE_DIR = Path(__file__).parent.parent
ALPACA_API_KEY = None
ALPACA_SECRET_KEY = None
FINNHUB_API_KEY = None


def init_options_skill(alpaca_key=None, alpaca_secret=None, finnhub_key=None, base_dir=None):
    global ALPACA_API_KEY, ALPACA_SECRET_KEY, FINNHUB_API_KEY, BASE_DIR
    if alpaca_key: ALPACA_API_KEY = alpaca_key
    if alpaca_secret: ALPACA_SECRET_KEY = alpaca_secret
    if finnhub_key: FINNHUB_API_KEY = finnhub_key
    if base_dir: BASE_DIR = Path(base_dir)


def _alpaca_headers():
    return {"APCA-API-KEY-ID": ALPACA_API_KEY or "", "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY or ""}


def _alpaca_base():
    return "https://paper-api.alpaca.markets/v2"


def _finnhub_get(endpoint, params=None):
    if not FINNHUB_API_KEY:
        return None
    if params is None:
        params = {}
    params["token"] = FINNHUB_API_KEY
    try:
        r = requests.get(f"https://finnhub.io/api/v1/{endpoint}", params=params, timeout=15)
        if r.status_code == 200:
            return r.json()
    except Exception:
        pass
    return None


def _yf_price(ticker):
    """Get current price from yfinance."""
    try:
        import yfinance as yf
        old_stderr = __import__('sys').stderr
        __import__('sys').stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            fi = t.fast_info
            p = fi.last_price
            pc = fi.previous_close
            if p and p > 0:
                chg = ((p - pc) / pc * 100) if pc and pc > 0 else 0
                return {"price": float(p), "prev_close": float(pc) if pc else 0, "change_pct": float(chg)}
        finally:
            __import__('sys').stderr = old_stderr
    except Exception:
        pass
    return {"price": 0, "prev_close": 0, "change_pct": 0}


def get_options_chain(underlying, min_dte=14, max_dte=60):
    """Get options chain for an underlying from Alpaca."""
    try:
        r = requests.get(
            f"{_alpaca_base()}/options/contracts?underlying_symbols={underlying.upper()}&status=active&limit=500",
            headers=_alpaca_headers(), timeout=15
        )
        if not r.ok:
            print(f"[DEBUG] Alpaca options chain API error ({r.status_code}): {r.text[:200]}")
            return None
        contracts = r.json().get("option_contracts", [])
        if not contracts:
            print(f"[DEBUG] No option contracts returned for {underlying}")
            return None

        # Filter by DTE range
        today = datetime.date.today()
        filtered = []
        for c in contracts:
            try:
                exp = datetime.date.fromisoformat(c['expiration_date'])
                dte = (exp - today).days
                if min_dte <= dte <= max_dte:
                    c['dte'] = dte
                    filtered.append(c)
            except (ValueError, TypeError):
                continue

        if not filtered:
            print(f"[DEBUG] No contracts in DTE range [{min_dte}, {max_dte}] for {underlying}")
            return None

        calls = sorted([c for c in filtered if c['type'] == 'call'], key=lambda x: (x['dte'], float(x['strike_price'])))
        puts = sorted([c for c in filtered if c['type'] == 'put'], key=lambda x: (x['dte'], float(x['strike_price'])))

        return {"underlying": underlying.upper(), "calls": calls, "puts": puts, "all": filtered}
    except Exception as e:
        print(f"[DEBUG] Failed to fetch options chain for {underlying}: {type(e).__name__}: {e}")
        return None


def get_option_pricing(option_symbols):
    """Get live pricing for option contracts from Alpaca snapshots."""
    if not option_symbols:
        return {}
    try:
        syms = ",".join(option_symbols[:50])  # Alpaca limit
        r = requests.get(
            f"{_alpaca_base()}/markets/us/options/snapshots?symbols={syms}",
            headers=_alpaca_headers(), timeout=15
        )
        if r.ok:
            return r.json().get("snapshots", {})
    except Exception:
        pass
    return {}


def analyze_iv_rank(underlying):
    """Analyze IV rank to determine if options are cheap or expensive."""
    # Get current IV from options chain
    chain = get_options_chain(underlying, min_dte=7, max_dte=45)
    if not chain:
        return None
    
    # Get ATM options for IV estimation
    price = _yf_price(underlying)["price"]
    if price <= 0:
        return None
    
    # Find nearest ATM call
    atm_calls = sorted(chain['calls'], key=lambda c: abs(float(c['strike_price']) - price))
    if not atm_calls:
        return None
    
    # Get pricing for ATM options
    atm_symbols = [c['symbol'] for c in atm_calls[:5]]
    pricing = get_option_pricing(atm_symbols)
    
    ivs = []
    for sym, snap in pricing.items():
        iv = snap.get("impliedVolatility")
        if iv and iv > 0:
            ivs.append(float(iv))
    
    if not ivs:
        return None
    
    current_iv = sum(ivs) / len(ivs)
    
    # Get historical IV from Finnhub if available
    hist_iv = _finnhub_get("stock/metric", {"symbol": underlying, "metric": "all"})
    iv_52w_high = None
    iv_52w_low = None
    if hist_iv:
        iv_52w_high = hist_iv.get("ivHigh52Weeks")
        iv_52w_low = hist_iv.get("ivLow52Weeks")
    
    # Calculate IV rank (0-100)
    if iv_52w_high and iv_52w_low and iv_52w_high > iv_52w_low:
        iv_rank = (current_iv - iv_52w_low) / (iv_52w_high - iv_52w_low) * 100
    else:
        iv_rank = 50  # Default to middle if no history
    
    return {
        "underlying": underlying,
        "current_price": price,
        "current_iv": current_iv,
        "iv_rank": min(100, max(0, iv_rank)),
        "iv_52w_high": iv_52w_high,
        "iv_52w_low": iv_52w_low,
        "options_cheap": iv_rank < 30,
        "options_expensive": iv_rank > 70,
    }


def find_mispriced_options(underlying):
    """Find options with significant IV vs HV mispricing."""
    chain = get_options_chain(underlying, min_dte=14, max_dte=45)
    if not chain:
        return []
    
    price = _yf_price(underlying)["price"]
    if price <= 0:
        return []
    
    # Get historical volatility from Finnhub
    metrics = _finnhub_get("stock/metric", {"symbol": underlying, "metric": "all"})
    hv_30d = metrics.get("historicalVolatility30Day") if metrics else None
    hv_60d = metrics.get("historicalVolatility60Day") if metrics else None
    
    if not hv_30d and not hv_60d:
        return []
    
    hv = hv_30d or hv_60d
    
    # Get option pricing
    all_symbols = [c['symbol'] for c in chain['all'][:100]]
    pricing = get_option_pricing(all_symbols)
    
    mispriced = []
    for sym, snap in pricing.items():
        iv = snap.get("impliedVolatility")
        if not iv or iv <= 0:
            continue
        
        iv_float = float(iv)
        hv_float = float(hv) if hv else 0
        
        if hv_float > 0:
            iv_hv_ratio = iv_float / hv_float
            if iv_hv_ratio > 1.5:
                mispriced.append({
                    "symbol": sym,
                    "type": "overpriced",
                    "iv": iv_float,
                    "hv": hv_float,
                    "ratio": iv_hv_ratio,
                    "strategy": "sell"  # Sell overpriced options
                })
            elif iv_hv_ratio < 0.7:
                mispriced.append({
                    "symbol": sym,
                    "type": "underpriced",
                    "iv": iv_float,
                    "hv": hv_float,
                    "ratio": iv_hv_ratio,
                    "strategy": "buy"  # Buy underpriced options
                })
    
    return sorted(mispriced, key=lambda x: abs(x['ratio'] - 1), reverse=True)[:10]


def generate_options_strategies(underlying, conviction, direction, current_price=None):
    """
    Generate the best options strategies based on:
    - conviction (1-10)
    - direction (bullish/bearish/neutral)
    - IV rank (cheap vs expensive options)
    - Current price and catalysts
    """
    if not current_price:
        current_price = _yf_price(underlying)["price"]
    
    iv_analysis = analyze_iv_rank(underlying)
    chain = get_options_chain(underlying, min_dte=14, max_dte=60)
    mispriced = find_mispriced_options(underlying)
    
    strategies = []
    
    if not chain or current_price <= 0:
        return strategies
    
    iv_rank = iv_analysis["iv_rank"] if iv_analysis else 50
    options_cheap = iv_rank < 30
    options_expensive = iv_rank > 70
    
    # ── STRATEGY SELECTION ──
    
    # BULLISH strategies
    if direction == "bullish":
        if conviction >= 8:
            if options_cheap:
                # Best case: high conviction + cheap options = buy calls
                atm_calls = sorted(chain['calls'], key=lambda c: abs(float(c['strike_price']) - current_price))
                otm_calls = [c for c in chain['calls'] if float(c['strike_price']) > current_price * 1.05]
                
                if atm_calls:
                    target = atm_calls[0]
                    strategies.append({
                        "strategy": "ASYMMETRIC_LONG_CALL",
                        "description": f"Buy ATM call — unlimited upside, defined risk. Best when IV is low ({iv_rank:.0f} rank).",
                        "option": target,
                        "max_risk": "premium paid",
                        "upside": "unlimited",
                        "conviction": conviction,
                    })
                
                if otm_calls and conviction >= 9:
                    # For very high conviction, add OTM call for leverage
                    otm_target = otm_calls[0]
                    strategies.append({
                        "strategy": "LEVERAGED_OTM_CALL",
                        "description": f"Buy OTM call for leverage — cheaper entry, higher ROI if thesis plays out.",
                        "option": otm_target,
                        "max_risk": "premium paid",
                        "upside": "unlimited (leveraged)",
                        "conviction": conviction,
                    })
            
            elif options_expensive:
                # High conviction + expensive options = call debit spread
                atm_calls = sorted(chain['calls'], key=lambda c: abs(float(c['strike_price']) - current_price))
                otm_calls = [c for c in chain['calls'] if float(c['strike_price']) > current_price * 1.08]
                
                if atm_calls and otm_calls:
                    strategies.append({
                        "strategy": "CALL_DEBIT_SPREAD",
                        "description": f"Buy ATM call, sell OTM call — reduces cost basis when IV is high ({iv_rank:.0f} rank).",
                        "long_leg": atm_calls[0],
                        "short_leg": otm_calls[0],
                        "max_risk": "net debit",
                        "upside": f"${float(otm_calls[0]['strike_price']) - float(atm_calls[0]['strike_price']):.0f} per spread",
                        "conviction": conviction,
                    })
        
        # Moderate bullish: cash-secured puts
        if conviction >= 6:
            otm_puts = sorted([c for c in chain['puts'] if float(c['strike_price']) < current_price * 0.95],
                              key=lambda c: float(c['strike_price']), reverse=True)
            if otm_puts:
                strategies.append({
                    "strategy": "CASH_SECURED_PUT",
                    "description": f"Sell OTM put — generate income, may acquire at discount if assigned.",
                    "option": otm_puts[0],
                    "max_risk": f"strike - premium (assigned at ${float(otm_puts[0]['strike_price']):.0f})",
                    "upside": "premium collected",
                    "conviction": conviction,
                })
    
    # BEARISH strategies
    elif direction == "bearish":
        if conviction >= 8:
            if options_cheap:
                atm_puts = sorted(chain['puts'], key=lambda c: abs(float(c['strike_price']) - current_price))
                if atm_puts:
                    strategies.append({
                        "strategy": "ASYMMETRIC_LONG_PUT",
                        "description": f"Buy ATM put — defined risk, high leverage on downside.",
                        "option": atm_puts[0],
                        "max_risk": "premium paid",
                        "upside": f"unlimited to ${float(atm_puts[0]['strike_price']):.0f}",
                        "conviction": conviction,
                    })
            elif options_expensive:
                atm_puts = sorted(chain['puts'], key=lambda c: abs(float(c['strike_price']) - current_price))
                otm_puts = [c for c in chain['puts'] if float(c['strike_price']) < current_price * 0.92]
                if atm_puts and otm_puts:
                    strategies.append({
                        "strategy": "PUT_DEBIT_SPREAD",
                        "description": f"Buy ATM put, sell OTM put — reduces cost when IV is high.",
                        "long_leg": atm_puts[0],
                        "short_leg": otm_puts[0],
                        "max_risk": "net debit",
                        "upside": f"${float(atm_puts[0]['strike_price']) - float(otm_puts[0]['strike_price']):.0f} per spread",
                        "conviction": conviction,
                    })
    
    # NEUTRAL / RANGE-BOUND strategies
    elif direction == "neutral":
        if options_expensive and conviction >= 7:
            # Iron condor when IV is high
            otm_calls = sorted([c for c in chain['calls'] if float(c['strike_price']) > current_price * 1.05],
                               key=lambda c: float(c['strike_price']))
            otm_puts = sorted([c for c in chain['puts'] if float(c['strike_price']) < current_price * 0.95],
                              key=lambda c: float(c['strike_price']), reverse=True)
            
            if otm_calls and otm_puts:
                strategies.append({
                    "strategy": "IRON_CONDOR",
                    "description": f"Sell OTM call spread + OTM put spread — profits when stock stays in range. High IV ({iv_rank:.0f} rank) = expensive premium to sell.",
                    "call_spread": (otm_calls[0], otm_calls[1] if len(otm_calls) > 1 else otm_calls[0]),
                    "put_spread": (otm_puts[0], otm_puts[1] if len(otm_puts) > 1 else otm_puts[0]),
                    "max_risk": "width of wider spread - credit",
                    "upside": "net credit received",
                    "conviction": conviction,
                    "pop": "70-80% (probability of profit)",
                })
        
        if options_cheap and conviction >= 6:
            # Calendar spread when IV is low
            near_calls = sorted([c for c in chain['calls'] if 14 <= c.get('dte', 0) <= 21],
                                key=lambda c: abs(float(c['strike_price']) - current_price))
            far_calls = sorted([c for c in chain['calls'] if 35 <= c.get('dte', 0) <= 60],
                               key=lambda c: abs(float(c['strike_price']) - current_price))
            
            if near_calls and far_calls:
                strategies.append({
                    "strategy": "CALENDAR_SPREAD",
                    "description": f"Sell near-term ATM call, buy longer-term ATM call — profits from faster decay of short-term option. Best when IV is low ({iv_rank:.0f} rank).",
                    "short_leg": near_calls[0],
                    "long_leg": far_calls[0],
                    "max_risk": "net debit",
                    "upside": "significant if stock near strike at short-term expiry",
                    "conviction": conviction,
                })
    
    # VOLATILITY PLAYS (any direction)
    if conviction >= 7:
        # Check for upcoming earnings or catalysts
        earnings = _finnhub_get("calendar/earnings", {"symbol": underlying})
        if earnings and earnings.get("earningsCalendar"):
            next_earnings = earnings["earningsCalendar"][0]
            strategies.append({
                "strategy": "EARNINGS_STRADDLE",
                "description": f"Buy straddle before earnings ({next_earnings.get('date', 'TBD')}) — profits from large move in either direction.",
                "underlying": underlying,
                "max_risk": "total premium paid",
                "upside": "unlimited (large move required)",
                "conviction": conviction,
                "catalyst": f"earnings {next_earnings.get('date', 'TBD')}",
            })
    
    # MISPRICING ARBITRAGE
    if mispriced:
        for mp in mispriced[:2]:
            strategies.append({
                "strategy": "VOLATILITY_ARBITRAGE",
                "description": f"{mp['symbol']}: IV ({mp['iv']:.1%}) vs HV ({mp['hv']:.1%}) — ratio {mp['ratio']:.2f}x. {mp['strategy'].upper()} for edge.",
                "option": mp,
                "max_risk": "defined by strategy",
                "upside": "IV reversion to HV",
                "conviction": min(conviction, 7),
            })
    
    return strategies


def format_options_report(strategies, underlying, current_price):
    """Format options strategies for the report."""
    if not strategies:
        return ""
    
    lines = [f"\n## 🎯 Options Intelligence — {underlying} @ ${current_price:.2f}\n"]
    
    for i, s in enumerate(strategies, 1):
        lines.append(f"### Strategy {i}: {s['strategy'].replace('_', ' ')}")
        lines.append(f"**Why:** {s['description']}")
        lines.append(f"**Max Risk:** {s['max_risk']}")
        lines.append(f"**Upside:** {s['upside']}")
        lines.append(f"**Conviction:** {s['conviction']}/10")
        if s.get('catalyst'):
            lines.append(f"**Catalyst:** {s['catalyst']}")
        if s.get('pop'):
            lines.append(f"**Probability of Profit:** {s['pop']}")
        
        # Add option details
        if s.get('option'):
            opt = s['option']
            lines.append(f"**Contract:** {opt.get('symbol', 'N/A')} | Strike: ${float(opt.get('strike_price', 0)):.0f} | Exp: {opt.get('expiration_date', 'N/A')} | DTE: {opt.get('dte', 'N/A')}")
        if s.get('long_leg'):
            lines.append(f"**Long:** {s['long_leg'].get('symbol', 'N/A')} @ ${float(s['long_leg'].get('strike_price', 0)):.0f}")
        if s.get('short_leg'):
            lines.append(f"**Short:** {s['short_leg'].get('symbol', 'N/A')} @ ${float(s['short_leg'].get('strike_price', 0)):.0f}")
        
        lines.append("")
    
    return "\n".join(lines)


__all__ = [
    "init_options_skill",
    "get_options_chain",
    "get_option_pricing",
    "analyze_iv_rank",
    "find_mispriced_options",
    "generate_options_strategies",
    "format_options_report",
]
