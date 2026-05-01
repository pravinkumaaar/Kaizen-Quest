# 🎓 Agent Learnings

*Auto-updated after each run. Read at the start of every run.*

## Human-Written Seed Rules
- Investment ideas must include specific entry prices, not just "buy now"
- Options: ALWAYS include the EXIT RULE reminding to close before expiry
- Learning topics: avoid obvious ones. Surprising and counterintuitive > popular
- News digest: every sentence should earn its place. Cut the fluff ruthlessly.
- Cross-domain insights are the most valued output — look for non-obvious connections
- Time horizons matter: always specify swing vs medium vs long-term clearly
- When suggesting covered calls: calculate and show the annualized yield
- For asymmetric options plays: explain WHY the market might be mispricing them

---
*Agent appends entries below after each run.*


## Run: 2026-04-22 17:36 UTC
[LLM unavailable: Error code: 429 - {'error': {'message': 'Provider returned error', 'code': 429, 'metadata': {'raw': 'qwen/qwen3-coder:free is temporarily rate-limited upstream. Please retry shortly, or add your own key to accumulate your rate limits: https://openrouter.ai/settings/integrations', 'provider_name': 'Venice', 'is_byok': False}}, 'user_id': 'user_3CjDMJJxt7kLXfsmDFwdcO4xdJF'}]

## Run: 2026-04-22 18:22 UTC
Here’s a critical self-assessment of this run’s performance with actionable learnings:

### **What Worked Well**  
✅ **Market Snapshot Clarity**  
- Clean, scannable formatting with color-coded arrows (▲/▼) improved readability  
- Included both major indices *and* sector-specific movers (Tech vs. Alt/Hedge)  

✅ **AI & Tech Developments Section**  
- Connected Railway’s funding to semiconductor/data center plays (NVIDIA, AMT)  
- Highlighted *non-obvious* pressure points (Claude Code vs. free alternatives)  

✅ **Geopolitical Context**  
- Linked Iran ceasefire to market highs *and* persistent energy risks (Hormuz blockade → oil hedges)  

---  

### **Improvement Areas**  
⚠️ **Weak Options Analysis**  
- User rated options ideas "weak" – didn’t calculate annualized yields for covered calls  
- Missed asymmetric opportunities (e.g., SpaceX IPO → space ETF mispricing)  

⚠️ **Portfolio Integration**  
- Holdings table was empty – should’ve auto-pulled from Yahoo Finance API  
- No linkage between recommendations (e.g., NVDA $300 target) and portfolio positions  

⚠️ **Rate Limit Issue**  
- Failed to handle LLM error gracefully (429 error). Should’ve:  
  - Switched to cached data  
  - Provided manual workaround faster  

---  

### **Patterns Noticed**  
🔍 **High Ratings Correlate With:**  
- Cross-domain insights (e.g., AI funding → chip demand)  
- Clear time horizons (swing vs. long-term calls)  

🔍 **Low Ratings Correlate With:**  
- Generic options ideas (lack of yield math)  
- Missing portfolio context (no position sizing)  

---  

### **Next-Run Fixes**  
1. **Pre-calculate Options Math**

## Run: 2026-04-22 21:07 UTC
[ERROR: OPENROUTER_API_KEY not set]

## Run: 2026-04-22 21:19 UTC
[LLM unavailable after 3 attempts]

## Run: 2026-04-22 23:29 UTC
# LEARNINGS.md - 2026-04-22 23:29 UTC

### What worked well in this run:
- **Market Snapshot Clarity**: The portfolio and indices performance were clearly presented with concise percentage changes, making it easy to grasp market trends at a glance. User feedback highlighted this as a strength (e.g., "Good summary of indices").
- **Tech Developments Relevance**: The analysis of Railway’s AI-native cloud challenge and Slackbot AI transformation tied tech developments to actionable investment insights, particularly for semis and cloud infrastructure stocks.
- **Portfolio Performance Tracking**: The detailed breakdown of current holdings and cost basis provided transparency and helped users contextualize the recommendations.

### What could be improved:
- **Outdated Data**: Multiple users pointed out that options data and stock prices (e.g., PLTR) were outdated. This undermines credibility and usefulness. Prioritize real-time or near-real-time data sourcing.
- **Mainstream Recommendations**: Feedback criticized the stock picks as too mainstream (e.g., "recommendations are too mainstream"). Explore more niche or under-the-radar opportunities to diversify recommendations.
- **Depth of Reasoning**: Users requested deeper explanations and learning insights behind recommendations (e.g., "teach me while recommending"). Include more detailed rationale, risk analysis, and educational content.
- **Options Recommendations Weakness**: One user noted that options ideas were weak. Strengthen this section with more sophisticated strategies and up-to-date data.

### Patterns noticed in portfolio performance vs recommendations:
- **High Conviction, Low Performance**: NVDA recommendation has a 5/10 confidence level, yet it remains flat. This highlights a need for better conviction accuracy and alignment with market trends.
- **Missed Opportunities**: Users suggested stocks like PLTR and MU, which were not included in recommendations. This signals a potential blind spot in identifying emerging or high-potential plays.

