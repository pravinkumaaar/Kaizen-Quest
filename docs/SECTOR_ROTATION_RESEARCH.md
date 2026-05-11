# 🔄 Sector Rotation & Thematic Trend Detection — Research Report

> **Research Date:** May 11, 2026  
> **Purpose:** Identify best indicators and data sources for detecting sector rotations and emerging themes early  
> **For:** Kaizen-Quest Agent — Sector Intelligence Module

---

## 1. SECTOR ROTATION INDICATORS

### 1.1 Relative Strength (RS) Analysis

**Concept:** Compare each sector's performance against SPY (S&P 500) to identify which sectors are outperforming/underperforming. RS = Sector Return / SPY Return over the same period.

**How to calculate:**
```python
import yfinance as yf
import pandas as pd
import numpy as np

# 11 S&P Sector ETFs
SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLV": "Healthcare",
    "XLE": "Energy",
    "XLI": "Industrials",
    "XLC": "Communication Services",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLU": "Utilities",
    "XLRE": "Real Estate",
    "XLB": "Materials",
}

def calculate_relative_strength(periods=[20, 60, 120]):
    """
    Calculate relative strength of each sector vs SPY.
    periods: trading days (20=1mo, 60=3mo, 120=6mo)
    """
    all_tickers = list(SECTOR_ETFS.keys()) + ["SPY"]
    data = yf.download(all_tickers, period="1y")["Close"]
    
    results = []
    for ticker, name in SECTOR_ETFS.items():
        row = {"Ticker": ticker, "Sector": name}
        for p in periods:
            if len(data) > p:
                sector_return = (data[ticker].iloc[-1] / data[ticker].iloc[-p] - 1) * 100
                spy_return = (data["SPY"].iloc[-1] / data["SPY"].iloc[-p] - 1) * 100
                rs = sector_return - spy_return  # Outperformance vs SPY
                row[f"RS_{p}d"] = round(rs, 2)
                row[f"Return_{p}d"] = round(sector_return, 2)
        results.append(row)
    
    df = pd.DataFrame(results)
    df = df.sort_values(f"RS_{periods[0]}d", ascending=False)
    return df

# Calculate RS
rs_data = calculate_relative_strength([20, 60, 120])
print(rs_data.to_string(index=False))
```

### 1.2 Sector Momentum Scoring

**Concept:** Rank sectors by their momentum across multiple timeframes. Strong momentum sectors tend to persist (momentum effect).

```python
def calculate_sector_momentum_score():
    """
    Calculate a composite momentum score for each sector.
    Weights: 1-month (40%), 3-month (35%), 6-month (25%)
    """
    all_tickers = list(SECTOR_ETFS.keys())
    data = yf.download(all_tickers, period="1y")["Close"]
    
    results = []
    for ticker, name in SECTOR_ETFS.items():
        returns = {
            "1m": (data[ticker].iloc[-1] / data[ticker].iloc[-20] - 1) * 100 if len(data) > 20 else 0,
            "3m": (data[ticker].iloc[-1] / data[ticker].iloc[-60] - 1) * 100 if len(data) > 60 else 0,
            "6m": (data[ticker].iloc[-1] / data[ticker].iloc[-120] - 1) * 100 if len(data) > 120 else 0,
        }
        
        # Weighted momentum score
        score = returns["1m"] * 0.40 + returns["3m"] * 0.35 + returns["6m"] * 0.25
        
        results.append({
            "Ticker": ticker,
            "Sector": name,
            "1M_Return": round(returns["1m"], 2),
            "3M_Return": round(returns["3m"], 2),
            "6M_Return": round(returns["6m"], 2),
            "Momentum_Score": round(score, 2),
        })
    
    df = pd.DataFrame(results).sort_values("Momentum_Score", ascending=False)
    return df

momentum = calculate_sector_momentum_score()
print(momentum.to_string(index=False))
```

### 1.3 Sector Breadth Indicators

**Concept:** Calculate the percentage of stocks in each sector trading above their 50-day moving average. High breadth = strong sector. Low breadth = weakening sector even if ETF is up.

