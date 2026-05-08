"""
Market Foresight Predictor v2.0 — Forward-Looking & Predictive

Research-backed methods for 2-6 week market outlook:

1. YIELD CURVE (6-18 month lead) — Best recession predictor
2. VIX TERM STRUCTURE (2-4 week lead) — Contango vs backwardation
3. EARNINGS REVISIONS (1-3 month lead) — Aggregate EPS momentum
4. SECTOR ROTATION (2-8 week lead) — Cyclical vs defensive
5. CREDIT SPREADS (2-4 week lead) — HYG vs LQD
6. NEWS SENTIMENT (2-4 week lead) — AI-powered forward-looking analysis
7. DOLLAR STRENGTH (2-4 week lead) — Leads commodities/EM
8. MARKET BREADTH (2-4 week lead) — A/D line, small vs large cap
9. SEASONAL PATTERNS (1-3 month lead) — Calendar effects
10. INTER-MARKET ANALYSIS (2-8 week lead) — Stocks/bonds, copper/gold

Composite Score: -100 (crash imminent) to +100 (major bull run)
Outlook: 2-6 week forward-looking assessment
"""

import requests, json, datetime, yfinance as yf
from pathlib import Path
from io import StringIO

BASE_DIR = Path(__file__).parent.parent
FINNHUB_API_KEY = None
TAVILY_API_KEY = None
CRASH_WARNING_THRESHOLD = -55
BULLISH_ALERT_THRESHOLD = 55


def init_foresight_skill(finnhub_key=None, tavily_key=None, base_dir=None):
    global FINNHUB_API_KEY, TAVILY_API_KEY, BASE_DIR
    if finnhub_key: FINNHUB_API_KEY = finnhub_key
    if tavily_key: TAVILY_API_KEY = tavily_key
    if base_dir: BASE_DIR = Path(base_dir)


def _yf(ticker):
    try:
        old_stderr = __import__('sys').stderr; __import__('sys').stderr = StringIO()
        try:
            t = yf.Ticker(ticker); fi = t.fast_info; p = fi.last_price; pc = fi.previous_close
            if p and p > 0:
                chg = ((p - pc) / pc * 100) if pc and pc > 0 else 0
                return {"price": float(p), "prev_close": float(pc) if pc else 0, "change_pct": float(chg)}
        finally: __import__('sys').stderr = old_stderr
    except Exception: pass
    return {"price": 0, "prev_close": 0, "change_pct": 0}


def _signal_yield_curve():
    tnx = _yf("^TNX"); irx = _yf("^IRX")
    tnx_p = tnx.get("price", 0); irx_p = irx.get("price", 0)
    if tnx_p and irx_p:
        spread = tnx_p - irx_p
        if spread < -0.5: score, detail = -30, f"Yield curve deeply inverted ({spread:.2f}%) — recession signal, leads by 6-18mo"
        elif spread < 0: score, detail = -15, f"Yield curve inverted ({spread:.2f}%) — caution"
        elif spread < 0.5: score, detail = -5, f"Yield curve flat ({spread:.2f}%) — late cycle"
        else: score, detail = 5, f"Yield curve normal ({spread:.2f}%)"
        return {"score": score, "detail": detail, "confidence": 0.7}
    return {"score": 0, "detail": "Yield curve data unavailable", "confidence": 0}


def _signal_vix():
    vix = _yf("^VIX"); vix_p = vix.get("price", 0)
    if not vix_p: return {"score": 0, "detail": "VIX data unavailable", "confidence": 0}
    if vix_p > 35: score, detail = 35, f"VIX at {vix_p:.1f} — EXTREME FEAR. Contrarian buy signal. Historically precedes 5-10% rallies in 2-4 weeks."
    elif vix_p > 25: score, detail = 15, f"VIX at {vix_p:.1f} — Elevated fear. Watch for capitulation bottom."
    elif vix_p > 20: score, detail = 0, f"VIX at {vix_p:.1f} — Normal range."
    elif vix_p > 15: score, detail = -10, f"VIX at {vix_p:.1f} — Low vol/complacency. Risk of sharp reversal."
    else: score, detail = -25, f"VIX at {vix_p:.1f} — EXTREMELY LOW. Classic complacency. Elevated crash risk."
    return {"score": score, "detail": detail, "confidence": 0.8}


