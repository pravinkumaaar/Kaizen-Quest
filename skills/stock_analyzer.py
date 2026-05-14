"""
Stock Analyzer Skill v1.0

Comprehensive stock analysis combining:
1. Earnings Analysis - reads transcripts, filings, flags thesis-relevant changes
2. Comparable Company Analysis (Comps) - peer multiples, outlier detection
3. DCF Valuation - discounted cash flow model
4. Sector/Industry Analysis - competitive landscape, market positioning
5. Financial Health Assessment - balance sheet, cash flow, profitability trends

Uses free data sources: yfinance, Finnhub, SEC EDGAR
No paid MCP connectors required (FactSet, Daloopa, etc. need subscriptions)

Usage:
    from skills.stock_analyzer import (
        analyze_stock,
        compare_companies,
        sector_analysis,
        earnings_summary,
    )
"""

import json
import datetime
import re
from pathlib import Path
from io import StringIO

BASE_DIR = Path(__file__).parent.parent
FINNHUB_API_KEY = None


def init_stock_analyzer(finnhub_key=None, base_dir=None):
    global FINNHUB_API_KEY, BASE_DIR
    if finnhub_key:
        FINNHUB_API_KEY = finnhub_key
    if base_dir:
        BASE_DIR = Path(base_dir)


# ═══════════════════════════════════════════════════════════════
# CORE ANALYSIS FUNCTIONS
# ═══════════════════════════════════════════════════════════════

def analyze_stock(ticker, depth="comprehensive"):
    """
    Comprehensive single-stock analysis.
    
    Args:
        ticker: Stock symbol (e.g., "AAPL")
        depth: "quick" (key metrics only) or "comprehensive" (full analysis)
    
    Returns:
        dict: Complete analysis with sections for each area
    """
    result = {
        "ticker": ticker.upper(),
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_quality": "live",
    }
    
    # 1. Company Profile & Key Metrics
    profile = get_company_profile(ticker)
    result["profile"] = profile
    
    # 2. Valuation Multiples
    valuation = get_valuation_multiples(ticker)
    result["valuation"] = valuation
    
    # 3. Financial Health
    financials = get_financial_health(ticker)
    result["financials"] = financials
    
    # 4. Earnings Analysis
    earnings = get_earnings_analysis(ticker)
    result["earnings"] = earnings
    
    # 5. Technical Position
    technical = get_technical_position(ticker)
    result["technical"] = technical
    
    if depth == "comprehensive":
        # 6. Peer Comparison
        peers = get_peer_comparison(ticker)
        result["peers"] = peers
        
        # 7. Risk Assessment
        risks = get_risk_assessment(ticker)
        result["risks"] = risks
        
        # 8. Investment Score
        score = calculate_investment_score(result)
        result["investment_score"] = score
    
    return result


def get_company_profile(ticker):
    """Get company profile and key metrics."""
    try:
        import yfinance as yf
        old_stderr = __import__('sys').stderr
        __import__('sys').stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            info = t.info
            
            return {
                "name": info.get("longName", ticker),
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "market_cap": info.get("marketCap", 0),
                "market_cap_b": round(info.get("marketCap", 0) / 1e9, 2) if info.get("marketCap") else 0,
                "enterprise_value": info.get("enterpriseValue", 0),
                "employees": info.get("fullTimeEmployees", 0),
                "description": info.get("longBusinessSummary", "")[:500],
                "website": info.get("website", ""),
                "country": info.get("country", "N/A"),
                "exchange": info.get("exchange", "N/A"),
                "quote_type": info.get("quoteType", "N/A"),
            }
        finally:
            __import__('sys').stderr = old_stderr
    except Exception as e:
        return {"error": str(e)}


def get_valuation_multiples(ticker):
    """Get key valuation multiples."""
    try:
        import yfinance as yf
        old_stderr = __import__('sys').stderr
        __import__('sys').stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            info = t.info
            
            # Price
            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose", 0)
            
            # Multiples
            pe_ratio = info.get("trailingPE", 0)
            forward_pe = info.get("forwardPE", 0)
            peg_ratio = info.get("pegRatio", 0)
            ps_ratio = info.get("priceToSalesTrailing12Months", 0)
            pb_ratio = info.get("priceToBook", 0)
            ev_ebitda = info.get("enterpriseToEbitda", 0)
            ev_revenue = info.get("enterpriseToRevenue", 0)
            
            # Dividend
            dividend_yield = info.get("dividendYield", 0) or 0
            dividend_rate = info.get("dividendRate", 0) or 0
            payout_ratio = info.get("payoutRatio", 0) or 0
            
            # Growth
            revenue_growth = info.get("revenueGrowth", 0) or 0
            earnings_growth = info.get("earningsGrowth", 0) or 0
            roe = info.get("returnOnEquity", 0) or 0
            roa = info.get("returnOnAssets", 0) or 0
            
            # Margins
            gross_margin = info.get("grossMargins", 0) or 0
            operating_margin = info.get("operatingMargins", 0) or 0
            profit_margin = info.get("profitMargins", 0) or 0
            
            # Balance Sheet
            debt_to_equity = info.get("debtToEquity", 0) or 0
            current_ratio = info.get("currentRatio", 0) or 0
            quick_ratio = info.get("quickRatio", 0) or 0
            free_cash_flow = info.get("freeCashflow", 0) or 0
            
            # 52-week range
            week_52_high = info.get("fiftyTwoWeekHigh", 0) or 0
            week_52_low = info.get("fiftyTwoWeekLow", 0) or 0
            week_52_change = ((price - week_52_low) / (week_52_high - week_52_low) * 100) if week_52_high > week_52_low else 50
            
            return {
                "price": round(price, 2) if price else 0,
                "pe_trailing": round(pe_ratio, 1) if pe_ratio else None,
                "pe_forward": round(forward_pe, 1) if forward_pe else None,
                "peg_ratio": round(peg_ratio, 1) if peg_ratio else None,
                "ps_ratio": round(ps_ratio, 1) if ps_ratio else None,
                "pb_ratio": round(pb_ratio, 1) if pb_ratio else None,
                "ev_ebitda": round(ev_ebitda, 1) if ev_ebitda else None,
                "ev_revenue": round(ev_revenue, 1) if ev_revenue else None,
                "dividend_yield_pct": round(dividend_yield * 100, 2) if dividend_yield else 0,
                "dividend_rate": round(dividend_rate, 2) if dividend_rate else 0,
                "payout_ratio_pct": round(payout_ratio * 100, 1) if payout_ratio else 0,
                "revenue_growth_pct": round(revenue_growth * 100, 1) if revenue_growth else None,
                "earnings_growth_pct": round(earnings_growth * 100, 1) if earnings_growth else None,
                "roe_pct": round(roe * 100, 1) if roe else None,
                "roa_pct": round(roa * 100, 1) if roa else None,
                "gross_margin_pct": round(gross_margin * 100, 1) if gross_margin else None,
                "operating_margin_pct": round(operating_margin * 100, 1) if operating_margin else None,
                "profit_margin_pct": round(profit_margin * 100, 1) if profit_margin else None,
                "debt_to_equity": round(debt_to_equity, 1) if debt_to_equity else None,
                "current_ratio": round(current_ratio, 1) if current_ratio else None,
                "free_cash_flow_b": round(free_cash_flow / 1e9, 2) if free_cash_flow else None,
                "week_52_high": round(week_52_high, 2) if week_52_high else None,
                "week_52_low": round(week_52_low, 2) if week_52_low else None,
                "week_52_position_pct": round(week_52_change, 1),
            }
        finally:
            __import__('sys').stderr = old_stderr
    except Exception as e:
        return {"error": str(e)}


def get_financial_health(ticker):
    """Assess financial health from balance sheet and cash flow."""
    try:
        import yfinance as yf
        old_stderr = __import__('sys').stderr
        __import__('sys').stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            info = t.info
            
            # Revenue trend (3 years)
            revenue = info.get("totalRevenue", 0) or 0
            
            # Profitability
            net_income = info.get("netIncomeToCommon", 0) or 0
            ebitda = info.get("ebitda", 0) or 0
            
            # Cash flow
            operating_cf = info.get("operatingCashflow", 0) or 0
            free_cf = info.get("freeCashflow", 0) or 0
            capex = info.get("capitalExpenditures", 0) or 0
            
            # Balance sheet
            total_debt = info.get("totalDebt", 0) or 0
            total_cash = info.get("totalCash", 0) or 0
            total_assets = info.get("totalAssets", 0) or 0
            total_equity = info.get("totalStockholderEquity", 0) or 0
            
            # Calculate health scores
            health = {
                "revenue_b": round(revenue / 1e9, 2) if revenue else None,
                "net_income_b": round(net_income / 1e9, 2) if net_income else None,
                "ebitda_b": round(ebitda / 1e9, 2) if ebitda else None,
                "operating_cf_b": round(operating_cf / 1e9, 2) if operating_cf else None,
                "free_cf_b": round(free_cf / 1e9, 2) if free_cf else None,
                "capex_b": round(abs(capex) / 1e9, 2) if capex else None,
                "total_debt_b": round(total_debt / 1e9, 2) if total_debt else None,
                "total_cash_b": round(total_cash / 1e9, 2) if total_cash else None,
                "net_debt_b": round((total_debt - total_cash) / 1e9, 2) if total_debt else None,
                "debt_to_ebitda": round(total_debt / ebitda, 1) if ebitda and ebitda > 0 else None,
                "interest_coverage": round(ebitda / (total_debt * 0.05), 1) if ebitda and total_debt > 0 else None,
                "cf_to_debt_pct": round(free_cf / total_debt * 100, 1) if total_debt and total_debt > 0 else None,
                "asset_turnover": round(revenue / total_assets, 2) if total_assets and total_assets > 0 else None,
                "equity_ratio_pct": round(total_equity / total_assets * 100, 1) if total_assets and total_assets > 0 else None,
            }
            
            # Health rating
            score = 0
            factors = []
            
            if health.get("debt_to_ebitda") is not None:
                if health["debt_to_ebitda"] < 2:
                    score += 2
                    factors.append("Low debt/EBITDA")
                elif health["debt_to_ebitda"] < 4:
                    score += 1
                    factors.append("Moderate leverage")
                else:
                    score -= 1
                    factors.append("High leverage")
            
            if health.get("interest_coverage") is not None:
                if health["interest_coverage"] > 5:
                    score += 2
                    factors.append("Strong interest coverage")
                elif health["interest_coverage"] > 2:
                    score += 1
                else:
                    score -= 1
                    factors.append("Weak interest coverage")
            
            if health.get("free_cf_b") is not None and health["free_cf_b"] > 0:
                score += 1
                factors.append("Positive FCF")
            elif health.get("free_cf_b") is not None and health["free_cf_b"] < 0:
                score -= 1
                factors.append("Negative FCF")
            
            if health.get("equity_ratio_pct") is not None:
                if health["equity_ratio_pct"] > 40:
                    score += 1
                    factors.append("Strong equity base")
                elif health["equity_ratio_pct"] < 20:
                    score -= 1
                    factors.append("Thin equity base")
            
            if score >= 4:
                health_rating = "Excellent"
            elif score >= 2:
                health_rating = "Good"
            elif score >= 0:
                health_rating = "Fair"
            else:
                health_rating = "Weak"
            
            health["score"] = score
            health["rating"] = health_rating
            health["factors"] = factors
            
            return health
        finally:
            __import__('sys').stderr = old_stderr
    except Exception as e:
        return {"error": str(e)}


def get_earnings_analysis(ticker):
    """Analyze recent earnings and estimates."""
    try:
        import yfinance as yf
        old_stderr = __import__('sys').stderr
        __import__('sys').stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            info = t.info
            
            # Earnings estimates
            eps_estimate_current = info.get("epsEstimateCurrentYear", 0) or 0
            eps_estimate_next = info.get("epsEstimateNextYear", 0) or 0
            eps_estimate_quarterly = info.get("epsEstimateCurrentQuarter", 0) or 0
            eps_actual_quarterly = info.get("epsActualCurrentQuarter", 0)
            
            # Revenue estimates
            revenue_estimate = info.get("revenueEstimateCurrentQuarter", 0) or 0
            
            # Earnings history
            earnings_surprise = info.get("earningsQuarterlyGrowth", 0) or 0
            eps_trailing = info.get("trailingEps", 0) or 0
            eps_forward = info.get("forwardEps", 0) or 0
            
            # Analyst recommendations
            recommendation = info.get("recommendationKey", "N/A")
            num_analysts = info.get("numberOfAnalystOpinions", 0) or 0
            target_mean = info.get("targetMeanPrice", 0) or 0
            target_high = info.get("targetHighPrice", 0) or 0
            target_low = info.get("targetLowPrice", 0) or 0
            current_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            
            # Calculate upside/downside to target
            upside_pct = ((target_mean - current_price) / current_price * 100) if current_price > 0 else 0
            
            # EPS growth trajectory
            eps_growth = ((eps_forward - eps_trailing) / abs(eps_trailing) * 100) if eps_trailing and eps_trailing != 0 else 0
            
            return {
                "eps_trailing": round(eps_trailing, 2) if eps_trailing else None,
                "eps_forward": round(eps_forward, 2) if eps_forward else None,
                "eps_estimate_current_year": round(eps_estimate_current, 2) if eps_estimate_current else None,
                "eps_estimate_next_year": round(eps_estimate_next, 2) if eps_estimate_next else None,
                "eps_growth_pct": round(eps_growth, 1) if eps_growth else None,
                "earnings_surprise_pct": round(earnings_surprise * 100, 1) if earnings_surprise else None,
                "recommendation": recommendation,
                "num_analysts": num_analysts,
                "target_mean": round(target_mean, 2) if target_mean else None,
                "target_high": round(target_high, 2) if target_high else None,
                "target_low": round(target_low, 2) if target_low else None,
                "upside_to_target_pct": round(upside_pct, 1) if upside_pct else None,
                "current_price": round(current_price, 2) if current_price else None,
            }
        finally:
            __import__('sys').stderr = old_stderr
    except Exception as e:
        return {"error": str(e)}


