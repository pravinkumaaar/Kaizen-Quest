"""
Smart Money Tracker Skill v1.0

Tracks where sophisticated investors are putting their money:
1. Hedge Fund Holdings (13F filings via SEC EDGAR)
2. Congressional Trading (Capitol Trades scraping)
3. Insider Trading (OpenInsider scraping)
4. Institutional Ownership (yfinance)

All data sources are FREE. No paid APIs required.

Usage:
    from skills.smart_money_tracker import (
        get_hedge_fund_top_holdings,
        get_congressional_trades,
        get_insider_trades,
        get_institutional_ownership,
        get_smart_money_summary,
        generate_smart_money_report
    )
"""

import requests
import json
import datetime
import time
import re
from pathlib import Path
from io import StringIO

BASE_DIR = Path(__file__).parent.parent
FINNHUB_API_KEY = None

# ── Known hedge fund CIKs for 13F tracking ──
# These are the most influential funds whose trades move markets
KNOWN_HEDGE_FUNDS = {
    "0001062909": "Vanguard Group",
    "0001166559": "Berkshire Hathaway",
    "0001336528": "Bridgewater Associates",
    "0001037389": "Renaissance Technologies",
    "0001135778": "Two Sigma Investments",
    "0001397545": "Citadel Advisors",
    "0001555283": "Millennium Management",
    "0001423053": "Elliott Management",
    "0001536433": "Third Point",
    "0001649339": "Pershing Square",
    "0001350694": "ValueAct Capital",
    "0001491028": "Coatue Management",
    "0001517139": "Tiger Global",
    "0001603145": "Baupost Group",
    "0001048423": "D.E. Shaw",
}

# ── Sector ETF mapping for sector analysis ──
SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financial",
    "XLV": "Healthcare",
    "XLE": "Energy",
    "XLI": "Industrial",
    "XLC": "Communication",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLU": "Utilities",
    "XLRE": "Real Estate",
    "XLB": "Materials",
}

# ── Sub-sector / thematic tickers for deep analysis ──
SUBSECTOR_TICKERS = {
    "Semiconductors": ["NVDA", "AVGO", "MRVL", "MU", "WDC", "ON", "MCHP", "ADI", "TXN", "QCOM", "AMD", "INTC", "AMAT", "LRCX", "KLAC", "TER", "ENTG", "MKSI", "ACLS", "CCMP"],
    "Memory_HBM": ["MU", "WDC", "SK HYNIX", "STX", "NTAP", "SMCI", "DELL"],
    "AI_Infrastructure": ["NVDA", "AVGO", "MRVL", "SMCI", "DELL", "HPE", "ANET", "CIEN", "LITE", "AAOI", "COHR", "IIVI"],
    "Cloud_Computing": ["MSFT", "AMZN", "GOOGL", "CRM", "NOW", "SNOW", "NET", "DDOG", "MDB", "PLTR"],
    "Cybersecurity": ["CRWD", "PANW", "ZS", "FTNT", "OKTA", "CYBR", "QLYS", "TENB", "VRNS", "SAIL"],
    "Fintech": ["V", "MA", "PYPL", "SQ", "COIN", "HOOD", "AFRM", "NU", "SOFI", "TOST"],
    "Biotech_Genomics": ["ILMN", "CRSP", "EDIT", "NTLA", "BEAM", "VRTX", "REGN", "BIIB", "GILD", "AMGN"],
    "CleanEnergy": ["ENPH", "SEDG", "FSLR", "NEE", "ICLN", "QCLN", "PBW", "TAN", "SMOG", "ACES"],
    "Defense_Aerospace": ["LMT", "RTX", "NOC", "GD", "BA", "HII", "LHX", "KTOS", "RDRBY", "AXON"],
    "Robotics_Automation": ["ISRO", "FANUC", "ABB", "ROK", "EMR", "OTIS", "Symbotic", "PATH", "AI", "PLTR"],
}


def init_smart_money_skill(finnhub_key=None, base_dir=None):
    """Initialize with API keys."""
    global FINNHUB_API_KEY, BASE_DIR
    if finnhub_key:
        FINNHUB_API_KEY = finnhub_key
    if base_dir:
        BASE_DIR = Path(base_dir)