```python
def calculate_sector_breadth():
    """
    Calculate % of stocks above 50-day MA for each sector.
    Uses a sample of stocks from each sector.
    """
    # Sample stocks per sector (expand as needed)
    sector_stocks = {
        "XLK": ["AAPL", "MSFT", "NVDA", "AVGO", "ADBE", "CRM", "ORCL", "CSCO", "ACN", "INTC"],
        "XLF": ["JPM", "BAC", "WFC", "GS", "MS", "BLK", "SCHW", "C", "AXP", "USB"],
        "XLV": ["UNH", "JNJ", "PFE", "ABBV", "MRK", "TMO", "ABT", "DHR", "BMY", "LLY"],
        "XLE": ["XOM", "CVX", "COP", "SLB", "EOG", "MPC", "PSX", "VLO", "OXY", "HAL"],
        "XLI": ["CAT", "HON", "UPS", "BA", "GE", "MMM", "LMT", "DE", "RTX", "FDX"],
        "XLC": ["GOOGL", "META", "DIS", "NFLX", "CMCSA", "T", "VZ", "TMUS", "EA", "TTWO"],
        "XLY": ["AMZN", "TSLA", "HD", "MCD", "NKE", "SBUX", "TGT", "LOW", "BKNG", "CMG"],
        "XLP": ["PG", "KO", "PEP", "WMT", "COST", "PM", "MO", "CL", "EL", "KMB"],
        "XLU": ["NEE", "DUK", "SO", "D", "AEP", "SRE", "XEL", "ED", "WEC", "ES"],
        "XLRE": ["AMT", "PLD", "CCI", "EQIX", "PSA", "O", "WELL", "DLR", "SPG", "VICI"],
        "XLB": ["LIN", "APD", "SHW", "FCX", "NEM", "ECL", "DOW", "PPG", "DD", "CTVA"],
    }
    
    results = []
    for etf, stocks in sector_stocks.items():
        above_50ma = 0
        total = 0
        
        for stock in stocks:
            try:
                data = yf.download(stock, period="6mo", progress=False)["Close"]
                if len(data) > 50:
                    ma50 = data.rolling(50).mean().iloc[-1]
                    if data.iloc[-1] > ma50:
                        above_50ma += 1
                    total += 1
            except Exception:
                continue
        
        if total > 0:
            pct_above = (above_50ma / total) * 100
            results.append({
                "ETF": etf,
                "Sector": SECTOR_ETFS[etf],
                "Stocks_Above_50MA": above_50ma,
                "Total_Stocks": total,
                "Pct_Above_50MA": round(pct_above, 1),
                "Signal": "Strong" if pct_above > 70 else "Neutral" if pct_above > 40 else "Weak",
            })
    
    return pd.DataFrame(results).sort_values("Pct_Above_50MA", ascending=False)

breadth = calculate_sector_breadth()
print(breadth.to_string(index=False))
```

### 1.4 ETF Fund Flow Analysis

**Concept:** Track money flowing in/out of sector ETFs as a percentage of AUM. Large inflows = institutional conviction. Large outflows = rotation away.

```python
def analyze_etf_flows():
    """
    Analyze ETF flows using yfinance volume and price data.
    Approximate flow = (Current AUM - Previous AUM) / Previous AUM
    """
    etf_data = {
        "XLK": "Technology",
        "XLF": "Financials",
        "XLV": "Healthcare",
        "XLE": "Energy",
        "XLI": "Industrials",
        "XLY": "Consumer Disc.",
        "XLP": "Consumer Staples",
        "XLU": "Utilities",
        "XLRE": "Real Estate",
        "XLB": "Materials",
    }
    
    results = []
    for ticker, name in etf_data.items():
        try:
            etf = yf.Ticker(ticker)
            info = etf.info
            
            # Get AUM and volume data
            aum = info.get("totalAssets", 0)
            avg_volume = info.get("averageVolume", 0)
            recent_volume = info.get("volume", 0)
            
            # Volume ratio (recent vs average) — proxy for flow intensity
            vol_ratio = recent_volume / avg_volume if avg_volume > 0 else 1
            
            results.append({
                "Ticker": ticker,
                "Sector": name,
                "AUM_Millions": round(aum / 1e6, 0) if aum else "N/A",
                "Avg_Volume": avg_volume,
                "Recent_Volume": recent_volume,
                "Volume_Ratio": round(vol_ratio, 2),
                "Flow_Signal": "Heavy Inflow" if vol_ratio > 1.5 else 
                               "Inflow" if vol_ratio > 1.1 else
                               "Outflow" if vol_ratio < 0.7 else "Neutral",
            })
        except Exception as e:
            print(f"Error for {ticker}: {e}")
    
    return pd.DataFrame(results)

flows = analyze_etf_flows()
print(flows.to_string(index=False))
```

### 1.5 Key Macro Ratios for Sector Rotation