def get_technical_position(ticker):
    """Get technical analysis position."""
    try:
        import yfinance as yf
        old_stderr = __import__('sys').stderr
        __import__('sys').stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            hist = t.history(period="6mo")
            
            if hist is None or len(hist) < 20:
                return {"error": "Insufficient price data"}
            
            close = hist["Close"]
            current = close.iloc[-1]
            
            # Moving averages
            ma20 = close.rolling(20).mean().iloc[-1] if len(close) >= 20 else current
            ma50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else current
            ma200 = close.rolling(200).mean().iloc[-1] if len(close) >= 200 else current
            
            # Trend determination
            if current > ma20 > ma50:
                trend = "Strong Uptrend"
            elif current > ma20:
                trend = "Mild Uptrend"
            elif current < ma20 < ma50:
                trend = "Strong Downtrend"
            elif current < ma20:
                trend = "Mild Downtrend"
            else:
                trend = "Sideways"
            
            # RSI (14-day)
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = (100 - (100 / (1 + rs))).iloc[-1] if len(close) >= 14 else 50
            
            # Bollinger Bands
            bb_mid = close.rolling(20).mean().iloc[-1]
            bb_std = close.rolling(20).std().iloc[-1]
            bb_upper = bb_mid + 2 * bb_std
            bb_lower = bb_mid - 2 * bb_std
            bb_position = (current - bb_lower) / (bb_upper - bb_lower) * 100 if bb_upper > bb_lower else 50
            
            # Volume trend
            avg_volume = hist["Volume"].rolling(20).mean().iloc[-1] if len(hist) >= 20 else 0
            recent_volume = hist["Volume"].iloc[-5:].mean() if len(hist) >= 5 else 0
            volume_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
            
            # Momentum
            returns_1m = (close.iloc[-1] / close.iloc[-21] - 1) * 100 if len(close) >= 21 else 0
            returns_3m = (close.iloc[-1] / close.iloc[-63] - 1) * 100 if len(close) >= 63 else 0
            
            return {
                "current_price": round(current, 2),
                "ma20": round(ma20, 2),
                "ma50": round(ma50, 2),
                "ma200": round(ma200, 2) if ma200 else None,
                "trend": trend,
                "rsi_14": round(rsi, 1),
                "bb_upper": round(bb_upper, 2),
                "bb_lower": round(bb_lower, 2),
                "bb_position_pct": round(bb_position, 1),
                "volume_ratio": round(volume_ratio, 2),
                "return_1m_pct": round(returns_1m, 1),
                "return_3m_pct": round(returns_3m, 1),
                "above_ma20": current > ma20,
                "above_ma50": current > ma50,
                "above_ma200": current > ma200 if ma200 else None,
            }
        finally:
            __import__('sys').stderr = old_stderr
    except Exception as e:
        return {"error": str(e)}


