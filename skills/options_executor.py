"""
Options Executor Skill v2.0

Handles execution of all options strategies via Alpaca's Trading API.
Supports both single-leg and multi-leg strategies using OrderClass.MLEG.

Strategy Types:
- Single: Long Call, Long Put, Cash-Secured Put, Covered Call
- Spreads: Call Debit Spread, Put Debit Spread, Call Credit Spread, Put Credit Spread
- Iron: Iron Condor, Iron Butterfly (4 legs)
- Calendar: Call Calendar Spread, Put Calendar Spread (2 legs, different expirations)
- Volatility: Long Straddle, Long Strangle, Short Straddle, Short Strangle

All multi-leg orders use Alpaca's native MLEG (multi-leg) order class.
"""

import json
import datetime
import time
import requests
from pathlib import Path
from io import StringIO

BASE_DIR = Path(__file__).parent.parent
ALPACA_API_KEY = None
ALPACA_SECRET_KEY = None

# Alpaca options trading levels
# Level 1: Covered calls, cash-secured puts
# Level 2: Long calls, long puts, spreads
# Level 3: Multi-leg strategies (iron condors, butterflies, straddles)
# Level 4: Uncovered options (not used - we only do defined-risk)


def init_options_executor(alpaca_key=None, alpaca_secret=None, base_dir=None):
    global ALPACA_API_KEY, ALPACA_SECRET_KEY, BASE_DIR
    if alpaca_key: ALPACA_API_KEY = alpaca_key
    if alpaca_secret: ALPACA_SECRET_KEY = alpaca_secret
    if base_dir: BASE_DIR = Path(base_dir)


def _headers():
    return {
        "APCA-API-KEY-ID": ALPACA_API_KEY or "",
        "APCA-API-SECRET-KEY": ALPACA_SECRET_KEY or "",
        "Content-Type": "application/json"
    }


def _base():
    return "https://paper-api.alpaca.markets/v2"


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
                return float(p)
        finally:
            __import__('sys').stderr = old_stderr
    except Exception:
        pass
    return 0


def get_options_chain(underlying, min_dte=7, max_dte=60, option_type=None):
    """Get options chain from Alpaca."""
    try:
        url = f"{_base()}/options/contracts"
        params = {
            "underlying_symbols": underlying.upper(),
            "status": "active",
            "limit": 500,
        }
        if option_type:
            params["type"] = option_type
        
        r = requests.get(url, headers=_headers(), params=params, timeout=15)
        if not r.ok:
            return []
        
        contracts = r.json().get("option_contracts", [])
        today = datetime.date.today()
        
        filtered = []
        for c in contracts:
            try:
                exp = datetime.date.fromisoformat(c['expiration_date'])
                dte = (exp - today).days
                if min_dte <= dte <= max_dte:
                    c['dte'] = dte
                    c['strike_price'] = float(c['strike_price'])
                    filtered.append(c)
            except (ValueError, TypeError):
                continue
        
        return sorted(filtered, key=lambda x: (x['dte'], x['strike_price']))
    except Exception:
        return []


def find_option_symbol(underlying, option_type, strike_price, target_dte, tolerance=7):
    """Find the best matching option symbol for given parameters."""
    contracts = get_options_chain(underlying, min_dte=target_dte - tolerance, max_dte=target_dte + tolerance, option_type=option_type)
    if not contracts:
        return None
    
    # Find closest strike to target
    target_strike = float(strike_price)
    best = min(contracts, key=lambda c: (abs(c['strike_price'] - target_strike), abs(c['dte'] - target_dte)))
    return best.get('symbol')


def get_option_live_price(option_symbol):
    """Get live option price from Alpaca snapshot."""
    try:
        r = requests.get(
            f"{_base()}/markets/us/options/snapshots",
            headers=_headers(),
            params={"symbols": option_symbol},
            timeout=10
        )
        if r.ok:
            snap = r.json().get("snapshots", {}).get(option_symbol, {})
            quote = snap.get("latest_quote", {})
            trade = snap.get("latestTrade", {})
            # Use mid-price
            bid = quote.get("bp", 0) or 0
            ask = quote.get("ap", 0) or 0
            last = trade.get("p", 0) or 0
            if bid and ask:
                return (float(bid) + float(ask)) / 2
            return float(last) if last else 0
    except Exception:
        pass
    return 0


def build_mleg_order(legs, qty=1):
    """
    Build a multi-leg options order for Alpaca.
    
    Args:
        legs: list of dicts with keys:
            - symbol: option symbol (e.g., "AAPL250321C00245000")
            - side: "buy" or "sell"
            - ratio_qty: relative quantity (usually 1)
        qty: number of contracts (multiplier for the whole spread)
    
    Returns:
        dict: JSON payload for Alpaca's POST /v2/orders
    """
    order_legs = []
    for leg in legs:
        order_legs.append({
            "symbol": leg["symbol"],
            "side": leg["side"],
            "ratio_qty": str(leg.get("ratio_qty", 1)),
        })
    
    return {
        "type": "market",
        "time_in_force": "day",
        "order_class": "mleg",
        "qty": str(qty),
        "legs": order_legs,
    }


