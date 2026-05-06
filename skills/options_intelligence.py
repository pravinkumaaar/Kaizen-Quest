"""
Options Intelligence Skill v2.0

Handles all options-related functionality:
- Live options chain data (Polygon.io primary, yfinance fallback)
- Implied volatility tracking
- Strategy recommendations (covered calls, LEAPS, etc.)
- Risk assessment for options plays
- Earnings-aware options analysis

FIXED: Now properly handles after-hours data, multiple fallback sources,
and provides clear status about data freshness.
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


def _get_live_price(ticker):
    """
    Get the most current available price for a stock.
    Tries multiple sources in order of reliability.
    Returns (price, prev_close, source_name) or (None, None, None).
    """
    price = None
    prev_close = None
    source = None

    # 1. Try yfinance fast_info (works after hours with delayed data)
    old_stderr = sys.stderr
    sys.stderr = StringIO()
    try:
        t = yf.Ticker(ticker)
        fi = t.fast_info
        p = fi.last_price
        pc = fi.previous_close
        if p and p > 0:
            price = p
            prev_close = pc if pc and pc > 0 else None
            source = "yfinance"
    except Exception:
        pass
    finally:
        sys.stderr = old_stderr

    # 2. Try yfinance info for more detail
    if price is None:
        sys.stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            info = t.info
            p = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
            pc = info.get('regularMarketPreviousClose') or info.get('previousClose')
            if p and p > 0:
                price = float(p)
                prev_close = float(pc) if pc and float(pc) > 0 else None
                source = "yfinance-info"
        except Exception:
            pass
        finally:
            sys.stderr = old_stderr

    return price, prev_close, source


def fetch_options_snapshot_polygon(tickers):
    """
    Fetch live options data from Polygon.io.
    Free tier: 5 API calls/min.
    """
    if not POLYGON_API_KEY:
        return None, "No Polygon API key"

    lines = []
    today = datetime.today().date()
    min_expiry = today + timedelta(days=14)
    errors = []

    for ticker in tickers:
        try:
            r = requests.get(
                f"https://api.polygon.io/v3/snapshot/options/{ticker}",
                params={"apiKey": POLYGON_API_KEY, "limit": 20},
                timeout=15
            )

            if r.status_code == 403:
                return None, "Polygon API key invalid/expired (403)"
            if r.status_code == 429:
                errors.append(f"{ticker}: rate limited")
                continue
            if r.status_code != 200:
                errors.append(f"{ticker}: HTTP {r.status_code}")
                continue

            data = r.json()
            results = data.get("results", [])
            if not results:
                errors.append(f"{ticker}: no results")
                continue

            # Get current price
            price, prev_close, source = _get_live_price(ticker)
            if not price:
                errors.append(f"{ticker}: no price")
                continue

            lines.append(f"\n{ticker} @ ${price:.2f} (via {source})")

            # Group by expiration
            expirations = {}
            for opt in results:
                exp_date = opt.get("expiration_date", "")
                if not exp_date:
                    continue
                try:
                    exp_dt = datetime.date.fromisoformat(exp_date)
                except ValueError:
                    continue
                if exp_dt < min_expiry:
                    continue

                if exp_date not in expirations:
                    expirations[exp_date] = {"calls": [], "puts": []}

                opt_type = opt.get("details", {}).get("contract_type", "").lower()
                strike = opt.get("details", {}).get("strike_price", 0)
                if not strike:
                    strike = opt.get("strike_price", 0)

                # Get bid/ask/iv from the day's data or last quote
                day = opt.get("day", {})
                bid = day.get("bid") or opt.get("last_quote", {}).get("bid")
                ask = day.get("ask") or opt.get("last_quote", {}).get("ask")
                iv = opt.get("implied_volatility")

                # Fallback: try to get from underlying
                if bid is None and ask is None:
                    last_trade = opt.get("last_trade", {})
                    bid = last_trade.get("price")
                    ask = last_trade.get("price")

                data_point = {"strike": strike, "bid": bid, "ask": ask, "iv": iv}

                if opt_type == "call":
                    expirations[exp_date]["calls"].append(data_point)
                elif opt_type == "put":
                    expirations[exp_date]["puts"].append(data_point)

            # Show top 2 nearest expirations
            for exp_date in sorted(expirations.keys())[:2]:
                days_out = (datetime.date.fromisoformat(exp_date) - today).days
                lines.append(f"  Expiry {exp_date} ({days_out}d):")

                exp_data = expirations[exp_date]

                # Find ATM call
                if exp_data["calls"]:
                    atm = min(exp_data["calls"], key=lambda x: abs(x["strike"] - price))
                    iv_str = f" IV={atm['iv']:.0%}" if atm.get('iv') else ""
                    bid_str = f"${atm['bid']:.2f}" if atm.get('bid') is not None else "N/A"
                    ask_str = f"${atm['ask']:.2f}" if atm.get('ask') is not None else "N/A"
                    lines.append(f"    ATM Call ${atm['strike']:.0f}: bid={bid_str} ask={ask_str}{iv_str}")

                if exp_data["puts"]:
                    atm = min(exp_data["puts"], key=lambda x: abs(x["strike"] - price))
                    iv_str = f" IV={atm['iv']:.0%}" if atm.get('iv') else ""
                    bid_str = f"${atm['bid']:.2f}" if atm.get('bid') is not None else "N/A"
                    ask_str = f"${atm['ask']:.2f}" if atm.get('ask') is not None else "N/A"
                    lines.append(f"    ATM Put  ${atm['strike']:.0f}: bid={bid_str} ask={ask_str}{iv_str}")

        except Exception as e:
            errors.append(f"{ticker}: {str(e)[:60]}")
            continue

    if errors:
        lines.append(f"\n[Polygon issues: {'; '.join(errors)}]")

    return "\n".join(lines) if lines else None, None


def fetch_options_snapshot_yfinance(tickers):
    """
    Free fallback: Fetch options chain via yfinance or direct Yahoo Finance API.
    Works with delayed data after market hours.
    """
    lines = []
    today = datetime.today().date()
    min_expiry = today + timedelta(days=14)
    errors = []

    for ticker in tickers:
        price = None
        exps = None
        chain_data = None
        t = None

        # METHOD 1: Try yfinance library
        try:
            old_stderr = sys.stderr
            sys.stderr = StringIO()
            try:
                t = yf.Ticker(ticker)
                price = t.fast_info.last_price
                exps = t.options
            except Exception:
                pass
            finally:
                sys.stderr = old_stderr
        except Exception:
            pass

        # METHOD 2: Direct Yahoo Finance API (when yfinance is broken)
        if not price or not exps:
            try:
                price, chain_data = _fetch_options_yahoo_direct(ticker)
            except Exception:
                pass

        if not price or (not exps and not chain_data):
            errors.append(f"{ticker}: no price or options data")
            continue

        # If we got chain_data from direct API, format and continue
        if chain_data:
            lines.append(f"\n{ticker} @ ${price:.2f} (via yahoo-direct)")
            shown = 0
            for exp_date in sorted(chain_data.keys()):
                if shown >= 2:
                    break
                exp_data = chain_data[exp_date]
                days_out = (datetime.date.fromisoformat(exp_date) - today).days
                lines.append(f"  Expiry {exp_date} ({days_out}d):")
                calls = exp_data.get("calls", [])
                puts = exp_data.get("puts", [])
                if calls:
                    atm = min(calls, key=lambda x: abs(x["strike"] - price))
                    iv_str = f" IV={atm['iv']:.0%}" if atm.get('iv') else ""
                    bid_str = f"${atm['bid']:.2f}" if atm.get('bid') is not None else "N/A"
                    ask_str = f"${atm['ask']:.2f}" if atm.get('ask') is not None else "N/A"
                    lines.append(f"    ATM Call ${atm['strike']:.0f}: bid={bid_str} ask={ask_str}{iv_str}")
                if puts:
                    atm = min(puts, key=lambda x: abs(x["strike"] - price))
                    iv_str = f" IV={atm['iv']:.0%}" if atm.get('iv') else ""
                    bid_str = f"${atm['bid']:.2f}" if atm.get('bid') is not None else "N/A"
                    ask_str = f"${atm['ask']:.2f}" if atm.get('ask') is not None else "N/A"
                    lines.append(f"    ATM Put  ${atm['strike']:.0f}: bid={bid_str} ask={ask_str}{iv_str}")
                shown += 1
            continue

        # METHOD 1 continued: yfinance data processing
        if not exps:
            errors.append(f"{ticker}: no options")
            continue

        if not price or price <= 0:
            try:
                sys.stderr = StringIO()
                try:
                    info = t.info
                    price = info.get('currentPrice') or info.get('regularMarketPrice')
                except Exception:
                    pass
                finally:
                    sys.stderr = old_stderr
            except Exception:
                pass

        if not price or price <= 0:
            errors.append(f"{ticker}: no price")
            continue

        valid_exps = []
        for e in exps:
            try:
                if datetime.date.fromisoformat(e) >= min_expiry:
                    valid_exps.append(e)
            except ValueError:
                continue

        if not valid_exps:
            errors.append(f"{ticker}: no valid expiries")
            continue

        target_exps = []
        for e in valid_exps:
            days_out = (datetime.date.fromisoformat(e) - today).days
            if 14 <= days_out <= 400 and len(target_exps) < 2:
                target_exps.append(e)
        for e in valid_exps:
            days_out = (datetime.date.fromisoformat(e) - today).days
            if days_out > 180 and e not in target_exps:
                target_exps.append(e)
                break

        lines.append(f"\n{ticker} @ ${price:.2f} (via yfinance)")
        lines.append(f"  Available expiries (≥2wk): {', '.join(valid_exps[:6])}")

        for exp in target_exps[:3]:
            try:
                sys.stderr = StringIO()
                try:
                    chain = t.option_chain(exp)
                finally:
                    sys.stderr = old_stderr

                days_out = (datetime.date.fromisoformat(exp) - today).days
                calls = chain.calls.copy()
                if calls.empty:
                    continue
                calls['diff'] = abs(calls['strike'] - price)
                atm_call = calls.nsmallest(1, 'diff').iloc[0]

                puts = chain.puts.copy()
                if puts.empty:
                    continue
                puts['diff'] = abs(puts['strike'] - price)
                atm_put = puts.nsmallest(1, 'diff').iloc[0]

                call_iv = f" IV={atm_call['impliedVolatility']:.0%}" if atm_call.get('impliedVolatility') and atm_call['impliedVolatility'] > 0 else ""
                put_iv = f" IV={atm_put['impliedVolatility']:.0%}" if atm_put.get('impliedVolatility') and atm_put['impliedVolatility'] > 0 else ""

                lines.append(f"  Expiry {exp} ({days_out}d out):")
                lines.append(f"    ATM Call ${atm_call['strike']:.0f}: "
                             f"bid=${atm_call.get('bid', 0):.2f} ask=${atm_call.get('ask', 0):.2f}{call_iv}")
                lines.append(f"    ATM Put  ${atm_put['strike']:.0f}: "
                             f"bid=${atm_put.get('bid', 0):.2f} ask=${atm_put.get('ask', 0):.2f}{put_iv}")
            except Exception as e:
                errors.append(f"{ticker} {exp}: {str(e)[:40]}")
                continue

    if errors:
        lines.append(f"\n[options issues: {'; '.join(errors)}]")

    return "\n".join(lines) if lines else None, None


def _fetch_options_yahoo_direct(ticker):
    """
    Fallback: Fetch options data directly from Yahoo Finance API.
    Works when yfinance library is broken. Free, no API key needed.
    Returns (price, options_chain_dict) or (None, None).
    """
    try:
        # Step 1: Get current price
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range=1d&interval=1d"
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code != 200:
            return None, None
        chart_data = r.json()
        result = chart_data.get("chart", {}).get("result", [])
        if not result:
            return None, None
        meta = result[0].get("meta", {})
        price = meta.get("regularMarketPrice") or meta.get("previousClose")
        if not price:
            return None, None

        # Step 2: Get options chain
        url2 = f"https://query2.finance.yahoo.com/v7/finance/options/{ticker}"
        r2 = requests.get(url2, headers=headers, timeout=15)
        if r2.status_code != 200:
            return price, None
        opt_data = r2.json()
        opt_result = opt_data.get("optionChain", {}).get("result", [])
        if not opt_result:
            return price, None

        options = opt_result[0].get("options", [])
        if not options:
            return price, None

        chain = {}
        today = datetime.today().date()
        min_expiry = today + timedelta(days=14)

        for opt_group in options:
            exp_date = opt_group.get("expirationDate", "")
            if not exp_date:
                continue
            try:
                exp_dt = datetime.date.fromisoformat(exp_date)
            except ValueError:
                continue
            if exp_dt < min_expiry:
                continue

            calls_list = []
            for c in opt_group.get("calls", []):
                calls_list.append({
                    "strike": c.get("strike", 0),
                    "bid": c.get("bid", 0),
                    "ask": c.get("ask", 0),
                    "iv": c.get("impliedVolatility", 0),
                    "volume": c.get("volume", 0),
                })

            puts_list = []
            for p in opt_group.get("puts", []):
                puts_list.append({
                    "strike": p.get("strike", 0),
                    "bid": p.get("bid", 0),
                    "ask": p.get("ask", 0),
                    "iv": p.get("impliedVolatility", 0),
                    "volume": p.get("volume", 0),
                })

            chain[exp_date] = {"calls": calls_list, "puts": puts_list}

        return float(price), chain
    except Exception:
        return None, None


def fetch_options_snapshot(tickers):
    """
    Route to best available options data source.
    Tries Polygon first, then yfinance fallback.
    Returns formatted string with data freshness info.
    """
    today = datetime.today().date()
    time_str = datetime.now().strftime("%H:%M")
    all_errors = []

    # Try Polygon first
    if POLYGON_API_KEY:
        result, err = fetch_options_snapshot_polygon(tickers)
        if result:
            return f"[Options data as of {today} {time_str}]\n{result}"
        if err:
            all_errors.append(f"Polygon: {err}")

    # Fallback to yfinance
    result, err = fetch_options_snapshot_yfinance(tickers)
    if result:
        return f"[Options data as of {today} {time_str}]\n{result}"
    if err:
        all_errors.append(f"yfinance: {err}")

    # If both fail, return a clear message with the tickers we tried
    error_detail = f" Errors: {'; '.join(all_errors)}" if all_errors else ""
    return (f"[Options data unavailable for {', '.join(tickers)} "
            f"as of {today} {time_str}.{error_detail}\n"
            f"Note: Options data may be limited after market hours (4:00 PM ET). "
            f"Polygon API key may need renewal. "
            f"Try again during market hours (9:30 AM - 4:00 PM ET) for best results.]")


def get_options_ideas(market_data, digest, tickers=None):
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
    ideas += f"### Live Options Data:\n```\n{options_context}\n```\n\n"
    ideas += "### Recommended Strategies:\n"
    ideas += "1. **Covered Calls** - On existing holdings for income\n"
    ideas += "2. **LEAPS Calls** - 6-24 months out for long-term bullish bets\n"
    ideas += "3. **Protective Puts** - Portfolio insurance during high VIX\n"
    ideas += "4. **Asymmetric Plays** - Low-cost, high-upside speculations\n"

    return ideas


def check_earnings_options(ticker):
    """
    Check if a stock has upcoming earnings and return options implications.
    High IV before earnings = expensive options = consider selling premium.
    """
    try:
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            info = t.info
            # Check for earnings date
            earnings_date = info.get('earningsDate') or info.get('earningsTimestamp')
            if earnings_date:
                return f"  ⚠️ {ticker} has upcoming earnings — IV may be elevated, consider selling premium (covered calls) rather than buying"
        except Exception:
            pass
        finally:
            sys.stderr = old_stderr
    except Exception:
        pass
    return None


__all__ = [
    'init_options_skill',
    'fetch_options_snapshot',
    'fetch_options_snapshot_polygon',
    'fetch_options_snapshot_yfinance',
    'get_options_ideas',
    'check_earnings_options',
    '_get_live_price',
    '_fetch_options_yahoo_direct',
]
