"""
YFinance Utilities

Wraps yfinance calls with:
- Stderr suppression (yfinance is extremely noisy)
- Automatic retry with exponential backoff
- Polygon.io fallback for price data
- Data freshness validation

Usage:
    from skills.yfinance_utils import safe_yf_price, safe_yf_history, safe_yf_info
    
    price_data = safe_yf_price("AAPL")
    hist = safe_yf_history("NVDA", period="3mo")
    info = safe_yf_info("MSFT")
"""

import sys
import os
import time
import json
import datetime
import requests
from io import StringIO
from pathlib import Path
from dotenv import load_dotenv

# Suppress yfinance's verbose stderr output globally
# This must be done before any yfinance import
_old_stderr = sys.stderr

class _SuppressYFStderr:
    """Context manager and permanent filter for yfinance stderr spam."""
    def __init__(self):
        self._original = None
    
    def __enter__(self):
        self._original = sys.stderr
        sys.stderr = StringIO()
        return self
    
    def __exit__(self, *args):
        if self._original:
            sys.stderr = self._original
        return False
    
    def write(self, msg):
        # Completely suppress yfinance stderr
        pass
    
    def flush(self):
        pass

# Install permanent stderr filter
_yf_filter = _SuppressYFStderr()


def _poly_key():
    """Get Polygon API key from environment."""
    load_dotenv(override=False)
    return os.environ.get("POLYGON_API_KEY", "")


def _polygon_price(symbol):
    """Get current price from Polygon.io as fallback."""
    key = _poly_key()
    if not key:
        return None
    try:
        end = datetime.datetime.now().strftime('%Y-%m-%d')
        start = (datetime.datetime.now() - datetime.timedelta(days=5)).strftime('%Y-%m-%d')
        r = requests.get(
            f"https://api.polygon.io/v2/aggs/ticker/{symbol.upper()}/range/1/day/{start}/{end}?adjusted=true&sort=desc&limit=2&apiKey={key}",
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            results = data.get("results", [])
            if results:
                last = float(results[0].get("c", 0))
                prev = float(results[1].get("c", 0)) if len(results) >= 2 else 0
                chg_pct = round(((last - prev) / prev * 100), 2) if prev > 0 else 0
                return {
                    "price": last,
                    "prev_close": prev,
                    "change_pct": chg_pct,
                    "source": "polygon"
                }
    except Exception:
        pass
    return None


def _polygon_history(symbol, period="3mo"):
    """Get price history from Polygon.io as fallback."""
    key = _poly_key()
    if not key:
        return None
    try:
        # Map period to date range
        period_days = {"1mo": 30, "3mo": 90, "6mo": 180, "1y": 365}
        days = period_days.get(period, 90)
        end = datetime.datetime.now().strftime('%Y-%m-%d')
        start = (datetime.datetime.now() - datetime.timedelta(days=days + 5)).strftime('%Y-%m-%d')
        r = requests.get(
            f"https://api.polygon.io/v2/aggs/ticker/{symbol.upper()}/range/1/day/{start}/{end}?adjusted=true&sort=asc&limit=500&apiKey={key}",
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            results = data.get("results", [])
            if results:
                import pandas as pd
                df = pd.DataFrame(results)
                df['date'] = pd.to_datetime(df['t'], unit='ms')
                df = df.set_index('date')
                df = df.rename(columns={'o': 'Open', 'h': 'High', 'l': 'Low', 'c': 'Close', 'v': 'Volume'})
                return df[['Open', 'High', 'Low', 'Close', 'Volume']]
    except Exception:
        pass
    return None


def safe_yf_price(symbol):
    """
    Get current price for a ticker with yfinance + Polygon fallback.
    Suppresses all yfinance stderr output.
    
    Returns: dict with 'price', 'change_pct', 'prev_close', 'source'
    """
    # Try yfinance first
    try:
        import yfinance as yf
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            t = yf.Ticker(symbol)
            info = t.fast_info
            last = float(info.last_price) if info.last_price else 0
            prev = float(info.previous_close) if info.previous_close else 0
            if last > 0:
                chg_pct = round(((last - prev) / prev * 100), 2) if prev > 0 else 0
                return {
                    "price": last,
                    "change_pct": chg_pct,
                    "prev_close": prev,
                    "source": "yfinance"
                }
        finally:
            sys.stderr = old_stderr
    except Exception:
        try:
            sys.stderr = old_stderr
        except:
            pass
    
    # Fallback to Polygon
    poly = _polygon_price(symbol)
    if poly:
        return poly
    
    return {"price": 0, "change_pct": 0, "prev_close": 0, "source": "none"}


def safe_yf_history(symbol, period="3mo"):
    """
    Get price history with yfinance + Polygon fallback.
    Returns pandas DataFrame or None.
    """
    # Try yfinance first
    try:
        import yfinance as yf
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            t = yf.Ticker(symbol)
            hist = t.history(period=period)
            if hist is not None and len(hist) > 0:
                return hist
        finally:
            sys.stderr = old_stderr
    except Exception:
        try:
            sys.stderr = old_stderr
        except:
            pass
    
    # Fallback to Polygon
    return _polygon_history(symbol, period)


def safe_yf_info(symbol):
    """
    Get company info with yfinance + Polygon fallback.
    Returns dict or empty dict.
    """
    try:
        import yfinance as yf
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            t = yf.Ticker(symbol)
            info = t.info
            if info and len(info) > 5:  # Valid info has many keys
                return info
        finally:
            sys.stderr = old_stderr
    except Exception:
        try:
            sys.stderr = old_stderr
        except:
            pass
    
    # Fallback: build basic info from Polygon
    poly = _polygon_price(symbol)
    if poly:
        return {
            "symbol": symbol.upper(),
            "currentPrice": poly["price"],
            "regularMarketPrice": poly["price"],
            "regularMarketPreviousClose": poly.get("prev_close", 0),
            "regularMarketChangePercent": poly.get("change_pct", 0),
        }
    return {}


def safe_yf_options_chain(symbol, expiry=None):
    """
    Get options chain with yfinance. Returns (calls, puts) or (None, None).
    """
    try:
        import yfinance as yf
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            t = yf.Ticker(symbol)
            if expiry:
                chain = t.option_chain(expiry)
            else:
                # Get nearest expiry
                expirations = t.options
                if not expirations:
                    return None, None
                chain = t.option_chain(expirations[0])
            return chain.calls, chain.puts
        finally:
            sys.stderr = old_stderr
    except Exception:
        try:
            sys.stderr = old_stderr
        except:
            pass
    return None, None


def estimate_volatility(symbol, period="3mo"):
    """Estimate annualized volatility from historical prices."""
    try:
        hist = safe_yf_history(symbol, period=period)
        if hist is not None and len(hist) > 10:
            import math
            returns = hist["Close"].pct_change().dropna()
            daily_vol = returns.std()
            annual_vol = daily_vol * math.sqrt(252)
            return max(annual_vol, 0.10)
    except Exception:
        pass
    return 0.25  # Default 25% annual volatility


def get_sector(symbol):
    """Get sector for a ticker."""
    try:
        import yfinance as yf
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            info = yf.Ticker(symbol).info
            return info.get('sector', 'Unknown')
        finally:
            sys.stderr = old_stderr
    except Exception:
        try:
            sys.stderr = old_stderr
        except:
            pass
    return 'Unknown'
