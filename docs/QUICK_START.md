# 🎯 Quick Start: Your Files & How to Use Them

## 📋 Essential Files to Know

### **PORTFOLIO.md** 
Your holdings from Yahoo Finance

**When to update**: After every trade (or weekly minimum)

**Format**:
```
AAPL | 100 | 150.00 | 175.00 | +$2,500
NVDA | 50 | 200.00 | 220.00 | +$1,000
```

**Why it matters**: Agent learns what investments work for YOU


---

### **RATINGS.md**
Rate agent performance (1-10 scale)

**When to update**: After each run (takes 30 seconds)

**Format**:
```
- 2026-04-22-1824: 8/10 - Great analysis, solid ideas
- 2026-04-21-1630: 7/10 - Good but missed crypto angle
```

**Why it matters**: Agent learns to improve based on your feedback


---

### **RECOMMENDATIONS.md** 
Tracks agent's best predictions over time

**When to update**: Never - agent updates this automatically!

**What it shows**:
- Entry price agent recommended at
- Target price agent thinks it will hit
- Current price (updated daily)
- Performance % (gain/loss)
- Conviction score (how confident agent was)

**Why it matters**: Proves agent is learning; shows if recommendations were right


---

### **MEMORY.md**
Your permanent profile & preferences

**When to update**: When your goals/preferences change

**Include**: Risk tolerance, investment philosophy, location, learning interests


---

### **CONTEXT.md**
Your current investment thesis & goals

**When to update**: Monthly or when goals change

**Include**: Current market outlook, focus areas, sector bets


---

### **LEARNINGS.md**
Auto-updated insights from agent

**When to update**: Never - agent updates this automatically!

**What it shows**: Agent's self-improvements each run


---

### **REPORTS/** folder
Daily intelligence reports (markdown files)

**When to read**: After each run you want to analyze

**What's inside**: News digest, investment ideas, options plays, learning topics


---

## 🚀 Workflow (Daily)

### 1. Run agent (2-5 min)
```bash
python3 agent.py
```

### 2. Read report (5 min)
Open latest file in `REPORTS/` folder

### 3. Rate it (30 sec)
Add line to `RATINGS.md`:
```
- 2026-04-22-1824: 8/10 - Comment about what was good/bad
```

### 4. Track your portfolio (optional)
Update `PORTFOLIO.md` if you made trades

---

## 📊 Monthly Routine

1. **Review RECOMMENDATIONS.md**
   - See which agent predictions came true
   - What conviction scores were right?

2. **Update PORTFOLIO.md**
   - Any major changes?
   - Rebalanced?

3. **Check LEARNINGS.md**
   - What is agent learning about you?

4. **Update CONTEXT.md**
   - Still bullish on AI?
   - Changed risk tolerance?

---

## 🎓 Deep Dive Guides

- **[YAHOO_FINANCE_GUIDE.md](YAHOO_FINANCE_GUIDE.md)** - How to link portfolio & ratings
- **[FIXES_SUMMARY.md](FIXES_SUMMARY.md)** - What we fixed
- **[README.md](README.md)** - Full system overview
- **[CLAUDE.md](CLAUDE.md)** - Investment rules & philosophy

---

## 💡 Key Concepts

### Conviction Score (1-10)
- **9-10**: Hold through -20% dips, thesis likely right
- **7-8**: Good idea, but watch closely
- **5-6**: Medium confidence, take profits quickly
- **1-4**: Speculative, hedge or skip

### Performance Tracking
Agent updates prices daily and calculates:
- **Performance %**: (Current - Entry) / Entry
- **Status**: Active / Target Hit / Stopped Out
- Learns which conviction scores are most accurate

### Rating System
- Be consistent (if 8/10 = "great", keep that standard)
- Add context (not just a score, explain why)
- Don't overthink (gut feeling is fine)

---

## ⚡ Quick Commands

```bash
# Run agent
python3 agent.py

# See latest report
cat REPORTS/2026-04-22-*.md | tail -100

# Update portfolio
open PORTFOLIO.md

# Rate latest run
open RATINGS.md

# Check recommendations
open RECOMMENDATIONS.md

# View all learnings
cat LEARNINGS.md
```

---

## 🆘 Troubleshooting

**Q: Agent not using my portfolio?**
A: Check `PORTFOLIO.md` format - must be: `TICKER | Shares | Cost | Current | P/L`

**Q: Ratings not affecting recommendations?**
A: Takes 5-10 runs to see patterns. Keep rating consistently!

**Q: Recommendations not tracking?**
A: Agent tracks ideas with 8+/10 conviction automatically. Check `RECOMMENDATIONS.md`

**Q: Too many errors in terminal?**
A: All fixed! Should see clean output now. If not, check agent.py syntax: `python3 -m py_compile agent.py`

---

## 📞 Support

- See `YAHOO_FINANCE_GUIDE.md` for portfolio questions
- See `FIXES_SUMMARY.md` for technical details
- See `CLAUDE.md` for investment philosophy
- See `README.md` for full documentation

---

**Start here**: 
1. `python3 agent.py` 
2. Read the report
3. Rate it in `RATINGS.md` 
4. Done! ✅