```python
def get_macro_rotation_signals():
    """
    Fetch key macro indicators that drive sector rotations.
    All free via yfinance or FRED.
    """
    signals = {}
    
    # 1. IWM/SPY Ratio (Small-cap vs Large-cap)
    # Rising = risk-on, favors small caps, cyclicals
    # Falling = risk-off, favors large caps, defensives
    iwm = yf.download("IWM", period="6mo", progress=False)["Close"]
    spy = yf.download("SPY", period="6mo", progress=False)["Close"]
    iwm_spy_ratio = iwm.iloc[-1] / spy.iloc[-1]
    iwm_spy_ma20 = (iwm / spy).rolling(20).mean().iloc[-1]
    signals["IWM/SPY"] = {
        "Current": round(float(iwm_spy_ratio), 4),
        "20D_MA": round(float(iwm_spy_ma20), 4),
        "Signal": "Risk-On (Small-cap leading)" if iwm_spy_ratio > iwm_spy_ma20 else "Risk-Off (Large-cap leading)"
    }
    
    # 2. XLE/XLU Ratio (Energy vs Utilities)
    # Rising = inflationary/growth, favors energy
    # Falling = deflationary/safe, favors utilities
    xle = yf.download("XLE", period="6mo", progress=False)["Close"]
    xlu = yf.download("XLU", period="6mo", progress=False)["Close"]
    xle_xlu_ratio = xle.iloc[-1] / xlu.iloc[-1]
    xle_xlu_ma20 = (xle / xlu).rolling(20).mean().iloc[-1]
    signals["XLE/XLU"] = {
        "Current": round(float(xle_xlu_ratio), 4),
        "20D_MA": round(float(xle_xlu_ma20), 4),
        "Signal": "Inflationary/Growth" if xle_xlu_ratio > xle_xlu_ma20 else "Defensive/Safe"
    }
    
    # 3. TNX (10-Year Treasury Yield)
    # Rising = growth/cyclicals favored
    # Falling = defensive/growth-at-reasonable-price favored
    tnx = yf.download("^TNX", period="3mo", progress=False)["Close"]
    signals["10Y_Yield"] = {
        "Current": round(float(tnx.iloc[-1]), 2),
        "3M_Ago": round(float(tnx.iloc[0]), 2),
        "Trend": "Rising" if tnx.iloc[-1] > tnx.iloc[0] else "Falling"
    }
    
    # 4. DXY (US Dollar Index)
    # Rising = headwind for commodities, international
    # Falling = tailwind for commodities, international
    dxy = yf.download("DX-Y.NYB", period="3mo", progress=False)["Close"]
    if not dxy.empty:
        signals["DXY"] = {
            "Current": round(float(dxy.iloc[-1]), 2),
            "Trend": "Rising" if dxy.iloc[-1] > dxy.iloc[0] else "Falling"
        }
    
    return signals

macro = get_macro_rotation_signals()
for key, val in macro.items():
    print(f"\n{key}: {val}")
```

---

## 2. SUB-SECTOR & THEMATIC DETECTION

### 2.1 Google Trends for Technology/Thematic Searches

**Concept:** Google Trends data can detect emerging themes before they show up in stock prices. The "AI memory bottleneck" theme would have shown up as surging searches for "HBM", "high bandwidth memory", "DDR5", etc.

```python
from pytrends.request import TrendReq
import pandas as pd

def detect_emerging_themes(keywords, timeframe="today 12-m"):
    """
    Use Google Trends to detect emerging themes.
    Rising interest = potential early-stage theme.
    """
    pytrends = TrendReq(hl="en-US", tz=360)
    
    results = {}
    for keyword in keywords:
        try:
            pytrends.build_payload([keyword], cat=0, timeframe=timeframe)
            interest = pytrends.interest_over_time()
            
            if not interest.empty:
                # Compare recent 3-month average vs prior 3-month average
                recent = interest[keyword].iloc[-90:].mean()
                prior = interest[keyword].iloc[-180:-90].mean()
                change_pct = ((recent / prior) - 1) * 100 if prior > 0 else 0
                
                results[keyword] = {
                    "Recent_Avg": round(recent, 1),
                    "Prior_Avg": round(prior, 1),
                    "Change_Pct": round(change_pct, 1),
                    "Signal": "🔥 Surging" if change_pct > 50 else
                              "📈 Rising" if change_pct > 20 else
                              "📉 Falling" if change_pct < -20 else "➡️ Stable",
                }
        except Exception as e:
            results[keyword] = {"Error": str(e)}
    
    return pd.DataFrame(results).T

# Detect AI/memory theme
ai_keywords = [
    "high bandwidth memory", "HBM", "AI memory", "DDR5 memory",
    "semiconductor shortage", "AI infrastructure", "data center memory",
    "chiplets", "advanced packaging", "CoWoS",
]
trends = detect_emerging_themes(ai_keywords)
print(trends)
```

### 2.2 Supply Chain Analysis

**Concept:** When a sub-sector booms, identify the entire supply chain. For AI memory: if HBM is booming, who makes HBM (SK Hynix, Micron, Samsung), who makes HBM equipment (BESI, ASML), who packages it (Amkor, ASE)?