# ═══════════════════════════════════════════════════════════════
# 1. HEDGE FUND TRACKING (13F Filings via SEC EDGAR)
# ═══════════════════════════════════════════════════════════════

def get_hedge_fund_top_holdings(num_funds=5, top_n=10):
    """
    Get top holdings from major hedge funds via SEC EDGAR 13F filings.
    Uses the SEC submissions API to find latest 13F filings.
    
    Args:
        num_funds: Number of hedge funds to check (max 15)
        top_n: Number of top holdings to return per fund
    
    Returns:
        dict: {fund_name: {"holdings": [...], "filing_date": "...", "value": ...}}
    """
    results = {}
    headers = {
        "User-Agent": "KaizenQuestAgent research@kaizenquest.ai"
    }
    
    fund_items = list(KNOWN_HEDGE_FUNDS.items())[:num_funds]
    
    for cik, fund_name in fund_items:
        try:
            # Get submissions for this CIK
            url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
            r = requests.get(url, headers=headers, timeout=15)
            
            if r.status_code != 200:
                continue
            
            data = r.json()
            recent = data.get("filings", {}).get("recent", {})
            forms = recent.get("form", [])
            dates = recent.get("filingDate", [])
            accession = recent.get("accessionNumber", [])
            primary_doc = recent.get("primaryDocument", [])
            
            # Find latest 13F-HR filing
            filing_idx = None
            for i, form in enumerate(forms):
                if form in ("13F-HR", "13F-HR/A"):
                    filing_idx = i
                    break
            
            if filing_idx is None:
                continue
            
            filing_date = dates[filing_idx]
            acc_num = accession[filing_idx].replace("-", "")
            doc = primary_doc[filing_idx]
            
            # Get the 13F holdings XML
            holdings_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{acc_num}/{doc}"
            
            # Try to get the infotable.xml which contains parsed holdings
            infotable_url = holdings_url.replace(".htm", "_infotable.xml").replace(".txt", "_infotable.xml")
            
            try:
                r2 = requests.get(infotable_url, headers=headers, timeout=15)
                if r2.status_code == 200:
                    holdings = _parse_13f_xml(r2.text, top_n)
                    if holdings:
                        results[fund_name] = {
                            "holdings": holdings,
                            "filing_date": filing_date,
                            "cik": cik,
                        }
                        continue
            except Exception:
                pass
            
            # Fallback: try the main filing page
            try:
                r3 = requests.get(holdings_url, headers=headers, timeout=15)
                if r3.status_code == 200:
                    holdings = _parse_13f_html(r3.text, top_n)
                    if holdings:
                        results[fund_name] = {
                            "holdings": holdings,
                            "filing_date": filing_date,
                            "cik": cik,
                        }
            except Exception:
                pass
            
            time.sleep(0.15)  # SEC rate limit: 10 req/sec
            
        except Exception:
            continue
    
    return results


def _parse_13f_xml(xml_text, top_n=10):
    """Parse 13F infotable XML to extract top holdings."""
    holdings = []
    try:
        import xml.etree.ElementTree as ET
        root = ET.fromstring(xml_text)
        for info in root.findall('.//infoTable')[:top_n]:
            name = info.findtext('nameOfIssuer', '')
            value = info.findtext('value', '0')
            shares = info.findtext('sshPrnamt', '0')
            share_type = info.findtext('sshPrnamtType', '')
            if name:
                holdings.append({
                    "name": name,
                    "value_thousands": int(value) if value.isdigit() else 0,
                    "shares": int(shares) if shares.isdigit() else 0,
                    "type": share_type,
                })
    except Exception:
        pass
    return holdings


def _parse_13f_html(html_text, top_n=10):
    """Parse 13F HTML filing to extract top holdings."""
    holdings = []
    try:
        # Look for table rows with holding data
        # 13F filings have a standard table structure
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html_text, re.DOTALL | re.IGNORECASE)
        for row in rows[:top_n + 5]:  # +5 to skip header rows
            cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL | re.IGNORECASE)
            if len(cells) >= 3:
                name = re.sub(r'<[^>]+>', '', cells[0]).strip()
                if name and len(name) > 2 and not name.lower().startswith('name'):
                    holdings.append({
                        "name": name,
                        "value_thousands": 0,
                        "shares": 0,
                        "type": "",
                    })
    except Exception:
        pass
    return holdings[:top_n]


