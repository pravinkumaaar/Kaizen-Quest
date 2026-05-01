# 📊 Multiple Portfolio Consolidation Guide

**Updated:** Agent v2.2.1 — Multiple Portfolio Support

---

## 🎯 What's New

Your agent now automatically **reads up to 4 separate Yahoo Finance portfolios** and consolidates all holdings into one unified view, including duplicate tickers.

### Example

If you have:
- **Portfolio 1:** NVDA (50 shares), AAPL (100 shares)
- **Portfolio 2:** NVDA (25 shares), MSFT (75 shares)  
- **Portfolio 3:** TSLA (10 shares)
- **Portfolio 4:** BTC-USD (0.5), AAPL (50 shares)

The agent will consolidate to:
- **NVDA:** 75 shares (50 + 25)
- **AAPL:** 150 shares (100 + 50)
- **MSFT:** 75 shares
- **TSLA:** 10 shares
- **BTC-USD:** 0.5

---

## 📝 Setup Instructions

### Step 1: Export Each Portfolio from Yahoo Finance

For each of your 4 portfolios:

1. Go to **Yahoo Finance** → **My Portfolios**
2. Select portfolio (e.g., "Portfolio 1")
3. Click **Download** (⬇️ icon in top right)
4. Choose **CSV** format
5. Save to your computer

### Step 2: Rename Files to portfolio1.csv, portfolio2.csv, etc.

Place the CSV files in:
```
/Users/pravinkumaarr/Documents/AI/Kaizen-Quest-Agent/Kaizen-Quest/
```

**Naming convention (IMPORTANT):**
```
portfolio1.csv  ← Portfolio 1
portfolio2.csv  ← Portfolio 2
portfolio3.csv  ← Portfolio 3
portfolio4.csv  ← Portfolio 4
```

❌ Don't use: `MyPortfolio.csv`, `Trading.csv`, etc.
✅ Must use: `portfolio1.csv`, `portfolio2.csv`, etc.

### Step 3: Verify CSV Format

Each portfolio file should have these columns:
```csv
Symbol,Shares,Purchase Price,Date
NVDA,50,200.00,2026-01-15
AAPL,100,150.00,2026-02-01
```

**Required columns:**
- `Symbol` - Ticker (e.g., NVDA, BTC-USD)
- `Shares` - Number of shares
- `Purchase Price` - Entry price per share

**Optional columns:**
- `Date` - Purchase date
- Any others (will be ignored)

### Step 4: Run the Agent

```bash
cd /Users/pravinkumaarr/Documents/AI/Kaizen-Quest-Agent/Kaizen-Quest
python3 agent.py
```

The agent will:
- ✅ Auto-discover portfolio1.csv through portfolio4.csv
- ✅ Consolidate all holdings
- ✅ Sum duplicate tickers
- ✅ Calculate weighted average cost basis
- ✅ Save consolidated view to PORTFOLIO.md

---

## 📄 Example CSV Format

### portfolio1.csv
```csv
Symbol,Shares,Purchase Price,Date
NVDA,50,200.00,2026-01-15
AAPL,100,150.00,2026-02-01
SPY,200,450.00,2025-11-15
GLD,50,425.00,2025-08-01
```

### portfolio2.csv
```csv
Symbol,Shares,Purchase Price,Date
NVDA,25,210.00,2026-02-20
MSFT,75,350.00,2025-12-10
TSLA,10,180.00,2026-03-01
```

### portfolio3.csv
```csv
Symbol,Shares,Purchase Price,Date
QQQ,100,600.00,2025-11-20
BTC-USD,0.5,65000.00,2025-10-05
AAPL,50,160.00,2026-03-15
```

### portfolio4.csv
```csv
Symbol,Shares,Purchase Price,Date
VOO,150,520.00,2025-09-01
META,30,450.00,2026-02-10
```

---

## 📊 What Gets Generated

When you run the agent with multiple portfolios, `PORTFOLIO.md` shows:

```markdown
## Consolidated Holdings (4 portfolios)

| Ticker | Shares | Avg Price | Cost Basis | From |
|--------|--------|-----------|-----------|------|
| **AAPL** | 150.00 | $154.67 | $23,200.00 | 2 portfolio(s) |
| **BTC-USD** | 0.50 | $65,000.00 | $32,500.00 | 1 portfolio(s) |
| **GLD** | 50.00 | $425.00 | $21,250.00 | 1 portfolio(s) |
| **META** | 30.00 | $450.00 | $13,500.00 | 1 portfolio(s) |
| **MSFT** | 75.00 | $350.00 | $26,250.00 | 1 portfolio(s) |
| **NVDA** | 75.00 | $203.33 | $15,250.00 | 2 portfolio(s) |
| **QQQ** | 100.00 | $600.00 | $60,000.00 | 1 portfolio(s) |
| **SPY** | 200.00 | $450.00 | $90,000.00 | 1 portfolio(s) |
| **TSLA** | 10.00 | $180.00 | $1,800.00 | 1 portfolio(s) |
| **VOO** | 150.00 | $520.00 | $78,000.00 | 1 portfolio(s) |

**Total Consolidated:**
- Unique Tickers: 10
- Total Shares (all): 840.00
- Total Cost Basis: $362,350.00
- Source Portfolios: 4
- Consolidated Tickers (across portfolios): 2
```

