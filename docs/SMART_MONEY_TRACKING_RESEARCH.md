# 🔍 Smart Money Tracking — Best Free/Cheap Data Sources

> **Research Date:** May 11, 2026  
> **Purpose:** Identify best free/cheap APIs for tracking sophisticated investor activity  
> **For:** Kaizen-Quest Agent — Smart Money Intelligence Module

---

## 1. HEDGE FUND HOLDINGS (13F Filings)

### 1.1 SEC EDGAR Full-Text Search API (FREE)

**Endpoint:** `https://efts.sec.gov/LATEST/search-index`

**What it returns:** JSON with filing metadata — CIK numbers, company names, filing dates, form types, SIC codes, business locations, and document IDs.

**Key fields per hit:**
- `ciks[]` — List of CIK numbers
- `display_names[]` — Company names with tickers
- `form` — Form type (13F-HR, 13F-NT, etc.)
- `file_date` — Filing date
- `period_ending` — Quarter end date
- `adsh` — Accession number (unique filing ID)
- `file_num[]` — SEC file numbers
- `sics[]` — SIC industry codes
- `biz_states[]` — Business state codes

**Rate limits:** SEC requests polite usage — no more than 10 requests/second. Must include proper User-Agent header.

**API Key:** ❌ Not required

**Python Example:**
```python
import requests
import json

def search_13f_filings(fund_name=None, cik=None, start_date="2025-01-01", end_date="2026-05-11", count=100):
    """
    Search SEC EDGAR for 13F filings.
    Free, no API key needed.
    Rate limit: ≤10 requests/second.
    """
    base_url = "https://efts.sec.gov/LATEST/search-index"
    
    # Build query
    must_clauses = [{"match_phrase": {"doc_text": "13F"}}]
    if fund_name:
        must_clauses.append({"match_phrase": {"doc_text": fund_name}})
    
    params = {
        "q": json.dumps({
            "_source": {"exclude": ["doc_text"]},
            "query": {
                "bool": {
                    "must": must_clauses,
                    "filter": [
                        {"range": {"file_date": {"gte": start_date, "lte": end_date}}}
                    ]
                }
            },
            "from": 0,
            "size": count,
            "aggregations": {
                "form_filter": {"terms": {"field": "root_forms", "size": 30}},
                "entity_filter": {"terms": {"field": "display_names.raw", "size": 30}}
            }
        })
    }
    
    headers = {
        "User-Agent": "KaizenQuest research@kaizenquest.com",
        "Accept": "application/json"
    }
    
    response = requests.get(base_url, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()
    
    filings = []
    for hit in data.get("hits", {}).get("hits", []):
        src = hit.get("_source", {})
        filings.append({
            "form": src.get("form"),
            "ciks": src.get("ciks", []),
            "display_names": src.get("display_names", []),
            "file_date": src.get("file_date"),
            "period_ending": src.get("period_ending"),
            "adsh": src.get("adsh"),
            "file_type": src.get("file_type"),
        })
    
    return filings

# Example: Get recent 13F filings
filings = search_13f_filings(start_date="2026-01-01", count=20)
for f in filings[:5]:
    print(f"{f['file_date']} | {f['display_names'][0] if f['display_names'] else 'N/A'} | {f['form']}")
```

### 1.2 sec-edgar-downloader Python Library (FREE)

**PyPI:** `pip install sec-edgar-downloader`

**What it does:** Downloads actual 13F XML/HTML filings from EDGAR by ticker or CIK.

**Rate limits:** Same as SEC — ≤10 requests/second with proper User-Agent.

**API Key:** ❌ Not required

**Python Example:**
```python
from sec_edgar_downloader import Downloader

# Initialize — company name + email for SEC compliance
dl = Downloader("KaizenQuest", "research@kaizenquest.com", "./sec_filings")

# Download latest 13F-HR for a specific fund (by CIK)
# Berkshire Hathaway CIK: 0001067983
dl.get("13F-HR", "0001067983", limit=1)

# Download latest 13F for a ticker
dl.get("13F-HR", "AAPL", limit=1)

# Download all 13F filings in date range
dl.get("13F-HR", "0001067983", after="2025-01-01", before="2026-05-11")

# Download the actual XML content (not just metadata)
dl.get("13F-HR", "0001067983", limit=1, download_details=True)
```