def get_hedge_fund_consensus(num_funds=8):
    """
    Get consensus holdings across major hedge funds.
    Returns stocks held by multiple funds with aggregate values.
    """
    all_holdings = get_hedge_fund_top_holdings(num_funds=num_funds, top_n=15)
    
    # Aggregate by stock name
    consensus = {}
    for fund_name, data in all_holdings.items():
        for h in data["holdings"]:
            name = h["name"]
            if name not in consensus:
                consensus[name] = {
                    "funds_owning": [],
                    "total_value": 0,
                    "count": 0,
                }
            consensus[name]["funds_owning"].append(fund_name)
            consensus[name]["total_value"] += h.get("value_thousands", 0)
            consensus[name]["count"] += 1
    
    # Sort by number of funds owning, then by total value
    sorted_consensus = sorted(
        consensus.items(),
        key=lambda x: (x[1]["count"], x[1]["total_value"]),
        reverse=True
    )
    
    return {
        "top_consensus": sorted_consensus[:20],
        "num_funds_analyzed": len(all_holdings),
        "total_stocks_tracked": len(consensus),
    }


# ═══════════════════════════════════════════════════════════════
# 2. CONGRESSIONAL TRADING TRACKING
# ═══════════════════════════════════════════════════════════════

def get_congressional_trades(days_back=30, min_value=10000):
    """
    Get recent congressional stock trades from Capitol Trades.
    Scrapes the public API/website for STOCK Act disclosures.
    
    Args:
        days_back: How many days back to look
        min_value: Minimum trade value to include
    
    Returns:
        list: Recent congressional trades
    """
    trades = []
    
    # Try Quiver Quantitative API first (free public endpoint)
    try:
        url = "https://api.quiverquant.com/v1/congresstrading"
        r = requests.get(url, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if isinstance(data, list):
                for trade in data[:50]:
                    try:
                        amount = _parse_congress_amount(trade.get("Amount", ""))
                        if amount >= min_value:
                            trades.append({
                                "politician": trade.get("Representative", trade.get("Senator", "Unknown")),
                                "party": trade.get("Party", ""),
                                "chamber": trade.get("Chamber", ""),
                                "ticker": trade.get("Ticker", ""),
                                "transaction": trade.get("Transaction", ""),
                                "amount": amount,
                                "amount_range": trade.get("Amount", ""),
                                "filed_date": trade.get("FilingDate", ""),
                                "trade_date": trade.get("TransactionDate", ""),
                            })
                    except Exception:
                        continue
    except Exception:
        pass
    
    # Fallback: Capitol Trades website
    if not trades:
        try:
            url = "https://www.capitoltrades.com/api/trades"
            r = requests.get(url, timeout=15)
            if r.status_code == 200:
                data = r.json()
                if isinstance(data, list):
                    for trade in data[:50]:
                        try:
                            amount = _parse_congress_amount(trade.get("amount", ""))
                            if amount >= min_value:
                                trades.append({
                                    "politician": trade.get("politician_name", "Unknown"),
                                    "party": trade.get("party", ""),
                                    "chamber": trade.get("chamber", ""),
                                    "ticker": trade.get("ticker", ""),
                                    "transaction": trade.get("type", ""),
                                    "amount": amount,
                                    "amount_range": trade.get("amount", ""),
                                    "filed_date": trade.get("filed_date", ""),
                                    "trade_date": trade.get("trade_date", ""),
                                })
                        except Exception:
                            continue
        except Exception:
            pass
    
    return trades


def _parse_congress_amount(amount_str):
    """Parse congressional trade amount string to numeric value."""
    if not amount_str:
        return 0
    amount_str = str(amount_str).strip()
    
    # Handle ranges like "$15,001 - $50,000"
    if "-" in amount_str:
        parts = amount_str.split("-")
        # Take the average of the range
        vals = []
        for p in parts:
            nums = re.findall(r'[\d,]+', p)
            if nums:
                vals.append(float(nums[0].replace(",", "")))
        return sum(vals) / len(vals) if vals else 0
    
    # Handle single values
    nums = re.findall(r'[\d,]+', amount_str)
    if nums:
        return float(nums[0].replace(",", ""))
    return 0


def get_congressional_top_trades(trades=None, top_n=10):
    """Get the most significant congressional trades."""
    if trades is None:
        trades = get_congressional_trades()
    
    # Filter to buys only (more signal than sells)
    buys = [t for t in trades if t.get("transaction", "").lower() in ("buy", "purchase")]
    
    # Sort by amount
    buys.sort(key=lambda x: x.get("amount", 0), reverse=True)
    
    # Aggregate by ticker
    ticker_scores = {}
    for t in buys:
        ticker = t.get("ticker", "")
        if not ticker:
            continue
        if ticker not in ticker_scores:
            ticker_scores[ticker] = {
                "ticker": ticker,
                "num_politicians": 0,
                "total_amount": 0,
                "politicians": [],
            }
        ticker_scores[ticker]["num_politicians"] += 1
        ticker_scores[ticker]["total_amount"] += t.get("amount", 0)
        ticker_scores[ticker]["politicians"].append(t.get("politician", ""))
    
    sorted_tickers = sorted(
        ticker_scores.values(),
        key=lambda x: (x["num_politicians"], x["total_amount"]),
        reverse=True
    )
    
    return {
        "top_buys": buys[:top_n],
        "ticker_consensus": sorted_tickers[:top_n],
        "total_trades": len(trades),
        "total_buys": len(buys),
    }


# ═══════════════════════════════════════════════════════════════
# 3. INSIDER TRADING TRACKING
# ═══════════════════════════════════════════════════════════════

def get_insider_trades(ticker=None, days_back=30, min_value=50000):
    """
    Get recent insider trading activity.
    Uses OpenInsider.com for structured data.
    
    Args:
        ticker: Specific ticker to check, or None for market-wide
        days_back: How many days back to look
        min_value: Minimum trade value
    
    Returns:
        list: Recent insider trades
    """
    trades = []
    
    try:
        if ticker:
            url = f"http://openinsider.com/screener?s={indicator}&o=&pl=&ph=&ll=&lh=&fd={days_back}&fdr=&td=0&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&xs=1&vl={min_value}&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&count=100&page=1"
        else:
            url = f"http://openinsider.com/screener?s=&o=&pl=&ph=&ll=&lh=&fd={days_back}&fdr=&td=0&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&xs=1&vl={min_value}&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&grp=0&nfl=&nfh=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&count=100&page=1"
        
        headers = {"User-Agent": "Mozilla/5.0 (research bot)"}
        r = requests.get(url, headers=headers, timeout=15)
        
        if r.status_code == 200:
            trades = _parse_openinsider_html(r.text)
    except Exception:
        pass
    
    # Fallback: use yfinance for institutional ownership
    if not trades and ticker:
        try:
            import yfinance as yf
            old_stderr = __import__('sys').stderr
            __import__('sys').stderr = StringIO()
            try:
                t = yf.Ticker(ticker)
                holders = t.insider_transactions
                if holders is not None and len(holders) > 0:
                    for _, row in holders.head(20).iterrows():
                        trades.append({
                            "insider": row.get("insider", ""),
                            "relation": row.get("relation", ""),
                            "transaction": row.get("transaction", ""),
                            "shares": row.get("shares", 0),
                            "value": row.get("value", 0),
                            "date": str(row.get("startDate", "")),
                            "ticker": ticker,
                        })
            finally:
                __import__('sys').stderr = old_stderr
        except Exception:
            pass
    
    return trades


def _parse_openinsider_html(html_text):
    """Parse OpenInsider HTML table to extract insider trades."""
    trades = []
    try:
        # Find the main data table
        table_match = re.search(r'<table class="tinytable"[^>]*>(.*?)</table>', html_text, re.DOTALL)
        if not table_match:
            table_match = re.search(r'<table[^>]*id="insider"[^>]*>(.*?)</table>', html_text, re.DOTALL)
        if not table_match:
            # Try any table with insider data
            table_match = re.search(r'<table[^>]*>(.*?)</table>', html_text, re.DOTALL)
        
        if table_match:
            table_html = table_match.group(0)
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.DOTALL)
            
            for row in rows[1:]:  # Skip header
                cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL)
                if len(cells) >= 8:
                    # Clean HTML tags from cell values
                    clean_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
                    trades.append({
                        "date": clean_cells[0] if len(clean_cells) > 0 else "",
                        "ticker": clean_cells[1] if len(clean_cells) > 1 else "",
                        "insider": clean_cells[2] if len(clean_cells) > 2 else "",
                        "relation": clean_cells[3] if len(clean_cells) > 3 else "",
                        "transaction": clean_cells[4] if len(clean_cells) > 4 else "",
                        "shares": clean_cells[5] if len(clean_cells) > 5 else "",
                        "value": clean_cells[6] if len(clean_cells) > 6 else "",
                        "own_change": clean_cells[7] if len(clean_cells) > 7 else "",
                    })
    except Exception:
        pass
    return trades


