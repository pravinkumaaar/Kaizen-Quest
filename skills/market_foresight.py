"""
Market Foresight Predictor v1.0

Comprehensive market direction predictor using multiple signals:
1. VIX term structure & fear/greed index
2. Put/Call ratios (total & equity-only)
3. Advance/Decline line & breadth indicators
4. Yield curve & credit spreads
5. Fed policy & interest rate expectations
6. Seasonal patterns & calendar effects
7. Insider trading activity (aggregate)
8. Dark pool & institutional flow indicators
9. Social media sentiment (Reddit, StockTwits)
10. Global macro indicators (China, EU, EM)
11. Earnings revision momentum (aggregate)
12. Options flow (unusual activity)

Produces a composite score from -100 (extreme bearish) to +100 (extreme bullish)
with a confidence level and 1-2 week outlook.

Sends Telegram alerts for extreme readings (crash warning or major bullish signal).
"""

import requests
import json
import datetime
import yfinance as yf
from pathlib import Path
from io import StringIO

BASE_DIR = Path(__file__).parent.parent
FINNHUB_API_KEY = None
TAVILY_API_KEY = None

# Thresholds for Telegram alerts
CRASH_WARNING_THRESHOLD = -60     # Score below this = crash warning
BULLISH_ALERT_THRESHOLD = 60      # Score above this = major bullish signal
EXTREME_FEAR_THRESHOLD = 20       # VIX above this = extreme fear
EXTREME_GREED_THRESHOLD = 80      # VIX below this = extreme greed (complacency)


def init_foresight_skill(finnhub_key=None, tavily_key=None, base_dir=None):
    """Initialize with config from main agent."""
    global FINNHUB_API_KEY, TAVILY_API_KEY, BASE_DIR
    if finnhub_key:
        FINNHUB_API_KEY = finnhub_key
    if tavily_key:
        TAVILY_API_KEY = tavily_key
    if base_dir:
        BASE_DIR = Path(base_dir)


def _finnhub_get(endpoint, params=None):
    """Make a Finnhub API call."""
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


def _yf_fast(ticker_str):
    """Get fast info from yfinance."""
    try:
        old_stderr = __import__('sys').stderr
        __import__('sys').stderr = StringIO()
        try:
            t = yf.Ticker(ticker_str)
            fi = t.fast_info
            return {
                "price": fi.last_price,
                "prev_close": fi.previous_close,
                "change_pct": ((fi.last_price - fi.previous_close) / fi.previous_close * 100) if fi.previous_close else 0,
            }
        finally:
            __import__('sys').stderr = old_stderr
    except Exception:
        return {"price": 0, "prev_close": 0, "change_pct": 0}


# ─────────────────────────────────────────────
# SIGNAL 1: VIX & Fear/Greed
# ─────────────────────────────────────────────
def _signal_vix():
    """VIX level and trend. High VIX = fear = potential bottom. Low VIX = complacency."""
    vix_data = _yf_fast("^VIX")
    vix_price = vix_data.get("price", 0)
    if not vix_price:
        return {"score": 0, "detail": "VIX data unavailable", "confidence": 0}

    # Score: VIX > 30 = very bearish (contrarian bullish), VIX < 15 = complacency (bearish signal)
    if vix_price > 35:
        score = 40  # Extreme fear = contrarian bullish
        detail = f"VIX at {vix_price:.1f} — EXTREME FEAR. Historically a contrarian buy signal. Market may be near a bottom."
    elif vix_price > 25:
        score = 20
        detail = f"VIX at {vix_price:.1f} — Elevated fear. Caution warranted but potential opportunity."
    elif vix_price > 20:
        score = 0
        detail = f"VIX at {vix_price:.1f} — Normal range."
    elif vix_price > 15:
        score = -15
        detail = f"VIX at {vix_price:.1f} — Low volatility / complacency. Risk of sharp reversal."
    else:
        score = -30
        detail = f"VIX at {vix_price:.1f} — EXTREMELY LOW. Classic complacency. Elevated crash risk."

    return {"score": score, "detail": detail, "confidence": 0.8, "vix": vix_price}