**Parsing the 13F XML for holdings:**
```python
import xml.etree.ElementTree as ET

def parse_13f_holdings(xml_file_path):
    """Parse 13F XML to extract individual holdings."""
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    
    # Define namespace
    ns = {'ns': 'http://www.sec.gov/edgar/document/thirteenf/informationtable'}
    
    holdings = []
    for info in root.findall('.//ns:infoTable', ns):
        holding = {
            "name_of_issuer": info.findtext("ns:nameOfIssuer", default="", namespaces=ns),
            "cusip": info.findtext("ns:cusip", default="", namespaces=ns),
            "value_thousands": int(info.findtext("ns:value", default="0", namespaces=ns)),
            "shares": int(info.findtext("ns:sshPrnamt", default="0", namespaces=ns)),
            "share_type": info.findtext("ns:sshPrnamtType", default="", namespaces=ns),
        }
        holdings.append(holding)
    
    return holdings
```

### 1.3 Dataroma (FREE)

**URL:** `https://www.dataroma.com/m/holdings.php?m=BRK`

**What it returns:** Pre-parsed 13F holdings for top hedge funds, updated quarterly. Shows current holdings, recent buys/sells, portfolio changes.

**Data available:**
- Current portfolio holdings with % of portfolio
- New positions (bought last quarter)
- Sold positions (exited last quarter)
- Increased/decreased positions
- Historical portfolio back to 2010+

**Rate limits:** Standard web scraping — be polite, add delays.

**API Key:** ❌ Not required

**Python Example (scraping):**
```python
import requests
from bs4 import BeautifulSoup
import pandas as pd
import time

def get_dataroma_holdings(fund_code="BRK"):
    """
    Scrape Dataroma for a fund's current holdings.
    Fund codes: BRK (Berkshire), BAUPST (Baupist), PMGR (Pershing), etc.
    """
    url = f"https://www.dataroma.com/m/holdings.php?m={fund_code}"
    headers = {"User-Agent": "KaizenQuest research@kaizenquest.com"}
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Find the holdings table
    table = soup.find("table", {"id": "grid"})
    if not table:
        return pd.DataFrame()
    
    df = pd.read_html(str(table))[0]
    time.sleep(2)  # Be polite
    return df

# Get Berkshire's current holdings
holdings = get_dataroma_holdings("BRK")
print(holdings.head(10))
```

### 1.4 WhaleWisdom (FREE TIER)

**URL:** `https://whale-wisdom.com`

**What it returns:** 13F filing data, pre-parsed. Free tier shows top holdings, sector allocation, and recent trades for major funds.

**Free tier limits:** Limited to top holdings and basic data. Full data requires paid plan (~$30/month).

**API Key:** ❌ Not required for web scraping

### 1.5 Fintel (FREE TIER)

**URL:** `https://fintel.io`

**What it returns:** 13F institutional ownership data, insider trading, short interest, options flow.

**Free tier:** Basic 13F data, limited queries per day. Paid plans from $29/month.

**API Key:** ❌ Not required for basic web access

---

## 2. CONGRESSIONAL TRADING

### 2.1 Quiver Quantitative API (PAID — $30/month)

**API Base URL:** `https://api.quiverquant.com`

**Endpoints:**
| Endpoint | Description | Tier |
|----------|-------------|------|
| `/v1/congress_trading` | All recent congressional trades | Tier 1 |
| `/v1/congress_trading?ticker=TSLA` | Trades for specific ticker | Tier 1 |
| `/v1/congress_trading?politician=Richard%20Burr` | Trades by specific politician | Tier 1 |
| `/v1/insiders` | Insider transactions | Tier 1 |
| `/v1/sec13FChanges` | 13F changes | Tier 2 |
| `/v1/sec13F` | Full 13F holdings | Tier 2 |
| `/v1/lobbying` | Corporate lobbying | Tier 2 |
| `/v1/gov_contracts` | Government contracts | Tier 2 |
| `/v1/offexchange` | Off-exchange short volume | Tier 1 |
| `/v1/wikipedia` | Wikipedia page views | Tier 1 |
| `/v1/patents` | Patent filings | Tier 2 |

**Pricing:** Starts at $30/month (Tier 1). Tier 2 (full 13F, lobbying, contracts) is higher.

**Rate limits:** Not publicly documented; reasonable use expected.

**API Key:** ✅ Required (sign up at api.quiverquant.com)

**Python Example:**
```python
import quiverquant
import pandas as pd

# Initialize with API token
quiver = quiverquant.quiver("YOUR_API_TOKEN")

# Get all recent congressional trades
df_congress = quiver.congress_trading()
print(df_congress.columns)
# Typical columns: Ticker, Representative, Transaction, Date, 
#                   Amount, Party, Chamber, State, Price

# Get Tesla trades by Congress
df_tsla = quiver.congress_trading("TSLA")

# Get trades by a specific politician
df_burr = quiver.congress_trading("Richard Burr", politician=True)

# Get insider transactions
df_insiders = quiver.insiders()
df_insiders_tsla = quiver.insiders("TSLA")

# Get 13F changes for a ticker
df_13f_amzn = quiver.sec13FChanges(ticker="AMZN")

# Get Wikipedia page views (momentum indicator)
df_wiki = quiver.wikipedia("NVDA")
```