```python
def analyze_supply_chain(theme="ai_memory"):
    """
    Map supply chains for emerging themes.
    Returns tickers at each level of the supply chain.
    """
    supply_chains = {
        "ai_memory": {
            "description": "AI Memory / HBM Supply Chain",
            "layers": {
                "HBM Manufacturers": ["MU", "000660.KS", "005930.KS"],  # Micron, SK Hynix, Samsung
                "Memory Equipment": ["BESI.AS", "ASML", "AMAT", "LRCX", "KLAC"],
                "Advanced Packaging": ["ASX", "AMKR", "005930.KS"],
                "Memory Controllers": ["MRVL", "AVGO"],
                "AI Chips (Buyers)": ["NVDA", "AMD", "AVGO"],
                "Memory ETFs": ["SMH", "SOXX", "XSD"],
            }
        },
        "ai_infrastructure": {
            "description": "AI Infrastructure / Data Centers",
            "layers": {
                "AI GPUs": ["NVDA", "AMD", "INTC"],
                "AI Networking": ["AVGO", "MRVL", "ANET"],
                "Data Center REITs": ["EQIX", "DLR", "AMT"],
                "Power/Cooling": ["VRT", "ETN", "VERT"],
                "Server OEMs": ["DELL", "HPE", "SMCI"],
                "Cloud Hyperscalers": ["MSFT", "GOOGL", "AMZN", "META"],
            }
        },
        "energy_transition": {
            "description": "Energy Transition / Clean Energy",
            "layers": {
                "Solar": ["FSLR", "ENPH", "SEDG", "NEE"],
                "Wind": ["VWS.CO", "GEV"],
                "Nuclear": ["CCJ", "SMR", "BWXT", "LEU"],
                "Grid/Storage": ["ETN", "VRT", "FLNC"],
                "EV/Batteries": ["TSLA", "QS", "ALB", "SQM"],
                "Clean Energy ETFs": ["ICLN", "TAN", "QCLN", "PBW"],
            }
        },
    }
    
    return supply_chains.get(theme, {})

# Get AI memory supply chain
chain = analyze_supply_chain("ai_memory")
for layer, tickers in chain["layers"].items():
    print(f"\n{layer}: {', '.join(tickers)}")
```

### 2.3 Social Media Momentum (StockTwits, Reddit)

```python
import requests
from collections import Counter
import re

def get_stocktwits_sentiment(ticker):
    """
    Get StockTwits sentiment and message volume for a ticker.
    Free API, no key required.
    """
    url = f"https://api.stocktwits.com/api/2/symbols/{ticker}/streams"
    headers = {"User-Agent": "KaizenQuest"}
    
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        data = response.json()
        messages = data.get("messages", [])
        
        bullish = sum(1 for m in messages if m.get("entities", {}).get("sentiment", {}).get("basic") == "Bullish")
        bearish = sum(1 for m in messages if m.get("entities", {}).get("sentiment", {}).get("basic") == "Bearish")
        
        return {
            "ticker": ticker,
            "total_messages": len(messages),
            "bullish": bullish,
            "bearish": bearish,
            "sentiment_ratio": round(bullish / max(bearish, 1), 2),
        }
    return None

def get_reddit_mentions(subreddits=["wallstreetbets", "stocks", "investing"], limit=100):
    """
    Get most mentioned tickers from Reddit.
    Uses Reddit's public JSON API (no auth needed for read-only).
    """
    ticker_pattern = re.compile(r'\b[A-Z]{1,5}\b')
    common_words = {"A", "I", "IT", "CEO", "CFO", "THE", "FOR", "AND", "ARE", "HAS", "CEO", "USA", "ETF", "IPO", "GDP", "CPI", "FED", "AI", "YOLO", "RH", "WSB", "ATH", "DD", "EOD", "PT", "EPS", "P/E", "RSI", "MACD", "ETF", "SPY", "QQQ", "IWM", "DIA", "VIX", "TLT", "GLD", "SLV", "XOM", "XLE", "XLF", "XLK", "XLV", "XLI", "XLC", "XLY", "XLP", "XLU", "XLRE", "XLB"}
    
    all_tickers = []
    
    for sub in subreddits:
        url = f"https://www.reddit.com/r/{sub}/hot.json?limit={limit}"
        headers = {"User-Agent": "KaizenQuest/1.0"}
        
        try:
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                data = response.json()
                posts = data.get("data", {}).get("children", [])
                
                for post in posts:
                    post_data = post.get("data", {})
                    title = post_data.get("title", "")
                    text = post_data.get("selftext", "")
                    
                    tickers = ticker_pattern.findall(title + " " + text)
                    tickers = [t for t in tickers if t not in common_words and len(t) >= 1]
                    all_tickers.extend(tickers)
        except Exception as e:
            print(f"Error fetching r/{sub}: {e}")
    
    # Count and rank
    counter = Counter(all_tickers)
    return counter.most_common(30)

# Get trending tickers on Reddit
mentions = get_reddit_mentions()
print("Top 20 Most Mentioned Tickers on Reddit:")
for ticker, count in mentions[:20]:
    print(f"  {ticker}: {count} mentions")
```

### 2.4 Earnings Call Transcript Analysis

```python
def detect_themes_from_earnings(ticker, num_quarters=4):
    """
    Analyze earnings call transcripts for emerging themes.
    Uses Seeking Alpha or similar sources.
    This is a simplified version — full implementation would use NLP.
    """
    # Key theme keywords to track
    theme_keywords = {
        "AI/ML": ["artificial intelligence", "machine learning", "AI", "ML", "generative", "LLM", "neural"],
        "Memory/HBM": ["memory", "HBM", "high bandwidth", "DDR5", "DRAM", "NAND", "storage"],
        "Cloud": ["cloud", "SaaS", "subscription", "recurring revenue", "ARR"],
        "Supply Chain": ["supply chain", "shortage", "constraint", "lead time", "capacity"],
        "Pricing Power": ["pricing", "price increase", "ASP", "average selling price", "margin expansion"],
        "Cost Cutting": ["efficiency", "cost reduction", "layoffs", "restructuring", "optimization"],
        "China": ["China", "Chinese", "Beijing", "Shanghai", "geopolitical"],
        "Energy/Power": ["power", "energy", "electricity", "cooling", "data center power"],
    }
    
    # In production, you would:
    # 1. Fetch earnings transcripts (Seeking Alpha API, or scrape)
    # 2. Count keyword occurrences per theme
    # 3. Track changes quarter-over-quarter
    # 4. Identify surging themes
    
    print(f"Theme detection framework for {ticker}")
    print("Themes tracked:", list(theme_keywords.keys()))
    return theme_keywords
```

