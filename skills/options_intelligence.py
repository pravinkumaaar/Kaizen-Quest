"""
Options Intelligence Skill

Handles all options-related functionality:
- Live options chain data (Polygon.io or yfinance)
- Implied volatility tracking
- Strategy recommendations (covered calls, LEAPS, etc.)
- Risk assessment for options plays
"""

import sys
import requests
import yfinance as yf
from datetime import datetime, timedelta
from io import StringIO

# Config (will be set by init)
POLYGON_API_KEY = None
BASE_DIR = None

def init_options_skill(polygon_key=None, base_dir=None):
    """Initialize with config from main agent."""
    global POLYGON_API_KEY, BASE_DIR
    if polygon_key:
        POLYGON_API_KEY = polygon_key
    if base_dir:
        BASE_DIR = base_dir

def fetch_options_snapshot_polygon(tickers: list) -> str:
    """
    Fetch live options data from Polygon.io.
    Free tier: 5 API calls/min.
    """
    if not POLYGON_API_KEY:
        return fetch_options_snapshot_yfinance(tickers)

    lines = []
    today = datetime.today().date()
    min_expiry = today + timedelta(days=14)
    
    for ticker in tickers:
        try:
            r = requests.get(
                f"https://api.polygon.io/v3/snapshot/options/{ticker}",
                params={"apikey": POLYGON_API_KEY},
                timeout=10
            )
            
            if r.status_code != 200:
                continue
            
            data = r.json().get("results", {})
            if not data:
                continue
            
            t = yf.Ticker(ticker)
            price = t.fast_info.last_price
            if not price:
                continue
            
            lines.append(f"\n{ticker} @ ${price:.2f}")
            
            options = data.get("options", [])
            expirations = {}
            
            for opt in options:
                exp_date = opt.get("expiration_date", "")
                if exp_date and datetime.date.fromisoformat(exp_date) >= min_expiry:
                    if exp_date not in expirations:
                        expirations[exp_date] = {"calls": [], "puts": []}
                    
                    opt_type = opt.get("option_type", "").lower()
                    strike = opt.get("strike_price", 0)
                    
                    if abs(strike - price) / price < 0.05:
                        bid = opt.get("bid", None)
                        ask = opt.get("ask", None)
                        iv = opt.get("implied_volatility", None)
                        
                        data_point = {"strike": strike, "bid": bid, "ask": ask, "iv": iv}
                        
                        if opt_type == "call":
                            expirations[exp_date]["calls"].append(data_point)
                        else:
                            expirations[exp_date]["puts"].append(data_point)
            
            for exp_date in sorted(expirations.keys())[:2]:
                days_out = (datetime.date.fromisoformat(exp_date) - today).days
                lines.append(f"  Expiry {exp_date} ({days_out}d):")
                
                exp_data = expirations[exp_date]
                
                if exp_data["calls"]:
                    call = exp_data["calls"][0]
                    iv_str = f" IV={call['iv']:.0%}" if call.get('iv') else ""
                    lines.append(f"    ATM Call: bid=${call['bid']:.2f} ask=${call['ask']:.2f}{iv_str}")
                
                if exp_data["puts"]:
                    put = exp_data["puts"][0]
                    iv_str = f" IV={put['iv']:.0%}" if put.get('iv') else ""
                    lines.append(f"    ATM Put:  bid=${put['bid']:.2f} ask=${put['ask']:.2f}{iv_str}")
        
        except Exception:
            continue
    
    return "\n".join(lines) if lines else fetch_options_snapshot_yfinance(tickers)