### 2.2 Capitol Trades (FREE)

**URL:** `https://www.capitoltrades.com`

**What it returns:** Congressional trading data, politician profiles, issuer tracking, trade history (3 years).

**Data available:**
- Individual trades with politician name, ticker, transaction type, amount range
- Party, chamber, state, committee membership
- Issuer pages showing all congressional trades in that stock
- Historical data back to ~2023

**Rate limits:** Standard web scraping — be polite.

**API Key:** ❌ Not required

**Python Example:**
```python
import requests
from bs4 import BeautifulSoup
import json

def get_capitol_trades_recent(pages=5):
    """Scrape recent congressional trades from CapitolTrades."""
    all_trades = []
    headers = {"User-Agent": "KaizenQuest research@kaizenquest.com"}
    
    for page in range(1, pages + 1):
        url = f"https://www.capitoltrades.com/trades?page={page}"
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Parse trade cards
        trade_cards = soup.find_all("div", class_="trade-card")
        for card in trade_cards:
            trade = {
                "politician": card.find("a", class_="politician-name").get_text(strip=True) if card.find("a", class_="politician-name") else None,
                "ticker": card.find("span", class_="ticker").get_text(strip=True) if card.find("span", class_="ticker") else None,
                "transaction": card.find("span", class_="transaction-type").get_text(strip=True) if card.find("span", class_="transaction-type") else None,
                "amount": card.find("span", class_="amount").get_text(strip=True) if card.find("span", class_="amount") else None,
                "date": card.find("time").get("datetime") if card.find("time") else None,
            }
            all_trades.append(trade)
    
    return all_trades
```

### 2.3 Senate Stock Watcher (FREE)

**URL:** `https://senatestockwatcher.com`

**What it returns:** Senate financial disclosures, stock trades, and ownership data.

**API Key:** ❌ Not required

### 2.4 House Stock Watcher (FREE)

**URL:** `https://housestockwatcher.com`

**What it returns:** House of Representatives financial disclosures and stock trades.

**API Key:** ❌ Not required

---

## 3. INSIDER TRADING

### 3.1 OpenInsider (FREE)

**URL:** `https://openinsider.com`

**What it returns:** SEC Form 4 filings — insider buys, sells, option exercises. One of the best free sources for insider data.

**Data fields:**
- Ticker, Company name
- Insider name, relationship (Officer, Director, 10% Owner)
- Transaction date, filing date
- Transaction type (Buy, Sale, Option Exercise)
- Number of shares, price per share
- Total value of transaction
- Shares owned after transaction

**Rate limits:** Standard web scraping.

**API Key:** ❌ Not required

**Python Example:**
```python
import requests
from bs4 import BeautifulSoup
import pandas as pd

def get_openinsider_buys(min_value=100000, pages=3):
    """
    Get significant insider buys from OpenInsider.
    min_value: Minimum transaction value in dollars.
    """
    all_trades = []
    headers = {"User-Agent": "KaizenQuest research@kaizenquest.com"}
    
    for page in range(1, pages + 1):
        url = f"http://openinsider.com/screener?s=&o=&pl=&ph=&ll=&lh=&fd=30&fdr=&td=0&tdr=&fdlyl=&fdlyh=&daysago=&xp=1&xs=1&vl={min_value}&vh=&ocl=&och=&sic1=-1&sicl=100&sich=9999&grp=0&nfl=&nfs=&nil=&nih=&nol=&noh=&v2l=&v2h=&oc2l=&oc2h=&sortcol=0&cnt=100&page={page}"
        
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        
        table = soup.find("table", {"class": "tinytable"})
        if table:
            df = pd.read_html(str(table))[0]
            all_trades.append(df)
    
    if all_trades:
        return pd.concat(all_trades, ignore_index=True)
    return pd.DataFrame()

# Get insider buys over $100K in last 30 days
buys = get_openinsider_buys(min_value=100000, pages=3)
print(f"Found {len(buys)} significant insider buys")
```

### 3.2 Finviz Insider Trading (FREE)

**URL:** `https://finviz.com/insidertrading.ashx`

**What it returns:** Insider trading data with relationship, transaction type, shares, value.

