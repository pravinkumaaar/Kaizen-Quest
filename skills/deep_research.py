"""
Deep Research Orchestrator v1.0

Orchestrates comprehensive, multi-source research on tickers before
the LLM makes investment decisions. Ensures the agent uses ALL available
data sources and tools to make well-informed decisions.

Research Pipeline (7 Layers):
  1. Quantitative Screen    — ratios, growth rates, valuation multiples
  2. Financial Deep-Dive    — financial statements, DCF, guidance history
  3. Competitive Landscape  — peer comparison, moat analysis, market share
  4. Management & Governance — insider activity, institutional ownership, ESG
  5. Macro & Sector Context — sector rotation, macro signals, economic calendar
  6. Contrarian Analysis    — short interest, bear case, risk deep-dive
  7. Temporal Evolution     — thesis history, change detection, fact freshness

Anti-Stale-Data Safeguards:
  - Every data point is timestamped
  - Confidence decays exponentially by fact type (half-life from 1-60 days)
  - Cross-references multiple sources (min 2/3 agreement for verification)
  - Never recommends on stale critical data (price, options)
  - Source reliability tracking — prefers sources with better track record

Usage:
    from skills.deep_research import DeepResearcher
    
    researcher = DeepResearcher()
    
    # Full deep research on a ticker (all 7 layers)
    result = researcher.deep_dive("NVDA")
    
    # Quick update (only what's changed since last research)
    result = researcher.quick_update("NVDA")
    
    # Research multiple tickers, returns prioritized results
    results = researcher.research_batch(["NVDA", "MU", "VRT"], max_depth=7)
    
    # Get formatted context for LLM investment decision
    context = researcher.get_llm_context("NVDA")
"""

import sys
import json
import datetime
import math
from io import StringIO
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent

# ─── Suppress yfinance stderr for all imports ──────────────────────
_old_stderr = sys.stderr
sys.stderr = StringIO()
try:
    import yfinance as yf
except Exception:
    pass
finally:
    sys.stderr = _old_stderr