def submit_options_order(order_payload):
    """Submit an options order to Alpaca."""
    try:
        r = requests.post(
            f"{_base()}/orders",
            headers=_headers(),
            json=order_payload,
            timeout=15
        )
        if r.ok:
            result = r.json()
            return {"status": result.get("status", "submitted"), "id": result.get("id"), "raw": result}
        else:
            return {"status": "REJECTED", "error": r.text[:200]}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def execute_single_leg(underlying, option_symbol, action, qty=1):
    """Execute a single-leg options order."""
    order = {
        "symbol": option_symbol,
        "qty": str(qty),
        "side": action,  # "buy" or "sell"
        "type": "market",
        "time_in_force": "day",
    }
    return submit_options_order(order)


def execute_straddle(underlying, strike, dte, qty=1):
    """
    Execute a long straddle: buy ATM call + buy ATM put at same strike/expiry.
    Best for: high volatility expected, direction uncertain (earnings, catalysts).
    """
    call_symbol = find_option_symbol(underlying, "call", strike, dte)
    put_symbol = find_option_symbol(underlying, "put", strike, dte)
    
    if not call_symbol or not put_symbol:
        return {"status": "ERROR", "error": f"Could not find straddle legs for {underlying}"}
    
    order = build_mleg_order([
        {"symbol": call_symbol, "side": "buy", "ratio_qty": 1},
        {"symbol": put_symbol, "side": "buy", "ratio_qty": 1},
    ], qty=qty)
    
    return submit_options_order(order)


def execute_strangle(underlying, call_strike, put_strike, dte, qty=1):
    """
    Execute a long strangle: buy OTM call + buy OTM put.
    Best for: very large expected move, cheaper than straddle.
    """
    call_symbol = find_option_symbol(underlying, "call", call_strike, dte)
    put_symbol = find_option_symbol(underlying, "put", put_strike, dte)
    
    if not call_symbol or not put_symbol:
        return {"status": "ERROR", "error": f"Could not find strangle legs for {underlying}"}
    
    order = build_mleg_order([
        {"symbol": call_symbol, "side": "buy", "ratio_qty": 1},
        {"symbol": put_symbol, "side": "buy", "ratio_qty": 1},
    ], qty=qty)
    
    return submit_options_order(order)


def execute_call_debit_spread(underlying, long_strike, short_strike, dte, qty=1):
    """
    Execute a call debit spread: buy lower strike call + sell higher strike call.
    Best for: bullish with defined risk, reduces cost vs naked call.
    """
    long_symbol = find_option_symbol(underlying, "call", long_strike, dte)
    short_symbol = find_option_symbol(underlying, "call", short_strike, dte)
    
    if not long_symbol or not short_symbol:
        return {"status": "ERROR", "error": f"Could not find call spread legs for {underlying}"}
    
    order = build_mleg_order([
        {"symbol": long_symbol, "side": "buy", "ratio_qty": 1},
        {"symbol": short_symbol, "side": "sell", "ratio_qty": 1},
    ], qty=qty)
    
    return submit_options_order(order)


def execute_put_debit_spread(underlying, long_strike, short_strike, dte, qty=1):
    """
    Execute a put debit spread: buy higher strike put + sell lower strike put.
    Best for: bearish with defined risk.
    """
    long_symbol = find_option_symbol(underlying, "put", long_strike, dte)
    short_symbol = find_option_symbol(underlying, "put", short_strike, dte)
    
    if not long_symbol or not short_symbol:
        return {"status": "ERROR", "error": f"Could not find put spread legs for {underlying}"}
    
    order = build_mleg_order([
        {"symbol": long_symbol, "side": "buy", "ratio_qty": 1},
        {"symbol": short_symbol, "side": "sell", "ratio_qty": 1},
    ], qty=qty)
    
    return submit_options_order(order)


def execute_iron_condor(underlying, put_sell_strike, put_buy_strike, call_sell_strike, call_buy_strike, dte, qty=1):
    """
    Execute a short iron condor (4 legs):
    - Sell OTM put (put_sell_strike)
    - Buy further OTM put (put_buy_strike) 
    - Sell OTM call (call_sell_strike)
    - Buy further OTM call (call_buy_strike)
    
    Best for: range-bound markets, high IV (sell premium).
    Max profit: net credit received.
    Max loss: width of wider spread - credit.
    """
    put_sell = find_option_symbol(underlying, "put", put_sell_strike, dte)
    put_buy = find_option_symbol(underlying, "put", put_buy_strike, dte)
    call_sell = find_option_symbol(underlying, "call", call_sell_strike, dte)
    call_buy = find_option_symbol(underlying, "call", call_buy_strike, dte)
    
    if not all([put_sell, put_buy, call_sell, call_buy]):
        return {"status": "ERROR", "error": f"Could not find iron condor legs for {underlying}"}
    
    order = build_mleg_order([
        {"symbol": put_sell, "side": "sell", "ratio_qty": 1},
        {"symbol": put_buy, "side": "buy", "ratio_qty": 1},
        {"symbol": call_sell, "side": "sell", "ratio_qty": 1},
        {"symbol": call_buy, "side": "buy", "ratio_qty": 1},
    ], qty=qty)
    
    return submit_options_order(order)