---

## 3. SPECIFIC TICKERS FOR TRACKING

### 3.1 Complete Sector/Theme Ticker Map

```python
# Complete ticker map for sector rotation tracking
TRACKING_UNIVERSE = {
    # === 11 S&P SECTORS ===
    "XLK": "Technology",
    "XLF": "Financials",
    "XLV": "Healthcare",
    "XLE": "Energy",
    "XLI": "Industrials",
    "XLC": "Communication Services",
    "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples",
    "XLU": "Utilities",
    "XLRE": "Real Estate",
    "XLB": "Materials",
    
    # === SIZE/CAP ===
    "SPY": "S&P 500",
    "QQQ": "Nasdaq 100",
    "IWM": "Russell 2000 (Small Cap)",
    "MDY": "S&P MidCap 400",
    "VTI": "Total Market",
    
    # === SEMICONDUCTOR / AI ===
    "SMH": "Semiconductor ETF",
    "SOXX": "PHLX Semiconductor ETF",
    "XSD": "S&P Semiconductor ETF",
    "NVDA": "NVIDIA",
    "AVGO": "Broadcom",
    "MRVL": "Marvell",
    "AMD": "AMD",
    "TSM": "TSMC",
    "ASML": "ASML",
    "AMAT": "Applied Materials",
    "LRCX": "Lam Research",
    "KLAC": "KLA Corp",
    
    # === MEMORY (AI BOTTLENECK THEME) ===
    "MU": "Micron",
    "WDC": "Western Digital",
    "STX": "Seagate",
    "SK HYNIX": "SK Hynix (000660.KS)",
    "SAMSUNG": "Samsung (005930.KS)",
    
    # === AI INFRASTRUCTURE ===
    "SMCI": "Super Micro Computer",
    "DELL": "Dell Technologies",
    "HPE": "Hewlett Packard Enterprise",
    "ANET": "Arista Networks",
    "CIEN": "Ciena",
    "EQIX": "Equinix (Data Center REIT)",
    "DLR": "Digital Realty (Data Center REIT)",
    
    # === ENERGY SUB-SECTORS ===
    "XLE": "Energy ETF",
    "XOP": "Oil & Gas Exploration ETF",
    "OIH": "Oil Services ETF",
    "FCG": "Natural Gas ETF",
    "TAN": "Solar ETF",
    "ICLN": "Clean Energy ETF",
    "URA": "Uranium ETF",
    "CCJ": "Cameco (Uranium)",
    "SMR": "NuScale Power (SMR Nuclear)",
    "LEU": "Centrus Energy (Uranium Enrichment)",
    "XOM": "Exxon Mobil",
    "CVX": "Chevron",
    "COP": "ConocoPhillips",
    "SLB": "Schlumberger",
    
    # === HEALTHCARE ===
    "XLV": "Healthcare ETF",
    "IBB": "Biotech ETF",
    "XBI": "Biotech ETF (SPDR)",
    "VHT": "Healthcare Vanguard",
    "ARKG": "ARK Genomic Revolution",
    "UNH": "UnitedHealth",
    "JNJ": "Johnson & Johnson",
    "LLY": "Eli Lilly",
    "ABBV": "AbbVie",
    "TMO": "Thermo Fisher",
    "DHR": "Danaher",
    "PFE": "Pfizer",
    "MRK": "Merck",
    "BMY": "Bristol-Myers",
    
    # === FINANCIALS ===
    "XLF": "Financial ETF",
    "KRE": "Regional Bank ETF",
    "KBE": "Bank ETF",
    "VFH": "Financial Vanguard",
    "JPM": "JPMorgan",
    "BAC": "Bank of America",
    "GS": "Goldman Sachs",
    "MS": "Morgan Stanley",
    "BLK": "BlackRock",
    "SCHW": "Charles Schwab",
    "C": "Citigroup",
    "AXP": "American Express",
    "V": "Visa",
    "MA": "Mastercard",
    
    # === DEFENSIVE / BOND PROXY ===
    "XLU": "Utilities",
    "XLP": "Consumer Staples",
    "TLT": "20+ Year Treasury",
    "IEF": "7-10 Year Treasury",
    "SHY": "1-3 Year Treasury",
    "GLD": "Gold",
    "SLV": "Silver",
    "IAU": "Gold (iShares)",
    "PDC": "Silver (Sprott)",
    
    # === CYCLICAL / GROWTH ===
    "XLY": "Consumer Discretionary",
    "XLC": "Communication Services",
    "ARKK": "ARK Innovation",
    "COIN": "Coinbase",
    "HOOD": "Robinhood",
    "TSLA": "Tesla",
    "AMZN": "Amazon",
    "GOOGL": "Alphabet",
    "META": "Meta",
    "NFLX": "Netflix",
    "DIS": "Disney",
    
    # === INTERNATIONAL ===
    "EFA": "Developed Markets",
    "EEM": "Emerging Markets",
    "FXI": "China Large Cap",
    "EWZ": "Brazil",
    "EWJ": "Japan",
    "INDA": "India",
    "VGK": "Europe",
    
    # === VOLATILITY / HEDGING ===
    "VIX": "Volatility Index",
    "VXX": "VIX Short-Term Futures",
    "SQQQ": "3x Inverse Nasdaq",
    "SH": "Inverse S&P 500",
    "PSQ": "Inverse Nasdaq",
}
```