def get_insider_summary(trades=None, top_n=10):
    """Summarize insider trading by ticker."""
    if trades is None:
        trades = get_insider_trades()
    
    ticker_summary = {}
    for t in trades:
        ticker = t.get("ticker", "")
        if not ticker:
            continue
        
        if ticker not in ticker_summary:
            ticker_summary[ticker] = {
                "ticker": ticker,
                "buys": 0,
                "sells": 0,
                "total_buy_value": 0,
                "total_sell_value": 0,
                "insiders": [],
            }
        
        txn = t.get("transaction", "").lower()
        value = t.get("value", 0) if isinstance(t.get("value"), (int, float)) else 0
        
        if "buy" in txn or "purchase" in txn:
            ticker_summary[ticker]["buys"] += 1
            ticker_summary[ticker]["total_buy_value"] += value
        elif "sell" in txn:
            ticker_summary[ticker]["sells"] += 1
            ticker_summary[ticker]["total_sell_value"] += value
        
        ticker_summary[ticker]["insiders"].append(t.get("insider", ""))
    
    # Calculate buy/sell ratio
    for ticker in ticker_summary:
        s = ticker_summary[ticker]
        s["buy_sell_ratio"] = s["buys"] / max(s["sells"], 1)
        s["net_activity"] = s["total_buy_value"] - s["total_sell_value"]
    
    # Sort by buy activity
    sorted_tickers = sorted(
        ticker_summary.values(),
        key=lambda x: (x["buy_sell_ratio"], x["total_buy_value"]),
        reverse=True
    )
    
    return {
        "top_insider_buys": sorted_tickers[:top_n],
        "total_trades": len(trades),
        "tickers_with_insider_activity": len(ticker_summary),
    }