**Data fields visible (from live data):**
- Ticker, Owner name, Relationship (Director, Officer, etc.)
- Date, Transaction (Buy/Sale/Option Exercise)
- Shares, Price, Total Value
- Shares Held After

**Python Example:**
```python
import requests
from bs4 import BeautifulSoup
import pandas as pd

def get_finviz_insider_trading():
    """Get insider trading data from Finviz."""
    url = "https://finviz.com/insidertrading.ashx"
    headers = {"User-Agent": "KaizenQuest research@kaizenquest.com"}
    
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    
    table = soup.find("table", {"class": "table-light"})
    if table:
        rows = []
        for tr in table.find_all("tr")[1:]:  # Skip header
            tds = tr.find_all("td")
            if len(tds) >= 8:
                rows.append({
                    "ticker": tds[0].get_text(strip=True),
                    "owner": tds[1].get_text(strip=True),
                    "relationship": tds[2].get_text(strip=True),
                    "date": tds[3].get_text(strip=True),
                    "transaction": tds[4].get_text(strip=True),
                    "cost": tds[5].get_text(strip=True),
                    "shares": tds[6].get_text(strip=True),
                    "value": tds[7].get_text(strip=True),
                })
        return pd.DataFrame(rows)
    return pd.DataFrame()

insider_data = get_finviz_insider_trading()
print(insider_data.head(10))
```

### 3.3 SEC Form 4 via EDGAR (FREE)

Use the `sec-edgar-downloader` library (shown in Section 1.2) with form type "4" or "4/A":
```python
dl.get("4", "AAPL", limit=10)  # Latest Form 4 filings for Apple
```

---

## 4. INSTITUTIONAL OWNERSHIP CHANGES

### 4.1 13F Filings (Primary Source)

All institutional investment managers with >$100M AUM must file 13F quarterly. This is the primary source for institutional ownership changes.

**Best free sources:**
1. **SEC EDGAR API** (Section 1.1) — raw filings
2. **sec-edgar-downloader** (Section 1.2) — easy download
3. **Dataroma** (Section 1.3) — pre-parsed
4. **Quiver Quantitative** (Section 2.1) — API with parsed data ($30/mo)

### 4.2 Yahoo Finance via yfinance (FREE)

```python
import yfinance as yf

def get_institutional_ownership(ticker):
    """Get institutional ownership data from Yahoo Finance."""
    stock = yf.Ticker(ticker)
    
    # Institutional holders
    inst_holders = stock.institutional_holders
    # Major holders
    major_holders = stock.major_holders
    # Mutual fund holders
    mf_holders = stock.mutualfund_holders
    
    return {
        "institutional_holders": inst_holders,
        "major_holders": major_holders,
        "mutualfund_holders": mf_holders,
    }

# Example
data = get_institutional_ownership("NVDA")
print("Top Institutional Holders:")
print(data["institutional_holders"].head(10))
```

---

## 5. COMPARISON TABLE

| Source | Type | Cost | API Key | Rate Limit | Data Quality | Best For |
|--------|------|------|---------|------------|-------------|----------|
| SEC EDGAR API | 13F filings | Free | No | 10 req/sec | Raw XML | Deep analysis |
| sec-edgar-downloader | 13F download | Free | No | 10 req/sec | Raw XML | Automated downloads |
| Dataroma | 13F parsed | Free | No | Scraping | Pre-parsed | Quick lookup |
| WhaleWisdom | 13F parsed | Free/Paid | No | Varies | Pre-parsed | Top holdings |
| Fintel | 13F + more | Free/Paid | No | Varies | Pre-parsed | Multi-source |
| Quiver Quantitative | Alternative data | $30/mo | Yes | Varies | API JSON | All-in-one |
| Capitol Trades | Congress | Free | No | Scraping | Pre-parsed | Congressional |
| OpenInsider | Insider | Free | No | Scraping | Pre-parsed | Insider buys |
| Finviz | Insider | Free | No | Scraping | Pre-parsed | Quick insider |
| yfinance | Ownership | Free | No | Varies | Pre-parsed | Institutional % |

---

## 6. RECOMMENDED STACK FOR KAIZEN-QUEST

**Free tier (immediate implementation):**
1. `sec-edgar-downloader` — Download and parse 13F filings
2. `yfinance` — Institutional ownership percentages
3. `requests` + `BeautifulSoup` — Scrape OpenInsider, Finviz, CapitolTrades
4. SEC EDGAR API — Direct filing search

**Paid upgrade (when budget allows):**
1. Quiver Quantitative API ($30/mo) — Unified API for congress, insider, 13F, short volume, Wikipedia trends, patents
