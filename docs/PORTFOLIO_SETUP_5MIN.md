# 🚀 Quick Start: 4 Portfolio Setup (5 Minutes)

---

## Step 1: Export Portfolio 1 from Yahoo Finance (1 min)

1. Go to **yahoo.com/finance**
2. Click **My Portfolios** (top menu)
3. Select **Portfolio 1** (or whatever your first portfolio is called)
4. Click **Download** (⬇️ icon, top right)
5. Choose **CSV** → Download
6. A file like `MyPortfolio.csv` or `Portfolio1.csv` will download

---

## Step 2: Repeat for Portfolios 2, 3, and 4 (3 min)

Same steps as Step 1 for each of your other 3 portfolios.

You'll now have 4 CSV files:
- `MyPortfolio.csv` (or Portfolio_1.csv, etc.)
- `Portfolio_2.csv`
- `Trading.csv`
- `Retirement.csv`

---

## Step 3: Rename Files (1 min)

Rename them to:
- `portfolio1.csv`
- `portfolio2.csv`
- `portfolio3.csv`
- `portfolio4.csv`

**On Mac (Terminal):**
```bash
cd ~/Downloads  # or wherever you saved them

# Rename the files
mv MyPortfolio.csv portfolio1.csv
mv Portfolio_2.csv portfolio2.csv
mv Trading.csv portfolio3.csv
mv Retirement.csv portfolio4.csv

# Verify they're renamed
ls -la portfolio*.csv
```

---

## Step 4: Move to Agent Directory (1 min)

Move all 4 files to:
```bash
/Users/pravinkumaarr/Documents/AI/Kaizen-Quest-Agent/Kaizen-Quest/
```

**On Mac (Terminal):**
```bash
mv portfolio1.csv portfolio2.csv portfolio3.csv portfolio4.csv \
  ~/Documents/AI/Kaizen-Quest-Agent/Kaizen-Quest/

# Verify they're there
ls -la ~/Documents/AI/Kaizen-Quest-Agent/Kaizen-Quest/portfolio*.csv
```

Should show:
```
-rw-r--r--  portfolio1.csv
-rw-r--r--  portfolio2.csv
-rw-r--r--  portfolio3.csv
-rw-r--r--  portfolio4.csv
```

---

## Step 5: Run the Agent (30 seconds)

```bash
cd ~/Documents/AI/Kaizen-Quest-Agent/Kaizen-Quest
python3 agent.py
```

Check the output for:
```
✓ Loaded 4 portfolios: XX unique holdings, $X,XXX,XXX.00 total cost basis
  → X tickers consolidated from multiple portfolios
```

---

## ✅ Verify It Worked

Check the generated report:

```bash
# View latest report
cat REPORTS/$(ls -t REPORTS/*.md | head -1)
```

Look for the **Market Snapshot** section — should show all your consolidated holdings at the top!

---

## 📊 What You'll See

### In PORTFOLIO.md:
```
## Consolidated Holdings (4 portfolios)

| Ticker | Shares | Avg Price | Cost Basis | From |
|--------|--------|-----------|-----------|------|
| NVDA | 150.00 | $205.00 | $30,750.00 | 2 portfolio(s) |
| AAPL | 200.00 | $155.00 | $31,000.00 | 2 portfolio(s) |
...
```

### In Market Snapshot:
```
  [📊 Your Portfolio]
    NVDA       $202.50  ▲1.31%
    AAPL       $273.17  ▲2.63%
    ...
```

---

## 🐛 If Something Goes Wrong

| Problem | Solution |
|---------|----------|
| Agent can't find files | Check filenames are exactly `portfolio1.csv`, `portfolio2.csv`, etc. (not `Portfolio1` or `portfolio_1`) |
| CSV parsing error | Check first line of CSV has: `Symbol,Shares,Purchase Price,Date` |
| Shares not adding up | Verify duplicate tickers have exact same spelling (e.g., NVDA vs nvda) |
| Files don't exist | Use full path: `~/Documents/AI/Kaizen-Quest-Agent/Kaizen-Quest/portfolio1.csv` |

---

## 💡 Pro Tips

1. **Check CSV format before moving:**
   ```bash
   head -3 portfolio1.csv
   # Should show: Symbol,Shares,Purchase Price,Date
   ```

2. **Use absolute paths if unsure:**
   ```bash
   cp ~/Downloads/portfolio1.csv /Users/pravinkumaarr/Documents/AI/Kaizen-Quest-Agent/Kaizen-Quest/
   ```

3. **Save this terminal command for next time:**
   ```bash
   alias run-agent="cd ~/Documents/AI/Kaizen-Quest-Agent/Kaizen-Quest && python3 agent.py"
   
   # Then just type: run-agent
   ```

---

## 🎯 Done!

Your agent now consolidates all 4 portfolios into one unified view. Each time you run it:

1. ✅ Reads all 4 portfolio CSVs
2. ✅ Sums duplicate tickers
3. ✅ Calculates weighted avg cost basis
4. ✅ Shows consolidated holdings in reports
5. ✅ Watches all your positions in market snapshot

**Next run:** `python3 agent.py` will automatically load all 4 portfolios!

---

## 📞 Need More Details?

See `MULTIPLE_PORTFOLIOS_GUIDE.md` for complete documentation including:
- CSV format examples
- Consolidation logic explanation
- Troubleshooting guide
- How weighted average cost basis is calculated

---

**Time estimate:** 5 minutes setup, then automatic forever! ⏱️