**Key Details:**
- **Avg Price:** Weighted average cost basis per share
- **From:** How many of your 4 portfolios contain this ticker
- **Total Shares (all):** Sum of all shares across all holdings
- **Consolidated Tickers:** Shows how many tickers appear in multiple portfolios (e.g., NVDA in 2, AAPL in 2)

---

## 📈 Market Snapshot Integration

Your market snapshot now shows **all consolidated holdings** at the top:

```
  [📊 Your Portfolio]
    NVDA       $202.50  ▲1.31%    (75 total shares from 2 portfolios)
    AAPL       $273.17  ▲2.63%    (150 total shares from 2 portfolios)
    MSFT       $432.92  ▲2.07%
    SPY        $450.00  ▲0.97%
    ... etc ...
```

---

## ⚙️ How Consolidation Works

### 1. **Load Phase**
- Agent looks for `portfolio1.csv`, `portfolio2.csv`, `portfolio3.csv`, `portfolio4.csv`
- If not found, falls back to single `portfolio.csv`

### 2. **Merge Phase**
- For each ticker found across all files:
  - **Sum shares:** 50 + 25 = 75 shares of NVDA
  - **Sum cost basis:** ($200 × 50) + ($210 × 25) = $15,250
  - **Calculate weighted avg price:** $15,250 / 75 = $203.33/share
  - **Track sources:** This ticker came from 2 portfolios

### 3. **Output Phase**
- Saves consolidated holdings to `PORTFOLIO.md`
- Uses consolidated tickers in market watchlist
- Logs consolidation details:
  ```
  ✓ Loaded 4 portfolios: 10 unique holdings, $362,350.00 total cost basis
    → 2 tickers consolidated from multiple portfolios
  ```

---

## 🔄 Fallback Behavior

**If you have different portfolio structures:**

| Scenario | Behavior |
|----------|----------|
| All 4 files (portfolio1-4.csv) exist | ✅ Consolidate all 4 |
| Only 3 files (portfolio1-3.csv) exist | ✅ Consolidate all 3 |
| Only portfolio.csv exists | ✅ Use single portfolio |
| No portfolio files found | ⚠️ Log warning, continue with empty watchlist |

---

## 💡 Pro Tips

1. **Keep filenames consistent:** Exactly `portfolio1.csv`, `portfolio2.csv`, etc. (not `Portfolio_1`, `portfolio-1`, etc.)

2. **One symbol per row:** Don't aggregate shares in Yahoo Finance before exporting — export each transaction

3. **Use same column names:** Stick to Yahoo Finance's CSV format (Symbol, Shares, Purchase Price)

4. **Crypto tickers:** Use `-USD` suffix (BTC-USD, ETH-USD) for consistency with yfinance

5. **Cost basis calculations:** The agent uses weighted average cost basis when consolidating duplicate tickers

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Portfolio not loading | Check file is named exactly `portfolio1.csv` not `Portfolio1.csv` |
| Tickers not consolidating | Verify ticker names match exactly (case doesn't matter, but spelling does) |
| Shares not summing correctly | Check for extra spaces in CSV: `NVDA ` vs `NVDA` |
| CSV parsing error | Verify columns match: Symbol, Shares, Purchase Price, Date |
| Cost basis wrong | Ensure Purchase Price is per-share, not total cost |

---

## 📞 Quick Check

After exporting from Yahoo Finance:

```bash
# Verify files exist
ls -la portfolio*.csv

# Check first few lines
head -3 portfolio1.csv
head -3 portfolio2.csv
```

Should show:
```
Symbol,Shares,Purchase Price,Date
NVDA,50,200.00,2026-01-15
AAPL,100,150.00,2026-02-01
```

---

## 🚀 Next Steps

1. **Export** each portfolio from Yahoo Finance as CSV
2. **Rename** to `portfolio1.csv`, `portfolio2.csv`, `portfolio3.csv`, `portfolio4.csv`
3. **Place** in `/Users/pravinkumaarr/Documents/AI/Kaizen-Quest-Agent/Kaizen-Quest/`
4. **Run** agent: `python3 agent.py`
5. **Check** PORTFOLIO.md for consolidated holdings
6. **Review** market snapshot for all your positions

---

*Your agent now treats all 4 portfolios as one unified position tracker. Duplicate holdings are automatically consolidated with weighted average cost basis.*