def fetch_options_snapshot_yfinance(tickers: list) -> str:
    """
    Free fallback: Fetch options chain via yfinance.
    """
    lines = []
    today = datetime.today().date()
    min_expiry = today + timedelta(days=14)

    for ticker in tickers:
        try:
            old_stderr = sys.stderr
            sys.stderr = StringIO()
            try:
                t = yf.Ticker(ticker)
                price = t.fast_info.last_price
                exps = t.options
            finally:
                sys.stderr = old_stderr

            if not exps or not price:
                continue

            valid_exps = [e for e in exps if datetime.date.fromisoformat(e) >= min_expiry]
            
            if not valid_exps:
                continue

            target_exps = []
            for e in valid_exps:
                days_out = (datetime.date.fromisoformat(e) - today).days
                if 14 <= days_out <= 400:
                    target_exps.append(e)
                if len(target_exps) >= 2:
                    break

            for e in valid_exps:
                days_out = (datetime.date.fromisoformat(e) - today).days
                if days_out > 180 and e not in target_exps:
                    target_exps.append(e)
                    break

            lines.append(f"\n{ticker} @ ${price:.2f}")
            lines.append(f"  Available expiries (≥2wk): {', '.join(valid_exps[:6])}")

            for exp in target_exps[:2]:
                try:
                    sys.stderr = StringIO()
                    try:
                        chain = t.option_chain(exp)
                    finally:
                        sys.stderr = old_stderr
                        
                    days_out = (datetime.date.fromisoformat(exp) - today).days

                    calls = chain.calls.copy()
                    calls['diff'] = abs(calls['strike'] - price)
                    atm_call = calls.nsmallest(1, 'diff').iloc[0]

                    puts = chain.puts.copy()
                    puts['diff'] = abs(puts['strike'] - price)
                    atm_put = puts.nsmallest(1, 'diff').iloc[0]

                    lines.append(f"  Expiry {exp} ({days_out}d out):")
                    lines.append(f"    ATM Call ${atm_call['strike']:.0f}: "
                                 f"bid=${atm_call['bid']:.2f} ask=${atm_call['ask']:.2f} "
                                 f"IV={atm_call['impliedVolatility']:.0%}")
                    lines.append(f"    ATM Put  ${atm_put['strike']:.0f}: "
                                 f"bid=${atm_put['bid']:.2f} ask=${atm_put['ask']:.2f} "
                                 f"IV={atm_put['impliedVolatility']:.0%}")
                except Exception:
                    pass

        except Exception:
            pass

    return "\n".join(lines) if lines else "[Options data unavailable]"

def get_options_ideas(market_data: str, digest: str, tickers: list = None) -> str:
    """
    Generate options strategy ideas following strict rules.
    - Only defined-risk strategies
    - Min 2 weeks to expiry
    - Max 10% portfolio allocation
    """
    if tickers is None:
        tickers = ["SPY", "QQQ", "NVDA", "AAPL"]
    
    options_context = fetch_options_snapshot(tickers)
    
    ideas = "## 🎯 Options Intelligence\n\n"
    ideas += "### Strategy Rules (STRICT):\n"
    ideas += "- ONLY defined-risk strategies (long calls/puts, covered calls, LEAPS)\n"
    ideas += "- Minimum 2 weeks to expiry (prefer 30-90 days or LEAPS)\n"
    ideas += "- Max 10% of portfolio in options total\n"
    ideas += "- NEVER let options expire ITM - always sell before expiry\n\n"
    ideas += f"### Live Options Data:\n{options_context}\n\n"
    ideas += "### Recommended Strategies:\n"
    ideas += "1. **Covered Calls** - On existing holdings for income\n"
    ideas += "2. **LEAPS Calls** - 6-24 months out for long-term bullish bets\n"
    ideas += "3. **Protective Puts** - Portfolio insurance during high VIX\n"
    ideas += "4. **Asymmetric Plays** - Low-cost, high-upside speculations\n"
    
    return ideas

def fetch_options_snapshot(tickers: list) -> str:
    """Route to best available options data source."""
    if POLYGON_API_KEY:
        return fetch_options_snapshot_polygon(tickers)
    else:
        return fetch_options_snapshot_yfinance(tickers)

__all__ = [
    'init_options_skill',
    'fetch_options_snapshot',
    'fetch_options_snapshot_polygon',
    'fetch_options_snapshot_yfinance',
    'get_options_ideas'
]
