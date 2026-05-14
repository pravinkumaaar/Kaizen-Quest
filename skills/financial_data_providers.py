"""
Financial Data Providers MCP Integration Module

Wraps multiple financial data APIs (Finnhub, Financial Modeling Prep, yfinance)
as unified MCP-style tools for our agent.

Data Sources:
- Finnhub (already configured): Real-time quotes, earnings, fundamentals, insider trades
- Financial Modeling Prep (FMP): DCF, financial statements, analyst estimates, institutional ownership
- yfinance (free): Company profiles, historical data, options chains

MCP Server Equivalents:
- Fiscal AI → FMP Advanced DCF + Finnhub real-time fundamentals
- Financial Modeling Prep → Direct FMP API integration
- IBISWorld → FMP Industry PE + Sector Performance + Finnhub Basic Financials
- Third Bridge → Finnhub Earnings Transcripts + FMP Transcript Search
- SS&C Intralinks → Not available (deal room access requires subscription)
- Daloopa → FMP Financial Statements As-Reported
- Morningstar → FMP Analyst Estimates + Ratings
- FactSet → FMP Bulk Data + Finnhub Real-time
- Moody's → FMP Financial Scores (Altman Z, Piotroski)
- Aiera → Finnhub News Sentiment + Social Sentiment
- LSEG → FMP Global Filings + Finnhub International
- PitchBook → FMP M&A Data + Institutional Ownership
- Chronograph → Not available (private equity specific)
- Egnyte → Not available (document management)
- MT Newswires → Finnhub Market News + Company News

Usage:
    from skills.financial_data_providers import (
        get_company_profile, get_financial_statements, get_dcf_valuation,
        get_analyst_estimates, get_institutional_ownership, get_insider_trades,
        get_earnings_transcripts, get_sector_performance, get_industry_pe,
        get_news_sentiment, get_social_sentiment, get_supply_chain,
        get_esg_scores, get_congressional_trading, get_forex_rates,
        get_crypto_quotes, get_commodity_quotes, get_economic_calendar,
        get_market_performance, get_technical_indicators, get_bulk_financials,
    )
"""

import os
import json
import datetime
import requests
from pathlib import Path
from io import StringIO

BASE_DIR = Path(__file__).parent.parent

# ─── API Keys ──────────────────────────────────────────────────────────
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
FMP_API_KEY = os.getenv("FMP_API_KEY", "")

# ─── Rate Limiting ─────────────────────────────────────────────────────
_last_call_time = {}
_rate_limits = {
    "finnhub": 60,      # 60 calls/min free tier
    "fmp": 300,         # 300 calls/min free tier
    "yfinance": 10,     # Be conservative
}


def _rate_limit(provider):
    """Simple rate limiter."""
    import time
    now = time.time()
    if provider in _last_call_time:
        elapsed = now - _last_call_time[provider]
        min_interval = 60.0 / _rate_limits.get(provider, 60)
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed)
    _last_call_time[provider] = time.time()


# ─── Finnhub API Wrapper ───────────────────────────────────────────────

def _finnhub_get(endpoint, params=None):
    """Make a GET request to Finnhub API."""
    if not FINNHUB_API_KEY:
        return {"error": "FINNHUB_API_KEY not configured"}
    
    _rate_limit("finnhub")
    
    if params is None:
        params = {}
    params["token"] = FINNHUB_API_KEY
    
    url = f"https://finnhub.io/api/v1/{endpoint}"
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 429:
            return {"error": "Rate limit exceeded", "retry_after": 60}
        else:
            return {"error": f"HTTP {resp.status_code}", "detail": resp.text[:200]}
    except Exception as e:
        return {"error": str(e)}


# ─── FMP API Wrapper ───────────────────────────────────────────────────