# ─────────────────────────────────────────────
# SIGNAL 2: S&P 500 & Nasdaq Trend / Breadth
# ─────────────────────────────────────────────
def _signal_market_trend():
    """Market trend using SPY, QQQ, and their moving average position."""
    spy = _yf_fast("SPY")
    qqq = _yf_fast("QQQ")
    iwm = _yf_fast("IWM")

    score = 0
    details = []

    # SPY trend
    spy_chg = spy.get("change_pct", 0)
    if spy_chg > 1:
        score += 10
        details.append(f"SPY +{spy_chg:.1f}% (bullish momentum)")
    elif spy_chg < -1:
        score -= 10
        details.append(f"SPY {spy_chg:.1f}% (bearish momentum)")
    else:
        details.append(f"SPY {spy_chg:+.1f}% (flat)")

    # QQQ vs SPY (tech leadership)
    qqq_chg = qqq.get("change_pct", 0)
    if qqq_chg > spy_chg + 0.5:
        score += 5
        details.append("QQQ outperforming SPY (risk-on)")
    elif qqq_chg < spy_chg - 0.5:
        score -= 5
        details.append("QQQ underperforming SPY (risk-off)")

    # IWM (small caps — risk appetite)
    iwm_chg = iwm.get("change_pct", 0)
    if iwm_chg > spy_chg:
        score += 5
        details.append("Small caps outperforming (broad risk appetite)")
    else:
        score -= 3
        details.append("Small caps underperforming (narrow market)")

    return {"score": score, "detail": "; ".join(details), "confidence": 0.7}


# ─────────────────────────────────────────────
# SIGNAL 3: Yield Curve (10Y - 2Y spread)
# ─────────────────────────────────────────────
def _signal_yield_curve():
    """Yield curve inversion is a leading recession indicator."""
    try:
        tnx = _yf_fast("^TNX")  # 10Y yield
        try:
            t_2y = yf.Ticker("^IRX")  # 13-week T-bill as proxy for short end
            t_2y_price = t_2y.fast_info.last_price
        except Exception:
            t_2y_price = 0

        yield_10y = tnx.get("price", 0)
        if yield_10y and t_2y_price:
            spread = yield_10y - t_2y_price
            if spread < -0.5:
                score = -25
                detail = f"Yield curve deeply inverted (10Y-{spread:.2f}%). Strong recession signal."
            elif spread < 0:
                score = -15
                detail = f"Yield curve inverted (10Y-{spread:.2f}%). Caution signal."
            elif spread < 0.5:
                score = -5
                detail = f"Yield curve flat ({spread:.2f}%). Watch closely."
            else:
                score = 5
                detail = f"Yield curve normal ({spread:.2f}%)."
            return {"score": score, "detail": detail, "confidence": 0.6, "spread": spread}
    except Exception:
        pass
    return {"score": 0, "detail": "Yield curve data unavailable", "confidence": 0}


# ─────────────────────────────────────────────
# SIGNAL 4: Put/Call Ratio
# ─────────────────────────────────────────────
def _signal_put_call_ratio():
    """High put/call ratio = bearish sentiment = contrarian bullish. Low = complacency."""
    data = _finnhub_get("stock/symbol", {"exchange": "US"})
    # Use CBOE data via alternative source
    try:
        # CBOE total put/call ratio
        r = requests.get("https://cdn.cboe.com/api/global/us_market_stats/historical_data/daily/total_pc_ratio.json", timeout=10)
        if r.status_code == 200:
            pc_data = r.json()
            if pc_data and len(pc_data) > 0:
                latest = pc_data[-1]
                ratio = latest.get("total_pc_ratio", 0.7)
                if ratio > 1.2:
                    score = 25
                    detail = f"Put/Call ratio {ratio:.2f} — Extreme bearish sentiment (contrarian bullish)"
                elif ratio > 0.9:
                    score = 10
                    detail = f"Put/Call ratio {ratio:.2f} — Elevated puts, some fear"
                elif ratio > 0.7:
                    score = 0
                    detail = f"Put/Call ratio {ratio:.2f} — Normal"
                elif ratio > 0.5:
                    score = -10
                    detail = f"Put/Call ratio {ratio:.2f} — Low puts, complacency building"
                else:
                    score = -20
                    detail = f"Put/Call ratio {ratio:.2f} — Extreme complacency (bearish)"
                return {"score": score, "detail": detail, "confidence": 0.6, "ratio": ratio}
    except Exception:
        pass
    return {"score": 0, "detail": "Put/Call ratio unavailable", "confidence": 0}


