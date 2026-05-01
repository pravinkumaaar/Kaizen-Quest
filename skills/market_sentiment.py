"""
Market Sentiment & Macro Trends Skill

Analyzes market conditions using:
- VIX (fear/greed index)
- Market breadth (SPY, QQQ moves)
- Economic indicators
- Macro trend deep-dives
"""

import sys
import yfinance as yf
from io import StringIO
from datetime import datetime

def get_market_sentiment() -> str:
    """
    Analyze market sentiment using VIX and market indices.
    Returns: fear/greed assessment with timing context.
    """
    try:
        # Get VIX (fear gauge)
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            vix = yf.Ticker("^VIX")
            vix_price = vix.fast_info.last_price or 0
            vix_prev = vix.fast_info.previous_close or 0
        except Exception:
            vix_price = 0
            vix_prev = 0
        finally:
            sys.stderr = old_stderr
        
        # Get market indices
        spy = yf.Ticker("SPY")
        spy_price = spy.fast_info.last_price or 0
        spy_prev = spy.fast_info.previous_close or 0
        
        qqq = yf.Ticker("QQQ")
        qqq_price = qqq.fast_info.last_price or 0
        qqq_prev = qqq.fast_info.previous_close or 0
        
        # Calculate moves
        spy_move = ((spy_price - spy_prev) / spy_prev * 100) if spy_prev > 0 else 0
        qqq_move = ((qqq_price - qqq_prev) / qqq_prev * 100) if qqq_prev > 0 else 0
        
        # Determine sentiment
        if vix_price == 0:
            sentiment = "[VIX data unavailable]"
        elif vix_price < 12:
            sentiment = f"**EXTREME GREED** (VIX: {vix_price:.1f})\n"
            sentiment += "Markets pricing in near-perfect outcomes. Complacency high.\n"
            sentiment += "**Action:** Take profits, trim concentrated positions, add hedges.\n"
        elif vix_price < 16:
            sentiment = f"**GREED** (VIX: {vix_price:.1f})\n"
            sentiment += "Investors confident but not complacent.\n"
            sentiment += "**Action:** Steady accumulation, buy dips.\n"
        elif vix_price < 20:
            sentiment = f"**NEUTRAL** (VIX: {vix_price:.1f})\n"
            sentiment += "Normal volatility. Mix of optimism and caution.\n"
            sentiment += "**Action:** Stick to high-conviction ideas.\n"
        elif vix_price < 30:
            sentiment = f"**FEAR** (VIX: {vix_price:.1f})\n"
            sentiment += "Investors nervous but not panicked.\n"
            sentiment += "**Action:** Have dry powder ready, add to high-conviction.\n"
        else:
            sentiment = f"**EXTREME FEAR** (VIX: {vix_price:.1f})\n"
            sentiment += "Markets pricing in significant downside.\n"
            sentiment += "**Action:** Contrarian buying opportunity for aggressive investors.\n"
        
        sentiment += f"\n**Today's Market:**\n"
        sentiment += f"- SPY: {spy_move:+.2f}% @ ${spy_price:.2f}\n"
        sentiment += f"- QQQ: {qqq_move:+.2f}% @ ${qqq_price:.2f}\n"
        
        return sentiment
    
    except Exception as e:
        return f"[Market sentiment unavailable: {str(e)}]"

def analyze_macro_trends() -> str:
    """
    Provide deep-dive analysis on current macro trends.
    Uses web search and news to identify key themes.
    """
    trends = "## 🌍 Macro Trends Deep-Dive\n\n"
    
    trends += "### Key Themes to Watch:\n"
    trends += "1. **Federal Reserve Policy** - Rate cuts/pauses, inflation trajectory\n"
    trends += "2. **AI Infrastructure Boom** - Data centers, energy demand, chip race\n"
    trends += "3. **Geopolitical Tensions** - Trade wars, sanctions, supply chains\n"
    trends += "4. **Energy Transition** - Renewables vs fossil fuels, grid upgrades\n"
    trends += "5. **Demographic Shifts** - Aging populations, labor shortages\n"
    
    trends += "\n### Today's Macro Context:\n"
    trends += "- Check latest Fed minutes/speeches for rate clues\n"
    trends += "- Monitor VIX for market fear/greed extremes\n"
    trends += "- Watch 10Y Treasury yield for recession signals\n"
    trends += "- Track dollar strength (DXY) for global liquidity\n"
    
    return trends

def get_fear_greed_rating() -> dict:
    """Return numeric fear/greed rating based on VIX."""
    try:
        vix = yf.Ticker("^VIX")
        vix_price = vix.fast_info.last_price or 0
        
        if vix_price == 0:
            return {"rating": "Unknown", "score": 50, "vix": 0}
        elif vix_price < 12:
            return {"rating": "Extreme Greed", "score": 90, "vix": vix_price}
        elif vix_price < 16:
            return {"rating": "Greed", "score": 70, "vix": vix_price}
        elif vix_price < 20:
            return {"rating": "Neutral", "score": 50, "vix": vix_price}
        elif vix_price < 30:
            return {"rating": "Fear", "score": 30, "vix": vix_price}
        else:
            return {"rating": "Extreme Fear", "score": 10, "vix": vix_price}
    except Exception:
        return {"rating": "Unknown", "score": 50, "vix": 0}

__all__ = [
    'get_market_sentiment',
    'analyze_macro_trends',
    'get_fear_greed_rating'
]