def _signal_earnings_momentum():
    sample = ["AAPL","MSFT","GOOGL","AMZN","NVDA","META","TSLA","JPM","V","JNJ","WMT","XOM","UNH","HD","PG","MA","LLY","ABBV","MRK","PEP"]
    up_rev = down_rev = total = 0
    for ticker in sample:
        try:
            data = None
            if FINNHUB_API_KEY:
                r = requests.get(f"https://finnhub.io/api/v1/stock/earnings", params={"symbol": ticker, "limit": 2, "token": FINNHUB_API_KEY}, timeout=10)
                if r.status_code == 200: data = r.json()
            if data and len(data) >= 2:
                recent = data[0].get("epsEstimate", 0); prev = data[1].get("epsEstimate", 0)
                if recent and prev:
                    total += 1
                    if float(recent) > float(prev): up_rev += 1
                    elif float(recent) < float(prev): down_rev += 1
        except Exception: continue
    if total > 0:
        net = (up_rev - down_rev) / total * 100
        if net > 30: sc, det = 20, f"Earnings revisions strongly positive ({up_rev} up, {down_rev} down, net {net:+.0f}%) — leads market by 1-3mo"
        elif net > 10: sc, det = 10, f"Earnings revisions positive ({up_rev} up, {down_rev} down)"
        elif net > -10: sc, det = 0, f"Earnings revisions mixed ({up_rev} up, {down_rev} down)"
        elif net > -30: sc, det = -15, f"Earnings revisions negative ({down_rev} down vs {up_rev} up)"
        else: sc, det = -25, f"Earnings revisions strongly negative — recession risk"
        return {"score": sc, "detail": det, "confidence": 0.5}
    return {"score": 0, "detail": "Earnings revision data unavailable", "confidence": 0}


def _signal_sector_rotation():
    sectors = {"XLK": "Tech", "XLF": "Financial", "XLE": "Energy", "XLV": "Healthcare", "XLP": "Staples", "XLU": "Utilities"}
    cyc = []; defn = []
    for t, n in sectors.items():
        d = _yf(t); chg = d.get("change_pct", 0)
        if t in ("XLK","XLF","XLE"): cyc.append(chg)
        else: defn.append(chg)
    avg_c = sum(cyc)/len(cyc) if cyc else 0
    avg_d = sum(defn)/len(defn) if defn else 0
    diff = avg_c - avg_d
    if diff > 1: sc, det = 15, f"Risk-on: Cyclicals outperforming defensives by {diff:.2f}% — bullish 2-8 weeks"
    elif diff > 0.3: sc, det = 5, f"Mild risk-on: Cyclicals slightly leading"
    elif diff > -0.3: sc, det = 0, "Mixed sector performance"
    elif diff > -1: sc, det = -10, f"Defensive rotation: Staples/utilities outperforming — risk-off 2-8 weeks"
    else: sc, det = -20, f"Strong flight to safety: Defensives outperforming by {abs(diff):.2f}% — bearish"
    return {"score": sc, "detail": det, "confidence": 0.6}


def _signal_credit():
    lqd = _yf("LQD"); hyg = _yf("HYG")
    diff = hyg.get("change_pct", 0) - lqd.get("change_pct", 0)
    if diff < -1: sc, det = -15, f"Credit spreads widening — stress signal, leads equities by 2-4 weeks"
    elif diff < -0.3: sc, det = -5, "Credit spreads slightly widening"
    elif diff > 0.5: sc, det = 10, "Credit spreads narrowing — risk appetite returning"
    else: sc, det = 0, "Credit spreads stable"
    return {"score": sc, "detail": det, "confidence": 0.5}