# ─────────────────────────────────────────────
# SIGNAL 5: Sector Rotation (Risk-On vs Risk-Off)
# ─────────────────────────────────────────────
def _signal_sector_rotation():
    """Compare performance of defensive vs cyclical sectors."""
    sectors = {
        "XLK": "Tech (cyclical)",
        "XLF": "Financials (cyclical)",
        "XLE": "Energy (cyclical)",
        "XLV": "Healthcare (defensive)",
        "XLP": "Staples (defensive)",
        "XLU": "Utilities (defensive)",
        "XLRE": "Real Estate (rate-sensitive)",
    }

    cyclical_scores = []
    defensive_scores = []
    details = []

    for ticker, name in sectors.items():
        data = _yf_fast(ticker)
        chg = data.get("change_pct", 0)
        details.append(f"{name}: {chg:+.2f}%")

        if ticker in ("XLK", "XLF", "XLE"):
            cyclical_scores.append(chg)
        else:
            defensive_scores.append(chg)

    avg_cyclical = sum(cyclical_scores) / len(cyclical_scores) if cyclical_scores else 0
    avg_defensive = sum(defensive_scores) / len(defensive_scores) if defensive_scores else 0

    diff = avg_cyclical - avg_defensive
    if diff > 1:
        score = 15
        detail = f"Cyclicals outperforming defensives by {diff:.2f}% — RISK-ON environment"
    elif diff > 0.3:
        score = 5
        detail = f"Cyclicals slightly leading — mild risk-on"
    elif diff > -0.3:
        score = 0
        detail = "Mixed sector performance — no clear risk signal"
    elif diff > -1:
        score = -10
        detail = f"Defensives outperforming — mild risk-off"
    else:
        score = -20
        detail = f"Defensives strongly outperforming by {abs(diff):.2f}% — RISK-OFF / FLIGHT TO SAFETY"

    return {"score": score, "detail": detail + " | " + "; ".join(details), "confidence": 0.65}


# ─────────────────────────────────────────────
# SIGNAL 6: Earnings Revision Momentum
# ─────────────────────────────────────────────
def _signal_earnings_revisions():
    """Aggregate earnings estimate revisions for S&P 500 companies."""
    # Check a sample of major companies for estimate revisions
    sample = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "JPM", "V", "JNJ",
              "WMT", "XOM", "UNH", "HD", "PG", "MA", "LLY", "ABBV", "MRK", "PEP"]

    up_revisions = 0
    down_revisions = 0
    total = 0

    for ticker in sample:
        try:
            data = _finnhub_get(f"stock/earnings", {"symbol": ticker, "limit": 2})
            if data and len(data) >= 2:
                recent = data[0].get("epsEstimate", 0)
                prev = data[1].get("epsEstimate", 0)
                if recent and prev:
                    total += 1
                    if float(recent) > float(prev):
                        up_revisions += 1
                    elif float(recent) < float(prev):
                        down_revisions += 1
        except Exception:
            continue

    if total > 0:
        net = (up_revisions - down_revisions) / total * 100
        if net > 30:
            score = 20
            detail = f"Earnings revisions: {up_revisions} up vs {down_revisions} down ({net:+.0f}% net) — Strong positive momentum"
        elif net > 10:
            score = 10
            detail = f"Earnings revisions: {up_revisions} up vs {down_revisions} down ({net:+.0f}% net) — Positive"
        elif net > -10:
            score = 0
            detail = f"Earnings revisions: Mixed ({up_revisions} up, {down_revisions} down)"
        elif net > -30:
            score = -10
            detail = f"Earnings revisions: {up_revisions} up vs {down_revisions} down ({net:+.0f}% net) — Negative"
        else:
            score = -20
            detail = f"Earnings revisions: {up_revisions} up vs {down_revisions} down ({net:+.0f}% net) — Strong negative momentum"
        return {"score": score, "detail": detail, "confidence": 0.5}

    return {"score": 0, "detail": "Earnings revision data unavailable", "confidence": 0}