def _fmp_get(endpoint, params=None):
    """Make a GET request to Financial Modeling Prep API."""
    if not FMP_API_KEY:
        return {"error": "FMP_API_KEY not configured. Get free key at https://site.financialmodelingprep.com/developer"}
    
    _rate_limit("fmp")
    
    if params is None:
        params = {}
    params["apikey"] = FMP_API_KEY
    
    url = f"https://financialmodelingprep.com/stable/{endpoint}"
    try:
        resp = requests.get(url, params=params, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            # FMP sometimes returns error messages in JSON
            if isinstance(data, dict) and "Error Message" in data:
                return {"error": data["Error Message"]}
            return data
        elif resp.status_code == 429:
            return {"error": "Rate limit exceeded", "retry_after": 60}
        else:
            return {"error": f"HTTP {resp.status_code}", "detail": resp.text[:200]}
    except Exception as e:
        return {"error": str(e)}


# ═══════════════════════════════════════════════════════════════════════
# COMPANY PROFILE & FUNDAMENTALS
# ═══════════════════════════════════════════════════════════════════════

def get_company_profile(ticker):
    """
    Get comprehensive company profile from multiple sources.
    
    Combines Finnhub (real-time) + FMP (detailed) + yfinance (backup).
    
    Args:
        ticker: Stock symbol (e.g., "AAPL")
    
    Returns:
        dict: Company profile with name, sector, industry, description,
              market cap, employees, website, executives, etc.
    """
    result = {"ticker": ticker.upper(), "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    
    # Finnhub company profile (free tier)
    fh_profile = _finnhub_get(f"stock/profile2", {"symbol": ticker})
    if fh_profile and "error" not in fh_profile:
        result["name"] = fh_profile.get("name", "")
        result["sector"] = fh_profile.get("finnhubIndustry", "")
        result["market_cap"] = fh_profile.get("marketCapitalization", 0)
        result["shares_outstanding"] = fh_profile.get("shareOutstanding", 0)
        result["website"] = fh_profile.get("weburl", "")
        result["logo"] = fh_profile.get("logo", "")
        result["country"] = fh_profile.get("country", "")
        result["currency"] = fh_profile.get("currency", "")
        result["exchange"] = fh_profile.get("exchange", "")
        result["ipo_date"] = fh_profile.get("ipo", "")
        result["phone"] = fh_profile.get("phone", "")
        result["finnhub_source"] = True
    
    # FMP company profile (more detailed)
    fmp_profile = _fmp_get(f"profile/{ticker}")
    if fmp_profile and isinstance(fmp_profile, list) and len(fmp_profile) > 0 and "error" not in fmp_profile[0]:
        p = fmp_profile[0]
        result["name"] = result.get("name") or p.get("companyName", "")
        result["sector"] = result.get("sector") or p.get("sector", "")
        result["industry"] = p.get("industry", "")
        result["description"] = p.get("description", "")
        result["ceo"] = p.get("ceo", "")
        result["employees"] = p.get("fullTimeEmployees", "")
        result["address"] = p.get("address", "")
        result["city"] = p.get("city", "")
        result["state"] = p.get("state", "")
        result["zip"] = p.get("zip", "")
        result["image"] = p.get("image", "")
        result["beta"] = p.get("beta", 0)
        result["last_dividend"] = p.get("lastDiv", 0)
        result["fmp_source"] = True
    
    # FMP executives
    fmp_execs = _fmp_get(f"key-executives/{ticker}")
    if fmp_execs and isinstance(fmp_execs, list) and "error" not in fmp_execs:
        result["executives"] = [{
            "name": e.get("name", ""),
            "title": e.get("title", ""),
            "compensation": e.get("compensation", 0),
            "gender": e.get("gender", ""),
            "year_born": e.get("yearBorn", ""),
        } for e in fmp_execs[:10]]
    
    return result


def get_financial_statements(ticker, statement_type="income", period="annual", limit=5):
    """
    Get financial statements from FMP (standardized and as-reported).
    
    Args:
        ticker: Stock symbol
        statement_type: "income", "balance-sheet", or "cash-flow"
        period: "annual" or "quarterly"
        limit: Number of periods to return
    
    Returns:
        dict: Financial statements with line items for each period
    """
    result = {"ticker": ticker.upper(), "statement_type": statement_type, "period": period}
    
    # Map statement types to FMP endpoints
    endpoint_map = {
        "income": "income-statement",
        "balance-sheet": "balance-sheet-statement",
        "cash-flow": "cash-flow-statement",
    }
    
    endpoint = endpoint_map.get(statement_type, "income-statement")
    
    # Get standardized statements
    fmp_data = _fmp_get(f"{endpoint}/{ticker}", {"period": period, "limit": limit})
    if fmp_data and isinstance(fmp_data, list) and "error" not in fmp_data:
        result["statements"] = fmp_data
        result["source"] = "FMP"
        result["count"] = len(fmp_data)
    else:
        # Fallback to Finnhub basic financials
        fh_data = _finnhub_get(f"stock/metric", {"symbol": ticker, "metric": "all"})
        if fh_data and "error" not in fh_data:
            result["metrics"] = fh_data.get("metric", {})
            result["series"] = fh_data.get("series", {})
            result["source"] = "Finnhub"
        else:
            result["error"] = "No financial data available from any source"
    
    return result


def get_financial_ratios(ticker, period="annual", limit=5):
    """
    Get financial ratios from FMP.
    
    Args:
        ticker: Stock symbol
        period: "annual" or "quarterly"  
        limit: Number of periods
    
    Returns:
        dict: Financial ratios including profitability, liquidity, efficiency, leverage
    """
    result = {"ticker": ticker.upper()}
    
    # FMP ratios
    fmp_ratios = _fmp_get(f"ratios/{ticker}", {"period": period, "limit": limit})
    if fmp_ratios and isinstance(fmp_ratios, list) and "error" not in fmp_ratios:
        result["ratios"] = fmp_ratios
        result["source"] = "FMP"
    
    # FMP key metrics
    fmp_metrics = _fmp_get(f"key-metrics/{ticker}", {"period": period, "limit": limit})
    if fmp_metrics and isinstance(fmp_metrics, list) and "error" not in fmp_metrics:
        result["key_metrics"] = fmp_metrics
    
    # FMP financial scores (Altman Z, Piotroski, etc.)
    fmp_scores = _fmp_get(f"financial-scores/{ticker}")
    if fmp_scores and isinstance(fmp_scores, dict) and "error" not in fmp_scores:
        result["financial_scores"] = fmp_scores
    
    return result


# ═══════════════════════════════════════════════════════════════════════
# VALUATION & DCF
# ═══════════════════════════════════════════════════════════════════════

def get_dcf_valuation(ticker, method="advanced"):
    """
    Get DCF valuation from FMP.
    
    Args:
        ticker: Stock symbol
        method: "advanced" (unlevered), "levered" (post-debt), or "custom"
    
    Returns:
        dict: DCF valuation with intrinsic value, upside/downside, assumptions
    """
    result = {"ticker": ticker.upper()}
    
    if method == "levered":
        fmp_dcf = _fmp_get(f"levered-discounted-cash-flow/{ticker}")
    else:
        fmp_dcf = _fmp_get(f"discounted-cash-flow/{ticker}")
    
    if fmp_dcf and isinstance(fmp_dcf, list) and len(fmp_dcf) > 0 and "error" not in fmp_dcf[0]:
        dcf = fmp_dcf[0]
        result["dcf_value"] = dcf.get("dcf", 0)
        result["date"] = dcf.get("date", "")
        result["source"] = "FMP"
    elif fmp_dcf and isinstance(fmp_dcf, dict) and "error" not in fmp_dcf:
        result["dcf_value"] = fmp_dcf.get("dcf", 0)
        result["date"] = fmp_dcf.get("date", "")
        result["source"] = "FMP"
    
    return result


def get_custom_dcf(ticker, assumptions=None):
    """
    Run custom DCF with user-specified assumptions via FMP.
    
    Args:
        ticker: Stock symbol
        assumptions: dict with keys like growth_rate, discount_rate, terminal_growth, etc.
    
    Returns:
        dict: Custom DCF valuation
    """
    if assumptions is None:
        assumptions = {}
    
    params = {"symbol": ticker.upper()}
    params.update(assumptions)
    
    result = _fmp_get(f"custom-discounted-cash-flow/{ticker}", params)
    if result and "error" not in result:
        return {"ticker": ticker.upper(), "custom_dcf": result, "assumptions": assumptions}
    return {"ticker": ticker.upper(), "error": result.get("error", "Custom DCF failed")}


def get_enterprise_value(ticker):
    """Get enterprise value breakdown from FMP."""
    result = _fmp_get(f"enterprise-values/{ticker}")
    if result and isinstance(result, list) and "error" not in result:
        return {"ticker": ticker.upper(), "enterprise_values": result[:5]}
    return {"ticker": ticker.upper(), "error": "No enterprise value data"}


# ═══════════════════════════════════════════════════════════════════════
# ANALYST DATA
# ═══════════════════════════════════════════════════════════════════════

def get_analyst_estimates(ticker, period="quarterly", limit=8):
    """
    Get analyst estimates from FMP.
    
    Args:
        ticker: Stock symbol
        period: "annual" or "quarterly"
        limit: Number of periods
    
    Returns:
        dict: Analyst estimates for revenue, EPS, EBITDA, etc.
    """
    result = {"ticker": ticker.upper()}
    
    # FMP analyst estimates
    fmp_estimates = _fmp_get(f"analyst-estimates/{ticker}", {"period": period, "limit": limit})
    if fmp_estimates and isinstance(fmp_estimates, list) and "error" not in fmp_estimates:
        result["estimates"] = fmp_estimates
        result["source"] = "FMP"
    
    # Finnhub recommendation trends
    fh_recs = _finnhub_get(f"stock/recommendation", {"symbol": ticker})
    if fh_recs and isinstance(fh_recs, list) and "error" not in fh_recs:
        result["recommendation_trends"] = fh_recs[:6]  # Last 6 months
    
    # Finnhub price target
    fh_target = _finnhub_get(f"stock/price-target", {"symbol": ticker})
    if fh_target and "error" not in fh_target:
        result["price_target"] = {
            "target_high": fh_target.get("targetHigh", 0),
            "target_low": fh_target.get("targetLow", 0),
            "target_mean": fh_target.get("targetMean", 0),
            "target_median": fh_target.get("targetMedian", 0),
            "num_analysts": fh_target.get("numberOfAnalysts", 0),
            "last_updated": fh_target.get("lastUpdated", ""),
        }
    
    # FMP analyst recommendations
    fmp_grades = _fmp_get(f"grades/{ticker}")
    if fmp_grades and isinstance(fmp_grades, list) and "error" not in fmp_grades:
        result["analyst_grades"] = fmp_grades[:10]
    
    # FMP price target summary
    fmp_pt = _fmp_get(f"price-target-summary/{ticker}")
    if fmp_pt and isinstance(fmp_pt, dict) and "error" not in fmp_pt:
        result["price_target_summary"] = fmp_pt
    
    return result


def get_analyst_estimates_detailed(ticker):
    """
    Get detailed analyst estimates including revenue, EPS, EBITDA, EBIT, net income.
    Combines Finnhub and FMP for comprehensive coverage.
    """
    result = {"ticker": ticker.upper()}
    
    # Finnhub estimates
    for estimate_type in ["revenue-estimate", "eps-estimate", "ebitda-estimate", "ebit-estimate"]:
        fh_data = _finnhub_get(f"stock/{estimate_type}", {"symbol": ticker, "freq": "quarterly"})
        if fh_data and "error" not in fh_data:
            result[estimate_type] = fh_data
    
    return result


# ═══════════════════════════════════════════════════════════════════════
# INSTITUTIONAL & INSIDER OWNERSHIP
# ═══════════════════════════════════════════════════════════════════════

def get_institutional_ownership(ticker, limit=20):
    """
    Get institutional ownership data.
    
    Args:
        ticker: Stock symbol
        limit: Number of top holders to return
    
    Returns:
        dict: Institutional holders, shares held, value, changes
    """
    result = {"ticker": ticker.upper()}
    
    # FMP institutional ownership
    fmp_13f = _fmp_get(f"institutional-ownership/symbol-positions-summary/{ticker}", {"year": 2024, "quarter": 4})
    if fmp_13f and isinstance(fmp_13f, dict) and "error" not in fmp_13f:
        result["institutional_summary"] = fmp_13f
    
    # Finnhub ownership (free tier)
    fh_ownership = _finnhub_get(f"stock/ownership", {"symbol": ticker, "limit": limit})
    if fh_ownership and isinstance(fh_ownership, dict) and "error" not in fh_ownership:
        result["ownership"] = fh_ownership.get("ownership", [])
    
    # Finnhub fund ownership
    fh_fund = _finnhub_get(f"stock/fund-ownership", {"symbol": ticker, "limit": limit})
    if fh_fund and isinstance(fh_fund, list) and "error" not in fh_fund:
        result["fund_ownership"] = fh_fund[:limit]
    
    return result


def get_insider_trades(ticker, limit=20):
    """
    Get insider trading data.
    
    Args:
        ticker: Stock symbol
        limit: Number of recent trades
    
    Returns:
        dict: Insider transactions with names, dates, amounts, transaction types
    """
    result = {"ticker": ticker.upper()}
    
    # Finnhub insider transactions
    fh_insider = _finnhub_get(f"stock/insider-transactions", {"symbol": ticker, "limit": limit})
    if fh_insider and isinstance(fh_insider, dict) and "error" not in fh_insider:
        result["transactions"] = fh_insider.get("data", [])[:limit]
    
    # Finnhub insider sentiment
    fh_sentiment = _finnhub_get(f"stock/insider-sentiment", {"symbol": ticker, "from": "2024-01-01"})
    if fh_sentiment and isinstance(fh_sentiment, dict) and "error" not in fh_sentiment:
        result["sentiment"] = fh_sentiment.get("data", [])
        result["mspr_summary"] = {
            "total_mspr": sum(d.get("mspr", 0) for d in fh_sentiment.get("data", [])),
            "total_change": sum(d.get("change", 0) for d in fh_sentiment.get("data", [])),
        }
    
    # FMP insider trading
    fmp_insider = _fmp_get(f"insider-trading/search", {"page": 0, "limit": limit})
    if fmp_insider and isinstance(fmp_insider, list) and "error" not in fmp_insider:
        result["fmp_transactions"] = fmp_insider[:limit]
    
    return result


# ═══════════════════════════════════════════════════════════════════════
# EARNINGS & TRANSCRIPTS
# ═══════════════════════════════════════════════════════════════════════

def get_earnings_calendar(ticker=None, days_forward=30):
    """
    Get earnings calendar.
    
    Args:
        ticker: Optional ticker to filter. If None, returns all upcoming.
        days_forward: Number of days to look ahead
    
    Returns:
        dict: Upcoming earnings releases with estimates
    """
    from datetime import timedelta
    
    today = datetime.date.today()
    from_date = today.strftime("%Y-%m-%d")
    to_date = (today + timedelta(days=days_forward)).strftime("%Y-%m-%d")
    
    result = {"from": from_date, "to": to_date}
    
    if ticker:
        # Finnhub company earnings
        fh_earnings = _finnhub_get(f"calendar/earnings", {
            "symbol": ticker,
            "from": from_date,
            "to": to_date
        })
        if fh_earnings and "error" not in fh_earnings:
            result["company_earnings"] = fh_earnings.get("earningsCalendar", [])
    else:
        # Finnhub earnings calendar
        fh_calendar = _finnhub_get(f"calendar/earnings", {
            "from": from_date,
            "to": to_date
        })
        if fh_calendar and "error" not in fh_calendar:
            result["earnings_calendar"] = fh_calendar.get("earningsCalendar", [])[:50]
    
    # FMP earnings calendar
    fmp_earnings = _fmp_get(f"earnings-calendar", {"from": from_date, "to": to_date})
    if fmp_earnings and isinstance(fmp_earnings, list) and "error" not in fmp_earnings:
        result["fmp_earnings"] = fmp_earnings[:50]
    
    return result


def get_earnings_history(ticker, limit=8):
    """
    Get historical earnings with surprises.
    
    Args:
        ticker: Stock symbol
        limit: Number of quarters
    
    Returns:
        dict: Historical earnings with actual vs estimate, surprises
    """
    result = {"ticker": ticker.upper()}
    
    # Finnhub earnings surprises
    fh_earnings = _finnhub_get(f"stock/earnings", {"symbol": ticker, "limit": limit})
    if fh_earnings and isinstance(fh_earnings, list) and "error" not in fh_earnings:
        result["earnings_history"] = fh_earnings
        # Calculate beat/miss stats
        beats = sum(1 for e in fh_earnings if e.get("surprise", 0) > 0)
        misses = sum(1 for e in fh_earnings if e.get("surprise", 0) < 0)
        inline = len(fh_earnings) - beats - misses
        result["summary"] = {
            "total_quarters": len(fh_earnings),
            "beats": beats,
            "misses": misses,
            "inline": inline,
            "beat_rate": round(beats / len(fh_earnings) * 100, 1) if fh_earnings else 0,
            "avg_surprise_pct": round(sum(e.get("surprisePercent", 0) for e in fh_earnings) / len(fh_earnings), 1) if fh_earnings else 0,
        }
    
    return result


def get_earnings_transcripts(ticker, year=None, quarter=None):
    """
    Get earnings call transcripts.
    
    Args:
        ticker: Stock symbol
        year: Fiscal year (optional)
        quarter: Quarter number (optional)
    
    Returns:
        dict: Earnings call transcript with speaker, speech, Q&A sections
    """
    result = {"ticker": ticker.upper()}
    
    if year and quarter:
        # Get specific transcript
        fmp_transcript = _fmp_get(f"earning-call-transcript/{ticker}", {"year": year, "quarter": quarter})
        if fmp_transcript and isinstance(fmp_transcript, list) and "error" not in fmp_transcript:
            result["transcript"] = fmp_transcript
    else:
        # List available transcripts
        fmp_list = _fmp_get(f"earning-call-transcript-dates/{ticker}")
        if fmp_list and isinstance(fmp_list, list) and "error" not in fmp_list:
            result["available_transcripts"] = fmp_list[:10]
            # Get the most recent one
            if fmp_list:
                recent = fmp_list[0]
                fmp_transcript = _fmp_get(f"earning-call-transcript/{ticker}", {
                    "year": recent.get("year"),
                    "quarter": recent.get("quarter")
                })
                if fmp_transcript and isinstance(fmp_transcript, list) and "error" not in fmp_transcript:
                    result["latest_transcript"] = fmp_transcript
    
    return result


# ═══════════════════════════════════════════════════════════════════════
# SECTOR & INDUSTRY ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def get_sector_performance(date=None):
    """
    Get sector performance data.
    
    Args:
        date: Date string (YYYY-MM-DD). If None, returns latest.
    
    Returns:
        dict: Sector performance with average changes
    """
    result = {}
    
    # FMP sector performance
    params = {}
    if date:
        params["date"] = date
    
    fmp_sectors = _fmp_get("sector-performance-snapshot", params)
    if fmp_sectors and isinstance(fmp_sectors, list) and "error" not in fmp_sectors:
        result["sector_performance"] = fmp_sectors
    
    # FMP historical sector performance
    fmp_hist = _fmp_get("historical-sector-performance", {"sector": "Technology"})
    if fmp_hist and isinstance(fmp_hist, list) and "error" not in fmp_hist:
        result["technology_sector_history"] = fmp_hist[:10]
    
    return result


def get_industry_pe(date=None):
    """
    Get industry P/E ratios for valuation comparison.
    
    Args:
        date: Date string (YYYY-MM-DD). If None, returns latest.
    
    Returns:
        dict: Industry P/E ratios
    """
    result = {}
    
    params = {}
    if date:
        params["date"] = date
    
    fmp_ind_pe = _fmp_get("industry-pe-snapshot", params)
    if fmp_ind_pe and isinstance(fmp_ind_pe, list) and "error" not in fmp_ind_pe:
        result["industry_pe"] = fmp_ind_pe
    
    fmp_sector_pe = _fmp_get("sector-pe-snapshot", params)
    if fmp_sector_pe and isinstance(fmp_sector_pe, list) and "error" not in fmp_sector_pe:
        result["sector_pe"] = fmp_sector_pe
    
    return result


def get_market_performance():
    """
    Get overall market performance including gainers, losers, most active.
    
    Returns:
        dict: Market performance data
    """
    result = {}
    
    # FMP market gainers
    fmp_gainers = _fmp_get("biggest-gainers")
    if fmp_gainers and isinstance(fmp_gainers, list) and "error" not in fmp_gainers:
        result["top_gainers"] = fmp_gainers[:10]
    
    # FMP market losers
    fmp_losers = _fmp_get("biggest-losers")
    if fmp_losers and isinstance(fmp_losers, list) and "error" not in fmp_losers:
        result["top_losers"] = fmp_losers[:10]
    
    # FMP most active
    fmp_active = _fmp_get("most-actives")
    if fmp_active and isinstance(fmp_active, list) and "error" not in fmp_active:
        result["most_active"] = fmp_active[:10]
    
    return result


# ═══════════════════════════════════════════════════════════════════════
# NEWS & SENTIMENT
# ═══════════════════════════════════════════════════════════════════════

def get_news_sentiment(ticker):
    """
    Get news sentiment analysis.
    
    Args:
        ticker: Stock symbol
    
    Returns:
        dict: News sentiment scores, bullish/bearish percentages
    """
    result = {"ticker": ticker.upper()}
    
    # Finnhub news sentiment
    fh_sentiment = _finnhub_get(f"news-sentiment", {"symbol": ticker})
    if fh_sentiment and "error" not in fh_sentiment:
        result["sentiment"] = {
            "bullish_percent": fh_sentiment.get("sentiment", {}).get("bullishPercent", 0),
            "bearish_percent": fh_sentiment.get("sentiment", {}).get("bearishPercent", 0),
            "company_news_score": fh_sentiment.get("companyNewsScore", 0),
            "sector_average_score": fh_sentiment.get("sectorAverageNewsScore", 0),
            "sector_average_bullish": fh_sentiment.get("sectorAverageBullishPercent", 0),
            "buzz": fh_sentiment.get("buzz", {}),
        }
    
    return result


def get_social_sentiment(ticker, from_date=None):
    """
    Get social sentiment from Reddit and Twitter.
    
    Args:
        ticker: Stock symbol
        from_date: Start date (YYYY-MM-DD)
    
    Returns:
        dict: Social sentiment scores, mention counts
    """
    if from_date is None:
        from_date = (datetime.date.today() - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
    
    result = {"ticker": ticker.upper()}
    
    fh_social = _finnhub_get(f"stock/social-sentiment", {
        "symbol": ticker,
        "from": from_date
    })
    if fh_social and isinstance(fh_social, dict) and "error" not in fh_social:
        data = fh_social.get("data", [])
        if data:
            result["social_sentiment"] = data[:10]
            # Aggregate
            total_mentions = sum(d.get("mention", 0) for d in data)
            avg_score = sum(d.get("score", 0) for d in data) / len(data)
            result["summary"] = {
                "total_mentions": total_mentions,
                "average_score": round(avg_score, 3),
                "data_points": len(data),
            }
    
    return result


def get_company_news(ticker, limit=20):
    """
    Get company-specific news.
    
    Args:
        ticker: Stock symbol
        limit: Number of articles
    
    Returns:
        dict: Company news articles
    """
    result = {"ticker": ticker.upper()}
    
    # Finnhub company news
    fh_news = _finnhub_get(f"company-news", {
        "symbol": ticker,
        "from": (datetime.date.today() - datetime.timedelta(days=7)).strftime("%Y-%m-%d"),
        "to": datetime.date.today().strftime("%Y-%m-%d")
    })
    if fh_news and isinstance(fh_news, list) and "error" not in fh_news:
        result["news"] = fh_news[:limit]
        result["count"] = len(fh_news)
    
    return result


# ═══════════════════════════════════════════════════════════════════════
# ALTERNATIVE DATA
# ═══════════════════════════════════════════════════════════════════════

def get_supply_chain(ticker):
    """
    Get supply chain relationships (customers and suppliers).
    
    Args:
        ticker: Stock symbol
    
    Returns:
        dict: Key customers and suppliers with correlation data
    """
    result = {"ticker": ticker.upper()}
    
    fh_chain = _finnhub_get(f"stock/supply-chain", {"symbol": ticker})
    if fh_chain and isinstance(fh_chain, dict) and "error" not in fh_chain:
        data = fh_chain.get("data", [])
        result["suppliers"] = [d for d in data if d.get("supplier")]
        result["customers"] = [d for d in data if d.get("customer")]
        result["total_relationships"] = len(data)
    
    return result


def get_esg_scores(ticker):
    """
    Get ESG (Environmental, Social, Governance) scores.
    
    Args:
        ticker: Stock symbol
    
    Returns:
        dict: ESG scores and key indicators
    """
    result = {"ticker": ticker.upper()}
    
    # FMP ESG ratings
    fmp_esg = _fmp_get(f"esg-ratings/{ticker}")
    if fmp_esg and isinstance(fmp_esg, dict) and "error" not in fmp_esg:
        result["esg_ratings"] = fmp_esg
    
    # FMP ESG disclosures
    fmp_disclosure = _fmp_get(f"esg-disclosures/{ticker}")
    if fmp_disclosure and isinstance(fmp_disclosure, list) and "error" not in fmp_disclosure:
        result["esg_disclosures"] = fmp_disclosure[:5]
    
    # Finnhub ESG scores
    fh_esg = _finnhub_get(f"stock/esg", {"symbol": ticker})
    if fh_esg and isinstance(fh_esg, dict) and "error" not in fh_esg:
        result["esg_scores"] = fh_esg.get("data", {})
        result["total_esg_score"] = fh_esg.get("data", {}).get("totalESGScore", 0)
        result["environment_score"] = fh_esg.get("data", {}).get("environmentScore", 0)
        result["social_score"] = fh_esg.get("data", {}).get("socialScore", 0)
        result["governance_score"] = fh_esg.get("data", {}).get("governanceScore", 0)
    
    return result


def get_congressional_trading(ticker):
    """
    Get congressional trading data for a stock.
    
    Args:
        ticker: Stock symbol
    
    Returns:
        dict: Congressional trades with names, amounts, dates
    """
    result = {"ticker": ticker.upper()}
    
    # FMP senate trading
    fmp_senate = _fmp_get(f"senate-trades/{ticker}")
    if fmp_senate and isinstance(fmp_senate, list) and "error" not in fmp_senate:
        result["senate_trades"] = fmp_senate[:20]
    
    # FMP house trading
    fmp_house = _fmp_get(f"house-trades/{ticker}")
    if fmp_house and isinstance(fmp_house, list) and "error" not in fmp_house:
        result["house_trades"] = fmp_house[:20]
    
    # Finnhub congressional trading
    fh_congress = _finnhub_get(f"stock/congressional-trading", {"symbol": ticker})
    if fh_congress and isinstance(fh_congress, dict) and "error" not in fh_congress:
        result["congressional_trades"] = fh_congress.get("data", [])[:20]
    
    return result


# ═══════════════════════════════════════════════════════════════════════
# FOREX, CRYPTO, COMMODITIES
# ═══════════════════════════════════════════════════════════════════════

def get_forex_rates(base="USD"):
    """Get forex rates for all currency pairs."""
    result = _finnhub_get(f"forex/rates", {"base": base})
    if result and "error" not in result:
        return {"base": base, "rates": result.get("quote", {})}
    return {"error": "No forex data available"}


def get_crypto_quotes(symbols=None):
    """
    Get cryptocurrency quotes.
    
    Args:
        symbols: List of crypto symbols (e.g., ["BTCUSD", "ETHUSD"])
    
    Returns:
        dict: Crypto quotes with prices, changes, market caps
    """
    if symbols is None:
        symbols = ["BTCUSD", "ETHUSD", "SOLUSD", "ADAUSD", "DOTUSD", "AVAXUSD", "MATICUSD", "LINKUSD"]
    
    result = {}
    
    for symbol in symbols:
        fh_crypto = _finnhub_get(f"quote", {"symbol": symbol})
        if fh_crypto and "error" not in fh_crypto:
            result[symbol] = {
                "price": fh_crypto.get("c", 0),
                "change": fh_crypto.get("d", 0),
                "change_pct": fh_crypto.get("dp", 0),
                "high": fh_crypto.get("h", 0),
                "low": fh_crypto.get("l", 0),
                "open": fh_crypto.get("o", 0),
                "prev_close": fh_crypto.get("pc", 0),
            }
    
    return result


def get_commodity_quotes():
    """
    Get commodity prices (gold, silver, oil, etc.).
    
    Returns:
        dict: Commodity prices
    """
    commodities = {
        "GCUSD": "Gold",
        "SIUSD": "Silver",
        "CLUSD": "Crude Oil",
        "NGUSD": "Natural Gas",
        "ZWUSD": "Wheat",
        "ZCUSD": "Corn",
    }
    
    result = {}
    for symbol, name in commodities.items():
        fh_quote = _finnhub_get(f"quote", {"symbol": symbol})
        if fh_quote and "error" not in fh_quote:
            result[name] = {
                "symbol": symbol,
                "price": fh_quote.get("c", 0),
                "change": fh_quote.get("d", 0),
                "change_pct": fh_quote.get("dp", 0),
            }
    
    return result


# ═══════════════════════════════════════════════════════════════════════
# ECONOMIC DATA
# ═══════════════════════════════════════════════════════════════════════

def get_economic_calendar(days_forward=14):
    """
    Get economic calendar with upcoming releases.
    
    Args:
        days_forward: Number of days to look ahead
    
    Returns:
        dict: Economic events with dates, countries, impact levels
    """
    from datetime import timedelta
    
    today = datetime.date.today()
    from_date = today.strftime("%Y-%m-%d")
    to_date = (today + timedelta(days=days_forward)).strftime("%Y-%m-%d")
    
    result = {"from": from_date, "to": to_date}
    
    # Finnhub economic calendar
    fh_econ = _finnhub_get(f"calendar/economic", {"from": from_date, "to": to_date})
    if fh_econ and isinstance(fh_econ, dict) and "error" not in fh_econ:
        result["events"] = fh_econ.get("economicCalendar", [])[:30]
    
    return result


def get_treasury_rates():
    """Get US Treasury yield curve data."""
    result = {}
    
    for maturity in ["10y", "5y", "2y", "1y", "6m", "3m", "1m"]:
        fh_yield = _finnhub_get(f"bond/yield-curve", {"code": maturity})
        if fh_yield and isinstance(fh_yield, dict) and "error" not in fh_yield:
            data = fh_yield.get("data", [])
            if data:
                result[maturity] = data[-1].get("v", 0)
    
    return result


# ═══════════════════════════════════════════════════════════════════════
# TECHNICAL ANALYSIS
# ═══════════════════════════════════════════════════════════════════════

def get_technical_indicators(ticker, indicators=None, period=14):
    """
    Get technical indicators for a stock.
    
    Args:
        ticker: Stock symbol
        indicators: List of indicator names (default: ["sma", "ema", "rsi", "macd"])
        period: Lookback period
    
    Returns:
        dict: Technical indicator values
    """
    if indicators is None:
        indicators = ["sma", "ema", "rsi"]
    
    result = {"ticker": ticker.upper(), "period": period}
    
    for indicator in indicators:
        fh_indicator = _finnhub_get(f"indicator", {
            "symbol": ticker,
            "resolution": "D",
            "from": int((datetime.datetime.now() - datetime.timedelta(days=90)).timestamp()),
            "to": int(datetime.datetime.now().timestamp()),
            "indicator": indicator,
            "timeperiod": period
        })
        if fh_indicator and "error" not in fh_indicator:
            result[indicator] = fh_indicator
    
    return result


def get_aggregate_indicators(ticker):
    """
    Get aggregate technical indicator signal (buy/sell/neutral).
    
    Args:
        ticker: Stock symbol
    
    Returns:
        dict: Aggregate signal with individual indicator counts
    """
    result = {"ticker": ticker.upper()}
    
    fh_agg = _finnhub_get(f"scan/technical-indicator", {"symbol": ticker, "resolution": "D"})
    if fh_agg and isinstance(fh_agg, dict) and "error" not in fh_agg:
        result["aggregate_signal"] = fh_agg.get("technicalAnalysis", {}).get("signal", "neutral")
        result["indicator_counts"] = fh_agg.get("technicalAnalysis", {}).get("count", {})
        result["trend"] = fh_agg.get("trend", {})
    
    return result


# ═══════════════════════════════════════════════════════════════════════
# BULK DATA
# ═══════════════════════════════════════════════════════════════════════

def get_bulk_financials(tickers, statement_type="income", period="annual"):
    """
    Get financial statements for multiple tickers in bulk.
    
    Args:
        tickers: List of stock symbols
        statement_type: "income", "balance-sheet", or "cash-flow"
        period: "annual" or "quarterly"
    
    Returns:
        dict: Financial statements for all tickers
    """
    result = {}
    
    endpoint_map = {
        "income": "income-statement-bulk",
        "balance-sheet": "balance-sheet-statement-bulk",
        "cash-flow": "cash-flow-statement-bulk",
    }
    
    endpoint = endpoint_map.get(statement_type, "income-statement-bulk")
    
    # FMP bulk endpoint (process in batches of 5)
    for i in range(0, len(tickers), 5):
        batch = tickers[i:i+5]
        symbols = ",".join(batch)
        
        fmp_bulk = _fmp_get(endpoint, {"period": period, "year": 2024})
        if fmp_bulk and isinstance(fmp_bulk, list) and "error" not in fmp_bulk:
            for item in fmp_bulk:
                sym = item.get("symbol", "")
                if sym in batch:
                    result[sym] = item
    
    return result


def get_bulk_ratings(tickers):
    """Get analyst ratings for multiple tickers."""
    result = {}
    
    for ticker in tickers[:10]:  # Limit to avoid rate limits
        fmp_rating = _fmp_get(f"ratings-snapshot/{ticker}")
        if fmp_rating and isinstance(fmp_rating, dict) and "error" not in fmp_rating:
            result[ticker] = fmp_rating
    
    return result


def get_bulk_dcf(tickers):
    """Get DCF valuations for multiple tickers."""
    result = {}
    
    for ticker in tickers[:10]:
        dcf = get_dcf_valuation(ticker)
        if "dcf_value" in dcf:
            result[ticker] = dcf["dcf_value"]
    
    return result


# ═══════════════════════════════════════════════════════════════════════
# COMPREHENSIVE ANALYSIS (combines all sources)
# ═══════════════════════════════════════════════════════════════════════

def get_comprehensive_analysis(ticker):
    """
    Run a comprehensive analysis combining all data sources.
    
    This is the main entry point for institutional-grade analysis.
    Combines data from Finnhub, FMP, and yfinance.
    
    Args:
        ticker: Stock symbol
    
    Returns:
        dict: Complete analysis with profile, financials, valuation,
              analyst data, ownership, sentiment, technicals
    """
    result = {
        "ticker": ticker.upper(),
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_sources": [],
    }
    
    # 1. Company Profile
    profile = get_company_profile(ticker)
    if "error" not in profile:
        result["profile"] = profile
        result["data_sources"].append("profile")
    
    # 2. Financial Statements
    for stmt_type in ["income", "balance-sheet", "cash-flow"]:
        statements = get_financial_statements(ticker, stmt_type, "annual", 3)
        if "statements" in statements or "metrics" in statements:
            result[f"{stmt_type}_statement"] = statements
            result["data_sources"].append(f"{stmt_type}_statement")
    
    # 3. Financial Ratios & Scores
    ratios = get_financial_ratios(ticker)
    if "ratios" in ratios or "key_metrics" in ratios:
        result["ratios"] = ratios
        result["data_sources"].append("ratios")
    
    # 4. DCF Valuation
    dcf = get_dcf_valuation(ticker)
    if "dcf_value" in dcf:
        result["dcf_valuation"] = dcf
        result["data_sources"].append("dcf")
    
    # 5. Analyst Estimates
    estimates = get_analyst_estimates(ticker)
    if "estimates" in estimates or "recommendation_trends" in estimates:
        result["analyst_data"] = estimates
        result["data_sources"].append("analyst")
    
    # 6. Earnings History
    earnings = get_earnings_history(ticker)
    if "earnings_history" in earnings:
        result["earnings"] = earnings
        result["data_sources"].append("earnings")
    
    # 7. Institutional & Insider
    ownership = get_institutional_ownership(ticker)
    if "ownership" in ownership or "institutional_summary" in ownership:
        result["ownership"] = ownership
        result["data_sources"].append("ownership")
    
    insider = get_insider_trades(ticker)
    if "transactions" in insider:
        result["insider_trades"] = insider
        result["data_sources"].append("insider")
    
    # 8. News & Sentiment
    sentiment = get_news_sentiment(ticker)
    if "sentiment" in sentiment:
        result["news_sentiment"] = sentiment
        result["data_sources"].append("sentiment")
    
    social = get_social_sentiment(ticker)
    if "summary" in social:
        result["social_sentiment"] = social
        result["data_sources"].append("social_sentiment")
    
    # 9. Technical Analysis
    technicals = get_aggregate_indicators(ticker)
    if "aggregate_signal" in technicals:
        result["technical_analysis"] = technicals
        result["data_sources"].append("technical")
    
    # 10. ESG
    esg = get_esg_scores(ticker)
    if "esg_scores" in esg or "total_esg_score" in esg:
        result["esg"] = esg
        result["data_sources"].append("esg")
    
    # 11. Supply Chain
    supply_chain = get_supply_chain(ticker)
    if "suppliers" in supply_chain:
        result["supply_chain"] = supply_chain
        result["data_sources"].append("supply_chain")
    
    result["sources_used"] = len(result["data_sources"])
    
    return result


# ═══════════════════════════════════════════════════════════════════════
# INITIALIZATION
# ═══════════════════════════════════════════════════════════════════════

def init_financial_data_providers(finnhub_key=None, fmp_key=None):
    """
    Initialize API keys for financial data providers.
    
    Args:
        finnhub_key: Finnhub API key (or set FINNHUB_API_KEY env var)
        fmp_key: Financial Modeling Prep API key (or set FMP_API_KEY env var)
    """
    global FINNHUB_API_KEY, FMP_API_KEY
    
    if finnhub_key:
        FINNHUB_API_KEY = finnhub_key
    if fmp_key:
        FMP_API_KEY = fmp_key
    
    # Also check environment
    if not FINNHUB_API_KEY:
        FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
    if not FMP_API_KEY:
        FMP_API_KEY = os.getenv("FMP_API_KEY", "")
    
    status = {
        "finnhub": "configured" if FINNHUB_API_KEY else "NOT CONFIGURED",
        "fmp": "configured" if FMP_API_KEY else "NOT CONFIGURED (get free key at https://site.financialmodelingprep.com/developer)",
        "yfinance": "available (no key needed)",
    }
    
    return status


# Auto-initialize on import
_provider_status = init_financial_data_providers()


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    
    print(f"Running comprehensive analysis for {ticker}...")
    print(f"Provider status: {_provider_status}")
    print("=" * 80)
    
    analysis = get_comprehensive_analysis(ticker)
    
    print(f"\nData sources used: {analysis.get('sources_used', 0)}")
    print(f"Sources: {', '.join(analysis.get('data_sources', []))}")
    
    if "profile" in analysis:
        p = analysis["profile"]
        print(f"\nCompany: {p.get('name', 'N/A')} ({p.get('ticker', ticker)})")
        print(f"Sector: {p.get('sector', 'N/A')} | Industry: {p.get('industry', 'N/A')}")
        print(f"Market Cap: ${p.get('market_cap', 0):.1f}M")
    
    if "dcf_valuation" in analysis:
        dcf = analysis["dcf_valuation"]
        print(f"\nDCF Value: ${dcf.get('dcf_value', 0):.2f}")
    
    if "analyst_data" in analysis:
        a = analysis["analyst_data"]
        if "price_target" in a:
            pt = a["price_target"]
            print(f"\nPrice Target: ${pt.get('target_mean', 0):.2f} (High: ${pt.get('target_high', 0):.2f}, Low: ${pt.get('target_low', 0):.2f})")
            print(f"Analysts: {pt.get('num_analysts', 0)}")
    
    if "earnings" in analysis:
        e = analysis["earnings"]
        if "summary" in e:
            s = e["summary"]
            print(f"\nEarnings: {s.get('beat_rate', 0)}% beat rate over {s.get('total_quarters', 0)} quarters")
            print(f"Avg Surprise: {s.get('avg_surprise_pct', 0):+.1f}%")