---

## 4. FREE DATA SOURCES FOR SECTOR ANALYSIS

### 4.1 Yahoo Finance via yfinance (FREE)

```python
import yfinance as yf

def get_sector_performance():
    """Get sector performance data from Yahoo Finance."""
    sectors = {
        "Technology": "XLK",
        "Financials": "XLF",
        "Healthcare": "XLV",
        "Energy": "XLE",
        "Industrials": "XLI",
        "Comm Services": "XLC",
        "Cons. Disc.": "XLY",
        "Cons. Staples": "XLP",
        "Utilities": "XLU",
        "Real Estate": "XLRE",
        "Materials": "XLB",
    }
    
    results = []
    for name, ticker in sectors.items():
        try:
            etf = yf.Ticker(ticker)
            info = etf.info
            hist = yf.download(ticker, period="6mo", progress=False)["Close"]
            
            if len(hist) > 0:
                results.append({
                    "Sector": name,
                    "Ticker": ticker,
                    "Price": round(float(hist.iloc[-1]), 2),
                    "1D_Change": round(float((hist.iloc[-1] / hist.iloc[-2] - 1) * 100), 2) if len(hist) > 1 else 0,
                    "1W_Change": round(float((hist.iloc[-1] / hist.iloc[-5] - 1) * 100), 2) if len(hist) > 5 else 0,
                    "1M_Change": round(float((hist.iloc[-1] / hist.iloc[-20] - 1) * 100), 2) if len(hist) > 20 else 0,
                    "3M_Change": round(float((hist.iloc[-1] / hist.iloc[-60] - 1) * 100), 2) if len(hist) > 60 else 0,
                    "6M_Change": round(float((hist.iloc[-1] / hist.iloc[0] - 1) * 100), 2),
                    "Volume": int(info.get("volume", 0)),
                    "Avg_Volume": int(info.get("averageVolume", 0)),
                })
        except Exception as e:
            print(f"Error for {name}: {e}")
    
    df = pd.DataFrame(results)
    df = df.sort_values("1M_Change", ascending=False)
    return df

perf = get_sector_performance()
print(perf.to_string(index=False))
```

### 4.2 FRED Economic Data (FREE)

```python
from fredapi import Fred
import os

def get_fred_sector_indicators():
    """
    Get economic indicators that drive sector rotations.
    Free API key from: https://fred.stlouisfed.org/docs/api/api_key.html
    """
    fred = Fred(api_key=os.getenv("FRED_API_KEY", "YOUR_KEY"))
    
    indicators = {
        # Yield Curve
        "T10Y2Y": "10Y-2Y Spread",
        "T10Y3M": "10Y-3M Spread",
        "DGS10": "10-Year Yield",
        "DGS2": "2-Year Yield",
        
        # Economic Health
        "UNRATE": "Unemployment Rate",
        "CPIAUCSL": "CPI (Inflation)",
        "PCEC1": "PCE (Fed's preferred inflation)",
        "INDPRO": "Industrial Production",
        "PAYEMS": "Nonfarm Payrolls",
        
        # Credit Conditions
        "BAMLH0A0HYM2": "High Yield Spread",
        "TOTLL": "Total Bank Loans",
        
        # Housing
        "HOUST": "Housing Starts",
        "PERMIT": "Building Permits",
        
        # Manufacturing
        "ISM/MAN_PMI": "ISM Manufacturing PMI",
        
        # Consumer
        "UMCSENT": "Consumer Sentiment",
        "PCEC1": "Personal Consumption",
        "RSAFS": "Retail Sales",
    }
    
    results = {}
    for series_id, name in indicators.items():
        try:
            data = fred.get_series(series_id, observation_start="2025-01-01")
            if not data.empty:
                results[name] = {
                    "Latest": round(float(data.iloc[-1]), 2),
                    "3M_Ago": round(float(data.iloc[-63]), 2) if len(data) > 63 else "N/A",
                    "Trend": "Rising" if len(data) > 20 and data.iloc[-1] > data.iloc[-20] else "Falling",
                }
        except Exception as e:
            results[name] = {"Error": str(e)}
    
    return pd.DataFrame(results).T

# fred_data = get_fred_sector_indicators()
# print(fred_data)
```