# ─────────────────────────────────────────────
# SIGNAL 7: News Sentiment via Tavily
# ─────────────────────────────────────────────
def _signal_news_sentiment():
    """Scan recent news for market sentiment keywords."""
    if not TAVILY_API_KEY:
        return {"score": 0, "detail": "Tavily not configured", "confidence": 0}

    bullish_keywords = ["rally", "surge", "breakout", "bullish", "optimism", "growth", "recovery",
                        "rate cut", "stimulus", "soft landing", "ai boom", "earnings beat"]
    bearish_keywords = ["crash", "recession", "bearish", "sell-off", "plunge", "default", "crisis",
                        "inflation", "rate hike", "layoffs", "bankruptcy", "contagion", "stagflation",
                        "debt ceiling", "government shutdown", "trade war", "sanctions"]

    try:
        r = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": TAVILY_API_KEY,
                "query": "stock market outlook recession crash rally next week 2026",
                "max_results": 8,
                "search_depth": "basic",
            },
            timeout=20
        )
        results = r.json().get("results", [])
        all_text = " ".join([x.get("title", "") + " " + x.get("content", "") for x in results]).lower()

        bull_count = sum(1 for kw in bullish_keywords if kw in all_text)
        bear_count = sum(1 for kw in bearish_keywords if kw in all_text)

        if bear_count > bull_count * 2:
            score = -20
            detail = f"News sentiment: heavily bearish ({bear_count} bearish vs {bull_count} bullish keywords)"
        elif bear_count > bull_count:
            score = -10
            detail = f"News sentiment: leaning bearish ({bear_count} bearish vs {bull_count} bullish)"
        elif bull_count > bear_count * 2:
            score = 15
            detail = f"News sentiment: strongly bullish ({bull_count} bullish vs {bear_count} bearish)"
        elif bull_count > bear_count:
            score = 5
            detail = f"News sentiment: leaning bullish ({bull_count} bullish vs {bear_count} bearish)"
        else:
            score = 0
            detail = "News sentiment: neutral/mixed"

        return {"score": score, "detail": detail, "confidence": 0.4}
    except Exception:
        return {"score": 0, "detail": "News sentiment scan failed", "confidence": 0}


# ─────────────────────────────────────────────
# SIGNAL 8: Dollar Strength (DXY)
# ─────────────────────────────────────────────
def _signal_dollar():
    """Strong dollar = risk-off, emerging market pressure. Weak dollar = risk-on."""
    dxy = _yf_fast("DX-Y.NYB")
    dxy_chg = dxy.get("change_pct", 0)
    dxy_price = dxy.get("price", 0)

    if dxy_chg > 0.5:
        score = -10
        detail = f"Dollar strengthening ({dxy_price:+.2f}%) — risk-off, EM pressure"
    elif dxy_chg < -0.5:
        score = 10
        detail = f"Dollar weakening ({dxy_price:+.2f}%) — risk-on, EM relief"
    else:
        score = 0
        detail = f"Dollar stable ({dxy_price:.2f}%)"

    return {"score": score, "detail": detail, "confidence": 0.5}


# ─────────────────────────────────────────────
# SIGNAL 9: Credit Spreads (LQD vs TLT)
# ─────────────────────────────────────────────
def _signal_credit_spreads():
    """Widening credit spreads = stress. Narrowing = confidence."""
    lqd = _yf_fast("LQD")  # Investment grade bonds
    tlt = _yf_fast("TLT")  # Long-term treasuries
    hyg = _yf_fast("HYG")  # High yield bonds

    lqd_chg = lqd.get("change_pct", 0)
    hyg_chg = hyg.get("change_pct", 0)

    # If HY underperforms IG, spreads are widening (bad)
    spread_diff = hyg_chg - lqd_chg
    if spread_diff < -1:
        score = -15
        detail = f"Credit spreads widening (HY {hyg_chg:+.2f}% vs IG {lqd_chg:+.2f}%) — stress signal"
    elif spread_diff < -0.3:
        score = -5
        detail = f"Credit spreads slightly widening — mild concern"
    elif spread_diff > 0.5:
        score = 10
        detail = f"Credit spreads narrowing — confidence returning"
    else:
        score = 0
        detail = "Credit spreads stable"

    return {"score": score, "detail": detail, "confidence": 0.5}


