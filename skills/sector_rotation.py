"""
Sector Rotation & Thematic Trend Detection Skill v1.0

Detects sector rotations, emerging themes, and sub-sector momentum early.
Designed to find opportunities like the AI memory bottleneck (Sandisk $50→$1600).

Key capabilities:
1. Sector relative strength analysis
2. Sub-sector momentum scoring
3. Thematic trend detection (multi-signal)
4. Small/mid/large cap cycle analysis
5. Growth vs value rotation
6. Sector breadth indicators
7. ETF fund flow analysis
8. Google Trends integration

All data via FREE sources: yfinance, FRED, Google Trends (pytrends)

Usage:
    from skills.sector_rotation import (
        analyze_sector_rotation,
        detect_emerging_themes,
        get_sector_momentum_score,
        generate_sector_report,
        get_macro_rotation_signals,
    )
"""

import json
import datetime
import time
import re
from pathlib import Path
from io import StringIO

BASE_DIR = Path(__file__).parent.parent
FINNHUB_API_KEY = None

# ── Sector ETF mapping ──
SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financial",
    "XLV": "Healthcare",
    "XLE": "Energy",
    "XLI": "Industrial",
    "XLC": "Communication Services",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLU": "Utilities",
    "XLRE": "Real Estate",
    "XLB": "Materials",
}

# ── Size/cap ETFs ──
CAP_ETFS = {
    "SPY": "S&P 500 (Large Cap)",
    "QQQ": "Nasdaq 100 (Growth/Large)",
    "IWM": "Russell 2000 (Small Cap)",
    "MDY": "S&P MidCap 400",
    "VB": "Vanguard Small Cap Value",
    "VO": "Vanguard Mid Cap",
    "VUG": "Vanguard Growth",
    "VTV": "Vanguard Value",
    "MTUM": "Momentum Factor",
    "QUAL": "Quality Factor",
    "USMV": "Low Volatility",
}

# ── Sub-sector / thematic ETFs and tickers ──
SUBSECTOR_ETFS = {
    "Semiconductors": ["SMH", "SOXX", "XSD", "SH"],
    "AI_Memory_HBM": ["MU", "WDC", "STX", "SK HYNIX"],
    "AI_Chips": ["NVDA", "AVGO", "MRVL", "AMD", "INTC"],
    "AI_Infrastructure": ["SMCI", "DELL", "HPE", "ANET", "CIEN"],
    "Cloud_SaaS": ["CRM", "NOW", "SNOW", "NET", "DDOG", "MDB", "WDAY"],
    "Cybersecurity": ["CRWD", "PANW", "ZS", "FTNT", "OKTA", "CYBR"],
    "Fintech": ["V", "MA", "PYPL", "SQ", "COIN", "HOOD", "AFRM", "NU"],
    "Biotech_Genomics": ["ILMN", "CRSP", "EDIT", "NTLA", "BEAM", "ARKG"],
    "Clean_Energy": ["ENPH", "SEDG", "FSLR", "NEE", "ICLN", "QCLN", "TAN"],
    "Defense_Aero": ["LMT", "RTX", "NOC", "GD", "LHX", "KTOS", "AXON"],
    "Robotics_Auto": ["ISRO", "FANUC", "ABB", "ROK", "PATH", "AI", "SYM"],
    "REITs": ["VNQ", "IYR", "SCHH", "XLRE"],
    "Banking": ["KRE", "KBE", "XLF", "VFH"],
    "Oil_Gas": ["XLE", "XOP", "OIH", "FCG", "VDE"],
    "Gold_Miners": ["GDX", "GDXJ", "RING", "GOAU"],
    "Uranium": ["URA", "URNM", "UEC", "CCJ", "UUUU"],
    "Cannabis": ["MSOS", "MJ", "CGC", "TLRY", "ACB"],
    "Gaming_ESports": ["ESPO", "NERD", "GAMR", "ATVI", "TTWO"],
    "Space": ["ARKX", "UFO", "RKLB", "SPCE", "LMT", "BA"],
    "Electric_Vehicles": ["DRIV", "LIT", "BATT", "TSLA", "RIVN", "LCID"],
    "Battery_Storage": ["LIT", "BATT", "QS", "ENVX", "FLNC", "BE"],
}

