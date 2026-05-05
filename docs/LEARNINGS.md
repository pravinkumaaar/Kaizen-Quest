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

## Run: 2026-05-05 03:43:37
# LEARNINGS.md — 2026-05-05

## Run 0343 Performance Review

---

- **Portfolio-aware analysis is winning but too narrow.** The 8.5/10 run on 04-30 succeeded because it analyzed actual holdings, weightages, and cost bases rather than generic picks. But the user explicitly called out that it *only* recommended from within the portfolio and missed new opportunities outside of it. Going forward: every scan must have a dual bucket — (A) portfolio position management (trim/add/hold with thesis for each), AND (B) 3–5 new actionable tickers NOT currently held that present compelling risk/reward. The 4.8 average confirms this: once the agent broke the pattern of only looking inward, the rating jumped to 8.5. Reversion to generic reporting dropped it back down.

- **Recommendation tracking remains non-functional, and repeat options data staleness is a trust killer.** The 04-23 user (7/10) noted "recommendation tracking part isn't working" — this is still unresolved. The active recommendations section was left as a placeholder comment. Users across multiple runs flagged stale options data (quotes from 2 years ago). The track record must be maintained in a structured format: date entered, ticker, direction (buy/sell/trim), thesis in one sentence, entry price, current price, P&L%, and pending/closed status. Every day's report should append new evaluations and score the previous day's recommendations. Without this, the "conviction accuracy" goal is meaningless — you can't claim a win rate if you're not actually tracking outcomes.

- **Sort holdings display by absolute dollar impact (shares × price change %), not by price level or alphabetical read-order.** Multiple users have said the portfolio movers list reads as "random." Currently it

## Run: 2026-05-05 10:59:15
## LEARNINGS.md

- **Strengths in this run:** The portfolio-centric approach continues to resonate with the user — the 8.5/10 rating on 2026-04-30 confirmed that analyzing existing holdings with thesis, weightage, and actionable suggestions is the highest-value feature. The news quality was also praised as "highest quality" in that run. The options education component (LEAPs, reasoning, teaching) has been consistently rated positively across multiple runs (4/10, 7/10, 8.5/10 runs all highlighted this). The biggest movers section in this run is a direct response to the 6/10 feedback requesting event-driven sorting — this is the right direction.

- **Critical gap — recommendations are too narrow:** The 8.5/10 user explicitly stated the "biggest problem" was that the system only recommends buy/sell actions on *existing* portfolio holdings and never surfaces *new* opportunities. This is a recurring theme: the 2/10 user wanted "more niche stocks that are not just megacaps," and the 4/10 user wanted deeper conviction on names like PLTR and MU. The system must add a dedicated "New Opportunities" section that screens for high-conviction tickers *not currently held*, using momentum, sector rotation signals, and thematic alignment with the user's existing strategy (AI infrastructure, quantum, space, fintech).

- **Data freshness is a persistent trust killer:** The 2/10 and 4/10 users both flagged outdated options data and stale price references (e.g., PLTR price not current). Even though this run shows live prices, the system must explicitly timestamp all data sources and flag any data older than 24 hours. A "Data Freshness" badge (✅ Live / ⚠️ Delayed / ❌ St

## Run: 2026-05-05 12:46:45
## LEARNINGS.md — 2026-05-5

• **Portfolio-aware analysis finally landed — but stop there at your peril.** The 8.5/10 run succeeded because it read actual holdings, compared cost basis to current prices, and gave position-specific theses. But the user explicitly said: *"only considered stocks from my portfolio — I want new stocks I may not have."* From now on, every report must have TWO sections: (1) portfolio position review AND (2) 3–5 new ticker ideas outside the portfolio with full thesis. Permanent rule, no exceptions.

• **Data freshness is non-negotiable.** Multiple users flagged outdated options data and stale PLTR prices across separate sessions. If a data source is older than 48 hours, say so explicitly and flag it — never present old data as current. Build a "data age" check into every ticker snippet: show the timestamp of the last price/volume update. If options data can't be confirmed live, drop the options section entirely rather than risk presenting 2-year-old expirations as actionable.

• **Recommendation tracking / decision journal is still a ghost section.** The 7/10 review pointed out it "isn't working" — and in this run it's literally empty (`<!-- Agent will update -->`). Every single run must log: (a) what was recommended last run, (b) what the P&L on that recommendation is today, (c) whether the thesis played out or broke. This is the single highest-leverage fix for hitting the 90–95% win-rate goal — you can't improve conviction accuracy if you don't track what you said and what happened.

• **Prioritize movers by event, not just magnitude.** A user (6/10) said they want *"the ones that had a big event or news or moved the

## Run: 2026-05-05 17:06:13
# LEARNINGS.md — 2026-05-05 17:06:13 (Run 1706)

- **✅ Biggest mover formatting worked well this time** — The user explicitly asked (6/10 rating) to see positions with the biggest daily moves first, not random order. This run correctly surfaced STRL (+47%), SHOP (-14.6%), SNDK (+12%), MU (+11.2%) etc. at the top of the portfolio display. The user's ratings climbed from 2 → 6 → 7 → 8.5 as this was fixed. *Lesson: Always sort the portfolio movers section by absolute daily change descending. Never present holdings in the order they were read from a file.*

- **❌ Portfolio-only recommendation tunnel vision persists and the user noticed (8.5/10)** — The latest rating praised understanding of positions but penalized only recommending from existing holdings. The user wants NEW tickers never held that may present better opportunities. The system has 67+ tickers and 19 consolidated holdings — there's enough context about the user's style (AI infrastructure, semis, quantum computing, fintech) to screen and suggest positions outside the current portfolio. *Recommendation engine must include a "new ideas" section with 2-3 tickers the user does NOT own, backed by screening criteria and thesis.*

- **❌ Options data freshness is still a critical failure point** — The 2/10 user flagged "options data is completely outdated and from 2 years back." Despite partial improvements (4/10 acknowledged "good options recommendations" but "PLTR data was old"), this remains unresolved. OWL must ensure options chains (iv, bid/ask, OI, Greeks) reflect current market conditions, not stale historical data. If real-time options data