### How to increase conviction accuracy for a 90-95% win rate

## Run: 2026-04-24 11:04:58
Here's my critical self-assessment and learnings from this run:

**LEARNINGS.md - 2026-04-24**

- **What worked well**:
  - Portfolio movers section effectively highlighted key gainers/losers (WOLF +9%, NVTS -7%) with clear formatting - aligns with user praise for "big event" visibility
  - Market narrative tied specific stock movements to macro catalysts (Taiwan Semi guidance, PPI data) - matches user preference for explanatory depth
  - Flagged data issues (OPENZ, SNDK) demonstrated analytical rigor - addresses prior complaints about outdated data

- **Improvement opportunities**:
  - Failed to connect analysis to user's actual holdings (NVDA, SMCI, PLTR positions visible in portfolio) - misses key feedback about personalization
  - No options analysis despite portfolio containing options positions - ignores repeated user requests for options education
  - Sentiment section marked "unavailable" shows incomplete data integration - contradicts user desire for comprehensive insights

- **Portfolio-recommendation gaps**:
  - Highlighted SMCI's 8.9% gain but didn't analyze position sizing (user holds 100 shares) - misses portfolio management opportunity
  - No commentary on PLTR despite being user's largest holding ($32k position) - ignores explicit user interest in this stock
  - RR's -3.5% move noted without discussing portfolio impact (1,647 shares held) - lacks position-aware risk analysis

- **Conviction accuracy boosters**:
  - Need deeper fundamental checks (e.g., verify SNDK's $996 price against acquisition history) - prevents data errors that hurt credibility
  - Should correlate technical moves with portfolio cost basis (e.g., NVDA's $208 vs $104 avg cost) - provides clearer profit-taking context
  - Must validate all tickers against current corporate actions - addresses user frustration with "defunct"

## Run: 2026-04-30 23:47:24
## LEARNINGS.md — Run #2347

- **What worked well:** The 2026-04-23 run earned a 7/10 (highest in the sample) because recommendations were *specific and nuanced with clear reasoning* — this is the ceiling to replicate. The user explicitly valued the LEAP options explanation and the "why" behind each call. The Biggest Movers section remains useful but only when filtered by news/event significance, not just sort order. Drop generic tickers; surface the ones the user actually holds that moved >3% *and explain why*.

- **Persistent data quality failure:** Multiple users called out outdated options data, stale prices (PLTR cited twice), and 2-year-old options chains. This single issue dragged ratings from 7→2 in one case. The system is not pulling *current-session* options Greeks, IV rank, or front-month flow data. Fix is non-negotiable before next run: real-time options data must be verified live at generation time, with timestamps shown.

- **Portfolio-aware recommendations are still absent:** Across 3 of 4 runs, the user noted recommendations don't reference or build on existing holdings. The portfolio has 67 tickers across 4 sub-portfolios with $143K cost basis — yet recommendations appear generic. The system should cross-reference every buy/sell recommendation against current positions, average cost, and P&L before suggesting. A SELL signal on a position up 40% with thesis erosion is infinitely more valuable than a generic buy.

- **Conviction accuracy gap (4.8 avg → 7+ target):** Low conviction stems from surface-level news summaries masquerading as edge. To reach 8+/10 consistently: (1) Every recommendation needs a thesis + catalyst + risk/stop level stated explicitly. (2) Recommendation tracking must *work*

## Run: 2026-05-01 00:53:35
## LEARNINGS.md — Run 0053

- **✅ Sticky reasoning worked — keep and deepen it.** The 4/10, 6/10, and 7/10 ratings all praised the shift to "specific, nuanced" recommendations with visible reasoning, especially the LEAPs explanation that "taught" the user something. The user explicitly said they want to be *taught*, not just told. Going forward, every recommendation should include a 2-sentence "because + mechanism" so the user learns the thesis, e.g., "Buy X because [catalyst], which historically has driven [outcome] in similar setups."

- **❌ Portfolio-context blindness is a recurring killer.** All three ratings complained that recommendations don't account for existing holdings (PLTR, MU, NVDA are already heavily held). The user has 516 shares of PLTR at $62.67, 18.58 shares of MU at $378.94, and 150 shares of NVDA at $103.77 — yet the report recommends or highlights these without noting concentration risk. **Rule: always cross-reference cost basis and position size before recommending. Flag positions >10% of portfolio as "already loaded — consider trimming or holding, not adding."**

- **❌ Options data staleness destroyed trust.** The 2/10 and 4/10 ratings specifically called out options data being "2 years back" and "not current." The report must surface options data dated within the last 5 trading days, or explicitly state "no current options data available" rather than silently showing stale chains. This is a credibility issue — one bad data point and the user dismisses the entire report.

- **📊 Conviction accuracy requires a feedback loop the system isn't doing.** The recommendation tracking section shows `