# ═══════════════════════════════════════════════════════════════
# 4. INSTITUTIONAL OWNERSHIP TRACKING
# ═══════════════════════════════════════════════════════════════

def get_institutional_ownership(ticker):
    """
    Get institutional ownership data for a ticker via yfinance.
    
    Returns:
        dict: Institutional ownership details
    """
    try:
        import yfinance as yf
        old_stderr = __import__('sys').stderr
        __import__('sys').stderr = StringIO()
        try:
            t = yf.Ticker(ticker)
            info = t.info
            
            return {
                "ticker": ticker,
                "institutional_ownership_pct": info.get("heldPercentInstitutions", 0) * 100 if info.get("heldPercentInstitutions") else 0,
                "insider_ownership_pct": info.get("heldPercentInsiders", 0) * 100 if info.get("heldPercentInsiders") else 0,
                "num_institutional_holders": info.get("institutionsCount", 0),
                "shares_outstanding": info.get("sharesOutstanding", 0),
                "float": info.get("floatShares", 0),
                "short_pct": info.get("shortPercentOfFloat", 0) * 100 if info.get("shortPercentOfFloat") else 0,
            }
        finally:
            __import__('sys').stderr = old_stderr
    except Exception:
        return {"ticker": ticker, "error": "Could not fetch data"}


# ═══════════════════════════════════════════════════════════════
# 5. SMART MONEY SUMMARY & REPORT
# ═══════════════════════════════════════════════════════════════

