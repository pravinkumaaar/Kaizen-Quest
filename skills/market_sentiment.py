"""
Market Sentiment & Macro Trends Skill v2.0

Analyzes market conditions using:
- VIX (fear/greed index) via Finnhub
- Market breadth (SPY, QQQ moves) via Finnhub
- Economic indicators
- Macro trend deep-dives

FIXED: Now uses Finnhub as primary data source instead of yfinance,
which was failing with 'currentTradingPeriod' errors.
"""

import sys
import requests
import yfinance as yf
from io import StringIO
from datetime import datetime

FINNHUB_API_KEY = None

def init_sentiment_skill(finnhub_key=None):
    """Initialize with API key."""
    global FINNHUB_API_KEY
    if finnhub_key:
        FINNHUB_API_KEY = finnhub_key


def _finnhub_quote(symbol):
    """Get quote from Finnhub. Returns (price, prev_close) or (0, 0)."""
    if not FINNHUB_API_KEY:
        return 0, 0
    try:
        r = requests.get(
            f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}",
            timeout=10
        )
        data = r.json()
        return data.get("c", 0), data.get("pc", 0)
    except Exception:
        return 0, 0


def get_market_sentiment() -> str:
    """
    Analyze market sentiment using VIX and market indices.
    Uses Finnhub as primary source, yfinance as fallback.
    Returns: fear/greed assessment with timing context.
    """
    vix_price, vix_prev = 0, 0
    spy_price, spy_prev = 0, 0
    qqq_price, qqq_prev = 0, 0
    source = "unknown"

    # PRIMARY: Finnhub
    if FINNHUB_API_KEY:
        vix_price, vix_prev = _finnhub_quote("^VIX")
        spy_price, spy_prev = _finnhub_quote("SPY")
        qqq_price, qqq_prev = _finnhub_quote("QQQ")
        source = "finnhub"

    # FALLBACK: yfinance if Finnhub returned nothing
    if vix_price == 0 and spy_price == 0:
        try:
            old_stderr = sys.stderr
            sys.stderr = StringIO()
            try:
                vix = yf.Ticker("^VIX")
                vix_price = vix.fast_info.last_price or 0
                vix_prev = vix.fast_info.previous_close or 0

                spy = yf.Ticker("SPY")
                spy_price = spy.fast_info.last_price or 0
                spy_prev = spy.fast_info.previous_close or 0

                qqq = yf.Ticker("QQQ")
                qqq_price = qqq.fast_info.last_price or 0
                qqq_prev = qqq.fast_info.previous_close or 0
                source = "yfinance"
            except Exception:
                pass
            finally:
                sys.stderr = old_stderr
        except Exception:
            pass

    # Calculate moves
    spy_move = ((spy_price - spy_prev) / spy_prev * 100) if spy_prev > 0 else 0
    qqq_move = ((qqq_price - qqq_prev) / qqq_prev * 100) if qqq_prev > 0 else 0

    # Build sentiment
    if vix_price == 0 and spy_price == 0:
        return "[Market sentiment unavailable — no data from Finnhub or yfinance]"

    sentiment = f"**Market Sentiment (via {source}):**\n\n"

    if vix_price > 0:
        if vix_price < 12:
            sentiment += f"**EXTREME GREED** (VIX: {vix_price:.1f})\n"
            sentiment += "Markets pricing in near-perfect outcomes. Complacency high.\n"
            sentiment += "**Action:** Take profits, trim concentrated positions, add hedges.\n"
        elif vix_price < 16:
            sentiment += f"**GREED** (VIX: {vix_price:.1f})\n"
            sentiment += "Investors confident but not complacent.\n"
            sentiment += "**Action:** Steady accumulation, buy dips.\n"
        elif vix_price < 20:
            sentiment += f"**NEUTRAL** (VIX: {vix_price:.1f})\n"
            sentiment += "Normal volatility. Mix of optimism and caution.\n"
            sentiment += "**Action:** Stick to high-conviction ideas.\n"
        elif vix_price < 30:
            sentiment += f"**FEAR** (VIX: {vix_price:.1f})\n"
            sentiment += "Investors nervous but not panicked.\n"
            sentiment += "**Action:** Have dry powder ready, add to high-conviction on weakness.\n"
        else:
            sentiment += f"**EXTREME FEAR** (VIX: {vix_price:.1f})\n"
            sentiment += "Markets pricing in significant downside.\n"
            sentiment += "**Action:** Contrarian buying opportunity for aggressive investors.\n"
    else:
        sentiment += "[VIX data unavailable]\n"

    sentiment += f"\n**Today's Market:**\n"
    if spy_price > 0:
        sentiment += f"- SPY: {spy_move:+.2f}% @ ${spy_price:.2f}\n"
    if qqq_price > 0:
        sentiment += f"- QQQ: {qqq_move:+.2f}% @ ${qqq_price:.2f}\n"

    return sentiment


def analyze_macro_trends() -> str:
    """Placeholder for macro trend analysis."""
    return "[Macro trend analysis — coming soon]"


__all__ = ['get_market_sentiment', 'analyze_macro_trends', 'init_sentiment_skill']