def execute_iron_butterfly(underlying, wing_width, dte, qty=1):
    """
    Execute a short iron butterfly (4 legs, 3 strikes):
    - Buy OTM put (strike - wing_width)
    - Sell ATM put (at-the-money strike)
    - Sell ATM call (at-the-money strike) 
    - Buy OTM call (strike + wing_width)
    
    Best for: range-bound markets, max profit when stock expires at short strike.
    Higher reward than iron condor but narrower profit zone.
    """
    price = _yf_price(underlying)
    if price <= 0:
        return {"status": "ERROR", "error": f"Could not get price for {underlying}"}
    
    # Find ATM strike (round to nearest 5 for stocks > $100, nearest 1 for others)
    if price > 100:
        atm_strike = round(price / 5) * 5
    else:
        atm_strike = round(price)
    
    put_buy_strike = atm_strike - wing_width
    put_sell_strike = atm_strike
    call_sell_strike = atm_strike
    call_buy_strike = atm_strike + wing_width
    
    put_buy = find_option_symbol(underlying, "put", put_buy_strike, dte)
    put_sell = find_option_symbol(underlying, "put", put_sell_strike, dte)
    call_sell = find_option_symbol(underlying, "call", call_sell_strike, dte)
    call_buy = find_option_symbol(underlying, "call", call_buy_strike, dte)
    
    if not all([put_buy, put_sell, call_sell, call_buy]):
        return {"status": "ERROR", "error": f"Could not find iron butterfly legs for {underlying}"}
    
    order = build_mleg_order([
        {"symbol": put_buy, "side": "buy", "ratio_qty": 1},
        {"symbol": put_sell, "side": "sell", "ratio_qty": 1},
        {"symbol": call_sell, "side": "sell", "ratio_qty": 1},
        {"symbol": call_buy, "side": "buy", "ratio_qty": 1},
    ], qty=qty)
    
    return submit_options_order(order)


def execute_calendar_spread(underlying, strike, near_dte, far_dte, option_type="call", qty=1):
    """
    Execute a long calendar spread:
    - Sell near-term option (shorter DTE)
    - Buy longer-term option (longer DTE)
    Same strike, same type (call or put).
    
    Best for: profit from time decay differential, IV term structure steep.
    """
    near_symbol = find_option_symbol(underlying, option_type, strike, near_dte)
    far_symbol = find_option_symbol(underlying, option_type, strike, far_dte)
    
    if not near_symbol or not far_symbol:
        return {"status": "ERROR", "error": f"Could not find calendar spread legs for {underlying}"}
    
    order = build_mleg_order([
        {"symbol": near_symbol, "side": "sell", "ratio_qty": 1},
        {"symbol": far_symbol, "side": "buy", "ratio_qty": 1},
    ], qty=qty)
    
    return submit_options_order(order)


def execute_covered_call(underlying, strike, dte, qty=None):
    """
    Execute a covered call: sell OTM call on stock already owned.
    If qty is None, use all owned shares / 100.
    Best for: income generation on existing holdings.
    """
    call_symbol = find_option_symbol(underlying, "call", strike, dte)
    if not call_symbol:
        return {"status": "ERROR", "error": f"Could not find call option for {underlying}"}
    
    if qty is None:
        # Get current position
        try:
            r = requests.get(f"{_base()}/positions/{underlying}", headers=_headers(), timeout=10)
            if r.ok:
                pos = r.json()
                shares = int(pos.get("qty", 0))
                qty = max(1, shares // 100)
            else:
                qty = 1
        except Exception:
            qty = 1
    
    return execute_single_leg(underlying, call_symbol, "sell", qty)


def execute_cash_secured_put(underlying, strike, dte, qty=1):
    """
    Execute a cash-secured put: sell OTM put.
    Best for: income generation, may acquire stock at discount.
    """
    put_symbol = find_option_symbol(underlying, "put", strike, dte)
    if not put_symbol:
        return {"status": "ERROR", "error": f"Could not find put option for {underlying}"}
    
    return execute_single_leg(underlying, put_symbol, "sell", qty)


def close_option_position(option_symbol, qty="all"):
    """Close an option position."""
    try:
        if qty == "all":
            r = requests.delete(
                f"{_base()}/positions/{option_symbol}",
                headers=_headers(),
                timeout=15
            )
        else:
            r = requests.delete(
                f"{_base()}/positions/{option_symbol}",
                headers=_headers(),
                params={"qty": str(qty)},
                timeout=15
            )
        if r.ok:
            return {"status": "closed", "raw": r.json()}
        else:
            return {"status": "ERROR", "error": r.text[:200]}
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}


def get_all_option_positions():
    """Get all open option positions."""
    try:
        r = requests.get(f"{_base()}/positions", headers=_headers(), timeout=15)
        if r.ok:
            positions = r.json()
            return [p for p in positions if p.get("asset_class") == "option"]
    except Exception:
        pass
    return []
