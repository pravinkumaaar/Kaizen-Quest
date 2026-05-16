# News Researcher Skill

## Description
Handles all news-related functionality: RSS feed aggregation, news summarization, cross-domain pattern recognition, and web search via Tavily.

## When to Use
- Generating daily news digest
- Deep-dives on specific topics (Tavily search)
- Cross-domain pattern recognition
- Connecting news to investment themes

## Instructions

### 1. RSS Feed Aggregation
Fetch from these categories (limit 4-6 items per category for token efficiency):
- 🤖 AI & Tech: VentureBeat, Ars Technica, TechCrunch, Hacker News
- 📈 Markets & Finance: The Daily Upside, OilPrice, MarketWatch
- 🌍 Geopolitics: Foreign Policy, The Economist
- 🔬 Science & Health: Science Daily, Nature
- 💡 Business & Ideas: a16z, NPR Planet Money

**Cache**: 1 hour (avoid re-fetching)

### 2. Finnhub Market News
Free tier: 60 req/min. Get general market news (8 items max).

### 3. Tavily Web Search
Free tier: 1,000 searches/month. Use SPARINGLY (2x/day max):
- Only in morning (11 AM) and evening (5 PM) runs
- Deep-dive on top story of the day
- Query: "latest [topic] investment implications"

### 4. Generate News Digest
Structure:
```markdown
## 🤖 AI & Tech Developments
3-5 key stories. For each: what happened + why it matters for investors/learners.

## 📈 Markets & Economics
What moved? Why? Connect to Fed policy, rates, dollar strength, earnings, geopolitical risk.

## 🌍 Geopolitics & Supply Chains
Conflicts, trade tensions, resource competition, sanctions. Investment implications.

## 🔬 Science & Health Signal
1-2 developments worth knowing. Longevity? Energy? Materials? Biotech?

## 💡 Cross-Domain Insight of the Day
One non-obvious connection across today's stories. First-principles thinking.
```

### 5. Summarization for Token Efficiency
- Summarize long texts to 200-300 words before sending to LLM
- Keep key facts, insights, and actionable points
- Use `summarize_text()` function

## Output Format

```markdown
## 📰 Daily Intelligence Digest

### 🤖 AI & Tech Developments
**Nvidia announces new AI chip** (Source: VentureBeat)
Why it matters: Accelerates data center buildout, benefits SMCI, cooling companies.

### 📈 Markets & Economics
Fed pauses rates. Dollar weakens. Emerging markets rally.
Connection: Rate-sensitive sectors (tech, growth) outperform.

### 🌍 Geopolitics
Trade tensions with China escalate. Semiconductor sanctions tightened.
Implication: Domestic chip makers (NVDA, AMD) gain market share.

### 🔬 Science
New longevity drug shows 30% lifespan extension in mice.
Relevance: Watch biotech sector for translational opportunities.

## 💡 Cross-Domain Insight
AI infrastructure boom + energy transition = massive power demand.
Play: Utilities, renewable energy, nuclear (small modular reactors).
```

## Key Reminders
- Use emojis: 🤖 AI, 📈 Markets, 🌍 Geo, 🔬 Science, 💡 Business
- Be specific: ticker symbols, percentages, company names
- Connect dots: "This matters because..."
- Skip fluff: Every sentence should earn its place
- Token efficiency: Limit RSS to 3 items/category, summarize before LLM
- Tavily sparingly: 2x/day max to conserve 1,000/month limit