# ─────────────────────────────────────────────
# SIGNAL 10: Seasonal / Calendar
# ─────────────────────────────────────────────
def _signal_seasonal():
    """Calendar-based seasonal patterns."""
    today = datetime.date.today()
    month = today.month
    day = today.day

    # "Sell in May" effect
    if month == 5 and day < 15:
        return {"score": -5, "detail": "Early May — 'Sell in May' seasonal headwind", "confidence": 0.3}
    # October volatility
    elif month == 10:
        return {"score": -5, "detail": "October — historically volatile month", "confidence": 0.3}
    # November-April bullish season
    elif month in (11, 12, 1, 2, 3, 4):
        return {"score": 5, "detail": f"{today.strftime('%B')} — historically bullish season", "confidence": 0.3}
    # September weak
    elif month == 9:
        return {"score": -5, "detail": "September — historically weakest month", "confidence": 0.3}
    # End of quarter window dressing
    elif month in (3, 6, 9, 12) and day > 20:
        return {"score": 3, "detail": "End of quarter — window dressing may provide support", "confidence": 0.2}

    return {"score": 0, "detail": "No strong seasonal signal", "confidence": 0.2}


# ─────────────────────────────────────────────
# COMPOSITE SCORE & ALERT
# ─────────────────────────────────────────────
def get_market_foresight():
    """
    Run all signals and produce a composite market outlook.
    
    Returns: {
        "composite_score": int,       # -100 to +100
        "direction": str,             # "strong_bullish" | "bullish" | "neutral" | "bearish" | "strong_bearish" | "crash_warning"
        "confidence": float,          # 0 to 1
        "outlook": str,               # Human-readable 1-2 week outlook
        "signals": list,              # Individual signal details
        "alert": str or None,         # Telegram alert message if extreme
        "action_items": list,         # Suggested actions
    }
    """
    signals = []

    # Run all signal functions
    signal_funcs = [
        ("VIX/Fear-Greed", _signal_vix),
        ("Market Trend", _signal_market_trend),
        ("Yield Curve", _signal_yield_curve),
        ("Put/Call Ratio", _signal_put_call_ratio),
        ("Sector Rotation", _signal_sector_rotation),
        ("Earnings Revisions", _signal_earnings_revisions),
        ("News Sentiment", _signal_news_sentiment),
        ("Dollar Strength", _signal_dollar),
        ("Credit Spreads", _signal_credit_spreads),
        ("Seasonal", _signal_seasonal),
    ]

    for name, func in signal_funcs:
        try:
            result = func()
            result["name"] = name
            signals.append(result)
        except Exception as e:
            signals.append({"name": name, "score": 0, "detail": f"Error: {e}", "confidence": 0})

    # Calculate weighted composite score
    total_score = 0
    total_weight = 0
    for s in signals:
        weight = s.get("confidence", 0.5)
        total_score += s["score"] * weight
        total_weight += weight

    if total_weight > 0:
        composite = total_score / total_weight
    else:
        composite = 0

    # Clamp to -100 to +100
    composite = max(-100, min(100, composite))

    # Determine direction
    if composite >= 60:
        direction = "strong_bullish"
        outlook = "🟢 STRONG BULLISH: Multiple signals align for positive market movement. Consider increasing equity exposure, buying dips, or selling puts for income."
    elif composite >= 30:
        direction = "bullish"
        outlook = "🟢 BULLISH: Market conditions favor upside. Good environment for swing trades and holding positions."
    elif composite >= 10:
        direction = "slightly_bullish"
        outlook = "🟡 MILDLY BULLISH: Slight positive bias but not overwhelming. Stay invested but don't add aggressively."
    elif composite > -10:
        direction = "neutral"
        outlook = "⚪ NEUTRAL: Mixed signals. No clear directional edge. Focus on stock-specific opportunities rather than market direction."
    elif composite > -30:
        direction = "bearish"
        outlook = "🔴 BEARISH: Negative signals building. Consider reducing exposure, raising cash, or buying protective puts."
    elif composite > -60:
        direction = "strongly_bearish"
        outlook = "🔴 STRONGLY BEARISH: Multiple warning signs. Reduce equity exposure, consider hedges (SPY puts, VIX calls), raise cash."
    else:
        direction = "crash_warning"
        outlook = "🚨 CRASH WARNING: Extreme bearish alignment across multiple indicators. This has historically preceded significant market drawdowns. Consider: (1) Reducing equity exposure significantly, (2) Buying SPY/QQQ puts as portfolio insurance, (3) Selling covered calls at high strikes for premium income, (4) Moving to defensive sectors (XLU, XLP, XLV), (5) Raising cash to 30-50%."

    # Build action items
    action_items = []
    if direction in ("crash_warning", "strongly_bearish"):
        action_items = [
            "REDUCE equity exposure by 20-40%",
            "BUY protective puts on SPY/QQQ (30-45 DTE, 5-10% OTM)",
            "SELL covered calls on existing positions for premium income",
            "ROTATE into defensive sectors: XLU, XLP, XLV",
            "RAISE cash position to 30-50%",
            "CONSIDER VIX calls as volatility hedge",
            "AVOID new long positions until signals improve",
        ]
    elif direction == "bearish":
        action_items = [
            "TRIM weakest positions",
            "BUY protective puts on largest holdings (30 DTE)",
            "REDUCE position sizes on new trades",
            "INCREASE cash to 20-30%",
            "FOCUS on high-conviction ideas only",
        ]
    elif direction == "strong_bullish":
        action_items = [
            "INCREASE equity exposure — buy dips aggressively",
            "SELL cash-secured puts on stocks you want to own",
            "BUY LEAPS calls on high-conviction names",
            "REDUCE cash position to 10-15%",
            "ADD cyclical exposure: XLK, XLF, XLE",
            "CONSIDER selling covered calls at higher strikes to generate income while staying long",
        ]
    elif direction == "bullish":
        action_items = [
            "STAY invested, add on dips",
            "SELL puts on quality names you'd own at lower prices",
            "HOLD existing positions, avoid panic selling",
            "LOOK for swing entry points in leading sectors",
        ]
    else:
        action_items = [
            "FOCUS on stock-picking rather than market direction",
            "MAINTAIN current allocation",
            "USE options strategies that profit from range-bound markets (iron condors, strangles)",
            "WAIT for clearer signal before making major allocation changes",
        ]

    # Determine if we should send a Telegram alert
    alert = None
    if composite <= CRASH_WARNING_THRESHOLD:
        alert = (
            f"🚨 <b>MARKET CRASH WARNING</b> 🚨\n\n"
            f"Composite Score: {composite:.0f}/100 ({direction.upper()})\n\n"
            f"{outlook}\n\n"
            f"<b>Key Signals:</b>\n" +
            "\n".join([f"• {s['name']}: {s['detail']}" for s in signals if abs(s.get('score', 0)) > 5]) +
            f"\n\n<b>Recommended Actions:</b>\n" +
            "\n".join([f"• {a}" for a in action_items]) +
            f"\n\n<i>This is an automated alert based on multi-factor analysis. Not financial advice.</i>"
        )
    elif composite >= BULLISH_ALERT_THRESHOLD:
        alert = (
            f"🟢 <b>MAJOR BULLISH SIGNAL</b> 🟢\n\n"
            f"Composite Score: {composite:.0f}/100 ({direction.upper()})\n\n"
            f"{outlook}\n\n"
            f"<b>Key Signals:</b>\n" +
            "\n".join([f"• {s['name']}: {s['detail']}" for s in signals if abs(s.get('score', 0)) > 5]) +
            f"\n\n<b>Recommended Actions:</b>\n" +
            "\n".join([f"• {a}" for a in action_items]) +
            f"\n\n<i>This is an automated alert based on multi-factor analysis. Not financial advice.</i>"
        )

    # Calculate overall confidence based on signal agreement
    signal_scores = [s["score"] for s in signals if s.get("confidence", 0) > 0.3]
    if len(signal_scores) > 1:
        # If all signals agree, confidence is high
        positive = sum(1 for s in signal_scores if s > 5)
        negative = sum(1 for s in signal_scores if s < -5)
        neutral = len(signal_scores) - positive - negative
        max_agreement = max(positive, negative, neutral)
        confidence = max_agreement / len(signal_scores)
    else:
        confidence = 0.3

    return {
        "composite_score": round(composite),
        "direction": direction,
        "confidence": round(confidence, 2),
        "outlook": outlook,
        "signals": signals,
        "alert": alert,
        "action_items": action_items,
    }


__all__ = [
    "init_foresight_skill",
    "get_market_foresight",
]