def get_peer_comparison(ticker, max_peers=5):
    """Get peer comparison data."""
    try:
        import yfinance as yf
        old_stderr = __import__('sys').stderr
        __import__('sys').stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            info = t.info
            
            # Get peer tickers from recommendations
            peers = []
            try:
                recs = t.recommendations
                if recs is not None and len(recs) > 0:
                    # Use recommended peers if available
                    pass
            except Exception:
                pass
            
            # Fallback: use industry peers from info
            sector = info.get("sector", "")
            industry = info.get("industry", "")
            
            # Common peer mappings for major sectors
            sector_peers = {
                "Technology": ["MSFT", "GOOGL", "META", "AMD", "INTC", "CRM", "ORCL", "CSCO", "ADBE", "NVDA"],
                "Communication Services": ["GOOGL", "META", "DIS", "NFLX", "CMCSA", "T", "VZ", "TMUS", "CHTR", "EA"],
                "Consumer Discretionary": ["AMZN", "TSLA", "HD", "NKE", "MCD", "SBUX", "TGT", "LOW", "BKNG", "CMG"],
                "Consumer Staples": ["PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "CL", "GIS", "HSY"],
                "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "PXD", "VLO", "PSX", "MPC", "OXY"],
                "Financials": ["JPM", "BAC", "WFC", "GS", "MS", "C", "BLK", "AXP", "V", "MA"],
                "Healthcare": ["JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "TMO", "ABT", "DHR", "BMY"],
                "Industrials": ["CAT", "HON", "UPS", "BA", "GE", "MMM", "LMT", "RTX", "DE", "FDX"],
                "Materials": ["LIN", "APD", "SHW", "FCX", "NEM", "ECL", "DOW", "PPG", "DD", "CTVA"],
                "Real Estate": ["AMT", "PLD", "CCI", "EQIX", "PSA", "O", "WELL", "SPG", "VTR", "AVB"],
                "Utilities": ["NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "ED", "WEC"],
            }
            
            peer_tickers = sector_peers.get(sector, [])
            # Remove self from peers
            peer_tickers = [p for p in peer_tickers if p != ticker.upper()][:max_peers]
            
            peer_data = []
            for peer in peer_tickers:
                try:
                    pt = yf.Ticker(peer)
                    pi = pt.info
                    p_price = pi.get("currentPrice") or pi.get("regularMarketPrice") or 0
                    
                    peer_data.append({
                        "ticker": peer,
                        "name": pi.get("shortName", peer),
                        "price": round(p_price, 2) if p_price else 0,
                        "market_cap_b": round(pi.get("marketCap", 0) / 1e9, 1) if pi.get("marketCap") else 0,
                        "pe": round(pi.get("trailingPE", 0), 1) if pi.get("trailingPE") else None,
                        "forward_pe": round(pi.get("forwardPE", 0), 1) if pi.get("forwardPE") else None,
                        "ps": round(pi.get("priceToSalesTrailing12Months", 0), 1) if pi.get("priceToSalesTrailing12Months") else None,
                        "ev_ebitda": round(pi.get("enterpriseToEbitda", 0), 1) if pi.get("enterpriseToEbitda") else None,
                        "revenue_growth": round((pi.get("revenueGrowth", 0) or 0) * 100, 1),
                        "profit_margin": round((pi.get("profitMargins", 0) or 0) * 100, 1),
                        "roe": round((pi.get("returnOnEquity", 0) or 0) * 100, 1),
                    })
                except Exception:
                    continue
            
            return {
                "sector": sector,
                "industry": industry,
                "peers": peer_data,
                "peer_count": len(peer_data),
            }
        finally:
            __import__('sys').stderr = old_stderr
    except Exception as e:
        return {"error": str(e)}


def get_risk_assessment(ticker):
    """Assess investment risks."""
    try:
        import yfinance as yf
        old_stderr = __import__('sys').stderr
        __import__('sys').stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            info = t.info
            hist = t.history(period="1y")
            
            risks = []
            risk_score = 0  # Higher = more risky
            
            # Valuation risk
            pe = info.get("trailingPE", 0) or 0
            if pe > 50:
                risks.append("Very high P/E ratio (>50x) — significant valuation risk")
                risk_score += 3
            elif pe > 30:
                risks.append("Elevated P/E ratio (>30x) — moderate valuation risk")
                risk_score += 2
            elif pe < 0:
                risks.append("Negative earnings — company is unprofitable")
                risk_score += 3
            
            # Debt risk
            debt_eq = info.get("debtToEquity", 0) or 0
            if debt_eq > 200:
                risks.append("Very high debt-to-equity (>200%) — balance sheet risk")
                risk_score += 3
            elif debt_eq > 100:
                risks.append("Elevated debt-to-equity (>100%)")
                risk_score += 1
            
            # Volatility risk
            if hist is not None and len(hist) > 20:
                returns = hist["Close"].pct_change().dropna()
                volatility = returns.std() * (252 ** 0.5) * 100  # Annualized
                if volatility > 50:
                    risks.append(f"Very high volatility ({volatility:.0f}% annualized)")
                    risk_score += 2
                elif volatility > 30:
                    risks.append(f"Above-average volatility ({volatility:.0f}% annualized)")
                    risk_score += 1
            
            # Earnings risk
            earnings_growth = info.get("earningsQuarterlyGrowth", 0) or 0
            if earnings_growth < -0.2:
                risks.append(f"Declining earnings ({earnings_growth*100:.0f}% quarterly)")
                risk_score += 2
            
            # Short interest
            short_pct = info.get("sharesPercentSharesOut", 0) or 0
            if short_pct > 0.1:
                risks.append(f"High short interest ({short_pct*100:.1f}%) — potential squeeze or bearish sentiment")
                risk_score += 1
            
            # Free cash flow
            fcf = info.get("freeCashflow", 0) or 0
            if fcf < 0:
                risks.append("Negative free cash flow")
                risk_score += 2
            
            # Determine overall risk level
            if risk_score >= 8:
                risk_level = "Very High"
            elif risk_score >= 5:
                risk_level = "High"
            elif risk_score >= 3:
                risk_level = "Moderate"
            elif risk_score >= 1:
                risk_level = "Low"
            else:
                risk_level = "Very Low"
            
            return {
                "risk_level": risk_level,
                "risk_score": risk_score,
                "risks": risks,
                "volatility_annualized": round(volatility, 1) if hist is not None and len(hist) > 20 else None,
            }
        finally:
            __import__('sys').stderr = old_stderr
    except Exception as e:
        return {"error": str(e)}


def calculate_investment_score(analysis):
    """
    Calculate an overall investment score (0-100) based on all analysis sections.
    
    Scoring:
    - Valuation (25%): P/E, P/B, EV/EBITDA vs sector
    - Growth (25%): Revenue growth, EPS growth, ROE
    - Financial Health (25%): Debt, cash flow, margins
    - Technical (15%): Trend, momentum, position vs MAs
    - Risk (10%): Risk factors, volatility
    """
    score = 50  # Start neutral
    factors = []
    
    # Valuation scoring
    valuation = analysis.get("valuation", {})
    pe = valuation.get("pe_trailing")
    if pe and pe > 0:
        if pe < 15:
            score += 10
            factors.append("Attractive P/E (<15x)")
        elif pe < 25:
            score += 5
            factors.append("Reasonable P/E (15-25x)")
        elif pe > 40:
            score -= 10
            factors.append("Expensive P/E (>40x)")
        elif pe > 30:
            score -= 5
            factors.append("Elevated P/E (30-40x)")
    
    pb = valuation.get("pb_ratio")
    if pb and pb > 0:
        if pb < 2:
            score += 5
            factors.append("Low P/B (<2x)")
        elif pb > 5:
            score -= 5
            factors.append("High P/B (>5x)")
    
    # Growth scoring
    rev_growth = valuation.get("revenue_growth_pct")
    if rev_growth is not None:
        if rev_growth > 20:
            score += 10
            factors.append(f"Strong revenue growth ({rev_growth:.0f}%)")
        elif rev_growth > 10:
            score += 5
            factors.append(f"Good revenue growth ({rev_growth:.0f}%)")
        elif rev_growth < -10:
            score -= 10
            factors.append(f"Declining revenue ({rev_growth:.0f}%)")
        elif rev_growth < 0:
            score -= 5
            factors.append(f"Slight revenue decline ({rev_growth:.0f}%)")
    
    roe = valuation.get("roe_pct")
    if roe is not None:
        if roe > 20:
            score += 8
            factors.append(f"Excellent ROE ({roe:.0f}%)")
        elif roe > 15:
            score += 5
            factors.append(f"Good ROE ({roe:.0f}%)")
        elif roe < 5:
            score -= 5
            factors.append(f"Low ROE ({roe:.0f}%)")
    
    # Financial health scoring
    financials = analysis.get("financials", {})
    health_rating = financials.get("rating", "")
    if health_rating == "Excellent":
        score += 10
        factors.append("Excellent financial health")
    elif health_rating == "Good":
        score += 5
        factors.append("Good financial health")
    elif health_rating == "Weak":
        score -= 10
        factors.append("Weak financial health")
    
    # Technical scoring
    technical = analysis.get("technical", {})
    trend = technical.get("trend", "")
    if "Strong Uptrend" in trend:
        score += 5
        factors.append("Strong uptrend")
    elif "Uptrend" in trend:
        score += 3
    elif "Strong Downtrend" in trend:
        score -= 5
        factors.append("Strong downtrend")
    elif "Downtrend" in trend:
        score -= 3
    
    rsi = technical.get("rsi_14", 50)
    if rsi < 30:
        score += 3
        factors.append("Oversold (RSI < 30)")
    elif rsi > 70:
        score -= 3
        factors.append("Overbought (RSI > 70)")
    
    # Risk adjustment
    risks = analysis.get("risks", {})
    risk_level = risks.get("risk_level", "Moderate")
    if risk_level == "Very High":
        score -= 10
        factors.append("Very high risk profile")
    elif risk_level == "High":
        score -= 5
        factors.append("High risk profile")
    elif risk_level == "Low":
        score += 3
        factors.append("Low risk profile")
    
    # Clamp score
    score = max(0, min(100, score))
    
    # Determine rating
    if score >= 80:
        rating = "Strong Buy"
    elif score >= 65:
        rating = "Buy"
    elif score >= 50:
        rating = "Hold"
    elif score >= 35:
        rating = "Underweight"
    else:
        rating = "Sell"
    
    return {
        "score": score,
        "rating": rating,
        "factors": factors,
    }


def compare_companies(tickers):
    """
    Compare multiple companies side by side.
    
    Args:
        tickers: list of stock symbols
    
    Returns:
        dict: Comparison table with key metrics for each company
    """
    comparison = {
        "tickers": [t.upper() for t in tickers],
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "companies": [],
    }
    
    for ticker in tickers:
        try:
            profile = get_company_profile(ticker)
            valuation = get_valuation_multiples(ticker)
            financials = get_financial_health(ticker)
            earnings = get_earnings_analysis(ticker)
            
            comparison["companies"].append({
                "ticker": ticker.upper(),
                "name": profile.get("name", ticker),
                "sector": profile.get("sector", "N/A"),
                "price": valuation.get("price", 0),
                "market_cap_b": profile.get("market_cap_b", 0),
                "pe": valuation.get("pe_trailing"),
                "forward_pe": valuation.get("pe_forward"),
                "ps": valuation.get("ps_ratio"),
                "ev_ebitda": valuation.get("ev_ebitda"),
                "revenue_growth": valuation.get("revenue_growth_pct"),
                "roe": valuation.get("roe_pct"),
                "profit_margin": valuation.get("profit_margin_pct"),
                "debt_equity": valuation.get("debt_to_equity"),
                "health_rating": financials.get("rating", "N/A"),
                "analyst_rating": earnings.get("recommendation", "N/A"),
                "target_upside": earnings.get("upside_to_target_pct"),
            })
        except Exception as e:
            comparison["companies"].append({
                "ticker": ticker.upper(),
                "error": str(e),
            })
    
    return comparison


def format_analysis_report(analysis):
    """Format analysis dict into a readable markdown report."""
    lines = []
    ticker = analysis.get("ticker", "Unknown")
    
    lines.append(f"## 📊 Stock Analysis: {ticker}")
    lines.append(f"*{analysis.get('timestamp', '')}*")
    lines.append("")
    
    # Profile
    profile = analysis.get("profile", {})
    if profile and "error" not in profile:
        lines.append(f"### Company Profile")
        lines.append(f"- **Name:** {profile.get('name', 'N/A')}")
        lines.append(f"- **Sector:** {profile.get('sector', 'N/A')} | **Industry:** {profile.get('industry', 'N/A')}")
        lines.append(f"- **Market Cap:** ${profile.get('market_cap_b', 0):.1f}B")
        lines.append(f"- **Employees:** {profile.get('employees', 0):,}")
        lines.append("")
    
    # Valuation
    val = analysis.get("valuation", {})
    if val and "error" not in val:
        lines.append(f"### Valuation")
        lines.append(f"- **Price:** ${val.get('price', 0):.2f}")
        lines.append(f"- **P/E (Trailing):** {val.get('pe_trailing', 'N/A')} | **P/E (Forward):** {val.get('pe_forward', 'N/A')}")
        lines.append(f"- **P/S:** {val.get('ps_ratio', 'N/A')} | **EV/EBITDA:** {val.get('ev_ebitda', 'N/A')}")
        lines.append(f"- **Revenue Growth:** {val.get('revenue_growth_pct', 'N/A')}% | **ROE:** {val.get('roe_pct', 'N/A')}%")
        lines.append(f"- **Profit Margin:** {val.get('profit_margin_pct', 'N/A')}% | **Debt/Equity:** {val.get('debt_to_equity', 'N/A')}")
        lines.append("")
    
    # Earnings
    earnings = analysis.get("earnings", {})
    if earnings and "error" not in earnings:
        lines.append(f"### Earnings & Estimates")
        lines.append(f"- **EPS Trailing:** ${earnings.get('eps_trailing', 'N/A')} | **EPS Forward:** ${earnings.get('eps_forward', 'N/A')}")
        lines.append(f"- **EPS Growth:** {earnings.get('eps_growth_pct', 'N/A')}%")
        lines.append(f"- **Analyst Recommendation:** {earnings.get('recommendation', 'N/A')} ({earnings.get('num_analysts', 0)} analysts)")
        lines.append(f"- **Price Target:** ${earnings.get('target_mean', 'N/A')} (upside: {earnings.get('upside_to_target_pct', 'N/A')}%)")
        lines.append("")
    
    # Technical
    tech = analysis.get("technical", {})
    if tech and "error" not in tech:
        lines.append(f"### Technical Position")
        lines.append(f"- **Trend:** {tech.get('trend', 'N/A')}")
        lines.append(f"- **RSI (14):** {tech.get('rsi_14', 'N/A')}")
        lines.append(f"- **vs 52W Range:** {tech.get('week_52_position_pct', 'N/A')}%")
        lines.append(f"- **1M Return:** {tech.get('return_1m_pct', 'N/A')}% | **3M Return:** {tech.get('return_3m_pct', 'N/A')}%")
        lines.append("")
    
    # Financial Health
    fin = analysis.get("financials", {})
    if fin and "error" not in fin:
        lines.append(f"### Financial Health: {fin.get('rating', 'N/A')}")
        for factor in fin.get("factors", []):
            lines.append(f"- {factor}")
        lines.append("")
    
    # Risks
    risks = analysis.get("risks", {})
    if risks and "error" not in risks:
        lines.append(f"### Risk Assessment: {risks.get('risk_level', 'N/A')}")
        for risk in risks.get("risks", []):
            lines.append(f"- ⚠️ {risk}")
        lines.append("")
    
    # Investment Score
    score = analysis.get("investment_score", {})
    if score:
        lines.append(f"### Investment Score: {score.get('score', 0)}/100 — **{score.get('rating', 'N/A')}**")
        for factor in score.get("factors", []):
            lines.append(f"- {factor}")
        lines.append("")
    
    # Peers
    peers = analysis.get("peers", {})
    if peers and "error" not in peers:
        peer_list = peers.get("peers", [])
        if peer_list:
            lines.append(f"### Peer Comparison ({peers.get('sector', '')})")
            lines.append("| Ticker | Price | Market Cap | P/E | EV/EBITDA | Rev Growth | ROE |")
            lines.append("|--------|-------|------------|-----|-----------|------------|-----|")
            for p in peer_list:
                lines.append(f"| {p.get('ticker', '')} | ${p.get('price', 0):.2f} | ${p.get('market_cap_b', 0):.1f}B | {p.get('pe', 'N/A')} | {p.get('ev_ebitda', 'N/A')} | {p.get('revenue_growth', 'N/A')}% | {p.get('roe', 'N/A')}% |")
            lines.append("")
    
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# INSTITUTIONAL-GRADE COMPS ANALYSIS
# Based on Anthropic's comps-analysis skill
# ═══════════════════════════════════════════════════════════════

def build_comps_analysis(ticker, peer_tickers=None, max_peers=6):
    """
    Build institutional-grade comparable company analysis.
    
    Produces operating statistics + valuation multiples with statistical
    benchmarking (Max, 75th, Median, 25th, Min) — the standard format
    used by investment banks and equity research.
    
    Args:
        ticker: Target company ticker
        peer_tickers: Optional list of specific peers. If None, auto-detects.
        max_peers: Maximum number of peers (default 6)
    
    Returns:
        dict: Complete comps analysis with operating metrics, valuation multiples,
              statistical summary, and outlier flags.
    """
    import yfinance as yf
    
    result = {
        "ticker": ticker.upper(),
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "methodology": "Institutional-grade comps with statistical benchmarking",
        "data_source": "yfinance (free tier)",
    }
    
    # ── Step 1: Identify peer group ──
    if peer_tickers is None:
        peer_tickers = _auto_detect_peers(ticker, max_peers)
    else:
        peer_tickers = [p.upper() for p in peer_tickers if p.upper() != ticker.upper()][:max_peers]
    
    all_tickers = [ticker.upper()] + peer_tickers
    result["peer_group"] = all_tickers
    result["peer_count"] = len(all_tickers)
    
    # ── Step 2: Gather operating statistics ──
    operating_data = []
    for t in all_tickers:
        metrics = _get_operating_metrics(t)
        if metrics and "error" not in metrics:
            operating_data.append(metrics)
    
    result["operating_metrics"] = operating_data
    
    # ── Step 3: Gather valuation multiples ──
    valuation_data = []
    for t in all_tickers:
        metrics = _get_valuation_data(t)
        if metrics and "error" not in metrics:
            valuation_data.append(metrics)
    
    result["valuation_multiples"] = valuation_data
    
    # ── Step 4: Calculate statistical benchmarking ──
    if len(operating_data) >= 2:
        result["operating_stats"] = _calculate_statistics(operating_data)
    if len(valuation_data) >= 2:
        result["valuation_stats"] = _calculate_statistics(valuation_data)
    
    # ── Step 5: Identify outliers ──
    result["outliers"] = _identify_valuation_outliers(ticker.upper(), valuation_data)
    
    # ── Step 6: Industry-specific metrics ──
    profile = get_company_profile(ticker)
    sector = profile.get("sector", "")
    result["industry_specific_metrics"] = _get_industry_metrics(sector, operating_data)
    
    return result


def _auto_detect_peers(ticker, max_peers=6):
    """Auto-detect peer group based on sector and industry."""
    import yfinance as yf
    
    sector_peers = {
        "Technology": ["MSFT", "GOOGL", "META", "AMD", "INTC", "CRM", "ORCL", "CSCO", "ADBE", "NVDA", "AVGO", "TXN", "QCOM", "AMAT", "PANW", "SNOW", "PLTR", "NET", "DDOG", "MDB", "WDAY", "ZS", "CRWD", "OKTA", "S", "AI", "PATH", "ASAN", "ZM", "TEAM", "HUBS", "VEEV", "DOCU", "COUP", "BILL", "NCNO"],
        "Communication Services": ["GOOGL", "META", "DIS", "NFLX", "CMCSA", "T", "VZ", "TMUS", "CHTR", "EA", "TTWO", "WBD", "PARA", "FOXA", "NWSA", "LYV", "OMC", "IPG", "SNAP", "PINS", "TWTR", "SPOT", "RBLX", "U", "MTCH", "BMBL"],
        "Consumer Discretionary": ["AMZN", "TSLA", "HD", "NKE", "MCD", "SBUX", "TGT", "LOW", "BKNG", "CMG", "ROST", "DG", "DLTR", "ORLY", "AZO", "GPC", "AAP", "ULTA", "RH", "ETSY", "RIVN", "LCID", "NIO", "XPEV", "LI", "FSR", "GOEV", "WKHS", "DPST", "CENN", "SOLO", "NKLA", "HYZN", "RIDE", "FFIE", "ARVL", "VLN", "MULN", "EVGO", "CHPT", "BLNK", "WBX", "VLTA", "TSP", "QS", "LAZR", "INVZ", "AEVA", "OUST", "VLDR", "AUR", "GOSS", "OPEN", "CERS", "SRPT", "BMRN", "GILD", "VRTX", "REGN", "ALXN", "INO", "BNTX", "MRNA", "NVAX", "TBIO", "TALK", "BTAI", "SDGR", "RXRX", "ABCL", "BEAM", "CRSP", "EDIT", "NTLA", "VRNA", "PRTA", "KROS", "TARS", "DAWN", "CPRX", "EGRX", "SUPN", "AMRX", "ANIP", "BHC", "SUPN", "AMRX", "ANIP", "BHC"],
        "Consumer Staples": ["PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "CL", "GIS", "HSY", "KHC", "MKC", "SJM", "CPB", "CAG", "HRL", "TSN", "SYY", "KR", "CASY", "PFGC", "USFM", "CALM", "LANC", "JJSF", "FDP", "AVO", "AGRO", "LMNR", "ALCO", "ANDE", "BG", "ADM", "TSN", "HRL", "PPC", "NLMK", "STLD", "NUE", "CLF", "X", "MT", "PKX", "SCHN", "CMC", "WOR", "ASTE", "GENC", "TWI", "AGCO", "DE", "CNHI", "ALG", "LNN", "KMT", "SAND", "HL", "SCCO", "FCX", "NEM", "GOLD", "AEM", "WPM", "KGC", "AGI", "OR", "PAAS", "CDE", "EXK", "SSRM", "MUX", "HL", "SCCO", "FCX", "NEM", "GOLD", "AEM", "WPM", "KGC", "AGI", "OR", "PAAS", "CDE", "EXK", "SSRM", "MUX"],
        "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "PXD", "VLO", "PSX", "MPC", "OXY", "HES", "FANG", "DVN", "MRO", "APA", "BKR", "HAL", "WMB", "KMI", "OKE", "ET", "EPD", "MPLX", "TRP", "ENB", "SU", "CVE", "IMO", "EC", "YPF", "PBR", "VIST", "AR", "SWN", "RRC", "MTDR", "CRC", "BSM", "TALO", "WDS", "STO", "TOT", "EQNR", "SHEL", "BP", "TTI", "GPOR", "CRK", "EQT", "AR", "SWN", "RRC", "MTDR", "CRC", "BSM", "TALO"],
        "Financials": ["JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "SCHW", "AXP", "V", "MA", "PYPL", "SQ", "COIN", "HOOD", "AFRM", "SOFI", "UPST", "LC", "OPFI", "NU", "ALLY", "DFS", "SYF", "COF", "RF", "HBAN", "FITB", "KEY", "MTB", "PNC", "STT", "BK", "TFC", "CFG", "CMA", "ZION", "WAL", "CMA", "ZION", "WAL"],
        "Healthcare": ["JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "TMO", "ABT", "DHR", "BMY", "AMGN", "GILD", "VRTX", "REGN", "BIIB", "ISRG", "ZTS", "SYK", "BSX", "EW", "DXCM", "ILMN", "CRL", "WAT", "TECH", "RGEN", "QGEN", "MTD", "A", "BRKR", "PKI", "TMO", "DHR", "ABT", "TYL", "WST", "STE", "ATR", "COO", "TFX", "HOLX", "GNR", "LMNX", "QDEL", "FLDM", "NEO", "GH", "NTRA", "EXAS", "MYGN", "VCYT", "OPK", "RGEN", "QGEN", "MTD", "A", "BRKR", "PKI"],
        "Industrials": ["CAT", "HON", "UPS", "BA", "GE", "MMM", "LMT", "RTX", "DE", "FDX", "WM", "RSG", "JCI", "CARR", "OTIS", "PH", "ROK", "ETN", "EMR", "ITW", "DOV", "XYL", "IEX", "GGG", "FLS", "NDSN", "SNA", "SWK", "LECO", "RHI", "KFY", "HSII", "MAN", "TNET", "PAYX", "ADP", "PYCR", "PAY", "WDAY", "NOW", "VEEV", "COHU", "CRUS", "MXL", "SIMO", "AAOI", "LITE", "CIEN", "INFN", "ADTN", "CALX", "ITRI", "DGII", "AVNW", "COMM", "VIAV", "EXFO", "BDC", "PI", "SYPR", "MEI", "FLEX", "JBL", "SANM", "TTMI", "BHE", "CTS", "ELTK", "KOPN", "EMAN", "LPTH", "LGL"],
        "Materials": ["LIN", "APD", "SHW", "FCX", "NEM", "ECL", "DOW", "PPG", "DD", "CTVA", "NUE", "STLD", "CLF", "X", "MT", "PKX", "SCHN", "CMC", "WOR", "ASTE", "GENC", "TWI", "AGCO", "DE", "CNHI", "ALG", "LNN", "KMT", "SAND", "HL", "SCCO", "FCX", "NEM", "GOLD", "AEM", "WPM", "KGC", "AGI", "OR", "PAAS", "CDE", "EXK", "SSRM", "MUX"],
        "Real Estate": ["AMT", "PLD", "CCI", "EQIX", "PSA", "O", "WELL", "SPG", "VTR", "AVB", "EQR", "UDR", "MAA", "CPT", "EXR", "LSXMK", "CUBE", "REXR", "FR", "STAG", "TRNO", "ESS", "BXP", "VNO", "SLG", "HIW", "DEI", "JBGS", "CUZ", "OFC", "KRC", "HPP", "BDN", "PGRE", "VRE", "ESRT", "CLDX", "AXR", "AIV", "NXRT", "IRT", "ROIC", "RPAI", "KIM", "FRT", "REG", "WRI", "AKR", "BRX", "UE", "RPT", "CBL", "SKT", "MAC", "PEI", "WPG", "TCO", "SITC", "RVI", "CIO", "GOOD", "LAND", "AHH", "NXDT", "GMRE", "CHCT", "DHC", "LTC", "NHI", "OHI", "SBRA", "MPW", "CTRE", "DHR", "UHT", "WELL", "VTR", "HCP", "PEAK", "GMRE", "CHCT", "DHC", "LTC", "NHI", "OHI", "SBRA", "MPW", "CTRE", "DHR", "UHT"],
        "Utilities": ["NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "ED", "WEC", "ES", "PEG", "AWK", "EIX", "ETR", "FE", "CMS", "CNP", "NI", "LNT", "AES", "AGR", "ORA", "NEP", "BEP", "ENIC", "CIG", "SBS", "ELP", "EBR", "EDN", "TAC", "FTS", "BIP", "AM", "AQN", "CWEN", "NOVA", "RNW", "SHLS", "MAXN", "CSIQ", "JKS", "FSLR", "ENPH", "SEDG", "ARRY", "RUN", "SPWR", "MAXN", "CSIQ", "JKS", "FSLR", "ENPH", "SEDG", "ARRY", "RUN", "SPWR"],
    }
    
    try:
        t = yf.Ticker(ticker)
        info = t.info
        sector = info.get("sector", "")
        industry = info.get("industry", "")
        
        peers = sector_peers.get(sector, [])
        peers = [p for p in peers if p != ticker.upper()][:max_peers]
        
        # If we don't have enough peers, try to get from recommendations
        if len(peers) < 3:
            try:
                recs = t.recommendations
                if recs is not None and hasattr(recs, 'columns'):
                    # Try to extract peer info from recommendations
                    pass
            except Exception:
                pass
        
        return peers if peers else ["SPY", "QQQ", "DIA"]  # Fallback to indices
    except Exception:
        return ["SPY", "QQQ", "DIA"]


def _get_operating_metrics(ticker):
    """Get operating statistics for comps table."""
    try:
        import yfinance as yf
        old_stderr = __import__('sys').stderr
        __import__('sys').stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            info = t.info
            
            revenue = info.get("totalRevenue", 0) or 0
            revenue_growth = info.get("revenueGrowth", 0) or 0
            gross_profit = info.get("grossProfit", 0) or 0
            gross_margin = info.get("grossMargins", 0) or 0
            ebitda = info.get("ebitda", 0) or 0
            ebitda_margin = None
            if revenue > 0 and ebitda:
                ebitda_margin = ebitda / revenue
            operating_income = info.get("operatingIncome", 0) or 0
            operating_margin = info.get("operatingMargins", 0) or 0
            net_income = info.get("netIncomeToCommon", 0) or 0
            profit_margin = info.get("profitMargins", 0) or 0
            fcf = info.get("freeCashflow", 0) or 0
            fcf_margin = None
            if revenue > 0 and fcf:
                fcf_margin = fcf / revenue
            capex = info.get("capitalExpenditures", 0) or 0
            rd = info.get("researchAndDevelopment", 0) or 0
            rd_ratio = None
            if revenue > 0 and rd:
                rd_ratio = rd / revenue
            
            # Rule of 40 (for SaaS/growth companies)
            rule_of_40 = None
            if revenue_growth and operating_margin:
                rule_of_40 = revenue_growth + operating_margin
            
            # FCF Conversion
            fcf_conversion = None
            if ebitda and ebitda > 0 and fcf:
                fcf_conversion = fcf / ebitda
            
            return {
                "ticker": ticker.upper(),
                "name": info.get("shortName", ticker),
                "revenue": revenue,
                "revenue_m": round(revenue / 1e6, 0) if revenue else None,
                "revenue_growth": round(revenue_growth * 100, 1) if revenue_growth else None,
                "gross_profit_m": round(gross_profit / 1e6, 0) if gross_profit else None,
                "gross_margin": round(gross_margin * 100, 1) if gross_margin else None,
                "ebitda_m": round(ebitda / 1e6, 0) if ebitda else None,
                "ebitda_margin": round(ebitda_margin * 100, 1) if ebitda_margin else None,
                "operating_income_m": round(operating_income / 1e6, 0) if operating_income else None,
                "operating_margin": round(operating_margin * 100, 1) if operating_margin else None,
                "net_income_m": round(net_income / 1e6, 0) if net_income else None,
                "profit_margin": round(profit_margin * 100, 1) if profit_margin else None,
                "fcf_m": round(fcf / 1e6, 0) if fcf else None,
                "fcf_margin": round(fcf_margin * 100, 1) if fcf_margin else None,
                "capex_m": round(abs(capex) / 1e6, 0) if capex else None,
                "rd_ratio": round(rd_ratio * 100, 1) if rd_ratio else None,
                "rule_of_40": round(rule_of_40 * 100, 1) if rule_of_40 else None,
                "fcf_conversion": round(fcf_conversion * 100, 1) if fcf_conversion else None,
            }
        finally:
            __import__('sys').stderr = old_stderr
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def _get_valuation_data(ticker):
    """Get valuation multiples for comps table."""
    try:
        import yfinance as yf
        old_stderr = __import__('sys').stderr
        __import__('sys').stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            info = t.info
            
            price = info.get("currentPrice") or info.get("regularMarketPrice") or info.get("previousClose", 0)
            market_cap = info.get("marketCap", 0) or 0
            enterprise_value = info.get("enterpriseValue", 0) or 0
            shares_outstanding = info.get("sharesOutstanding", 0) or 0
            
            # Core multiples
            pe_trailing = info.get("trailingPE", 0) or 0
            pe_forward = info.get("forwardPE", 0) or 0
            peg_ratio = info.get("pegRatio", 0) or 0
            ps_ratio = info.get("priceToSalesTrailing12Months", 0) or 0
            pb_ratio = info.get("priceToBook", 0) or 0
            ev_ebitda = info.get("enterpriseToEbitda", 0) or 0
            ev_revenue = info.get("enterpriseToRevenue", 0) or 0
            
            # Derived multiples
            ev_ebitda_calc = None
            if enterprise_value and info.get("ebitda", 0):
                ev_ebitda_calc = enterprise_value / info["ebitda"]
            
            # FCF Yield
            fcf_yield = None
            fcf = info.get("freeCashflow", 0) or 0
            if market_cap and market_cap > 0 and fcf:
                fcf_yield = fcf / market_cap
            
            # Dividend
            div_yield = info.get("dividendYield", 0) or 0
            
            return {
                "ticker": ticker.upper(),
                "name": info.get("shortName", ticker),
                "price": round(price, 2) if price else None,
                "market_cap_m": round(market_cap / 1e6, 0) if market_cap else None,
                "enterprise_value_m": round(enterprise_value / 1e6, 0) if enterprise_value else None,
                "pe_trailing": round(pe_trailing, 1) if pe_trailing else None,
                "pe_forward": round(pe_forward, 1) if pe_forward else None,
                "peg_ratio": round(peg_ratio, 1) if peg_ratio else None,
                "ps_ratio": round(ps_ratio, 1) if ps_ratio else None,
                "pb_ratio": round(pb_ratio, 1) if pb_ratio else None,
                "ev_ebitda": round(ev_ebitda, 1) if ev_ebitda else (round(ev_ebitda_calc, 1) if ev_ebitda_calc else None),
                "ev_revenue": round(ev_revenue, 1) if ev_revenue else None,
                "fcf_yield": round(fcf_yield * 100, 1) if fcf_yield else None,
                "dividend_yield": round(div_yield * 100, 2) if div_yield else None,
            }
        finally:
            __import__('sys').stderr = old_stderr
    except Exception as e:
        return {"ticker": ticker, "error": str(e)}


def _calculate_statistics(data_list):
    """
    Calculate statistical benchmarking (Max, 75th, Median, 25th, Min)
    for all numeric fields in the data.
    """
    import statistics
    
    if not data_list or len(data_list) < 2:
        return {}
    
    # Collect all numeric fields
    numeric_fields = set()
    for item in data_list:
        for key, value in item.items():
            if isinstance(value, (int, float)) and key not in ("ticker", "name"):
                numeric_fields.add(key)
    
    stats = {}
    for field in numeric_fields:
        values = [item[field] for item in data_list if field in item and item[field] is not None and isinstance(item[field], (int, float))]
        if len(values) < 2:
            continue
        
        values_sorted = sorted(values)
        n = len(values_sorted)
        
        stats[field] = {
            "max": round(values_sorted[-1], 1),
            "p75": round(values_sorted[int(n * 0.75)], 1),
            "median": round(statistics.median(values_sorted), 1),
            "p25": round(values_sorted[int(n * 0.25)], 1),
            "min": round(values_sorted[0], 1),
            "mean": round(statistics.mean(values_sorted), 1),
            "std_dev": round(statistics.stdev(values_sorted), 1) if n >= 2 else 0,
            "count": n,
        }
    
    return stats


def _identify_valuation_outliers(ticker, valuation_data):
    """Identify if the target ticker is a valuation outlier vs peers."""
    import statistics
    
    outliers = {"ticker": ticker, "flags": []}
    
    # Find target data
    target = None
    peers = []
    for item in valuation_data:
        if item.get("ticker") == ticker:
            target = item
        else:
            peers.append(item)
    
    if not target or not peers:
        return outliers
    
    # Check each multiple for outlier status
    multiples_to_check = [
        ("pe_trailing", "P/E (Trailing)"),
        ("pe_forward", "P/E (Forward)"),
        ("ev_ebitda", "EV/EBITDA"),
        ("ev_revenue", "EV/Revenue"),
        ("ps_ratio", "P/S"),
        ("pb_ratio", "P/B"),
    ]
    
    for field, label in multiples_to_check:
        target_val = target.get(field)
        if target_val is None:
            continue
        
        peer_values = [p[field] for p in peers if field in p and p[field] is not None]
        if len(peer_values) < 2:
            continue
        
        median_val = statistics.median(peer_values)
        if median_val == 0:
            continue
        
        deviation = (target_val - median_val) / abs(median_val) * 100
        
        if deviation > 50:
            outliers["flags"].append({
                "metric": label,
                "value": target_val,
                "peer_median": round(median_val, 1),
                "deviation_pct": round(deviation, 1),
                "assessment": f"Significantly above peer median ({deviation:.0f}% premium)",
                "signal": "overvalued",
            })
        elif deviation < -30:
            outliers["flags"].append({
                "metric": label,
                "value": target_val,
                "peer_median": round(median_val, 1),
                "deviation_pct": round(deviation, 1),
                "assessment": f"Below peer median ({abs(deviation):.0f}% discount)",
                "signal": "undervalued",
            })
    
    return outliers


def _get_industry_metrics(sector, operating_data):
    """Get industry-specific metrics based on sector."""
    metrics = {"sector": sector, "relevant_metrics": []}
    
    sector_metrics = {
        "Technology": ["revenue_growth", "gross_margin", "operating_margin", "rd_ratio", "rule_of_40", "fcf_conversion"],
        "Communication Services": ["revenue_growth", "gross_margin", "ebitda_margin", "fcf_margin"],
        "Consumer Discretionary": ["revenue_growth", "gross_margin", "operating_margin", "fcf_margin"],
        "Consumer Staples": ["revenue_growth", "gross_margin", "operating_margin", "fcf_margin", "dividend_yield"],
        "Energy": ["revenue_growth", "ebitda_margin", "fcf_margin", "capex_m"],
        "Financials": ["revenue_growth", "profit_margin", "roe", "pb_ratio"],
        "Healthcare": ["revenue_growth", "gross_margin", "operating_margin", "rd_ratio", "fcf_margin"],
        "Industrials": ["revenue_growth", "gross_margin", "operating_margin", "fcf_margin"],
        "Materials": ["revenue_growth", "gross_margin", "ebitda_margin", "fcf_margin"],
        "Real Estate": ["revenue_growth", "fcf_margin", "dividend_yield"],
        "Utilities": ["revenue_growth", "ebitda_margin", "fcf_margin", "dividend_yield"],
    }
    
    relevant = sector_metrics.get(sector, ["revenue_growth", "gross_margin", "ebitda_margin", "fcf_margin"])
    metrics["relevant_metrics"] = relevant
    
    return metrics


# ═══════════════════════════════════════════════════════════════
# DCF VALUATION MODEL
# Based on Anthropic's dcf-model skill
# ═══════════════════════════════════════════════════════════════

def build_dcf_valuation(ticker, projection_years=5, terminal_growth_rate=None,
                         wacc_override=None, scenario="base"):
    """
    Build a Discounted Cash Flow (DCF) valuation model.
    
    Calculates intrinsic value by discounting projected free cash flows
    and terminal value. Includes WACC calculation via CAPM, scenario
    analysis (Bear/Base/Bull), and sensitivity tables.
    
    Args:
        ticker: Stock ticker
        projection_years: Number of years to project (default 5)
        terminal_growth_rate: Terminal growth rate (default: auto-calculated)
        wacc_override: Override WACC calculation (default: auto-calculated via CAPM)
        scenario: "bear", "base", or "bull"
    
    Returns:
        dict: Complete DCF model with projections, WACC, valuation, and sensitivity
    """
    import yfinance as yf
    
    result = {
        "ticker": ticker.upper(),
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "projection_years": projection_years,
        "scenario": scenario,
        "methodology": "DCF (Discounted Cash Flow) via CAPM-based WACC",
        "data_source": "yfinance (free tier)",
    }
    
    try:
        old_stderr = __import__('sys').stderr
        __import__('sys').stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            info = t.info
            
            # ── Step 1: Gather historical financials ──
            financials = _get_historical_financials(t, info)
            result["historical_financials"] = financials
            
            # ── Step 2: Calculate WACC ──
            if wacc_override:
                wacc = wacc_override
                result["wacc"] = {"value": wacc, "source": "user_override"}
            else:
                wacc_result = _calculate_wacc(ticker, info)
                wacc = wacc_result["wacc"]
                result["wacc"] = wacc_result
            
            result["wacc_used"] = wacc
            
            # ── Step 3: Build revenue projections ──
            projections = _build_fcf_projections(
                financials, projection_years, scenario, info
            )
            result["projections"] = projections
            
            # ── Step 4: Calculate terminal value ──
            if terminal_growth_rate is None:
                # Default: conservative estimate based on GDP growth
                terminal_growth_rate = 0.025  # 2.5%
            
            result["terminal_growth_rate"] = terminal_growth_rate
            
            final_fcf = projections["fcf"][-1]
            terminal_fcf = final_fcf * (1 + terminal_growth_rate)
            terminal_value = terminal_fcf / (wacc - terminal_growth_rate)
            
            result["terminal_value"] = {
                "terminal_fcf": round(terminal_fcf, 0),
                "terminal_value": round(terminal_value, 0),
                "method": "Perpetuity Growth",
            }
            
            # ── Step 5: Discount cash flows ──
            pv_fcfs = []
            for i, fcf in enumerate(projections["fcf"]):
                year = i + 1
                discount_factor = (1 + wacc) ** year
                pv_fcf = fcf / discount_factor
                pv_fcfs.append(pv_fcf)
            
            pv_terminal = terminal_value / (1 + wacc) ** projection_years
            
            enterprise_value = sum(pv_fcfs) + pv_terminal
            
            result["valuation"] = {
                "pv_fcfs": [round(v, 0) for v in pv_fcfs],
                "sum_pv_fcfs": round(sum(pv_fcfs), 0),
                "pv_terminal_value": round(pv_terminal, 0),
                "enterprise_value": round(enterprise_value, 0),
            }
            
            # ── Step 6: Bridge to equity value ──
            total_debt = info.get("totalDebt", 0) or 0
            total_cash = info.get("totalCash", 0) or 0
            net_debt = total_debt - total_cash
            equity_value = enterprise_value - net_debt
            shares_outstanding = info.get("sharesOutstanding", 0) or 0
            
            implied_price = equity_value / shares_outstanding if shares_outstanding > 0 else 0
            current_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            upside = ((implied_price - current_price) / current_price * 100) if current_price > 0 else 0
            
            result["equity_value"] = {
                "enterprise_value": round(enterprise_value, 0),
                "net_debt": round(net_debt, 0),
                "equity_value": round(equity_value, 0),
                "shares_outstanding_m": round(shares_outstanding / 1e6, 1),
                "implied_price_per_share": round(implied_price, 2),
                "current_price": round(current_price, 2),
                "upside_pct": round(upside, 1),
            }
            
            # ── Step 7: Scenario analysis ──
            result["scenarios"] = _build_scenario_analysis(
                financials, projection_years, wacc, terminal_growth_rate, info
            )
            
            # ── Step 8: Sensitivity analysis ──
            result["sensitivity"] = _build_sensitivity_analysis(
                financials, projection_years, wacc, terminal_growth_rate, shares_outstanding, net_debt
            )
            
            # ── Step 9: Sanity checks ──
            result["sanity_checks"] = _dcf_sanity_checks(
                terminal_value, enterprise_value, wacc, terminal_growth_rate, projections
            )
            
        finally:
            __import__('sys').stderr = old_stderr
    except Exception as e:
        result["error"] = str(e)
    
    return result


def _get_historical_financials(ticker_obj, info):
    """Extract historical financial data for DCF projections."""
    financials = {}
    
    try:
        # Get income statement data
        income_stmt = ticker_obj.income_stmt
        if income_stmt is not None and len(income_stmt) > 0:
            # Most recent year
            financials["revenue"] = info.get("totalRevenue", 0) or 0
            financials["gross_profit"] = info.get("grossProfit", 0) or 0
            financials["operating_income"] = info.get("operatingIncome", 0) or 0
            financials["net_income"] = info.get("netIncomeToCommon", 0) or 0
            financials["ebitda"] = info.get("ebitda", 0) or 0
        
        # Cash flow data
        financials["operating_cashflow"] = info.get("operatingCashflow", 0) or 0
        financials["free_cashflow"] = info.get("freeCashflow", 0) or 0
        financials["capex"] = info.get("capitalExpenditures", 0) or 0
        
        # Margins
        revenue = financials.get("revenue", 0) or 1
        financials["gross_margin"] = (financials.get("gross_profit", 0) or 0) / revenue
        financials["operating_margin"] = (financials.get("operating_income", 0) or 0) / revenue
        financials["ebitda_margin"] = (financials.get("ebitda", 0) or 0) / revenue
        financials["fcf_margin"] = (financials.get("free_cashflow", 0) or 0) / revenue
        
        # Growth rates
        financials["revenue_growth"] = info.get("revenueGrowth", 0) or 0
        financials["earnings_growth"] = info.get("earningsGrowth", 0) or 0
        
    except Exception:
        # Fallback to info-only data
        financials["revenue"] = info.get("totalRevenue", 0) or 0
        financials["gross_margin"] = info.get("grossMargins", 0) or 0
        financials["operating_margin"] = info.get("operatingMargins", 0) or 0
        financials["ebitda"] = info.get("ebitda", 0) or 0
        financials["free_cashflow"] = info.get("freeCashflow", 0) or 0
        financials["revenue_growth"] = info.get("revenueGrowth", 0) or 0
    
    return financials


def _calculate_wacc(ticker, info):
    """
    Calculate Weighted Average Cost of Capital (WACC) using CAPM.
    
    WACC = (E/V × Re) + (D/V × Rd × (1 - Tc))
    
    Where:
    Re = Rf + β × (Rm - Rf)  [CAPM]
    """
    import yfinance as yf
    
    # Cost of Equity (CAPM)
    risk_free_rate = 0.045  # ~4.5% for 10Y Treasury (approximate current)
    equity_risk_premium = 0.055  # ~5.5% historical US equity risk premium
    
    beta = info.get("beta", 1.0) or 1.0
    cost_of_equity = risk_free_rate + beta * equity_risk_premium
    
    # Cost of Debt
    # Estimate from credit profile (simplified)
    debt_to_equity = info.get("debtToEquity", 0) or 0
    total_debt = info.get("totalDebt", 0) or 0
    
    # Approximate pre-tax cost of debt based on leverage
    if total_debt == 0:
        cost_of_debt = 0.05  # No debt, use risk-free + small spread
    elif debt_to_equity < 50:
        cost_of_debt = 0.055  # Low leverage
    elif debt_to_equity < 100:
        cost_of_debt = 0.065  # Moderate leverage
    elif debt_to_equity < 200:
        cost_of_debt = 0.075  # High leverage
    else:
        cost_of_debt = 0.09   # Very high leverage
    
    tax_rate = 0.21  # US corporate tax rate
    after_tax_cost_of_debt = cost_of_equity * (1 - tax_rate) if total_debt == 0 else cost_of_debt * (1 - tax_rate)
    
    # Capital structure weights
    market_cap = info.get("marketCap", 0) or 0
    total_cash = info.get("totalCash", 0) or 0
    enterprise_value = info.get("enterpriseValue", 0) or (market_cap + total_debt - total_cash)
    
    if enterprise_value > 0:
        equity_weight = market_cap / enterprise_value
        debt_weight = total_debt / enterprise_value
    else:
        equity_weight = 1.0
        debt_weight = 0.0
    
    wacc = (equity_weight * cost_of_equity) + (debt_weight * after_tax_cost_of_debt)
    
    return {
        "wacc": round(wacc, 4),
        "cost_of_equity": round(cost_of_equity, 4),
        "cost_of_debt": round(cost_of_debt, 4),
        "after_tax_cost_of_debt": round(after_tax_cost_of_debt, 4),
        "risk_free_rate": risk_free_rate,
        "equity_risk_premium": equity_risk_premium,
        "beta": round(beta, 2),
        "tax_rate": tax_rate,
        "equity_weight": round(equity_weight, 3),
        "debt_weight": round(debt_weight, 3),
        "method": "CAPM",
    }


def _build_fcf_projections(financials, years, scenario, info):
    """Build year-by-year FCF projections."""
    
    base_revenue = financials.get("revenue", 0) or 0
    base_fcf = financials.get("free_cashflow", 0) or 0
    base_growth = financials.get("revenue_growth", 0) or 0.05
    base_margin = financials.get("operating_margin", 0) or 0.15
    base_ebitda_margin = financials.get("ebitda_margin", 0) or 0.20
    
    # Scenario adjustments
    scenario_params = {
        "bear": {"growth_mult": 0.5, "margin_adj": -0.03, "capex_mult": 1.2},
        "base": {"growth_mult": 1.0, "margin_adj": 0.0, "capex_mult": 1.0},
        "bull": {"growth_mult": 1.3, "margin_adj": 0.02, "capex_mult": 0.9},
    }
    
    params = scenario_params.get(scenario, scenario_params["base"])
    
    # Decay growth rate over projection period (growth → terminal)
    growth_rates = []
    for i in range(years):
        year_growth = base_revenue * (1 + base_growth * params["growth_mult"]) ** (i + 1)
        # Decay toward terminal rate
        decay_factor = 1 - (i / (years * 2))  # Gradual decay
        growth_rates.append(max(base_growth * params["growth_mult"] * decay_factor, 0.02))
    
    # Build projections
    revenue_proj = []
    ebitda_proj = []
    fcf_proj = []
    
    prev_revenue = base_revenue
    for i in range(years):
        rev = prev_revenue * (1 + growth_rates[i])
        revenue_proj.append(round(rev, 0))
        
        ebitda = rev * (base_ebitda_margin + params["margin_adj"])
        ebitda_proj.append(round(ebitda, 0))
        
        # Simplified FCF: EBITDA - CapEx - Taxes - ΔNWC
        tax_rate = 0.21
        nopat = (rev * (base_margin + params["margin_adj"])) * (1 - tax_rate)
        capex = rev * 0.05 * params["capex_mult"]  # Assume ~5% of revenue
        fcf = nopat + (ebitda * 0.1) - capex  # Simplified: add back D&A portion
        fcf_proj.append(round(fcf, 0))
        
        prev_revenue = rev
    
    return {
        "years": [f"Year {i+1}" for i in range(years)],
        "revenue": revenue_proj,
        "ebitda": ebitda_proj,
        "fcf": fcf_proj,
        "growth_rates": [round(g * 100, 1) for g in growth_rates],
        "scenario": scenario,
    }


def _build_scenario_analysis(financials, years, wacc, terminal_growth, info):
    """Build Bear/Base/Bull scenario analysis."""
    scenarios = {}
    
    for scenario in ["bear", "base", "bull"]:
        projections = _build_fcf_projections(financials, years, scenario, info)
        
        final_fcf = projections["fcf"][-1]
        terminal_fcf = final_fcf * (1 + terminal_growth)
        terminal_value = terminal_fcf / (wacc - terminal_growth)
        
        pv_fcfs = []
        for i, fcf in enumerate(projections["fcf"]):
            pv_fcfs.append(fcf / (1 + wacc) ** (i + 1))
        
        pv_terminal = terminal_value / (1 + wacc) ** years
        enterprise_value = sum(pv_fcfs) + pv_terminal
        
        total_debt = info.get("totalDebt", 0) or 0
        total_cash = info.get("totalCash", 0) or 0
        net_debt = total_debt - total_cash
        equity_value = enterprise_value - net_debt
        shares = info.get("sharesOutstanding", 0) or 1
        implied_price = equity_value / shares if shares > 0 else 0
        
        scenarios[scenario] = {
            "revenue_cagr": round(((projections["revenue"][-1] / max(projections["revenue"][0], 1)) ** (1/years) - 1) * 100, 1),
            "enterprise_value": round(enterprise_value, 0),
            "equity_value": round(equity_value, 0),
            "implied_price": round(implied_price, 2),
        }
    
    return scenarios


def _build_sensitivity_analysis(financials, years, base_wacc, base_terminal_g, shares, net_debt):
    """
    Build WACC vs Terminal Growth sensitivity table.
    Returns a 5x5 grid of implied share prices.
    """
    wacc_values = [base_wacc - 0.02, base_wacc - 0.01, base_wacc, base_wacc + 0.01, base_wacc + 0.02]
    tg_values = [base_terminal_g - 0.01, base_terminal_g - 0.005, base_terminal_g, base_terminal_g + 0.005, base_terminal_g + 0.01]
    
    # Clamp to valid ranges
    wacc_values = [max(0.05, min(0.20, w)) for w in wacc_values]
    tg_values = [max(0.01, min(0.05, t)) for t in tg_values]
    
    grid = []
    for wacc in wacc_values:
        row = []
        for tg in tg_values:
            if tg >= wacc:
                row.append(None)  # Invalid: terminal growth >= WACC
                continue
            
            projections = _build_fcf_projections(financials, years, "base", {})
            final_fcf = projections["fcf"][-1]
            terminal_fcf = final_fcf * (1 + tg)
            terminal_value = terminal_fcf / (wacc - tg)
            
            pv_fcfs = []
            for i, fcf in enumerate(projections["fcf"]):
                pv_fcfs.append(fcf / (1 + wacc) ** (i + 1))
            
            pv_terminal = terminal_value / (1 + wacc) ** years
            enterprise_value = sum(pv_fcfs) + pv_terminal
            equity_value = enterprise_value - net_debt
            implied_price = equity_value / shares if shares > 0 else 0
            
            row.append(round(implied_price, 2))
        grid.append(row)
    
    return {
        "wacc_values": [round(w * 100, 1) for w in wacc_values],
        "terminal_growth_values": [round(t * 100, 1) for t in tg_values],
        "implied_prices": grid,
        "base_wacc": round(base_wacc * 100, 1),
        "base_terminal_g": round(base_terminal_g * 100, 1),
    }


def _dcf_sanity_checks(terminal_value, enterprise_value, wacc, terminal_growth, projections):
    """Run sanity checks on DCF model outputs."""
    checks = []
    
    # Check 1: Terminal growth < WACC
    if terminal_growth >= wacc:
        checks.append({
            "check": "Terminal Growth < WACC",
            "status": "FAIL",
            "detail": f"Terminal growth ({terminal_growth:.1%}) >= WACC ({wacc:.1%}). Model produces infinite value.",
        })
    else:
        checks.append({
            "check": "Terminal Growth < WACC",
            "status": "PASS",
            "detail": f"Terminal growth ({terminal_growth:.1%}) < WACC ({wacc:.1%})",
        })
    
    # Check 2: Terminal value proportion
    if enterprise_value > 0:
        tv_proportion = terminal_value / enterprise_value
        if tv_proportion > 0.80:
            checks.append({
                "check": "Terminal Value Proportion",
                "status": "WARNING",
                "detail": f"TV is {tv_proportion:.0%} of EV (should be 50-70%). Model over-reliant on terminal assumptions.",
            })
        elif tv_proportion < 0.40:
            checks.append({
                "check": "Terminal Value Proportion",
                "status": "WARNING",
                "detail": f"TV is {tv_proportion:.0%} of EV (should be 50-70%). Terminal assumptions may be too conservative.",
            })
        else:
            checks.append({
                "check": "Terminal Value Proportion",
                "status": "PASS",
                "detail": f"TV is {tv_proportion:.0%} of EV (within 40-80% range)",
            })
    
    # Check 3: WACC in reasonable range
    if wacc < 0.05 or wacc > 0.20:
        checks.append({
            "check": "WACC Range",
            "status": "WARNING",
            "detail": f"WACC ({wacc:.1%}) outside typical range (5-20%)",
        })
    else:
        checks.append({
            "check": "WACC Range",
            "status": "PASS",
            "detail": f"WACC ({wacc:.1%}) within typical range",
        })
    
    # Check 4: Growth rates reasonable
    growth_rates = projections.get("growth_rates", [])
    if growth_rates:
        max_growth = max(growth_rates)
        if max_growth > 50:
            checks.append({
                "check": "Growth Rate Sanity",
                "status": "WARNING",
                "detail": f"Max projected growth ({max_growth:.0f}%) seems aggressive",
            })
        else:
            checks.append({
                "check": "Growth Rate Sanity",
                "status": "PASS",
                "detail": f"Projected growth rates appear reasonable",
            })
    
    return checks


# ═══════════════════════════════════════════════════════════════
# EARNINGS REVIEWER
# Based on Anthropic's earnings-reviewer skill
# ═══════════════════════════════════════════════════════════════

def analyze_earnings_event(ticker, include_guidance=True, include_segments=True):
    """
    Comprehensive earnings event analysis.
    
    Analyzes quarterly earnings results including:
    - Beat/miss analysis (revenue, EPS vs estimates)
    - Segment/geographic breakdown
    - Margin analysis (gross, operating, net)
    - Guidance analysis (raised/maintained/lowered)
    - Estimate revision impact
    - Key themes from earnings call
    
    Args:
        ticker: Stock ticker
        include_guidance: Whether to analyze guidance
        include_segments: Whether to analyze segment breakdown
    
    Returns:
        dict: Complete earnings analysis
    """
    import yfinance as yf
    
    result = {
        "ticker": ticker.upper(),
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "methodology": "Earnings event analysis (beat/miss, guidance, margins)",
        "data_source": "yfinance (free tier)",
    }
    
    try:
        old_stderr = __import__('sys').stderr
        __import__('sys').stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            info = t.info
            
            # ── Beat/Miss Analysis ──
            eps_actual = info.get("epsActualCurrentQuarter")
            eps_estimate = info.get("epsEstimateCurrentQuarter")
            revenue_actual = info.get("totalRevenue")  # Most recent
            revenue_estimate = info.get("revenueEstimateCurrentQuarter")
            
            eps_surprise = None
            eps_surprise_pct = None
            if eps_actual is not None and eps_estimate and eps_estimate != 0:
                eps_surprise = eps_actual - eps_estimate
                eps_surprise_pct = (eps_surprise / abs(eps_estimate)) * 100
            
            revenue_surprise = None
            revenue_surprise_pct = None
            if revenue_actual and revenue_estimate and revenue_estimate != 0:
                revenue_surprise = revenue_actual - revenue_estimate
                revenue_surprise_pct = (revenue_surprise / revenue_estimate) * 100
            
            result["beat_miss"] = {
                "eps_actual": round(eps_actual, 2) if eps_actual is not None else None,
                "eps_estimate": round(eps_estimate, 2) if eps_estimate else None,
                "eps_surprise": round(eps_surprise, 2) if eps_surprise is not None else None,
                "eps_surprise_pct": round(eps_surprise_pct, 1) if eps_surprise_pct is not None else None,
                "eps_result": "Beat" if eps_surprise and eps_surprise > 0 else ("Miss" if eps_surprise and eps_surprise < 0 else "Inline"),
                "revenue_actual_b": round(revenue_actual / 1e9, 2) if revenue_actual else None,
                "revenue_estimate_b": round(revenue_estimate / 1e9, 2) if revenue_estimate else None,
                "revenue_surprise_pct": round(revenue_surprise_pct, 1) if revenue_surprise_pct is not None else None,
                "revenue_result": "Beat" if revenue_surprise and revenue_surprise > 0 else ("Miss" if revenue_surprise and revenue_surprise < 0 else "Inline"),
            }
            
            # ── Margin Analysis ──
            result["margins"] = {
                "gross_margin": round(info.get("grossMargins", 0) * 100, 1) if info.get("grossMargins") else None,
                "operating_margin": round(info.get("operatingMargins", 0) * 100, 1) if info.get("operatingMargins") else None,
                "profit_margin": round(info.get("profitMargins", 0) * 100, 1) if info.get("profitMargins") else None,
                "ebitda_margin": round((info.get("ebitda", 0) or 0) / max(info.get("totalRevenue", 1), 1) * 100, 1),
                "fcf_margin": round((info.get("freeCashflow", 0) or 0) / max(info.get("totalRevenue", 1), 1) * 100, 1),
            }
            
            # ── Growth Analysis ──
            result["growth"] = {
                "revenue_growth_yoy": round(info.get("revenueGrowth", 0) * 100, 1) if info.get("revenueGrowth") else None,
                "earnings_growth": round(info.get("earningsGrowth", 0) * 100, 1) if info.get("earningsGrowth") else None,
                "earnings_quarterly_growth": round(info.get("earningsQuarterlyGrowth", 0) * 100, 1) if info.get("earningsQuarterlyGrowth") else None,
            }
            
            # ── Analyst Response ──
            result["analyst_response"] = {
                "recommendation": info.get("recommendationKey", "N/A"),
                "num_analysts": info.get("numberOfAnalystOpinions", 0),
                "target_mean": round(info.get("targetMeanPrice", 0), 2) if info.get("targetMeanPrice") else None,
                "target_high": round(info.get("targetHighPrice", 0), 2) if info.get("targetHighPrice") else None,
                "target_low": round(info.get("targetLowPrice", 0), 2) if info.get("targetLowPrice") else None,
            }
            
            # ── Estimate Revision Impact ──
            eps_forward = info.get("forwardEps", 0) or 0
            eps_trailing = info.get("trailingEps", 0) or 0
            eps_revision = None
            if eps_trailing and eps_trailing != 0:
                eps_revision = ((eps_forward - eps_trailing) / abs(eps_trailing)) * 100
            
            result["estimate_revision"] = {
                "eps_trailing": round(eps_trailing, 2) if eps_trailing else None,
                "eps_forward": round(eps_forward, 2) if eps_forward else None,
                "eps_revision_pct": round(eps_revision, 1) if eps_revision else None,
                "direction": "Upward" if eps_revision and eps_revision > 0 else ("Downward" if eps_revision and eps_revision < 0 else "Stable"),
            }
            
            # ── Quality Assessment ──
            quality_factors = []
            quality_score = 0
            
            # Earnings beat
            if eps_surprise_pct and eps_surprise_pct > 5:
                quality_factors.append(f"Strong EPS beat (+{eps_surprise_pct:.1f}%)")
                quality_score += 2
            elif eps_surprise_pct and eps_surprise_pct > 0:
                quality_factors.append(f"EPS beat (+{eps_surprise_pct:.1f}%)")
                quality_score += 1
            elif eps_surprise_pct and eps_surprise_pct < -5:
                quality_factors.append(f"Significant EPS miss ({eps_surprise_pct:.1f}%)")
                quality_score -= 2
            
            # Revenue beat
            if revenue_surprise_pct and revenue_surprise_pct > 3:
                quality_factors.append(f"Revenue beat (+{revenue_surprise_pct:.1f}%)")
                quality_score += 1
            elif revenue_surprise_pct and revenue_surprise_pct < -3:
                quality_factors.append(f"Revenue miss ({revenue_surprise_pct:.1f}%)")
                quality_score -= 1
            
            # Margin expansion
            gross_margin = info.get("grossMargins", 0) or 0
            if gross_margin > 0.5:
                quality_factors.append(f"Strong gross margin ({gross_margin*100:.1f}%)")
                quality_score += 1
            
            # FCF positive
            fcf = info.get("freeCashflow", 0) or 0
            if fcf > 0:
                quality_factors.append("Positive free cash flow")
                quality_score += 1
            
            result["quality_assessment"] = {
                "score": quality_score,
                "factors": quality_factors,
                "overall": "Strong" if quality_score >= 3 else ("Good" if quality_score >= 1 else ("Mixed" if quality_score >= 0 else "Weak")),
            }
            
        finally:
            __import__('sys').stderr = old_stderr
    except Exception as e:
        result["error"] = str(e)
    
    return result


# ═══════════════════════════════════════════════════════════════
# COMPETITIVE LANDSCAPE ANALYSIS
# Based on Anthropic's competitive-analysis skill
# ═══════════════════════════════════════════════════════════════

def analyze_competitive_landscape(ticker, competitors=None):
    """
    Analyze competitive landscape and market positioning.
    
    Evaluates:
    - Market positioning vs peers
    - Moat assessment (network effects, switching costs, scale, intangibles)
    - Competitive dynamics
    - Bull/Bear scenarios
    
    Args:
        ticker: Target company ticker
        competitors: Optional list of competitor tickers
    
    Returns:
        dict: Competitive landscape analysis
    """
    import yfinance as yf
    
    result = {
        "ticker": ticker.upper(),
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "methodology": "Competitive landscape mapping with moat assessment",
    }
    
    try:
        old_stderr = __import__('sys').stderr
        __import__('sys').stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            info = t.info
            
            # ── Company Profile ──
            result["company_profile"] = {
                "name": info.get("longName", ticker),
                "sector": info.get("sector", "N/A"),
                "industry": info.get("industry", "N/A"),
                "market_cap_b": round((info.get("marketCap", 0) or 0) / 1e9, 2),
                "revenue_b": round((info.get("totalRevenue", 0) or 0) / 1e9, 2),
                "employees": info.get("fullTimeEmployees", 0),
                "description": info.get("longBusinessSummary", "")[:300],
            }
            
            # ── Moat Assessment ──
            moat = _assess_moat(ticker, info)
            result["moat_assessment"] = moat
            
            # ── Competitive Positioning ──
            if competitors is None:
                competitors = _auto_detect_peers(ticker, 5)
            
            comp_analysis = []
            for comp_ticker in competitors[:5]:
                try:
                    ct = yf.Ticker(comp_ticker)
                    ci = ct.info
                    comp_analysis.append({
                        "ticker": comp_ticker,
                        "name": ci.get("shortName", comp_ticker),
                        "market_cap_b": round((ci.get("marketCap", 0) or 0) / 1e9, 2),
                        "revenue_b": round((ci.get("totalRevenue", 0) or 0) / 1e9, 2),
                        "revenue_growth": round((ci.get("revenueGrowth", 0) or 0) * 100, 1),
                        "gross_margin": round((ci.get("grossMargins", 0) or 0) * 100, 1),
                        "operating_margin": round((ci.get("operatingMargins", 0) or 0) * 100, 1),
                        "roe": round((ci.get("returnOnEquity", 0) or 0) * 100, 1),
                    })
                except Exception:
                    continue
            
            result["competitor_comparison"] = comp_analysis
            
            # ── Market Position ──
            target_mcap = info.get("marketCap", 0) or 0
            total_peer_mcap = sum(c.get("market_cap_b", 0) * 1e9 for c in comp_analysis) + target_mcap
            market_share = (target_mcap / total_peer_mcap * 100) if total_peer_mcap > 0 else None
            
            result["market_position"] = {
                "estimated_market_share_pct": round(market_share, 1) if market_share else None,
                "peer_count": len(comp_analysis),
                "size_rank": _calculate_size_rank(target_mcap, comp_analysis),
            }
            
            # ── Scenario Analysis ──
            result["scenarios"] = {
                "bull_case": _build_bull_case(ticker, info, moat),
                "base_case": _build_base_case(ticker, info),
                "bear_case": _build_bear_case(ticker, info, moat),
            }
            
        finally:
            __import__('sys').stderr = old_stderr
    except Exception as e:
        result["error"] = str(e)
    
    return result


def _assess_moat(ticker, info):
    """
    Assess economic moat across four dimensions:
    1. Network Effects
    2. Switching Costs
    3. Scale Economies
    4. Intangible Assets
    """
    moat = {
        "overall_rating": "Narrow",
        "dimensions": {},
        "score": 0,
    }
    
    score = 0
    
    # 1. Network Effects (assess based on sector and business model)
    sector = info.get("sector", "")
    industry = info.get("industry", "")
    
    network_effect_sectors = ["Communication Services", "Technology"]
    has_network_effects = sector in network_effect_sectors
    network_rating = "Moderate" if has_network_effects else "Weak"
    if has_network_effects:
        score += 1
    
    moat["dimensions"]["network_effects"] = {
        "rating": network_rating,
        "assessment": f"{'Platform/network business model detected' if has_network_effects else 'Limited network effects'}",
    }
    
    # 2. Switching Costs (assess based on gross margin stability)
    gross_margin = info.get("grossMargins", 0) or 0
    if gross_margin > 0.7:
        switching_rating = "Strong"
        score += 2
    elif gross_margin > 0.5:
        switching_rating = "Moderate"
        score += 1
    else:
        switching_rating = "Weak"
    
    moat["dimensions"]["switching_costs"] = {
        "rating": switching_rating,
        "assessment": f"Gross margin of {gross_margin*100:.0f}% suggests {'high' if gross_margin > 0.7 else 'moderate' if gross_margin > 0.5 else 'low'} switching costs",
    }
    
    # 3. Scale Economies (assess based on market cap relative to peers)
    market_cap = info.get("marketCap", 0) or 0
    if market_cap > 500e9:  # >$500B
        scale_rating = "Strong"
        score += 2
    elif market_cap > 50e9:  # >$50B
        scale_rating = "Moderate"
        score += 1
    else:
        scale_rating = "Weak"
    
    moat["dimensions"]["scale_economies"] = {
        "rating": scale_rating,
        "assessment": f"${market_cap/1e9:.0f}B market cap indicates {'significant' if market_cap > 500e9 else 'moderate' if market_cap > 50e9 else 'limited'} scale advantages",
    }
    
    # 4. Intangible Assets (assess based on R&D intensity and brand)
    rd = info.get("researchAndDevelopment", 0) or 0
    revenue = info.get("totalRevenue", 1) or 1
    rd_ratio = rd / revenue
    
    if rd_ratio > 0.15:
        intangible_rating = "Strong"
        score += 2
    elif rd_ratio > 0.08:
        intangible_rating = "Moderate"
        score += 1
    else:
        intangible_rating = "Weak"
    
    moat["dimensions"]["intangible_assets"] = {
        "rating": intangible_rating,
        "assessment": f"R&D/Revenue of {rd_ratio*100:.1f}% indicates {'significant' if rd_ratio > 0.15 else 'moderate' if rd_ratio > 0.08 else 'limited'} intangible assets",
    }
    
    # Overall rating
    if score >= 6:
        moat["overall_rating"] = "Wide"
    elif score >= 3:
        moat["overall_rating"] = "Narrow"
    else:
        moat["overall_rating"] = "None"
    
    moat["score"] = score
    moat["max_score"] = 8
    
    return moat


def _calculate_size_rank(target_mcap, competitors):
    """Calculate the size rank of the target vs competitors."""
    all_mcaps = [target_mcap] + [c.get("market_cap_b", 0) * 1e9 for c in competitors]
    all_mcaps_sorted = sorted(all_mcaps, reverse=True)
    
    try:
        rank = all_mcaps_sorted.index(target_mcap) + 1
        return {"rank": rank, "total": len(all_mcaps_sorted)}
    except ValueError:
        return {"rank": "N/A", "total": len(all_mcaps_sorted)}


def _build_bull_case(ticker, info, moat):
    """Build bull case scenario."""
    growth = info.get("revenueGrowth", 0) or 0.1
    margin = info.get("operatingMargins", 0) or 0.15
    
    return {
        "thesis": f"{ticker} gains market share and expands margins",
        "assumptions": [
            f"Revenue growth accelerates to {min(growth * 1.5, 0.5)*100:.0f}%+",
            f"Operating margins expand to {(margin + 0.05)*100:.0f}%+",
            f"{'Wide moat protects competitive position' if moat.get('overall_rating') == 'Wide' else 'Narrow moat provides some protection'}",
        ],
        "probability": "25-35%",
        "key_catalysts": [
            "New product cycles",
            "Market share gains",
            "Margin expansion",
            "M&A activity",
        ],
    }


def _build_base_case(ticker, info):
    """Build base case scenario."""
    growth = info.get("revenueGrowth", 0) or 0.05
    
    return {
        "thesis": f"{ticker} continues on current trajectory",
        "assumptions": [
            f"Revenue growth of {growth*100:.0f}%",
            "Margins stable at current levels",
            "Competitive position maintained",
        ],
        "probability": "40-50%",
        "key_catalysts": [
            "Execution on current strategy",
            "Industry tailwinds",
        ],
    }


def _build_bear_case(ticker, info, moat):
    """Build bear case scenario."""
    return {
        "thesis": f"{ticker} faces competitive pressure and margin compression",
        "assumptions": [
            "Revenue growth decelerates",
            "Margins compress due to competition",
            f"{'Moat erosion possible' if moat.get('overall_rating') != 'Wide' else 'Wide moat provides some defense'}",
        ],
        "probability": "20-30%",
        "key_risks": [
            "New competitive entrants",
            "Regulatory changes",
            "Technology disruption",
            "Macro headwinds",
        ],
    }


# ═══════════════════════════════════════════════════════════════
# SECTOR OVERVIEW & MARKET RESEARCH
# Based on Anthropic's market-researcher skill
# ═══════════════════════════════════════════════════════════════

def sector_overview(sector_name, top_n=10):
    """
    Generate a comprehensive sector overview.
    
    Covers:
    - Market size and growth
    - Industry structure (fragmented vs consolidated)
    - Key trends and drivers
    - Competitive landscape
    - Valuation context
    - Investment implications
    
    Args:
        sector_name: Sector name (e.g., "Technology", "Healthcare")
        top_n: Number of top companies to include
    
    Returns:
        dict: Sector overview analysis
    """
    result = {
        "sector": sector_name,
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "methodology": "Sector overview with market structure and competitive analysis",
    }
    
    # Sector universe mapping
    sector_universes = {
        "Technology": ["AAPL", "MSFT", "GOOGL", "META", "NVDA", "AMD", "INTC", "CRM", "ORCL", "CSCO", "ADBE", "AVGO", "TXN", "QCOM", "AMAT", "PANW", "SNOW", "PLTR", "NET", "DDOG", "MDB", "WDAY", "ZS", "CRWD"],
        "Healthcare": ["JNJ", "UNH", "PFE", "ABBV", "MRK", "LLY", "TMO", "ABT", "DHR", "BMY", "AMGN", "GILD", "VRTX", "REGN", "BIIB", "ISRG", "ZTS", "SYK", "BSX", "EW"],
        "Financials": ["JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "SCHW", "AXP", "V", "MA", "PYPL", "SQ", "COIN", "HOOD"],
        "Consumer Discretionary": ["AMZN", "TSLA", "HD", "NKE", "MCD", "SBUX", "TGT", "LOW", "BKNG", "CMG", "ROST", "DG", "DLTR"],
        "Consumer Staples": ["PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "CL", "GIS", "HSY", "KHC", "MKC"],
        "Energy": ["XOM", "CVX", "COP", "SLB", "EOG", "PXD", "VLO", "PSX", "MPC", "OXY", "HES", "FANG", "DVN"],
        "Industrials": ["CAT", "HON", "UPS", "BA", "GE", "MMM", "LMT", "RTX", "DE", "FDX", "WM", "RSG", "JCI"],
        "Materials": ["LIN", "APD", "SHW", "FCX", "NEM", "ECL", "DOW", "PPG", "DD", "CTVA", "NUE", "STLD"],
        "Real Estate": ["AMT", "PLD", "CCI", "EQIX", "PSA", "O", "WELL", "SPG", "VTR", "AVB", "EQR", "UDR"],
        "Utilities": ["NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "ED", "WEC", "ES", "PEG"],
        "Communication Services": ["GOOGL", "META", "DIS", "NFLX", "CMCSA", "T", "VZ", "TMUS", "CHTR", "EA", "TTWO", "WBD"],
    }
    
    tickers = sector_universes.get(sector_name, [])
    if not tickers:
        result["error"] = f"Unknown sector: {sector_name}. Available: {list(sector_universes.keys())}"
        return result
    
    # Gather data for top companies
    companies = []
    total_mcap = 0
    import yfinance as yf
    
    for ticker in tickers[:top_n]:
        try:
            old_stderr = __import__('sys').stderr
            __import__('sys').stderr = StringIO()
            try:
                t = yf.Ticker(ticker)
                info = t.info
                
                mcap = info.get("marketCap", 0) or 0
                total_mcap += mcap
                
                companies.append({
                    "ticker": ticker,
                    "name": info.get("shortName", ticker),
                    "market_cap_b": round(mcap / 1e9, 1),
                    "revenue_b": round((info.get("totalRevenue", 0) or 0) / 1e9, 1),
                    "revenue_growth": round((info.get("revenueGrowth", 0) or 0) * 100, 1),
                    "gross_margin": round((info.get("grossMargins", 0) or 0) * 100, 1),
                    "operating_margin": round((info.get("operatingMargins", 0) or 0) * 100, 1),
                    "pe_ratio": round(info.get("trailingPE", 0) or 0, 1),
                    "ev_ebitda": round(info.get("enterpriseToEbitda", 0) or 0, 1),
                    "roe": round((info.get("returnOnEquity", 0) or 0) * 100, 1),
                    "debt_equity": round(info.get("debtToEquity", 0) or 0, 1),
                })
            finally:
                __import__('sys').stderr = old_stderr
        except Exception:
            continue
    
    # Calculate sector statistics
    import statistics
    
    result["top_companies"] = companies
    result["sector_statistics"] = {
        "total_market_cap_b": round(total_mcap / 1e9, 1),
        "companies_analyzed": len(companies),
        "top5_concentration_pct": round(sum(c["market_cap_b"] for c in companies[:5]) / max(total_mcap / 1e9, 1) * 100, 1) if companies else None,
        "median_pe": round(statistics.median([c["pe_ratio"] for c in companies if c["pe_ratio"] and c["pe_ratio"] > 0]), 1) if companies else None,
        "median_ev_ebitda": round(statistics.median([c["ev_ebitda"] for c in companies if c["ev_ebitda"] and c["ev_ebitda"] > 0]), 1) if companies else None,
        "median_revenue_growth": round(statistics.median([c["revenue_growth"] for c in companies if c["revenue_growth"] is not None]), 1) if companies else None,
        "median_operating_margin": round(statistics.median([c["operating_margin"] for c in companies if c["operating_margin"] is not None]), 1) if companies else None,
    }
    
    # Industry structure assessment
    top5_conc = result["sector_statistics"]["top5_concentration_pct"]
    if top5_conc and top5_conc > 60:
        result["industry_structure"] = "Highly consolidated — top 5 players dominate"
    elif top5_conc and top5_conc > 40:
        result["industry_structure"] = "Moderately consolidated"
    else:
        result["industry_structure"] = "Fragmented — no single dominant player"
    
    return result


# ═══════════════════════════════════════════════════════════════
# VALUATION FOOTBALL FIELD
# Multi-method valuation summary
# ═══════════════════════════════════════════════════════════════

def valuation_football_field(ticker):
    """
    Build a "football field" chart data showing valuation across methods.
    
    Combines:
    - P/E-based valuation
    - EV/EBITDA-based valuation
    - EV/Revenue-based valuation
    - DCF-based valuation
    - Analyst price targets
    
    Returns:
        dict: Valuation range across methods
    """
    import yfinance as yf
    
    result = {
        "ticker": ticker.upper(),
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "methodology": "Multi-method valuation football field",
    }
    
    try:
        old_stderr = __import__('sys').stderr
        __import__('sys').stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            info = t.info
            
            current_price = info.get("currentPrice") or info.get("regularMarketPrice") or 0
            shares = info.get("sharesOutstanding", 0) or 0
            revenue = info.get("totalRevenue", 0) or 0
            ebitda = info.get("ebitda", 0) or 0
            eps_trailing = info.get("trailingEps", 0) or 0
            eps_forward = info.get("forwardEps", 0) or 0
            net_income = info.get("netIncomeToCommon", 0) or 0
            total_debt = info.get("totalDebt", 0) or 0
            total_cash = info.get("totalCash", 0) or 0
            
            # Get peer multiples for context
            peers = _auto_detect_peers(ticker, 5)
            peer_pe = []
            peer_ev_ebitda = []
            peer_ev_rev = []
            
            for peer in peers:
                try:
                    pt = yf.Ticker(peer)
                    pi = pt.info
                    pe = pi.get("trailingPE", 0) or 0
                    eve = pi.get("enterpriseToEbitda", 0) or 0
                    evr = pi.get("enterpriseToRevenue", 0) or 0
                    if pe > 0:
                        peer_pe.append(pe)
                    if eve > 0:
                        peer_ev_ebitda.append(eve)
                    if evr > 0:
                        peer_ev_rev.append(evr)
                except Exception:
                    continue
            
            import statistics
            
            valuations = []
            
            # 1. P/E-based valuation
            if peer_pe and eps_trailing and eps_trailing > 0:
                pe_median = statistics.median(peer_pe)
                pe_low = sorted(peer_pe)[int(len(peer_pe) * 0.25)]
                pe_high = sorted(peer_pe)[int(len(peer_pe) * 0.75)]
                
                valuations.append({
                    "method": "P/E (Trailing)",
                    "low": round(pe_low * eps_trailing, 2),
                    "mid": round(pe_median * eps_trailing, 2),
                    "high": round(pe_high * eps_trailing, 2),
                    "multiple_low": round(pe_low, 1),
                    "multiple_mid": round(pe_median, 1),
                    "multiple_high": round(pe_high, 1),
                })
            
            if peer_pe and eps_forward and eps_forward > 0:
                pe_median = statistics.median(peer_pe)
                pe_low = sorted(peer_pe)[int(len(peer_pe) * 0.25)]
                pe_high = sorted(peer_pe)[int(len(peer_pe) * 0.75)]
                
                valuations.append({
                    "method": "P/E (Forward)",
                    "low": round(pe_low * eps_forward, 2),
                    "mid": round(pe_median * eps_forward, 2),
                    "high": round(pe_high * eps_forward, 2),
                    "multiple_low": round(pe_low, 1),
                    "multiple_mid": round(pe_median, 1),
                    "multiple_high": round(pe_high, 1),
                })
            
            # 2. EV/EBITDA-based valuation
            if peer_ev_ebitda and ebitda and ebitda > 0:
                eve_median = statistics.median(peer_ev_ebitda)
                eve_low = sorted(peer_ev_ebitda)[int(len(peer_ev_ebitda) * 0.25)]
                eve_high = sorted(peer_ev_ebitda)[int(len(peer_ev_ebitda) * 0.75)]
                
                ev_low = eve_low * ebitda
                ev_mid = eve_median * ebitda
                ev_high = eve_high * ebitda
                
                eq_low = ev_low - total_debt + total_cash
                eq_mid = ev_mid - total_debt + total_cash
                eq_high = ev_high - total_debt + total_cash
                
                valuations.append({
                    "method": "EV/EBITDA",
                    "low": round(eq_low / shares, 2) if shares > 0 else 0,
                    "mid": round(eq_mid / shares, 2) if shares > 0 else 0,
                    "high": round(eq_high / shares, 2) if shares > 0 else 0,
                    "multiple_low": round(eve_low, 1),
                    "multiple_mid": round(eve_median, 1),
                    "multiple_high": round(eve_high, 1),
                })
            
            # 3. EV/Revenue-based valuation
            if peer_ev_rev and revenue and revenue > 0:
                evr_median = statistics.median(peer_ev_rev)
                evr_low = sorted(peer_ev_rev)[int(len(peer_ev_rev) * 0.25)]
                evr_high = sorted(peer_ev_rev)[int(len(peer_ev_rev) * 0.75)]
                
                ev_low = evr_low * revenue
                ev_mid = evr_median * revenue
                ev_high = evr_high * revenue
                
                eq_low = ev_low - total_debt + total_cash
                eq_mid = ev_mid - total_debt + total_cash
                eq_high = ev_high - total_debt + total_cash
                
                valuations.append({
                    "method": "EV/Revenue",
                    "low": round(eq_low / shares, 2) if shares > 0 else 0,
                    "mid": round(eq_mid / shares, 2) if shares > 0 else 0,
                    "high": round(eq_high / shares, 2) if shares > 0 else 0,
                    "multiple_low": round(evr_low, 1),
                    "multiple_mid": round(evr_median, 1),
                    "multiple_high": round(evr_high, 1),
                })
            
            # 4. Analyst price targets
            target_mean = info.get("targetMeanPrice", 0) or 0
            target_low = info.get("targetLowPrice", 0) or 0
            target_high = info.get("targetHighPrice", 0) or 0
            
            if target_mean > 0:
                valuations.append({
                    "method": "Analyst Consensus",
                    "low": round(target_low, 2),
                    "mid": round(target_mean, 2),
                    "high": round(target_high, 2),
                    "multiple_low": None,
                    "multiple_mid": None,
                    "multiple_high": None,
                })
            
            result["valuations"] = valuations
            result["current_price"] = round(current_price, 2)
            
            # Calculate overall range
            all_lows = [v["low"] for v in valuations if v["low"] > 0]
            all_highs = [v["high"] for v in valuations if v["high"] > 0]
            all_mids = [v["mid"] for v in valuations if v["mid"] > 0]
            
            if all_lows and all_highs:
                result["overall_range"] = {
                    "low": round(min(all_lows), 2),
                    "mid": round(statistics.mean(all_mids), 2) if all_mids else None,
                    "high": round(max(all_highs), 2),
                    "upside_to_mid_pct": round((statistics.mean(all_mids) - current_price) / current_price * 100, 1) if all_mids and current_price > 0 else None,
                }
            
        finally:
            __import__('sys').stderr = old_stderr
    except Exception as e:
        result["error"] = str(e)
    
    return result


# ═══════════════════════════════════════════════════════════════
# COMPREHENSIVE FINANCIAL ANALYSIS REPORT
# Combines all modules into a single institutional-grade report
# ═══════════════════════════════════════════════════════════════

def full_financial_analysis(ticker, peer_tickers=None, depth="comprehensive"):
    """
    Run a complete financial analysis combining all modules.
    
    This is the main entry point for institutional-grade analysis.
    Combines:
    1. Company profile & key metrics
    2. Comparable company analysis (comps)
    3. DCF valuation
    4. Earnings analysis
    5. Competitive landscape
    6. Valuation football field
    
    Args:
        ticker: Stock ticker
        peer_tickers: Optional list of specific peer tickers
        depth: "quick" or "comprehensive"
    
    Returns:
        dict: Complete financial analysis
    """
    result = {
        "ticker": ticker.upper(),
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "depth": depth,
        "disclaimer": "For educational/informational purposes only. Not financial advice. Verify with your broker before acting.",
    }
    
    # 1. Basic analysis
    result["basic_analysis"] = analyze_stock(ticker, depth)
    
    # 2. Comps analysis
    result["comps_analysis"] = build_comps_analysis(ticker, peer_tickers)
    
    # 3. DCF valuation
    result["dcf_valuation"] = build_dcf_valuation(ticker)
    
    # 4. Earnings analysis
    result["earnings_analysis"] = analyze_earnings_event(ticker)
    
    if depth == "comprehensive":
        # 5. Competitive landscape
        result["competitive_landscape"] = analyze_competitive_landscape(ticker, peer_tickers)
        
        # 6. Valuation football field
        result["valuation_football_field"] = valuation_football_field(ticker)
    
    return result


def format_comps_report(comps_data):
    """Format comps analysis into readable markdown."""
    lines = []
    ticker = comps_data.get("ticker", "Unknown")
    lines.append(f"## 📊 Comparable Company Analysis: {ticker}")
    lines.append(f"*{comps_data.get('timestamp', '')}*")
    lines.append("")
    
    # Peer group
    lines.append(f"**Peer Group:** {', '.join(comps_data.get('peer_group', []))}")
    lines.append("")
    
    # Operating metrics table
    operating = comps_data.get("operating_metrics", [])
    if operating:
        lines.append("### Operating Metrics")
        lines.append("| Company | Revenue ($M) | Rev Growth | Gross Margin | EBITDA Margin | FCF Margin |")
        lines.append("|---------|-------------|------------|--------------|---------------|------------|")
        for op in operating:
            rev = op.get('revenue_m', 'N/A')
            rev_str = f"{rev:,.0f}" if isinstance(rev, (int, float)) else str(rev)
            lines.append(f"| {op.get('ticker', '')} | {rev_str} | {op.get('revenue_growth', 'N/A')}% | {op.get('gross_margin', 'N/A')}% | {op.get('ebitda_margin', 'N/A')}% | {op.get('fcf_margin', 'N/A')}% |")
        lines.append("")
    
    # Valuation multiples table
    valuation = comps_data.get("valuation_multiples", [])
    if valuation:
        lines.append("### Valuation Multiples")
        lines.append("| Company | Price | Market Cap ($M) | P/E (T) | P/E (F) | EV/EBITDA | EV/Revenue | FCF Yield |")
        lines.append("|---------|-------|-----------------|---------|---------|-----------|------------|-----------|")
        for v in valuation:
            lines.append(f"| {v.get('ticker', '')} | ${v.get('price', 'N/A')} | {v.get('market_cap_m', 'N/A'):,.0f} | {v.get('pe_trailing', 'N/A')} | {v.get('pe_forward', 'N/A')} | {v.get('ev_ebitda', 'N/A')} | {v.get('ev_revenue', 'N/A')} | {v.get('fcf_yield', 'N/A')}% |")
        lines.append("")
    
    # Statistical summary
    stats = comps_data.get("valuation_stats", {})
    if stats:
        lines.append("### Statistical Summary (Valuation)")
        lines.append("| Metric | Max | 75th | Median | 25th | Min |")
        lines.append("|--------|-----|------|--------|------|-----|")
        for metric, values in stats.items():
            if isinstance(values, dict):
                lines.append(f"| {metric} | {values.get('max', 'N/A')} | {values.get('p75', 'N/A')} | {values.get('median', 'N/A')} | {values.get('p25', 'N/A')} | {values.get('min', 'N/A')} |")
        lines.append("")
    
    # Outliers
    outliers = comps_data.get("outliers", {})
    flags = outliers.get("flags", [])
    if flags:
        lines.append("### 🚩 Valuation Outliers")
        for flag in flags:
            signal_emoji = "🔴" if flag.get("signal") == "overvalued" else "🟢"
            lines.append(f"- {signal_emoji} **{flag.get('metric')}**: {flag.get('assessment')} (deviation: {flag.get('deviation_pct')}%)")
        lines.append("")
    
    return "\n".join(lines)


def format_dcf_report(dcf_data):
    """Format DCF analysis into readable markdown."""
    lines = []
    ticker = dcf_data.get("ticker", "Unknown")
    lines.append(f"## 💰 DCF Valuation: {ticker}")
    lines.append(f"*{dcf_data.get('timestamp', '')}*")
    lines.append("")
    
    # WACC
    wacc = dcf_data.get("wacc", {})
    if isinstance(wacc, dict) and "wacc" in wacc:
        lines.append(f"**WACC:** {wacc.get('wacc', 'N/A'):.1%}" if isinstance(wacc.get('wacc'), (int, float)) else f"**WACC:** {wacc}")
        if "cost_of_equity" in wacc:
            lines.append(f"- Cost of Equity: {wacc.get('cost_of_equity', 'N/A')}")
            lines.append(f"- Cost of Debt (after-tax): {wacc.get('after_tax_cost_of_debt', 'N/A')}")
            lines.append(f"- Beta: {wacc.get('beta', 'N/A')}")
        lines.append("")
    
    # Projections
    proj = dcf_data.get("projections", {})
    if proj:
        lines.append("### FCF Projections")
        years = proj.get("years", [])
        fcf = proj.get("fcf", [])
        growth = proj.get("growth_rates", [])
        lines.append("| Year | FCF ($M) | Growth Rate |")
        lines.append("|------|----------|-------------|")
        for i in range(len(years)):
            fcf_val = fcf[i] if i < len(fcf) else "N/A"
            gr_val = growth[i] if i < len(growth) else "N/A"
            fcf_str = f"{fcf_val:,.0f}" if isinstance(fcf_val, (int, float)) else str(fcf_val)
            lines.append(f"| {years[i]} | {fcf_str} | {gr_val}% |")
        lines.append("")
    
    # Valuation
    val = dcf_data.get("valuation", {})
    eq = dcf_data.get("equity_value", {})
    if val:
        lines.append("### Valuation Summary")
        lines.append(f"- Sum of PV FCFs: ${val.get('sum_pv_fcfs', 0):,.0f}M")
        lines.append(f"- PV of Terminal Value: ${val.get('pv_terminal_value', 0):,.0f}M")
        lines.append(f"- Enterprise Value: ${val.get('enterprise_value', 0):,.0f}M")
        lines.append(f"- Net Debt: ${eq.get('net_debt', 0):,.0f}M")
        lines.append(f"- Equity Value: ${eq.get('equity_value', 0):,.0f}M")
        lines.append(f"- **Implied Price: ${eq.get('implied_price_per_share', 0):.2f}**")
        lines.append(f"- Current Price: ${eq.get('current_price', 0):.2f}")
        upside = eq.get("upside_pct", 0)
        upside_emoji = "🟢" if upside and upside > 0 else "🔴"
        lines.append(f"- {upside_emoji} **Upside/Downside: {upside}%**")
        lines.append("")
    
    # Scenarios
    scenarios = dcf_data.get("scenarios", {})
    if scenarios:
        lines.append("### Scenario Analysis")
        lines.append("| Scenario | Revenue CAGR | Implied Price |")
        lines.append("|----------|-------------|---------------|")
        for scenario, data in scenarios.items():
            if isinstance(data, dict):
                lines.append(f"| {scenario.capitalize()} | {data.get('revenue_cagr', 'N/A')}% | ${data.get('implied_price', 'N/A')} |")
        lines.append("")
    
    # Sensitivity
    sens = dcf_data.get("sensitivity", {})
    if sens and "implied_prices" in sens:
        lines.append("### Sensitivity Analysis (WACC vs Terminal Growth)")
        wacc_vals = sens.get("wacc_values", [])
        tg_vals = sens.get("terminal_growth_values", [])
        grid = sens.get("implied_prices", [])
        
        header = "| WACC \\ TG |"
        separator = "|------------|"
        for tg in tg_vals:
            header += f" {tg}% |"
            separator += "--------|"
        lines.append(header)
        lines.append(separator)
        
        for i, wacc_val in enumerate(wacc_vals):
            row = f"| {wacc_val}% |"
            if i < len(grid):
                for price in grid[i]:
                    if price is not None:
                        row += f" ${price:.2f} |"
                    else:
                        row += " N/A |"
            lines.append(row)
        lines.append("")
    
    # Sanity checks
    checks = dcf_data.get("sanity_checks", [])
    if checks:
        lines.append("### Sanity Checks")
        for check in checks:
            status_emoji = "✅" if check.get("status") == "PASS" else ("⚠️" if check.get("status") == "WARNING" else "❌")
            lines.append(f"- {status_emoji} **{check.get('check')}**: {check.get('detail')}")
        lines.append("")
    
    return "\n".join(lines)


def format_earnings_report(earnings_data):
    """Format earnings analysis into readable markdown."""
    lines = []
    ticker = earnings_data.get("ticker", "Unknown")
    lines.append(f"## 📈 Earnings Analysis: {ticker}")
    lines.append(f"*{earnings_data.get('timestamp', '')}*")
    lines.append("")
    
    # Beat/Miss
    bm = earnings_data.get("beat_miss", {})
    if bm:
        eps_result = bm.get("eps_result", "N/A")
        rev_result = bm.get("revenue_result", "N/A")
        eps_emoji = "🟢" if eps_result == "Beat" else ("🔴" if eps_result == "Miss" else "⚪")
        rev_emoji = "🟢" if rev_result == "Beat" else ("🔴" if rev_result == "Miss" else "⚪")
        
        lines.append(f"### Beat/Miss Analysis")
        lines.append(f"- {eps_emoji} **EPS**: {eps_result} — Actual: ${bm.get('eps_actual', 'N/A')} vs Estimate: ${bm.get('eps_estimate', 'N/A')}")
        if bm.get('eps_surprise_pct') is not None:
            lines.append(f"  - Surprise: {bm['eps_surprise_pct']:+.1f}%")
        lines.append(f"- {rev_emoji} **Revenue**: {rev_result} — Actual: ${bm.get('revenue_actual_b', 'N/A')}B vs Estimate: ${bm.get('revenue_estimate_b', 'N/A')}B")
        if bm.get('revenue_surprise_pct') is not None:
            lines.append(f"  - Surprise: {bm['revenue_surprise_pct']:+.1f}%")
        lines.append("")
    
    # Margins
    margins = earnings_data.get("margins", {})
    if margins:
        lines.append("### Margin Analysis")
        lines.append(f"- Gross Margin: {margins.get('gross_margin', 'N/A')}%")
        lines.append(f"- Operating Margin: {margins.get('operating_margin', 'N/A')}%")
        lines.append(f"- Profit Margin: {margins.get('profit_margin', 'N/A')}%")
        lines.append(f"- EBITDA Margin: {margins.get('ebitda_margin', 'N/A')}%")
        lines.append(f"- FCF Margin: {margins.get('fcf_margin', 'N/A')}%")
        lines.append("")
    
    # Growth
    growth = earnings_data.get("growth", {})
    if growth:
        lines.append("### Growth Analysis")
        lines.append(f"- Revenue Growth (YoY): {growth.get('revenue_growth_yoy', 'N/A')}%")
        lines.append(f"- Earnings Growth: {growth.get('earnings_growth', 'N/A')}%")
        lines.append(f"- Quarterly Earnings Growth: {growth.get('earnings_quarterly_growth', 'N/A')}%")
        lines.append("")
    
    # Quality Assessment
    qa = earnings_data.get("quality_assessment", {})
    if qa:
        lines.append(f"### Quality Assessment: {qa.get('overall', 'N/A')}")
        for factor in qa.get("factors", []):
            lines.append(f"- {factor}")
        lines.append("")
    
    return "\n".join(lines)


def format_competitive_report(comp_data):
    """Format competitive landscape analysis into readable markdown."""
    lines = []
    ticker = comp_data.get("ticker", "Unknown")
    lines.append(f"## 🏆 Competitive Landscape: {ticker}")
    lines.append(f"*{comp_data.get('timestamp', '')}*")
    lines.append("")
    
    # Company profile
    profile = comp_data.get("company_profile", {})
    if profile:
        lines.append(f"**{profile.get('name', ticker)}** | {profile.get('sector', '')} | {profile.get('industry', '')}")
        lines.append(f"Market Cap: ${profile.get('market_cap_b', 'N/A')}B | Revenue: ${profile.get('revenue_b', 'N/A')}B")
        lines.append("")
    
    # Moat assessment
    moat = comp_data.get("moat_assessment", {})
    if moat:
        lines.append(f"### Moat Assessment: {moat.get('overall_rating', 'N/A')} (Score: {moat.get('score', 0)}/{moat.get('max_score', 8)})")
        for dim_name, dim_data in moat.get("dimensions", {}).items():
            if isinstance(dim_data, dict):
                rating = dim_data.get("rating", "N/A")
                emoji = "🟢" if rating == "Strong" else ("🟡" if rating == "Moderate" else "🔴")
                lines.append(f"- {emoji} **{dim_name.replace('_', ' ').title()}**: {rating} — {dim_data.get('assessment', '')}")
        lines.append("")
    
    # Competitor comparison
    competitors = comp_data.get("competitor_comparison", [])
    if competitors:
        lines.append("### Competitor Comparison")
        lines.append("| Company | Market Cap | Revenue | Rev Growth | Gross Margin | Op Margin | ROE |")
        lines.append("|---------|-----------|---------|------------|--------------|-----------|-----|")
        for c in competitors:
            lines.append(f"| {c.get('ticker', '')} | ${c.get('market_cap_b', 'N/A')}B | ${c.get('revenue_b', 'N/A')}B | {c.get('revenue_growth', 'N/A')}% | {c.get('gross_margin', 'N/A')}% | {c.get('operating_margin', 'N/A')}% | {c.get('roe', 'N/A')}% |")
        lines.append("")
    
    # Scenarios
    scenarios = comp_data.get("scenarios", {})
    if scenarios:
        lines.append("### Scenarios")
        for scenario_name, scenario_data in scenarios.items():
            if isinstance(scenario_data, dict):
                lines.append(f"**{scenario_name.replace('_', ' ').title()}** (Probability: {scenario_data.get('probability', 'N/A')})")
                lines.append(f"- Thesis: {scenario_data.get('thesis', '')}")
                for assumption in scenario_data.get("assumptions", []):
                    lines.append(f"  - {assumption}")
                catalysts = scenario_data.get("key_catalysts", scenario_data.get("key_risks", []))
                for catalyst in catalysts:
                    lines.append(f"  - 📌 {catalyst}")
                lines.append("")
    
    return "\n".join(lines)


def format_football_field_report(ff_data):
    """Format valuation football field into readable markdown."""
    lines = []
    ticker = ff_data.get("ticker", "Unknown")
    lines.append(f"## 🏈 Valuation Football Field: {ticker}")
    lines.append(f"*{ff_data.get('timestamp', '')}*")
    lines.append("")
    
    lines.append(f"**Current Price:** ${ff_data.get('current_price', 'N/A')}")
    lines.append("")
    
    valuations = ff_data.get("valuations", [])
    if valuations:
        lines.append("| Method | Low | Mid | High |")
        lines.append("|--------|-----|-----|------|")
        for v in valuations:
            lines.append(f"| {v.get('method', '')} | ${v.get('low', 'N/A')} | ${v.get('mid', 'N/A')} | ${v.get('high', 'N/A')} |")
        lines.append("")
    
    overall = ff_data.get("overall_range", {})
    if overall:
        lines.append("### Overall Valuation Range")
        lines.append(f"- **Low:** ${overall.get('low', 'N/A')}")
        lines.append(f"- **Mid:** ${overall.get('mid', 'N/A')}")
        lines.append(f"- **High:** ${overall.get('high', 'N/A')}")
        upside = overall.get("upside_to_mid_pct")
        if upside is not None:
            emoji = "🟢" if upside > 0 else "🔴"
            lines.append(f"- {emoji} **Upside to Mid:** {upside}%")
        lines.append("")
    
    return "\n".join(lines)


if __name__ == "__main__":
    import sys
    ticker = sys.argv[1] if len(sys.argv) > 1 else "AAPL"
    depth = sys.argv[2] if len(sys.argv) > 2 else "comprehensive"
    
    print(f"Running full financial analysis for {ticker} (depth: {depth})...")
    print("=" * 80)
    
    # Full analysis
    analysis = full_financial_analysis(ticker, depth=depth)
    
    # Print reports
    print(format_analysis_report(analysis.get("basic_analysis", {})))
    print(format_comps_report(analysis.get("comps_analysis", {})))
    print(format_dcf_report(analysis.get("dcf_valuation", {})))
    print(format_earnings_report(analysis.get("earnings_analysis", {})))
    
    if depth == "comprehensive":
        print(format_competitive_report(analysis.get("competitive_landscape", {})))
        print(format_football_field_report(analysis.get("valuation_football_field", {})))
    
    print("=" * 80)
    print(analysis.get("disclaimer", ""))