class DeepResearcher:
    """
    Orchestrates deep research using all available data sources.
    """
    
    def __init__(self, verbose=True):
        self.verbose = verbose
        self.now = datetime.datetime.now().isoformat()
        self._research_findings = {}
        self._sources_used = set()
        self._errors = []
    
    def _log(self, msg):
        if self.verbose:
            print(f"  [DeepResearch] {msg}")
    
    def _safe_call(self, func_name, func, *args, **kwargs):
        """Safely call a data function, suppressing stderr and catching errors."""
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            result = func(*args, **kwargs)
            self._sources_used.add(func_name)
            return result
        except Exception as e:
            self._errors.append(f"{func_name}: {str(e)[:100]}")
            return None
        finally:
            sys.stderr = old_stderr
    
    # ═══════════════════════════════════════════════════════════════════
    # LAYER 1: Quantitative Screen
    # ═══════════════════════════════════════════════════════════════════
    
    def _layer1_quant_screen(self, ticker):
        """Layer 1: Ratios, growth rates, valuation multiples."""
        self._log(f"  L1: Quantitative screen for {ticker}")
        findings = {"layer": 1, "data": {}, "facts": [], "timestamp": self.now}
        
        # Price data (from yfinance_utils with Polygon fallback)
        try:
            from skills.yfinance_utils import safe_yf_price, safe_yf_info
            price_data = safe_yf_price(ticker)
            if price_data.get("price", 0) > 0:
                findings["data"]["price"] = price_data
                findings["facts"].append({
                    "claim": f"{ticker} trading at ${price_data['price']:.2f} ({price_data.get('change_pct', 0):+.2f}%)",
                    "type": "price", "initial_confidence": 0.95, "source": price_data.get("source", "unknown"),
                    "first_verified": self.now, "last_verified": self.now, "verification_count": 1,
                })
        except Exception as e:
            self._errors.append(f"price: {e}")
        
        # Company info & key metrics
        try:
            info = safe_yf_info(ticker)
            if not info:
                self._log(f"  ⚠️ L1: No company info returned for {ticker}")
            elif len(info) <= 5:
                self._log(f"  ⚠️ L1: Sparse company info ({len(info)} keys): {list(info.keys())}")
            if info and len(info) > 5:
                findings["data"]["info"] = {
                    "sector": info.get("sector", "Unknown"),
                    "industry": info.get("industry", "Unknown"),
                    "market_cap": info.get("marketCap", 0) or info.get("market_cap", 0),
                    "pe_ratio": info.get("trailingPE", 0) or info.get("peRatio", 0),
                    "forward_pe": info.get("forwardPE", 0),
                    "peg_ratio": info.get("pegRatio", 0),
                    "price_to_book": info.get("priceToBook", 0),
                    "price_to_sales": info.get("priceToSalesTrailing12Months", 0),
                    "ev_to_ebitda": info.get("enterpriseToEbitda", 0),
                    "profit_margin": info.get("profitMargins", 0),
                    "operating_margin": info.get("operatingMargins", 0),
                    "revenue_growth": info.get("revenueGrowth", 0),
                    "earnings_growth": info.get("earningsGrowth", 0),
                    "roa": info.get("returnOnAssets", 0),
                    "roe": info.get("returnOnEquity", 0),
                    "debt_to_equity": info.get("debtToEquity", 0),
                    "current_ratio": info.get("currentRatio", 0),
                    "free_cash_flow": info.get("freeCashflow", 0),
                    "dividend_yield": info.get("dividendYield", 0),
                    "beta": info.get("beta", 1),
                    "fifty_two_week_high": info.get("fiftyTwoWeekHigh", 0),
                    "fifty_two_week_low": info.get("fiftyTwoWeekLow", 0),
                    "fifty_day_avg": info.get("fiftyDayAverage", 0),
                    "two_hundred_day_avg": info.get("twoHundredDayAverage", 0),
                    "avg_volume": info.get("averageVolume", 0),
                    "short_ratio": info.get("shortRatio", 0),
                    "short_percent": info.get("shortPercentOfFloat", 0),
                    "recommendation": info.get("recommendationKey", ""),
                    "target_price": info.get("targetMeanPrice", 0),
                    "analyst_count": info.get("numberOfAnalystOpinions", 0),
                }
                # Extract key facts
                info_data = findings["data"]["info"]
                if info_data.get("pe_ratio"):
                    findings["facts"].append({
                        "claim": f"P/E: {info_data['pe_ratio']:.1f}, Forward P/E: {info_data.get('forward_pe', 0) or 'N/A'}",
                        "type": "fundamentals", "initial_confidence": 0.9, "source": "yfinance",
                        "first_verified": self.now, "last_verified": self.now, "verification_count": 1,
                    })
                if info_data.get("revenue_growth"):
                    findings["facts"].append({
                        "claim": f"Revenue growth: {info_data['revenue_growth']*100:.1f}%",
                        "type": "fundamentals", "initial_confidence": 0.9, "source": "yfinance",
                        "first_verified": self.now, "last_verified": self.now, "verification_count": 1,
                    })
                if info_data.get("roe"):
                    findings["facts"].append({
                        "claim": f"ROE: {info_data['roe']*100:.1f}%",
                        "type": "fundamentals", "initial_confidence": 0.9, "source": "yfinance",
                        "first_verified": self.now, "last_verified": self.now, "verification_count": 1,
                    })
        except Exception as e:
            self._errors.append(f"info: {e}")
        
        # Financial ratios from data providers
        try:
            from skills.financial_data_providers import get_financial_ratios
            ratios = self._safe_call("financial_ratios", get_financial_ratios, ticker)
            if ratios:
                findings["data"]["financial_ratios"] = ratios
        except Exception:
            pass
        
        # Valuation multiples
        try:
            from skills.stock_analyzer import get_valuation_multiples
            multiples = self._safe_call("valuation_multiples", get_valuation_multiples, ticker)
            if multiples:
                findings["data"]["multiples"] = multiples
        except Exception:
            pass
        
        return findings
    
    # ═══════════════════════════════════════════════════════════════════
    # LAYER 2: Financial Deep-Dive
    # ═══════════════════════════════════════════════════════════════════
    
    def _layer2_financial_deep_dive(self, ticker):
        """Layer 2: Financial statements, DCF, guidance history."""
        self._log(f"  L2: Financial deep-dive for {ticker}")
        findings = {"layer": 2, "data": {}, "facts": [], "timestamp": self.now}
        
        # Financial statements
        try:
            from skills.financial_data_providers import get_financial_statements
            income = self._safe_call("income_statement", get_financial_statements, ticker, "income", "annual", 5)
            balance = self._safe_call("balance_sheet", get_financial_statements, ticker, "balance", "annual", 5)
            cashflow = self._safe_call("cashflow", get_financial_statements, ticker, "cashflow", "annual", 5)
            if income or balance or cashflow:
                findings["data"]["financial_statements"] = {
                    "income": income, "balance": balance, "cashflow": cashflow
                }
        except Exception:
            pass
        
        # DCF valuation
        try:
            from skills.financial_data_providers import get_dcf_valuation
            dcf = self._safe_call("dcf", get_dcf_valuation, ticker)
            if dcf:
                findings["data"]["dcf"] = dcf
                if isinstance(dcf, dict):
                    fair_value = dcf.get("fair_value") or dcf.get("dcf_value") or dcf.get("price")
                    current = dcf.get("current_price", 0)
                    if fair_value and current:
                        upside = (fair_value - current) / current * 100
                        findings["facts"].append({
                            "claim": f"DCF fair value: ${fair_value:.2f} vs current ${current:.2f} ({upside:+.1f}% upside)",
                            "type": "fundamentals", "initial_confidence": 0.7, "source": "dcf_model",
                            "first_verified": self.now, "last_verified": self.now, "verification_count": 1,
                        })
        except Exception:
            pass
        
        # Analyst estimates
        try:
            from skills.financial_data_providers import get_analyst_estimates
            estimates = self._safe_call("analyst_estimates", get_analyst_estimates, ticker)
            if estimates:
                findings["data"]["analyst_estimates"] = estimates
        except Exception:
            pass
        
        # Earnings history & surprises
        try:
            from skills.financial_data_providers import get_earnings_history
            earnings_hist = self._safe_call("earnings_history", get_earnings_history, ticker)
            if earnings_hist:
                findings["data"]["earnings_history"] = earnings_hist
                # Count beats vs misses
                if isinstance(earnings_hist, list):
                    beats = sum(1 for e in earnings_hist if isinstance(e, dict) and e.get("surprisePercent", 0) > 0)
                    total = len(earnings_hist)
                    if total > 0:
                        findings["facts"].append({
                            "claim": f"Earnings beat rate: {beats}/{total} ({beats/total*100:.0f}%)",
                            "type": "earnings", "initial_confidence": 0.85, "source": "finnhub",
                            "first_verified": self.now, "last_verified": self.now, "verification_count": 1,
                        })
        except Exception:
            pass
        
        # Price targets
        try:
            from skills.earnings_intelligence import get_price_target
            pt = self._safe_call("price_target", get_price_target, ticker)
            if pt:
                findings["data"]["price_target"] = pt
        except Exception:
            pass
        
        return findings
    
    # ═══════════════════════════════════════════════════════════════════
    # LAYER 3: Competitive Landscape
    # ═══════════════════════════════════════════════════════════════════
    
    def _layer3_competitive(self, ticker):
        """Layer 3: Peer comparison, moat analysis, market share."""
        self._log(f"  L3: Competitive landscape for {ticker}")
        findings = {"layer": 3, "data": {}, "facts": [], "timestamp": self.now}
        
        # Peer comparison from stock_analyzer
        try:
            from skills.stock_analyzer import build_comps_analysis, analyze_competitive_landscape
            comps = self._safe_call("comps_analysis", build_comps_analysis, ticker)
            if comps:
                findings["data"]["peer_comparison"] = comps
        except Exception:
            pass
        
        # Competitive landscape analysis
        try:
            comp_landscape = self._safe_call("competitive_landscape", analyze_competitive_landscape, ticker)
            if comp_landscape:
                findings["data"]["competitive_landscape"] = comp_landscape
                moat = comp_landscape.get("moat_assessment", {})
                if moat:
                    findings["facts"].append({
                        "claim": f"Moat: {moat.get('rating', 'N/A')} — {moat.get('description', '')}",
                        "type": "competitive", "initial_confidence": 0.75, "source": "stock_analyzer",
                        "first_verified": self.now, "last_verified": self.now, "verification_count": 1,
                    })
        except Exception:
            pass
        
        # Supply chain analysis
        try:
            from skills.financial_data_providers import get_supply_chain
            supply_chain = self._safe_call("supply_chain", get_supply_chain, ticker)
            if supply_chain:
                findings["data"]["supply_chain"] = supply_chain
        except Exception:
            pass
        
        # Industry P/E comparison
        try:
            from skills.financial_data_providers import get_industry_pe
            industry_pe = self._safe_call("industry_pe", get_industry_pe)
            if industry_pe:
                findings["data"]["industry_pe"] = industry_pe
        except Exception:
            pass
        
        return findings
    
    # ═══════════════════════════════════════════════════════════════════
    # LAYER 4: Management & Governance
    # ═══════════════════════════════════════════════════════════════════
    
    def _layer4_management(self, ticker):
        """Layer 4: Insider activity, institutional ownership, ESG."""
        self._log(f"  L4: Management & governance for {ticker}")
        findings = {"layer": 4, "data": {}, "facts": [], "timestamp": self.now}
        
        # Insider trades
        try:
            from skills.financial_data_providers import get_insider_trades
            insider = self._safe_call("insider_trades", get_insider_trades, ticker)
            if insider:
                findings["data"]["insider_trades"] = insider
                if isinstance(insider, list) and len(insider) > 0:
                    # Summarize insider activity
                    buys = sum(1 for t in insider if isinstance(t, dict) and t.get("transactionType", "") in ["P", "Purchase"])
                    sells = sum(1 for t in insider if isinstance(t, dict) and t.get("transactionType", "") in ["S", "Sale"])
                    findings["facts"].append({
                        "claim": f"Insider activity (90d): {buys} buys, {sells} sells",
                        "type": "insider", "initial_confidence": 0.85, "source": "finnhub",
                        "first_verified": self.now, "last_verified": self.now, "verification_count": 1,
                    })
        except Exception:
            pass
        
        # Institutional ownership
        try:
            from skills.financial_data_providers import get_institutional_ownership
            inst = self._safe_call("institutional", get_institutional_ownership, ticker)
            if inst:
                findings["data"]["institutional_ownership"] = inst
        except Exception:
            pass
        
        # Congressional trading
        try:
            from skills.financial_data_providers import get_congressional_trading
            congress = self._safe_call("congressional", get_congressional_trading, ticker)
            if congress:
                findings["data"]["congressional_trading"] = congress
                if isinstance(congress, list) and len(congress) > 0:
                    findings["facts"].append({
                        "claim": f"Congressional trades: {len(congress)} transactions in last 90 days",
                        "type": "insider", "initial_confidence": 0.8, "source": "finnhub",
                        "first_verified": self.now, "last_verified": self.now, "verification_count": 1,
                    })
        except Exception:
            pass
        
        # ESG scores
        try:
            from skills.financial_data_providers import get_esg_scores
            esg = self._safe_call("esg", get_esg_scores, ticker)
            if esg:
                findings["data"]["esg"] = esg
        except Exception:
            pass
        
        # Smart money summary
        try:
            from skills.smart_money_tracker import get_finnhub_insider_sentiment, get_finnhub_recommendation_trends
            sentiment = self._safe_call("insider_sentiment", get_finnhub_insider_sentiment, ticker)
            recommendations = self._safe_call("recommendation_trends", get_finnhub_recommendation_trends, ticker)
            if sentiment or recommendations:
                findings["data"]["smart_money"] = {
                    "insider_sentiment": sentiment,
                    "analyst_recommendations": recommendations,
                }
        except Exception:
            pass
        
        return findings
    
    # ═══════════════════════════════════════════════════════════════════
    # LAYER 5: Macro & Sector Context
    # ═══════════════════════════════════════════════════════════════════
    
    def _layer5_macro_sector(self, ticker):
        """Layer 5: Sector rotation, macro signals, economic calendar."""
        self._log(f"  L5: Macro & sector context for {ticker}")
        findings = {"layer": 5, "data": {}, "facts": [], "timestamp": self.now}
        
        # Sector performance
        try:
            from skills.financial_data_providers import get_sector_performance
            sector_perf = self._safe_call("sector_performance", get_sector_performance)
            if sector_perf:
                findings["data"]["sector_performance"] = sector_perf
        except Exception:
            pass
        
        # Sector rotation analysis
        try:
            from skills.sector_rotation import analyze_sector_rotation, get_macro_rotation_signals
            rotation = self._safe_call("sector_rotation", analyze_sector_rotation)
            macro_signals = self._safe_call("macro_rotation", get_macro_rotation_signals)
            if rotation or macro_signals:
                findings["data"]["rotation"] = {
                    "sector_rotation": rotation,
                    "macro_signals": macro_signals,
                }
        except Exception:
            pass
        
        # Economic calendar
        try:
            from skills.financial_data_providers import get_economic_calendar
            calendar = self._safe_call("economic_calendar", get_economic_calendar, None, 14)
            if calendar:
                findings["data"]["economic_calendar"] = calendar
        except Exception:
            pass
        
        # Treasury rates (for discount rate context)
        try:
            from skills.financial_data_providers import get_treasury_rates
            rates = self._safe_call("treasury_rates", get_treasury_rates)
            if rates:
                findings["data"]["treasury_rates"] = rates
        except Exception:
            pass
        
        # Market sentiment
        try:
            from skills.market_sentiment import get_market_sentiment
            sentiment = self._safe_call("market_sentiment", get_market_sentiment)
            if sentiment:
                findings["data"]["market_sentiment"] = sentiment
        except Exception:
            pass
        
        # Technical indicators
        try:
            from skills.financial_data_providers import get_technical_indicators, get_aggregate_indicators
            tech = self._safe_call("technical_indicators", get_technical_indicators, ticker)
            agg = self._safe_call("aggregate_indicators", get_aggregate_indicators, ticker)
            if tech or agg:
                findings["data"]["technicals"] = {
                    "indicators": tech,
                    "aggregate": agg,
                }
        except Exception:
            pass
        
        return findings
    
    # ═══════════════════════════════════════════════════════════════════
    # LAYER 6: Contrarian Analysis
    # ═══════════════════════════════════════════════════════════════════
    
    def _layer6_contrarian(self, ticker):
        """Layer 6: Actively seek disconfirming evidence — the bear case."""
        self._log(f"  L6: Contrarian analysis for {ticker}")
        findings = {"layer": 6, "data": {}, "facts": [], "contrarian_signals": [], "timestamp": self.now}
        
        # Get company info for context
        try:
            from skills.yfinance_utils import safe_yf_info
            info = safe_yf_info(ticker)
        except Exception:
            info = {}
        
        # 1. Short interest analysis
        short_pct = info.get("shortPercentOfFloat", 0) or 0
        short_ratio = info.get("shortRatio", 0) or 0
        if short_pct > 0.10:
            findings["contrarian_signals"].append({
                "type": "high_short_interest",
                "signal": f"Short interest: {short_pct*100:.1f}% of float, ratio: {short_ratio:.1f}",
                "severity": "high" if short_pct > 0.20 else "medium",
            })
        
        # 2. Insider selling
        try:
            from skills.financial_data_providers import get_insider_trades
            insider = self._safe_call("insider_trades_contrarian", get_insider_trades, ticker, 20)
            if isinstance(insider, list):
                sells = [t for t in insider if isinstance(t, dict) and t.get("transactionType", "") in ["S", "Sale"]]
                buys = [t for t in insider if isinstance(t, dict) and t.get("transactionType", "") in ["P", "Purchase"]]
                if len(sells) > len(buys) * 2 and len(sells) >= 3:
                    findings["contrarian_signals"].append({
                        "type": "insider_selling",
                        "signal": f"Heavy insider selling: {len(sells)} sells vs {len(buys)} buys in 90 days",
                        "severity": "high" if len(sells) > len(buys) * 4 else "medium",
                    })
        except Exception:
            pass
        
        # 3. Deteriorating fundamentals check
        revenue_growth = info.get("revenueGrowth", 0) or 0
        earnings_growth = info.get("earningsGrowth", 0) or 0
        profit_margin = info.get("profitMargins", 0) or 0
        declining = []
        if revenue_growth < 0:
            declining.append(f"revenue declining ({revenue_growth*100:.1f}%)")
        if earnings_growth < -0.1:
            declining.append(f"earnings declining ({earnings_growth*100:.1f}%)")
        if profit_margin < 0:
            declining.append("negative profit margin")
        if len(declining) >= 2:
            findings["contrarian_signals"].append({
                "type": "deteriorating_fundamentals",
                "signal": f"Deteriorating: {', '.join(declining)}",
                "severity": "high" if len(declining) >= 3 else "medium",
            })
        
        # 4. Valuation risk — quality-aware
        # High-quality growth stocks deserve premium valuations.
        # Only flag as risky if valuation is extreme AND fundamentals don't justify it.
        pe = info.get("trailingPE", 0) or 0
        forward_pe = info.get("forwardPE", 0) or 0
        pb = info.get("priceToBook", 0) or 0
        rev_growth = info.get("revenueGrowth", 0) or 0
        roe = info.get("returnOnEquity", 0) or 0
        
        # Assess if the premium is justified by quality
        _is_high_quality = (rev_growth > 0.15 and roe > 0.15)
        _is_extreme_pe = pe > 100 or (forward_pe > 80 and forward_pe > 0)
        _is_moderate_pe = pe > 50 or (forward_pe > 40 and forward_pe > 0)
        
        if _is_extreme_pe:
            # Even for quality stocks, extreme P/E is a risk
            findings["contrarian_signals"].append({
                "type": "expensive_valuation",
                "signal": f"Extreme valuation: P/E {pe:.0f}, Forward P/E {forward_pe:.0f}, P/B {pb:.1f} — even quality stocks can correct at these levels",
                "severity": "medium",
            })
        elif _is_moderate_pe and not _is_high_quality:
            # Moderate P/E is only risky if fundamentals don't justify it
            findings["contrarian_signals"].append({
                "type": "expensive_valuation",
                "signal": f"Rich valuation without quality backing: P/E {pe:.0f}, Rev Growth {rev_growth*100:.0f}%, ROE {roe*100:.0f}%",
                "severity": "medium",
            })
        # If high quality + moderate P/E: NO penalty — this is what we want to own
        
        # 5. Balance sheet risk
        debt_to_equity = info.get("debtToEquity", 0) or 0
        current_ratio = info.get("currentRatio", 0) or 0
        if debt_to_equity > 100:
            findings["contrarian_signals"].append({
                "type": "high_leverage",
                "signal": f"High leverage: D/E {debt_to_equity:.0f}, Current ratio {current_ratio:.1f}",
                "severity": "high" if debt_to_equity > 200 else "medium",
            })
        
        # 6. Price position risk
        price = info.get("currentPrice", 0) or info.get("regularMarketPrice", 0) or 0
        high52 = info.get("fiftyTwoWeekHigh", 0) or 0
        low52 = info.get("fiftyTwoWeekLow", 0) or 0
        if price > 0 and high52 > 0 and low52 > 0:
            position_in_range = (price - low52) / (high52 - low52) if high52 > low52 else 0.5
            if position_in_range > 0.95:
                findings["contrarian_signals"].append({
                    "type": "near_highs",
                    "signal": f"Trading near 52-week high: ${price:.2f} vs high ${high52:.2f} ({position_in_range*100:.0f}% of range)",
                    "severity": "low",
                })
            elif position_in_range < 0.10:
                findings["contrarian_signals"].append({
                    "type": "near_lows",
                    "signal": f"Trading near 52-week low: ${price:.2f} vs low ${low52:.2f} — potential value trap or falling knife",
                    "severity": "medium",
                })
        
        # 7. News sentiment (negative search)
        try:
            from skills.news_research import tavily_search
            neg_news = self._safe_call("negative_news", tavily_search, f"{ticker} stock risks concerns problems challenges", 3)
            if neg_news and len(neg_news) > 100:
                findings["data"]["negative_news"] = neg_news[:500]
        except Exception:
            pass
        
        # 8. Risk assessment from stock_analyzer
        try:
            from skills.stock_analyzer import get_risk_assessment
            risk = self._safe_call("risk_assessment", get_risk_assessment, ticker)
            if risk:
                findings["data"]["risk_assessment"] = risk
        except Exception:
            pass
        
        # Summarize bear risk
        high_risk = sum(1 for s in findings["contrarian_signals"] if s.get("severity") == "high")
        med_risk = sum(1 for s in findings["contrarian_signals"] if s.get("severity") == "medium")
        findings["data"]["bear_risk_score"] = min(10, high_risk * 3 + med_risk)
        
        return findings
    
    # ═══════════════════════════════════════════════════════════════════
    # LAYER 7: Temporal Evolution
    # ═══════════════════════════════════════════════════════════════════
    
    def _layer7_temporal(self, ticker):
        """Layer 7: Thesis history, change detection, fact freshness."""
        self._log(f"  L7: Temporal evolution for {ticker}")
        findings = {"layer": 7, "data": {}, "facts": [], "timestamp": self.now}
        
        # Load research memory
        try:
            from skills.research_memory import get_memory
            mem = get_memory()
            
            # Get existing research summary
            summary = mem.get_ticker_summary(ticker, max_chars=1000)
            findings["data"]["research_memory"] = summary
            
            # Detect changes
            from skills.yfinance_utils import safe_yf_price
            price_data = safe_yf_price(ticker)
            if price_data:
                changes = mem.detect_changes(ticker, new_price=price_data.get("price"))
                findings["data"]["changes"] = changes
            
            # Get research gaps
            gaps = mem.get_research_gaps(ticker)
            findings["data"]["research_gaps"] = gaps
            
            # Get thesis journal
            from skills.thesis_journal import get_insights, get_journal
            insights = get_insights()
            if insights and "message" not in insights:
                findings["data"]["thesis_insights"] = insights
            
        except Exception as e:
            self._errors.append(f"temporal: {e}")
        
        # Earnings momentum
        try:
            from skills.earnings_intelligence import analyze_earnings_momentum
            momentum = self._safe_call("earnings_momentum", analyze_earnings_momentum, ticker)
            if momentum:
                findings["data"]["earnings_momentum"] = momentum
        except Exception:
            pass
        
        return findings
    
    # ═══════════════════════════════════════════════════════════════════
    # ORCHESTRATION: Deep Dive & Quick Update
    # ═══════════════════════════════════════════════════════════════════
    
    def deep_dive(self, ticker, layers=None):
        """
        Perform deep research on a ticker.
        
        Args:
            ticker: Stock symbol
            layers: List of layer numbers to run (default: all 7)
        
        Returns:
            dict with all research findings, facts, contrarian signals
        """
        ticker = ticker.upper()
        self._log(f"Starting deep dive on {ticker}")
        
        if layers is None:
            layers = [1, 2, 3, 4, 5, 6, 7]
        
        result = {
            "ticker": ticker,
            "timestamp": self.now,
            "layers_run": [],
            "data": {},
            "facts": [],
            "catalysts": [],
            "contrarian_signals": [],
            "risks": [],
            "sources_used": [],
            "errors": [],
            "research_depth": 0,
        }
        
        layer_funcs = {
            1: self._layer1_quant_screen,
            2: self._layer2_financial_deep_dive,
            3: self._layer3_competitive,
            4: self._layer4_management,
            5: self._layer5_macro_sector,
            6: self._layer6_contrarian,
            7: self._layer7_temporal,
        }
        
        for layer_num in layers:
            func = layer_funcs.get(layer_num)
            if func:
                try:
                    layer_result = func(ticker)
                    result["layers_run"].append(layer_num)
                    if layer_result:
                        # Merge data
                        if layer_result.get("data"):
                            result["data"].update(layer_result["data"])
                        # Collect facts
                        if layer_result.get("facts"):
                            result["facts"].extend(layer_result["facts"])
                        # Collect contrarian signals
                        if layer_result.get("contrarian_signals"):
                            result["contrarian_signals"].extend(layer_result["contrarian_signals"])
                except Exception as e:
                    self._errors.append(f"layer{layer_num}: {e}")
        
        # Calculate research depth score based on actual meaningful data gathered
        _depth_score = 0
        if result["data"].get("price", {}).get("price", 0) > 0:
            _depth_score += 1  # L1: Price data
        if result["data"].get("dcf") or result["data"].get("financial_statements"):
            _depth_score += 1  # L2: Financials/DCF
        if result["data"].get("competitive_landscape") or result["data"].get("peer_comparison"):
            _depth_score += 1  # L3: Competitive
        if result["data"].get("insider_trades") or result["data"].get("institutional_ownership"):
            _depth_score += 1  # L4: Smart money
        if result["data"].get("sector_performance") or result["data"].get("technicals"):
            _depth_score += 1  # L5: Macro/sector/technical
        if result["contrarian_signals"]:
            _depth_score += 1  # L6: Contrarian
        if result["data"].get("changes") or result["data"].get("research_memory"):
            _depth_score += 1  # L7: Temporal/memory
        
        result["research_depth"] = _depth_score
        result["sources_used"] = list(self._sources_used)
        result["errors"] = self._errors
        
        # ── Extract meaningful catalysts from all gathered data ──
        _catalysts = []
        _info = result["data"].get("info", {})

        # Log what data we actually have
        data_keys = list(result["data"].keys())
        self._log(f"  Data collected: {', '.join(data_keys[:10])}")

        # From earnings/estimates
        if result["data"].get("analyst_estimates"):
            _catalysts.append("Analyst estimates available")
        else:
            self._log(f"    → No analyst_estimates")
        if result["data"].get("earnings_history"):
            _catalysts.append("Earnings history tracked")
        else:
            self._log(f"    → No earnings_history")
        
        # From competitive landscape
        if result["data"].get("competitive_landscape"):
            _comp = result["data"]["competitive_landscape"]
            if isinstance(_comp, dict):
                _moat = _comp.get("moat_assessment", {})
                if _moat.get("rating"):
                    _catalysts.append(f"Moat: {_moat['rating']}")
        
        # From insider/institutional activity
        if result["data"].get("insider_trades"):
            _ins = result["data"]["insider_trades"]
            if isinstance(_ins, list) and len(_ins) > 0:
                _catalysts.append(f"{len(_ins)} insider transactions found")
        
        # From sector/macro
        if result["data"].get("sector_performance"):
            _catalysts.append("Sector performance analyzed")
        
        # From DCF
        if result["data"].get("dcf"):
            _dcf = result["data"]["dcf"]
            if isinstance(_dcf, dict) and _dcf.get("fair_value"):
                _catalysts.append(f"DCF fair value: ${_dcf['fair_value']:.2f}")
        
        # ── Build investment thesis from gathered data ──
        _thesis_parts = []
        if _info.get("sector"):
            _thesis_parts.append(f"{ticker} operates in {_info['sector']}")
        else:
            self._log(f"  [DEBUG] No sector data for {ticker}")
        if _info.get("revenueGrowth"):
            growth = float(_info["revenueGrowth"]) * 100
            _thesis_parts.append(f"{growth:.0f}% revenue growth")
        if _info.get("roe"):
            roe = float(_info["roe"]) * 100
            _thesis_parts.append(f"{roe:.0f}% ROE")
        if _info.get("recommendation"):
            _thesis_parts.append(f"Analyst: {_info['recommendation']}")

        if not _thesis_parts:
            self._log(f"  [DEBUG] No thesis parts built — info keys: {list(_info.keys())[:10]}")
        
        _thesis = " | ".join(_thesis_parts) if _thesis_parts else ""
        
        # ── Extract risks from contrarian analysis ──
        _risks = []
        for _sig in result.get("contrarian_signals", []):
            if isinstance(_sig, dict):
                _risk = _sig.get("signal", "")
                _sev = _sig.get("severity", "medium")
                _risks.append(f"[{_sev}] {_risk}")
        
        # ── Determine conviction based on data quality ──
        _conviction = 5  # Default neutral
        if _depth_score >= 6 and len(_catalysts) >= 3:
            _conviction = 8
        elif _depth_score >= 5 and len(_catalysts) >= 2:
            _conviction = 7
        elif _depth_score >= 4:
            _conviction = 6
        if _risks:
            _conviction = max(3, _conviction - 1)  # Reduce conviction if risks found
        
        # ── Save comprehensive research to memory ──
        try:
            from skills.research_memory import get_memory
            mem = get_memory()
            price = result["data"].get("price", {}).get("price", 0)

            # Debug: check what data we actually collected
            self._log(f"[DEBUG] result['data'] keys: {list(result['data'].keys())}")
            for key in result["data"]:
                val = result["data"][key]
                if isinstance(val, dict):
                    self._log(f"  {key}: dict with {len(val)} keys")
                elif isinstance(val, list):
                    self._log(f"  {key}: list with {len(val)} items")
                else:
                    self._log(f"  {key}: {type(val).__name__}")

            # Debug: check types of parameters
            import pprint
            self._log(f"[DEBUG] Calling record_research with:")
            self._log(f"  ticker={ticker} (type: {type(ticker).__name__})")
            self._log(f"  facts={type(result['facts']).__name__} (len: {len(result['facts']) if isinstance(result['facts'], list) else 'N/A'})")
            if result["facts"] and isinstance(result["facts"], list) and len(result["facts"]) > 0:
                self._log(f"    first fact type: {type(result['facts'][0]).__name__}: {str(result['facts'][0])[:100]}")
            self._log(f"  catalysts={type(_catalysts).__name__}")
            self._log(f"  contrarian={type(result['contrarian_signals']).__name__} (len: {len(result['contrarian_signals']) if isinstance(result['contrarian_signals'], list) else 'N/A'})")

            mem.record_research(
                ticker,
                depth=_depth_score,
                facts=result["facts"],
                catalysts=_catalysts if _catalysts else None,
                thesis=_thesis if _thesis else None,
                conviction=_conviction,
                price=price,
                risks=_risks if _risks else None,
                contrarian=result["contrarian_signals"] if result["contrarian_signals"] else None,
                competitive=result["data"].get("competitive_landscape"),
                sources=result["sources_used"],
            )
            self._log(f"✅ Research saved to memory")
        except Exception as e:
            import traceback
            self._log(f"⚠️ Failed to save research to memory: {e}")
            self._log(f"[DEBUG] Traceback:\n{traceback.format_exc()}")
        
        self._log(f"Deep dive complete: depth={_depth_score}/7, facts={len(result['facts'])}, catalysts={len(_catalysts)}, risks={len(_risks)}")
        
        self._research_findings[ticker] = result
        return result
    
    def quick_update(self, ticker):
        """
        Quick update — only research what's changed since last run.
        Much faster than deep_dive, suitable for alerts-only mode.
        """
        ticker = ticker.upper()
        self._log(f"Quick update for {ticker}")
        
        # Check research memory for what needs updating
        try:
            from skills.research_memory import get_memory
            mem = get_memory()
            
            if not mem.needs_research(ticker, min_depth=3, max_age_hours=6):
                self._log(f"  {ticker} research is fresh, skipping")
                return {"ticker": ticker, "skipped": True, "reason": "research_fresh"}
            
            gaps = mem.get_research_gaps(ticker)
            self._log(f"  Gaps: {gaps[:5]}")
        except Exception:
            gaps = []
        
        # Always do Layer 1 (price) and Layer 6 (contrarian/risk)
        layers = [1, 6]
        
        # Add layers based on gaps
        if any("fundamental" in g or "earnings" in g for g in gaps):
            layers.append(2)
        if any("peer" in g or "competitive" in g for g in gaps):
            layers.append(3)
        if any("insider" in g or "institutional" in g for g in gaps):
            layers.append(4)
        if any("sector" in g or "macro" in g for g in gaps):
            layers.append(5)
        
        layers = list(set(layers))
        return self.deep_dive(ticker, layers=layers)
    
    def research_batch(self, tickers, max_depth=5, max_tickers=5):
        """
        Research multiple tickers, prioritized by research memory.
        Returns results sorted by research depth achieved.
        """
        # Prioritize
        try:
            from skills.research_memory import get_memory
            mem = get_memory()
            queue = mem.get_research_queue(tickers, min_depth=max_depth, max_per_run=max_tickers)
        except Exception:
            queue = tickers[:max_tickers]
        
        results = []
        for ticker in queue:
            if max_depth >= 7:
                result = self.deep_dive(ticker)
            else:
                result = self.quick_update(ticker)
            results.append(result)
        
        return results
    
    # ═══════════════════════════════════════════════════════════════════
    # LLM CONTEXT GENERATION
    # ═══════════════════════════════════════════════════════════════════
    
    def get_llm_context(self, ticker, max_chars=3000):
        """
        Generate a comprehensive, well-structured context string for the LLM
        to make investment decisions. This is the KEY output — it feeds into
        the investment ideas generation.
        """
        # Check if we already researched this ticker in this run
        if ticker.upper() in self._research_findings:
            result = self._research_findings[ticker.upper()]
        else:
            result = self.deep_dive(ticker)
        
        lines = []
        lines.append(f"# Deep Research: {ticker.upper()}")
        lines.append(f"Research depth: {result.get('research_depth', 0)}/7 layers | {len(result.get('facts', []))} facts verified")
        lines.append("")
        
        # Price & valuation
        price_data = result.get("data", {}).get("price", {})
        info = result.get("data", {}).get("info", {})
        if price_data:
            lines.append(f"## Price & Valuation")
            lines.append(f"- Current: ${price_data.get('price', 0):.2f} ({price_data.get('change_pct', 0):+.2f}%)")
            lines.append(f"- Source: {price_data.get('source', 'unknown')}")
            if info:
                lines.append(f"- P/E: {info.get('pe_ratio', 'N/A')} | Forward P/E: {info.get('forward_pe', 'N/A')}")
                lines.append(f"- P/B: {info.get('price_to_book', 'N/A')} | EV/EBITDA: {info.get('ev_to_ebitda', 'N/A')}")
                lines.append(f"- Market Cap: ${info.get('market_cap', 0):,.0f}")
                lines.append(f"- Sector: {info.get('sector', 'N/A')} | Industry: {info.get('industry', 'N/A')}")
                lines.append(f"- Beta: {info.get('beta', 'N/A')} | 52w Range: ${info.get('fifty_two_week_low', 0):.2f} - ${info.get('fifty_two_week_high', 0):.2f}")
            lines.append("")
        
        # Growth & profitability
        if info:
            lines.append(f"## Growth & Profitability")
            lines.append(f"- Revenue Growth: {info.get('revenue_growth', 0)*100:.1f}%")
            lines.append(f"- Earnings Growth: {info.get('earnings_growth', 0)*100:.1f}%")
            lines.append(f"- ROE: {info.get('roe', 0)*100:.1f}% | ROA: {info.get('roa', 0)*100:.1f}%")
            lines.append(f"- Profit Margin: {info.get('profit_margin', 0)*100:.1f}% | Operating Margin: {info.get('operating_margin', 0)*100:.1f}%")
            lines.append(f"- FCF: ${info.get('free_cash_flow', 0):,.0f}")
            lines.append(f"- D/E: {info.get('debt_to_equity', 'N/A')} | Current Ratio: {info.get('current_ratio', 'N/A')}")
            lines.append("")
        
        # Analyst consensus
        pt_data = result.get("data", {}).get("price_target", {})
        estimates = result.get("data", {}).get("analyst_estimates", {})
        if pt_data or estimates:
            lines.append(f"## Analyst Consensus")
            if isinstance(pt_data, dict):
                lines.append(f"- Target: ${pt_data.get('targetMeanPrice', 'N/A')} (Low: ${pt_data.get('targetLowPrice', 'N/A')}, High: ${pt_data.get('targetHighPrice', 'N/A')})")
                lines.append(f"- Analysts: {pt_data.get('numberOfAnalystOpinions', 'N/A')} | Recommendation: {pt_data.get('recommendationKey', 'N/A')}")
            lines.append("")
        
        # Earnings
        earnings_hist = result.get("data", {}).get("earnings_history", [])
        if earnings_hist:
            lines.append(f"## Earnings History")
            if isinstance(earnings_hist, list):
                for e in earnings_hist[:4]:
                    if isinstance(e, dict):
                        surprise = e.get("surprisePercent", 0)
                        emoji = "✅" if surprise > 0 else "❌" if surprise < 0 else "➡️"
                        lines.append(f"- {emoji} Q{e.get('quarter', '?')} {e.get('year', '?')}: EPS est ${e.get('estimate', 0):.2f} vs actual ${e.get('actual', 0):.2f} ({surprise:+.1f}%)")
            lines.append("")
        
        # DCF
        dcf = result.get("data", {}).get("dcf", {})
        if dcf and isinstance(dcf, dict):
            lines.append(f"## DCF Valuation")
            fair = dcf.get("fair_value") or dcf.get("dcf_value") or dcf.get("price")
            current = dcf.get("current_price", 0)
            if fair and current:
                upside = (fair - current) / current * 100
                lines.append(f"- Fair Value: ${fair:.2f} | Current: ${current:.2f} | Upside: {upside:+.1f}%")
            wacc = dcf.get("wacc", 0)
            tg = dcf.get("terminal_growth", 0)
            if wacc:
                lines.append(f"- WACC: {wacc*100:.1f}% | Terminal Growth: {tg*100:.1f}%" if tg else f"- WACC: {wacc*100:.1f}%")
            lines.append("")
        
        # Smart money
        smart_money = result.get("data", {}).get("smart_money", {})
        insider = result.get("data", {}).get("insider_trades", [])
        inst = result.get("data", {}).get("institutional_ownership", {})
        if smart_money or insider or inst:
            lines.append(f"## Smart Money Activity")
            if isinstance(insider, list):
                buys = sum(1 for t in insider if isinstance(t, dict) and t.get("transactionType", "") in ["P", "Purchase"])
                sells = sum(1 for t in insider if isinstance(t, dict) and t.get("transactionType", "") in ["S", "Sale"])
                lines.append(f"- Insider (90d): {buys} buys, {sells} sells")
            if isinstance(smart_money, dict):
                sentiment = smart_money.get("insider_sentiment", {})
                if isinstance(sentiment, dict):
                    mspr = sentiment.get("mspr", 0)
                    lines.append(f"- Insider Sentiment (MSPR): {mspr:+.2f} ({'bullish' if mspr > 0 else 'bearish' if mspr < 0 else 'neutral'})")
                recs = smart_money.get("analyst_recommendations", {})
                if isinstance(recs, dict):
                    lines.append(f"- Analyst: {recs.get('strongBuy', 0)} strong buy, {recs.get('buy', 0)} buy, {recs.get('hold', 0)} hold, {recs.get('sell', 0)} sell")
            lines.append("")
        
        # Competitive
        comp = result.get("data", {}).get("competitive_landscape", {})
        peers = result.get("data", {}).get("peer_comparison", {})
        if comp or peers:
            lines.append(f"## Competitive Position")
            if isinstance(comp, dict):
                moat = comp.get("moat_assessment", {})
                if moat:
                    lines.append(f"- Moat: {moat.get('rating', 'N/A')} — {moat.get('description', '')}")
            lines.append("")
        
        # Sector & macro
        rotation = result.get("data", {}).get("rotation", {})
        sentiment = result.get("data", {}).get("market_sentiment", {})
        if rotation or sentiment:
            lines.append(f"## Macro & Sector Context")
            if isinstance(rotation, dict):
                macro = rotation.get("macro_signals", {})
                if isinstance(macro, dict):
                    lines.append(f"- Macro: {macro.get('signal', 'N/A')} ({macro.get('detail', '')})")
            lines.append("")
        
        # Technicals
        tech = result.get("data", {}).get("technicals", {})
        if tech:
            lines.append(f"## Technical Position")
            indicators = tech.get("indicators", {}) or {}
            agg = tech.get("aggregate", {}) or {}
            if isinstance(indicators, dict):
                rsi = indicators.get("rsi", 0)
                if rsi:
                    lines.append(f"- RSI: {rsi:.0f} ({'overbought' if rsi > 70 else 'oversold' if rsi < 30 else 'neutral'})")
            if isinstance(agg, dict):
                rec = agg.get("recommendation", "")
                if rec:
                    lines.append(f"- Aggregate: {rec}")
            lines.append("")
        
        # ⚠️ CONTRARIAN SIGNALS (critical for balanced decision-making)
        contrarian = result.get("contrarian_signals", [])
        if contrarian:
            lines.append(f"## ⚠️ Contrarian Signals / Bear Case ({len(contrarian)} signals)")
            for sig in contrarian:
                emoji = "🔴" if sig.get("severity") == "high" else "🟡" if sig.get("severity") == "medium" else "🟢"
                lines.append(f"- {emoji} [{sig.get('type', '?')}] {sig.get('signal', '')}")
            lines.append("")
        
        # Key verified facts
        facts = result.get("facts", [])
        if facts:
            lines.append(f"## Key Verified Facts")
            for f in facts[:10]:
                lines.append(f"- {f.get('claim', '')}")
            lines.append("")
        
        # Research memory
        memory = result.get("data", {}).get("research_memory", "")
        if memory:
            lines.append(f"## Research Memory")
            lines.append(memory[:500])
            lines.append("")
        
        # Changes since last research
        changes = result.get("data", {}).get("changes", {})
        if changes and changes.get("price_moved"):
            lines.append(f"## Changes Since Last Research")
            lines.append(f"- Price moved: {changes.get('price_change_pct', 0):+.1f}%")
            if changes.get("new_catalysts"):
                lines.append(f"- New catalysts: {', '.join(changes['new_catalysts'])}")
            if changes.get("thesis_stale"):
                lines.append(f"- ⚠️ Thesis is stale (>14 days old)")
            lines.append("")
        
        # Data quality
        lines.append(f"## Data Quality")
        lines.append(f"- Sources used: {', '.join(result.get('sources_used', []))}")
        lines.append(f"- Layers researched: {result.get('layers_run', [])}")
        if result.get("errors"):
            lines.append(f"- Errors ({len(result['errors'])}): {', '.join(result['errors'][:3])}")
        
        result_str = "\n".join(lines)
        if len(result_str) > max_chars:
            result_str = result_str[:max_chars] + "\n... [truncated — use deep_dive() for full data]"
        
        return result_str


# ═══════════════════════════════════════════════════════════════════════
# Module-level convenience functions
# ═══════════════════════════════════════════════════════════════════════

_researcher = None

def get_researcher(verbose=True):
    global _researcher
    if _researcher is None:
        _researcher = DeepResearcher(verbose=verbose)
    return _researcher

def deep_dive(ticker, layers=None):
    return get_researcher().deep_dive(ticker, layers=layers)

def quick_update(ticker):
    return get_researcher().quick_update(ticker)

def research_batch(tickers, max_depth=5, max_tickers=5):
    return get_researcher().research_batch(tickers, max_depth, max_tickers)

def get_llm_context(ticker, max_chars=3000):
    return get_researcher().get_llm_context(ticker, max_chars)