### 4.3 Finviz Sector Maps (FREE)

```python
import requests
from bs4 import BeautifulSoup

def get_finviz_sector_performance():
    """
    Scrape Finviz sector performance table.
    Free, no API key needed.
    """
    url = "https://finviz.com/groups.ashx?g=sector&v=110&o=-perf.1w"
    headers = {"User-Agent": "KaizenQuest research@kaizenquest.com"}
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Parse the sector table
    table = soup.find("table", {"class": "table-light"})
    if table:
        rows = []
        for tr in table.find_all("tr")[1:]:
            tds = tr.find_all("td")
            if len(tds) >= 10:
                rows.append({
                    "Rank": tds[0].get_text(strip=True),
                    "Sector": tds[1].get_text(strip=True),
                    "Stocks": tds[2].get_text(strip=True),
                    "Market_Cap": tds[3].get_text(strip=True),
                    "Perf_1W": tds[4].get_text(strip=True),
                    "Perf_1M": tds[5].get_text(strip=True),
                    "Perf_3M": tds[6].get_text(strip=True),
                    "Perf_6M": tds[7].get_text(strip=True),
                    "Perf_YTD": tds[8].get_text(strip=True),
                    "Perf_1Y": tds[9].get_text(strip=True),
                })
        return pd.DataFrame(rows)
    return pd.DataFrame()

# sector_perf = get_finviz_sector_performance()
# print(sector_perf.to_string(index=False))
```

### 4.4 ETF Flow Data from ETF.com / ETFdb (FREE)

```python
def get_etf_flow_data():
    """
    Get ETF flow data from ETFdb.com.
    Shows inflows/outflows as % of AUM.
    """
    # ETFdb provides fund flow data for free
    # URL format: https://etfdb.com/etf/TICKER/#fund-flows
    
    etfs_to_track = ["SPY", "QQQ", "IWM", "XLK", "XLF", "XLV", "XLE", "XLI", "XLY", "XLP", "XLU", "XLRE", "XLB", "SMH", "TLT", "GLD"]
    
    results = []
    for ticker in etfs_to_track:
        url = f"https://etfdb.com/etf/{ticker}/#fund-flows"
        # In production, scrape the fund flows table
        # For now, use yfinance as a proxy
        try:
            etf = yf.Ticker(ticker)
            info = etf.info
            results.append({
                "Ticker": ticker,
                "Name": info.get("shortName", "N/A"),
                "AUM": info.get("totalAssets", 0),
                "Volume": info.get("volume", 0),
                "Avg_Volume": info.get("averageVolume", 0),
            })
        except Exception:
            pass
    
    return pd.DataFrame(results)
```

---

## 5. COMPLETE SECTOR ROTATION DASHBOARD

```python
def generate_sector_rotation_dashboard():
    """
    Complete sector rotation analysis dashboard.
    Combines all indicators into a single view.
    """
    print("=" * 70)
    print("🔄 SECTOR ROTATION DASHBOARD")
    print("=" * 70)
    
    # 1. Relative Strength
    print("\n📊 RELATIVE STRENGTH vs SPY")
    print("-" * 50)
    rs = calculate_relative_strength([20, 60, 120])
    print(rs[["Sector", "RS_20d", "RS_60d", "RS_120d"]].to_string(index=False))
    
    # 2. Momentum Score
    print("\n📈 MOMENTUM SCORE (40% 1M + 35% 3M + 25% 6M)")
    print("-" * 50)
    mom = calculate_sector_momentum_score()
    print(mom[["Sector", "1M_Return", "3M_Return", "6M_Return", "Momentum_Score"]].to_string(index=False))
    
    # 3. Macro Signals
    print("\n🌍 MACRO ROTATION SIGNALS")
    print("-" * 50)
    macro = get_macro_rotation_signals()
    for key, val in macro.items():
        print(f"  {key}: {val}")
    
    # 4. Top/Bottom Sectors
    print("\n🏆 TOP 3 SECTORS (by 20-day RS):")
    top3 = rs.head(3)
    for _, row in top3.iterrows():
        print(f"  {row['Sector']}: RS={row['RS_20d']}%")
    
    print("\n⚠️ BOTTOM 3 SECTORS (by 20-day RS):")
    bot3 = rs.tail(3).iloc[::-1]
    for _, row in bot3.iterrows():
        print(f"  {row['Sector']}: RS={row['RS_20d']}%")
    
    # 5. Rotation Signal
    print("\n🔄 ROTATION SIGNAL:")
    avg_rs = rs["RS_20d"].mean()
    if avg_rs > 2:
        print("  → Strong risk-on environment. Favor: Technology, Consumer Disc, Small Caps")
    elif avg_rs > 0:
        print("  → Moderate risk-on. Favor: Cyclicals, Industrials, Financials")
    elif avg_rs > -2:
        print("  → Neutral/uncertain. Favor: Balanced, Quality, Healthcare")
    else:
        print("  → Risk-off environment. Favor: Utilities, Staples, Bonds, Gold")

# Run the dashboard
# generate_sector_rotation_dashboard()
```