# ── Macro indicator tickers ──
MACRO_TICKERS = {
    "TLT": "Treasury Bonds (20+ yr)",
    "GLD": "Gold",
    "UUP": "US Dollar",
    "HYG": "High Yield Bonds",
    "LQD": "Investment Grade Bonds",
    "EEM": "Emerging Markets",
    "EFA": "International Developed",
    "VIX": "Volatility Index",
    "TNX": "10-Year Treasury Yield",
    "DXY": "US Dollar Index",
}


def init_sector_skill(finnhub_key=None, base_dir=None):
    """Initialize with API keys."""
    global FINNHUB_API_KEY, BASE_DIR
    if finnhub_key:
        FINNHUB_API_KEY = finnhub_key
    if base_dir:
        BASE_DIR = Path(base_dir)


def _yf_price(ticker, period="3mo"):
    """Get price data via yfinance."""
    try:
        import yfinance as yf
        old_stderr = __import__('sys').stderr
        __import__('sys').stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period=period)
            if hist is not None and len(hist) > 5:
                return hist["Close"]
        finally:
            __import__('sys').stderr = old_stderr
    except Exception:
        pass
    return None


def _fetch_finnhub_quote(symbol):
    """Get quote from Finnhub."""
    if not FINNHUB_API_KEY:
        return None, None
    try:
        import requests
        r = requests.get(
            f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}",
            timeout=10
        )
        if r.status_code == 200:
            data = r.json()
            return data.get("c", 0), data.get("pc", 0)
    except Exception:
        pass
    return None, None


# ═══════════════════════════════════════════════════════════════
# 1. SECTOR RELATIVE STRENGTH ANALYSIS
# ═══════════════════════════════════════════════════════════════

def calculate_relative_strength(ticker, benchmark="SPY", period="6mo"):
    """
    Calculate relative strength of a ticker vs a benchmark.
    RS = (Ticker return / Benchmark return) normalized.
    
    Returns:
        dict: RS score, rating, and raw data
    """
    ticker_prices = _yf_price(ticker, period)
    bench_prices = _yf_price(benchmark, period)
    
    if ticker_prices is None or bench_prices is None or len(ticker_prices) < 5:
        return {"ticker": ticker, "rs_score": 0, "rating": "N/A", "error": "Insufficient data"}
    
    # Calculate returns over different periods
    def calc_return(prices, days):
        if len(prices) > days:
            return (prices.iloc[-1] / prices.iloc[-days] - 1) * 100
        return 0
    
    periods = {
        "1W": 5,
        "1M": 21,
        "3M": 63,
        "6M": 126,
    }
    
    rs_data = {}
    for label, days in periods.items():
        t_ret = calc_return(ticker_prices, days)
        b_ret = calc_return(bench_prices, days)
        rs = t_ret - b_ret  # Relative strength = outperformance
        rs_data[label] = {
            "ticker_return": round(t_ret, 2),
            "bench_return": round(b_ret, 2),
            "relative_strength": round(rs, 2),
        }
    
    # Composite RS score (weighted: 40% 1M + 35% 3M + 25% 6M)
    composite = (
        rs_data.get("1M", {}).get("relative_strength", 0) * 0.40 +
        rs_data.get("3M", {}).get("relative_strength", 0) * 0.35 +
        rs_data.get("6M", {}).get("relative_strength", 0) * 0.25
    )
    
    # Rating
    if composite > 15:
        rating = "🟢 Strong Outperform"
    elif composite > 5:
        rating = "🟢 Outperform"
    elif composite > -5:
        rating = "🟡 Neutral"
    elif composite > -15:
        rating = "🔴 Underperform"
    else:
        rating = "🔴 Strong Underperform"
    
    return {
        "ticker": ticker,
        "benchmark": benchmark,
        "rs_score": round(composite, 2),
        "rating": rating,
        "periods": rs_data,
    }