def get_smart_money_summary():
    """
    Get a comprehensive smart money summary.
    Combines hedge fund, congressional, and insider data.
    """
    summary = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "hedge_funds": {},
        "congress": {},
        "insiders": {},
    }
    
    # Hedge fund consensus
    try:
        consensus = get_hedge_fund_consensus(num_funds=5)
        summary["hedge_funds"] = consensus
    except Exception as e:
        summary["hedge_funds"] = {"error": str(e)}
    
    # Congressional trades
    try:
        trades = get_congressional_trades(days_back=14, min_value=25000)
        summary["congress"] = get_congressional_top_trades(trades)
    except Exception as e:
        summary["congress"] = {"error": str(e)}
    
    # Insider trades
    try:
        insider_trades = get_insider_trades(days_back=14, min_value=100000)
        summary["insiders"] = get_insider_summary(insider_trades)
    except Exception as e:
        summary["insiders"] = {"error": str(e)}
    
    return summary


def generate_smart_money_report(summary=None):
    """
    Generate a markdown report of smart money activity.
    """
    if summary is None:
        summary = get_smart_money_summary()
    
    lines = []
    lines.append("## 🏦 SMART MONEY TRACKING")
    lines.append(f"*{summary['timestamp']}*")
    lines.append("")
    
    # Hedge Fund Consensus
    hf = summary.get("hedge_funds", {})
    if hf and "top_consensus" in hf:
        lines.append("### 📊 Hedge Fund Consensus (13F Filings)")
        lines.append(f"Analyzed {hf.get('num_funds_analyzed', 0)} major funds, tracking {hf.get('total_stocks_tracked', 0)} unique holdings.")
        lines.append("")
        lines.append("| Stock | Funds Owning | Total Value ($K) |")
        lines.append("|-------|-------------|------------------|")
        for name, data in hf["top_consensus"][:15]:
            lines.append(f"| {name} | {data['count']} | ${data['total_value']:,.0f} |")
        lines.append("")
    
    # Congressional Trading
    congress = summary.get("congress", {})
    if congress and "ticker_consensus" in congress:
        lines.append("### 🏛️ Congressional Trading (Last 14 Days)")
        lines.append(f"{congress.get('total_trades', 0)} total trades, {congress.get('total_buys', 0)} buys.")
        lines.append("")
        if congress["ticker_consensus"]:
            lines.append("| Ticker | Politicians Buying | Total Amount |")
            lines.append("|--------|-------------------|--------------|")
            for t in congress["ticker_consensus"][:10]:
                pols = ", ".join(t["politicians"][:3])
                lines.append(f"| **{t['ticker']}** | {t['num_politicians']} ({pols}) | ${t['total_amount']:,.0f} |")
        lines.append("")
        
        # Top individual trades
        if congress.get("top_buys"):
            lines.append("**Top Individual Trades:**")
            for t in congress["top_buys"][:5]:
                lines.append(f"• **{t['politician']}** ({t.get('party', '')}) — {t['transaction']} **{t['ticker']}** ({t.get('amount_range', '')})")
            lines.append("")
    
    # Insider Trading
    insiders = summary.get("insiders", {})
    if insiders and "top_insider_buys" in insiders:
        lines.append("### 👔 Insider Trading (Last 14 Days)")
        lines.append(f"{insiders.get('total_trades', 0)} trades across {insiders.get('tickers_with_insider_activity', 0)} tickers.")
        lines.append("")
        lines.append("| Ticker | Buys | Sells | Buy/Sell Ratio | Net Activity |")
        lines.append("|--------|------|-------|----------------|--------------|")
        for t in insiders["top_insider_buys"][:10]:
            lines.append(f"| **{t['ticker']}** | {t['buys']} | {t['sells']} | {t['buy_sell_ratio']:.1f}x | ${t['net_activity']:,.0f} |")
        lines.append("")
    
    lines.append("---")
    lines.append("*Data sources: SEC EDGAR 13F filings, Capitol Trades/Quiver Quantitative, OpenInsider. Not financial advice.*")
    
    return "\n".join(lines)


if __name__ == "__main__":
    print("Fetching smart money data...")
    summary = get_smart_money_summary()
    report = generate_smart_money_report(summary)
    print(report)