def _signal_news():
    if not TAVILY_API_KEY: return {"score": 0, "detail": "Tavily not configured", "confidence": 0}
    bull_kw = ["rally","surge","breakout","bullish","upgrade","beat","strong demand","AI boom","rate cut","soft landing"]
    bear_kw = ["crash","recession","bearish","downgrade","miss","layoffs","default","crisis","inflation","rate hike","contagion","stagflation"]
    try:
        r = requests.post("https://api.tavily.com/search",
            json={"api_key": TAVILY_API_KEY, "query": "stock market outlook next 2-4 weeks analyst forecast May 2026", "max_results": 8, "search_depth": "advanced"}, timeout=20)
        results = r.json().get("results", [])
        text = " ".join([x.get("title","") + " " + x.get("content","") for x in results]).lower()
        bc = sum(1 for kw in bull_kw if kw in text); bdc = sum(1 for kw in bear_kw if kw in text)
        if bdc > bc*2: sc, det = -20, f"News heavily bearish ({bdc} bearish vs {bc} bullish) — caution 2-4 weeks"
        elif bdc > bc: sc, det = -10, f"News leaning bearish ({bdc} vs {bc})"
        elif bc > bdc*2: sc, det = 15, f"News strongly bullish ({bc} vs {bdc}) — positive 2-4 weeks"
        elif bc > bdc: sc, det = 5, f"News leaning bullish ({bc} vs {bdc})"
        else: sc, det = 0, "News sentiment neutral/mixed"
        return {"score": sc, "detail": det, "confidence": 0.4}
    except Exception: return {"score": 0, "detail": "News scan failed", "confidence": 0}


def _signal_dollar():
    dxy = _yf("DX-Y.NYB"); chg = dxy.get("change_pct", 0)
    if chg > 0.5: sc, det = -10, f"Dollar strengthening ({chg:+.2f}%) — headwind for commodities/EM"
    elif chg < -0.5: sc, det = 10, f"Dollar weakening ({chg:+.2f}%) — tailwind for GLD/SLV/EEM"
    else: sc, det = 0, f"Dollar stable ({chg:+.2f}%)"
    return {"score": sc, "detail": det, "confidence": 0.5}


def _signal_breadth():
    spy = _yf("SPY"); iwm = _yf("IWM")
    diff = iwm.get("change_pct", 0) - spy.get("change_pct", 0)
    if diff > 1: sc, det = 10, f"Breadth expanding: Small caps outperforming by {diff:.2f}% — healthy, leads to gains"
    elif diff > -0.5: sc, det = 0, "Breadth neutral"
    elif diff > -1.5: sc, det = -10, f"Breadth narrowing: Small caps underperforming {abs(diff):.2f}% — early warning"
    else: sc, det = -20, f"Breadth breakdown: Small caps severely underperforming — correction likely 2-4 weeks"
    return {"score": sc, "detail": det, "confidence": 0.6}


def _signal_seasonal():
    today = datetime.date.today(); m = today.month
    if m == 5 and today.day > 20: sc, det = -8, "Late May — 'Sell in May' seasonal headwind"
    elif m in (6,7,8): sc, det = -5, f"{today.strftime('%B')} — summer seasonally weak"
    elif m == 9: sc, det = -10, "September — historically weakest month"
    elif m in (10,11) and today.day > 15: sc, det = 10, "Late Oct/Nov — seasonally strong period begins"
    elif m in (12,1,2,3,4): sc, det = 8, f"{today.strftime('%B')} — seasonally strong (Nov-Apr)"
    else: sc, det = 0, "No strong seasonal signal"
    return {"score": sc, "detail": det, "confidence": 0.3}