---

## 6. THEMATIC TREND DETECTION FRAMEWORK

### 6.1 Multi-Signal Theme Scoring

```python
def score_theme(theme_name, keywords, related_tickers):
    """
    Score an emerging theme across multiple signals.
    Returns a composite score from 0-100.
    """
    score = 0
    signals = {}
    
    # Signal 1: Price momentum of related tickers (30 points)
    try:
        data = yf.download(related_tickers, period="3mo", progress=False)["Close"]
        avg_return = 0
        for ticker in related_tickers:
            if ticker in data.columns and len(data) > 20:
                ret = (data[ticker].iloc[-1] / data[ticker].iloc[-20] - 1) * 100
                avg_return += ret
        avg_return /= len(related_tickers)
        momentum_score = min(30, max(0, avg_return * 2))  # Cap at 30
        score += momentum_score
        signals["Momentum"] = round(momentum_score, 1)
    except Exception:
        signals["Momentum"] = 0
    
    # Signal 2: Volume surge (20 points)
    try:
        avg_vol_ratio = 0
        for ticker in related_tickers[:3]:  # Check top 3
            etf = yf.Ticker(ticker)
            info = etf.info
            vol = info.get("volume", 0)
            avg_vol = info.get("averageVolume", 1)
            if avg_vol > 0:
                avg_vol_ratio += vol / avg_vol
        avg_vol_ratio /= 3
        vol_score = min(20, max(0, (avg_vol_ratio - 1) * 20))
        score += vol_score
        signals["Volume"] = round(vol_score, 1)
    except Exception:
        signals["Volume"] = 0
    
    # Signal 3: Google Trends (20 points) — requires pytrends
    # Signal 4: Social media mentions (15 points) — requires Reddit API
    # Signal 5: Insider buying in theme (15 points) — requires OpenInsider
    
    return {
        "Theme": theme_name,
        "Total_Score": round(score, 1),
        "Max_Possible": 100,
        "Signals": signals,
        "Verdict": "🔥 Strong" if score > 60 else "📈 Moderate" if score > 30 else "➡️ Weak",
    }

# Score the AI Memory theme
ai_memory_score = score_theme(
    "AI Memory / HBM",
    ["HBM", "high bandwidth memory", "AI memory", "DDR5"],
    ["MU", "WDC", "SMH", "SOXX", "NVDA"]
)
print(ai_memory_score)
```

---

## 7. COMPARISON TABLE — SECTOR DATA SOURCES

| Source | Type | Cost | API Key | Data | Best For |
|--------|------|------|---------|------|----------|
| yfinance | Market data | Free | No | Prices, volume, AUM | All sector ETFs |
| FRED | Economic data | Free | Yes (free) | Yield curve, CPI, PMI | Macro rotation signals |
| Finviz Groups | Sector perf | Free | No | Sector rankings | Quick sector view |
| ETFdb | ETF flows | Free | No | Fund flows, holdings | Flow analysis |
| Google Trends | Search trends | Free | No | Search interest | Theme detection |
| StockTwits | Social sentiment | Free | No | Message sentiment | Retail sentiment |
| Reddit API | Social mentions | Free | No | Ticker mentions | Meme/retail trends |
| Quiver Quantitative | Alternative | $30/mo | Yes | Short volume, Wikipedia | Multi-signal |
| pytrends | Google Trends | Free | No | Trend data | Theme detection |

---

## 8. RECOMMENDED STACK FOR KAIZEN-QUEST

**Free tier (immediate implementation):**
1. `yfinance` — Sector ETF prices, volume, AUM, institutional ownership
2. `fredapi` — Yield curve, economic indicators (free API key)
3. `pytrends` — Google Trends for theme detection
4. `requests` + `BeautifulSoup` — Finviz sector performance, ETFdb flows
5. StockTwits API — Social sentiment
6. Reddit JSON API — Retail mentions

**Paid upgrade (when budget allows):**
1. Quiver Quantitative ($30/mo) — Short volume, Wikipedia trends, patents
2. Seeking Alpha API — Earnings call transcripts for NLP theme detection

---

## 9. KEY TAKEAWAYS — DETECTING THE NEXT "SANDECK $50→$1600"

1. **Start with Relative Strength** — The AI memory theme would have shown XLK and SMH surging in RS months before Sandisk moved
2. **Watch the supply chain** — When NVDA reports strong data center demand, trace it to memory (MU, SK Hynix), equipment (ASML, AMAT), packaging
3. **Google Trends leads price** — "HBM" and "high bandwidth memory" searches surged before the stock moves
4. **ETF flows confirm institutional conviction** — SMH/SOXX inflows as % of AUM would have signaled smart money positioning
5. **Insider buying in small-caps** — Insiders at smaller companies (like Sandisk) buying before the theme goes mainstream
6. **Breadth confirms the move** — When >70% of semiconductor stocks are above their 50-day MA, the sector has real momentum
7. **Macro context matters** — The IWM/SPY ratio and XLE/XLU ratio tell you whether the environment favors risk-on cyclicals or defensive positions