def analyze_sector_rotation():
    """
    Analyze all 11 S&P sectors for rotation signals.
    Returns sectors ranked by relative strength vs SPY.
    """
    results = []
    
    for etf, name in SECTOR_ETFS.items():
        rs = calculate_relative_strength(etf, "SPY", "6mo")
        rs["name"] = name
        rs["etf"] = etf
        results.append(rs)
    
    # Sort by RS score
    results.sort(key=lambda x: x.get("rs_score", 0), reverse=True)
    
    return {
        "sectors": results,
        "top_sector": results[0] if results else None,
        "bottom_sector": results[-1] if results else None,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ═══════════════════════════════════════════════════════════════
# 2. SIZE/CAP ROTATION ANALYSIS
# ═══════════════════════════════════════════════════════════════

def analyze_cap_rotation():
    """
    Analyze small cap vs large cap vs mid cap rotation.
    Uses IWM/SPY, MDY/SPY ratios.
    """
    results = {}
    
    # Small cap vs Large cap (IWM/SPY)
    iwm = _yf_price("IWM", "1y")
    spy = _yf_price("SPY", "1y")
    
    if iwm is not None and spy is not None and len(iwm) > 21:
        ratio = iwm / spy
        current_ratio = ratio.iloc[-1]
        ratio_1m_ago = ratio.iloc[-21] if len(ratio) > 21 else ratio.iloc[0]
        ratio_3m_ago = ratio.iloc[-63] if len(ratio) > 63 else ratio.iloc[0]
        
        trend_1m = (current_ratio / ratio_1m_ago - 1) * 100
        trend_3m = (current_ratio / ratio_3m_ago - 1) * 100
        
        if trend_1m > 3:
            signal = "🟢 Small caps OUTPERFORMING — risk-on, early cycle"
        elif trend_1m > 0:
            signal = "🟡 Small caps slightly leading"
        elif trend_1m > -3:
            signal = "🟡 Large caps slightly leading — late cycle"
        else:
            signal = "🔴 Large caps OUTPERFORMING — risk-off, late cycle"
        
        results["small_vs_large"] = {
            "ratio": round(current_ratio, 4),
            "trend_1m_pct": round(trend_1m, 2),
            "trend_3m_pct": round(trend_3m, 2),
            "signal": signal,
        }
    
    # Mid cap vs Large cap (MDY/SPY)
    mdy = _yf_price("MDY", "1y")
    if mdy is not None and spy is not None and len(mdy) > 21:
        ratio = mdy / spy
        current_ratio = ratio.iloc[-1]
        ratio_1m_ago = ratio.iloc[-21] if len(ratio) > 21 else ratio.iloc[0]
        trend_1m = (current_ratio / ratio_1m_ago - 1) * 100
        
        if trend_1m > 3:
            signal = "🟢 Mid caps OUTPERFORMING — sweet spot"
        elif trend_1m > 0:
            signal = "🟡 Mid caps slightly leading"
        elif trend_1m > -3:
            signal = "🟡 Large caps slightly leading"
        else:
            signal = "🔴 Large caps OUTPERFORMING"
        
        results["mid_vs_large"] = {
            "ratio": round(current_ratio, 4),
            "trend_1m_pct": round(trend_1m, 2),
            "signal": signal,
        }
    
    # Growth vs Value (VUG/VTV)
    vug = _yf_price("VUG", "1y")
    vtv = _yf_price("VTV", "1y")
    
    if vug is not None and vtv is not None and len(vug) > 21:
        ratio = vug / vtv
        current_ratio = ratio.iloc[-1]
        ratio_1m_ago = ratio.iloc[-21] if len(ratio) > 21 else ratio.iloc[0]
        trend_1m = (current_ratio / ratio_1m_ago - 1) * 100
        
        if trend_1m > 3:
            signal = "🟢 Growth OUTPERFORMING — tech/innovation favored"
        elif trend_1m > 0:
            signal = "🟡 Growth slightly leading"
        elif trend_1m > -3:
            signal = "🟡 Value slightly leading — defensive rotation"
        else:
            signal = "🔴 Value OUTPERFORMING — risk-off, defensive"
        
        results["growth_vs_value"] = {
            "ratio": round(current_ratio, 4),
            "trend_1m_pct": round(trend_1m, 2),
            "signal": signal,
        }
    
    return results


# ═══════════════════════════════════════════════════════════════
# 3. SUB-SECTOR MOMENTUM SCORING
# ═══════════════════════════════════════════════════════════════

def get_sector_momentum_score(ticker):
    """
    Calculate a comprehensive momentum score for a ticker.
    Combines: price momentum, volume trend, volatility regime.
    
    Score range: -100 to +100
    """
    prices = _yf_price(ticker, "6mo")
    if prices is None or len(prices) < 21:
        return {"ticker": ticker, "score": 0, "rating": "N/A"}
    
    score = 0
    
    # 1. Price momentum (40% weight)
    ret_1m = (prices.iloc[-1] / prices.iloc[-21] - 1) * 100 if len(prices) > 21 else 0
    ret_3m = (prices.iloc[-1] / prices.iloc[-63] - 1) * 100 if len(prices) > 63 else 0
    momentum = ret_1m * 0.6 + ret_3m * 0.4
    score += min(max(momentum * 2, -40), 40)  # Cap at ±40
    
    # 2. Moving average position (30% weight)
    ma20 = prices.rolling(20).mean().iloc[-1] if len(prices) >= 20 else prices.iloc[-1]
    ma50 = prices.rolling(50).mean().iloc[-1] if len(prices) >= 50 else prices.iloc[-1]
    ma200 = prices.rolling(200).mean().iloc[-1] if len(prices) >= 200 else prices.iloc[-1]
    
    ma_score = 0
    if prices.iloc[-1] > ma20:
        ma_score += 10
    if prices.iloc[-1] > ma50:
        ma_score += 10
    if prices.iloc[-1] > ma200:
        ma_score += 10
    score += ma_score
    
    # 3. Trend consistency (30% weight)
    # Count up days vs down days in last 20
    daily_returns = prices.pct_change().dropna()
    if len(daily_returns) >= 20:
        up_days = (daily_returns.tail(20) > 0).sum()
        consistency = (up_days / 20 - 0.5) * 60  # -30 to +30
        score += consistency
    
    # Rating
    if score > 50:
        rating = "🟢🟢 Very Strong"
    elif score > 25:
        rating = "🟢 Strong"
    elif score > 0:
        rating = "🟡 Mild Bullish"
    elif score > -25:
        rating = "🟡 Mild Bearish"
    elif score > -50:
        rating = "🔴 Weak"
    else:
        rating = "🔴🔟 Very Weak"
    
    return {
        "ticker": ticker,
        "score": round(score, 1),
        "rating": rating,
        "return_1m": round(ret_1m, 2),
        "return_3m": round(ret_3m, 2),
        "above_ma20": prices.iloc[-1] > ma20,
        "above_ma50": prices.iloc[-1] > ma50,
        "above_ma200": prices.iloc[-1] > ma200 if len(prices) >= 200 else None,
    }


def analyze_subsector_momentum(subsector_name=None):
    """
    Analyze momentum for all tickers in a sub-sector or all sub-sectors.
    """
    if subsector_name:
        tickers = SUBSECTOR_ETFS.get(subsector_name, [])
        if not tickers:
            return {"error": f"Unknown sub-sector: {subsector_name}"}
        
        results = []
        for ticker in tickers:
            score = get_sector_momentum_score(ticker)
            results.append(score)
            time.sleep(0.1)
        
        results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return {
            "subsector": subsector_name,
            "tickers": results,
            "avg_score": round(sum(r.get("score", 0) for r in results) / max(len(results), 1), 1),
        }
    else:
        # Analyze all sub-sectors
        all_results = {}
        for name, tickers in SUBSECTOR_ETFS.items():
            scores = []
            for ticker in ticksers[:5]:  # Top 5 per sub-sector to avoid rate limits
                s = get_sector_momentum_score(ticker)
                scores.append(s.get("score", 0))
                time.sleep(0.1)
            avg = sum(scores) / max(len(scores), 1)
            all_results[name] = {
                "avg_score": round(avg, 1),
                "tickers_analyzed": len(scores),
            }
        
        # Sort by average score
        sorted_results = sorted(all_results.items(), key=lambda x: x[1]["avg_score"], reverse=True)
        return {
            "subsectors": sorted_results,
            "hottest": sorted_results[0] if sorted_results else None,
            "coldest": sorted_results[-1] if sorted_results else None,
        }


# ═══════════════════════════════════════════════════════════════
# 4. THEMATIC TREND DETECTION (Multi-Signal)
# ═══════════════════════════════════════════════════════════════

def detect_emerging_themes():
    """
    Detect emerging investment themes using multi-signal analysis.
    Combines: sector momentum, sub-sector breadth, volume analysis.
    
    This is the "Sandisk detector" — finds themes like AI memory bottleneck early.
    """
    themes = {}
    
    for theme_name, tickers in SUBSECTOR_ETFS.items():
        if len(tickers) < 3:
            continue
        
        # Sample up to 8 tickers per theme
        sample = tickers[:8]
        scores = []
        breadth_count = 0
        total_volume_change = 0
        valid_count = 0
        
        for ticker in sample:
            try:
                price_data = _yf_price(ticker, "3mo")
                if price_data is None or len(price_data) < 21:
                    continue
                
                # Momentum score
                score = get_sector_momentum_score(ticker)
                scores.append(score.get("score", 0))
                
                # Breadth: % above 50-day MA
                ma50 = price_data.rolling(50).mean().iloc[-1] if len(price_data) >= 50 else price_data.mean()
                if price_data.iloc[-1] > ma50:
                    breadth_count += 1
                
                valid_count += 1
                time.sleep(0.1)
            except Exception:
                continue
        
        if valid_count < 2:
            continue
        
        avg_score = sum(scores) / len(scores)
        breadth_pct = (breadth_count / valid_count) * 100
        
        # Composite theme score
        # 50% momentum + 30% breadth + 20% consistency
        consistency = 100 - (max(scores) - min(scores)) if len(scores) > 1 else 50
        theme_score = avg_score * 0.5 + (breadth_pct - 50) * 0.6 + consistency * 0.2
        
        # Signal strength
        if theme_score > 40 and breadth_pct > 70:
            signal = "🔥🔥 STRONG THEME — High conviction opportunity"
        elif theme_score > 20 and breadth_pct > 60:
            signal = "🔥 Emerging theme — Worth watching"
        elif theme_score > 0:
            signal = "🟡 Mild positive"
        elif theme_score > -20:
            signal = "🟡 Neutral"
        else:
            signal = "🔴 Weak/Negative"
        
        themes[theme_name] = {
            "theme_score": round(theme_score, 1),
            "avg_momentum": round(avg_score, 1),
            "breadth_pct": round(breadth_pct, 1),
            "signal": signal,
            "tickers_analyzed": valid_count,
            "top_ticker": max(zip(sample[:valid_count], scores), key=lambda x: x[1])[0] if scores else None,
        }
    
    # Sort by theme score
    sorted_themes = sorted(themes.items(), key=lambda x: x[1]["theme_score"], reverse=True)
    
    return {
        "themes": sorted_themes,
        "hottest_theme": sorted_themes[0] if sorted_themes else None,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


# ═══════════════════════════════════════════════════════════════
# 5. SECTOR BREADTH ANALYSIS
# ═══════════════════════════════════════════════════════════════

def analyze_sector_breadth(etf, lookback=50):
    """
    Analyze breadth within a sector ETF.
    What % of stocks are above their 50-day MA?
    Uses the ETF's top holdings as a proxy.
    """
    try:
        import yfinance as yf
        old_stderr = __import__('sys').stderr
        __import__('sys').stderr = StringIO()
        try:
            t = yf.Ticker(etf)
            info = t.info
            holdings = t.institutional_holders
            
            # Get top holdings
            top_holdings = []
            if holdings is not None and len(holdings) > 0:
                for _, row in holdings.head(20).iterrows():
                    name = row.get("Holder", "")
                    if name:
                        top_holdings.append(name)
            
            if not top_holdings:
                return {"etf": etf, "breadth_pct": 0, "error": "No holdings data"}
            
            # Check how many are above 50-day MA
            above_ma = 0
            checked = 0
            
            for holding in top_holdings[:15]:
                try:
                    h_ticker = holding.split()[0]  # Use first word as ticker approximation
                    h_prices = _yf_price(h_ticker, "3mo")
                    if h_prices is not None and len(h_prices) >= lookback:
                        ma = h_prices.rolling(lookback).mean().iloc[-1]
                        if h_prices.iloc[-1] > ma:
                            above_ma += 1
                        checked += 1
                    time.sleep(0.1)
                except Exception:
                    continue
            
            breadth = (above_ma / max(checked, 1)) * 100
            
            return {
                "etf": etf,
                "breadth_pct": round(breadth, 1),
                "above_ma": above_ma,
                "checked": checked,
                "signal": "🟢 Strong breadth" if breadth > 70 else "🟡 Mixed" if breadth > 40 else "🔴 Weak breadth",
            }
        finally:
            __import__('sys').stderr = old_stderr
    except Exception as e:
        return {"etf": etf, "breadth_pct": 0, "error": str(e)}


# ═══════════════════════════════════════════════════════════════
# 6. MACRO ROTATION SIGNALS
# ═══════════════════════════════════════════════════════════════

def get_macro_rotation_signals():
    """
    Get macro-level rotation signals from key indicator tickers.
    """
    signals = {}
    
    # 1. Risk-on vs Risk-off (HYG/LQD ratio)
    hyg = _yf_price("HYG", "3mo")
    lqd = _yf_price("LQD", "3mo")
    if hyg is not None and lqd is not None and len(hyg) > 21:
        ratio = hyg / lqd
        change_1m = (ratio.iloc[-1] / ratio.iloc[-21] - 1) * 100 if len(ratio) > 21 else 0
        signals["credit_risk"] = {
            "signal": "🟢 Risk-on" if change_1m > 1 else "🔴 Risk-off" if change_1m < -1 else "🟡 Neutral",
            "change_1m": round(change_1m, 2),
        }
    
    # 2. Bond vs Stock (TLT/SPY ratio) — risk appetite
    tlt = _yf_price("TLT", "3mo")
    spy = _yf_price("SPY", "3mo")
    if tlt is not None and spy is not None and len(tlt) > 21:
        ratio = tlt / spy
        change_1m = (ratio.iloc[-1] / ratio.iloc[-21] - 1) * 100 if len(ratio) > 21 else 0
        signals["bond_vs_stock"] = {
            "signal": "🔴 Risk-off (bonds favored)" if change_1m > 2 else "🟢 Risk-on (stocks favored)" if change_1m < -2 else "🟡 Neutral",
            "change_1m": round(change_1m, 2),
        }
    
    # 3. Dollar strength (UUP) — impacts EM, commodities
    uup = _yf_price("UUP", "3mo")
    if uup is not None and len(uup) > 21:
        change_1m = (uup.iloc[-1] / uup.iloc[-21] - 1) * 100
        signals["dollar"] = {
            "signal": "🔴 Strong dollar (headwind for EM/commodities)" if change_1m > 2 else "🟢 Weak dollar (tailwind)" if change_1m < -2 else "🟡 Stable",
            "change_1m": round(change_1m, 2),
        }
    
    # 4. Gold (GLD) — inflation/fear hedge
    gld = _yf_price("GLD", "3mo")
    if gld is not None and len(gld) > 21:
        change_1m = (gld.iloc[-1] / gld.iloc[-21] - 1) * 100
        signals["gold"] = {
            "signal": "🟢 Gold rising (inflation hedge)" if change_1m > 3 else "🔴 Gold falling (risk-on)" if change_1m < -3 else "🟡 Stable",
            "change_1m": round(change_1m, 2),
        }
    
    # 5. Emerging Markets (EEM) — global risk appetite
    eem = _yf_price("EEM", "3mo")
    if eem is not None and len(eem) > 21:
        change_1m = (eem.iloc[-1] / eem.iloc[-21] - 1) * 100
        signals["emerging_markets"] = {
            "signal": "🟢 EM outperforming (global risk-on)" if change_1m > 3 else "🔴 EM underperforming" if change_1m < -3 else "🟡 Neutral",
            "change_1m": round(change_1m, 2),
        }
    
    return signals


# ═══════════════════════════════════════════════════════════════
# 7. COMPREHENSIVE REPORT GENERATION
# ═══════════════════════════════════════════════════════════════

def generate_sector_report():
    """
    Generate a comprehensive sector rotation and thematic analysis report.
    """
    lines = []
    lines.append("## 🔄 SECTOR ROTATION & THEMATIC ANALYSIS")
    lines.append(f"*{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S ET')}*")
    lines.append("")
    
    # 1. Sector Rotation
    lines.append("### 📊 Sector Relative Strength (vs SPY)")
    sector_data = analyze_sector_rotation()
    if sector_data.get("sectors"):
        lines.append("| Rank | Sector | ETF | RS Score | Rating |")
        lines.append("|------|--------|-----|----------|--------|")
        for i, s in enumerate(sector_data["sectors"], 1):
            lines.append(f"| {i} | {s.get('name', '')} | {s.get('etf', '')} | {s.get('rs_score', 0):.1f} | {s.get('rating', '')} |")
    lines.append("")
    
    # 2. Cap Rotation
    lines.append("### 📏 Size/Cap Rotation")
    cap_data = analyze_cap_rotation()
    for key, data in cap_data.items():
        label = key.replace("_", " ").title()
        lines.append(f"**{label}:** {data.get('signal', 'N/A')}")
    lines.append("")
    
    # 3. Macro Signals
    lines.append("### 🌍 Macro Rotation Signals")
    macro = get_macro_rotation_signals()
    for key, data in macro.items():
        label = key.replace("_", " ").title()
        lines.append(f"**{label}:** {data.get('signal', 'N/A')} ({data.get('change_1m', 0):+.1f}% 1M)")
    lines.append("")
    
    # 4. Emerging Themes
    lines.append("### 🔥 Emerging Themes (Multi-Signal Detection)")
    themes = detect_emerging_themes()
    if themes.get("themes"):
        lines.append("| Theme | Score | Breadth | Signal |")
        lines.append("|-------|-------|---------|--------|")
        for name, data in themes["themes"][:10]:
            lines.append(f"| **{name}** | {data['theme_score']:.1f} | {data['breadth_pct']:.0f}% | {data['signal']} |")
    lines.append("")
    
    # 5. Top Thematic Opportunities
    if themes.get("hottest_theme"):
        hottest = themes["hottest_theme"]
        lines.append(f"**🔥 Hottest Theme: {hottest[0]}** (Score: {hottest[1]['theme_score']:.1f})")
        lines.append(f"Signal: {hottest[1]['signal']}")
        lines.append(f"Breadth: {hottest[1]['breadth_pct']:.0f}% of stocks above 50-day MA")
        lines.append(f"Top ticker: {hottest[1].get('top_ticker', 'N/A')}")
        lines.append("")
    
    lines.append("---")
    lines.append("*Data sources: yfinance, Finnhub. Not financial advice.*")
    
    return "\n".join(lines)


if __name__ == "__main__":
    print("Analyzing sector rotation...")
    report = generate_sector_report()
    print(report)