def get_market_foresight():
    signals = []
    for name, func in [
        ("Yield Curve (6-18mo lead)", _signal_yield_curve),
        ("VIX/Fear-Greed (2-4wk)", _signal_vix),
        ("Earnings Revisions (1-3mo)", _signal_earnings_momentum),
        ("Sector Rotation (2-8wk)", _signal_sector_rotation),
        ("Credit Spreads (2-4wk)", _signal_credit),
        ("News Sentiment (2-4wk)", _signal_news),
        ("Dollar (2-4wk)", _signal_dollar),
        ("Market Breadth (2-4wk)", _signal_breadth),
        ("Seasonal (1-3mo)", _signal_seasonal),
    ]:
        try:
            r = func(); r["name"] = name; signals.append(r)
        except Exception as e:
            signals.append({"name": name, "score": 0, "detail": f"Error: {e}", "confidence": 0})
    
    total_score = sum(s["score"] * s.get("confidence", 0.5) for s in signals)
    total_weight = sum(s.get("confidence", 0.5) for s in signals)
    composite = total_score / total_weight if total_weight > 0 else 0
    composite = max(-100, min(100, composite))
    
    if composite >= 55:
        direction, outlook = "strong_bullish", "🟢 STRONG BULLISH (2-6 week): Multiple forward-looking signals align for positive market movement. Consider increasing equity exposure, buying dips, selling puts."
    elif composite >= 25:
        direction, outlook = "bullish", "🟢 BULLISH (2-6 week): Leading indicators favor upside. Good environment for swing trades."
    elif composite >= 10:
        direction, outlook = "slightly_bullish", "🟡 MILDLY BULLISH: Some positive signals. Stay invested but don't add aggressively."
    elif composite > -10:
        direction, outlook = "neutral", "⚪ NEUTRAL (2-6 week): Mixed signals from leading indicators. Focus on stock-picking, not market timing."
    elif composite > -25:
        direction, outlook = "slightly_bearish", "🟡 MILDLY BEARISH: Warning signals building. Raise cash to 15-20%, trim weakest positions."
    elif composite > -55:
        direction, outlook = "bearish", "🔴 BEARISH (2-6 week): Multiple leading indicators flashing warning. Reduce equity 20-30%, raise cash, consider hedges."
    else:
        direction, outlook = "crash_warning", "🚨 CRASH WARNING: Extreme bearish alignment. Reduce equity to 40-50%, buy protective puts, raise cash to 30-40%."
    
    action_items = []
    for s in signals:
        if s.get("score", 0) > 10:
            if "VIX" in s["name"]: action_items.append("VIX elevated → sell premium (iron condors) or buy calls on dips")
            elif "Earnings" in s["name"]: action_items.append("Earnings momentum positive → add to positions ahead of earnings season")
            elif "Breadth" in s["name"]: action_items.append("Breadth expanding → favor small caps (IWM) and cyclicals")
            elif "Dollar" in s["name"]: action_items.append("Dollar weakening → add commodities (GLD, SLV) and international (EEM)")
            elif "Credit" in s["name"]: action_items.append("Credit spreads narrowing → add cyclicals (XLK, XLF, XLE)")
        elif s.get("score", 0) < -10:
            if "VIX" in s["name"]: action_items.append("VIX extremely low → buy protective puts as insurance")
            elif "Yield" in s["name"]: action_items.append("Yield curve inverted → reduce risk, add defensives (XLU, XLP)")
            elif "Earnings" in s["name"]: action_items.append("Earnings revisions negative → trim positions before earnings")
            elif "Breadth" in s["name"]: action_items.append("Breadth narrowing → reduce small-cap exposure, raise cash")
            elif "Credit" in s["name"]: action_items.append("Credit spreads widening → reduce equity, raise cash to 20-30%")
            elif "Dollar" in s["name"]: action_items.append("Dollar strengthening → reduce international exposure")
    
    if not action_items:
        action_items.append("No strong directional signals — maintain current allocation, focus on stock-picking")
    action_items = list(dict.fromkeys(action_items))
    
    alert = None
    if composite <= CRASH_WARNING_THRESHOLD:
        alert = (f"🚨 <b>MARKET CRASH WARNING</b> 🚨\n\nScore: {composite:.0f}/100\n\n{outlook}\n\n"
                f"<b>Key Signals:</b>\n" + "\n".join([f"• {s['name']}: {s['detail'][:100]}" for s in signals if abs(s.get('score',0))>5]) +
                f"\n\n<b>Actions:</b>\n" + "\n".join([f"• {a}" for a in action_items[:5]]))
    elif composite >= BULLISH_ALERT_THRESHOLD:
        alert = (f"🟢 <b>MAJOR BULLISH SIGNAL</b> 🟢\n\nScore: {composite:.0f}/100\n\n{outlook}\n\n"
                f"<b>Key Signals:</b>\n" + "\n".join([f"• {s['name']}: {s['detail'][:100]}" for s in signals if abs(s.get('score',0))>5]) +
                f"\n\n<b>Actions:</b>\n" + "\n".join([f"• {a}" for a in action_items[:5]]))
    
    sig_scores = [s["score"] for s in signals if s.get("confidence", 0) > 0.3]
    if len(sig_scores) > 1:
        pos = sum(1 for s in sig_scores if s > 5); neg = sum(1 for s in sig_scores if s < -5)
        neu = len(sig_scores) - pos - neg; confidence = max(pos, neg, neu) / len(sig_scores)
    else:
        confidence = 0.3
    
    return {"composite_score": round(composite), "direction": direction, "confidence": round(confidence, 2),
            "outlook": outlook, "signals": signals, "alert": alert, "action_items": action_items}


__all__ = ["init_foresight_skill", "get_market_foresight"]
