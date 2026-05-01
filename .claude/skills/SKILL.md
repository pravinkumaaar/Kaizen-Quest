# Kaizen Quest Skills System

This folder contains modular skills that the AI agent can use to perform specialized tasks. Each skill is a self-contained module that can be invoked independently.

## Available Skills

### 1. **portfolio-analysis** 
Deep analysis of portfolio holdings, weightings, concentration risk, and rebalancing suggestions.

### 2. **market-sentiment**
VIX-based fear/greed assessment, market timing, and macro trend analysis.

### 3. **crypto-tracker**
Cryptocurrency price tracking, market cap analysis, and crypto-specific investment ideas.

### 4. **macro-research** 
Deep-dive macroeconomic research using web search and news analysis.

### 5. **options-intelligence**
Live options chain analysis, implied volatility tracking, and strategy recommendations.

### 6. **learning-curator**
Weekly theme management, daily deep-dives, and educational content curation.

### 7. **news-researcher**
RSS feed aggregation, news summarization, and cross-domain pattern recognition.

### 8. **investment-analyst**
Full investment analysis for specific tickers with thesis, catalysts, and risk assessment.

### 9. **recommendation-tracker**
Manage active recommendations, track performance, and update P&L.

---

## How Skills Work

Each skill is defined by a Python module in `skills/` folder and can be:
1. **Imported** into `agent.py` for regular use
2. **Invoked independently** for specific tasks
3. **Combined** with other skills for complex analysis

---

## Using Skills in Agent

```python
# In agent.py
from skills.portfolio_analysis import analyze_portfolio_weightage, suggest_rebalancing
from skills.market_sentiment import get_market_sentiment, analyze_macro_trends

# Skills are called based on the task
portfolio_data = analyze_portfolio_weightage()
sentiment = get_market_sentiment()
```

---

## Creating New Skills

1. Create a new Python file in `skills/` folder
2. Define functions with clear docstrings
3. Import and use in `agent.py` or call independently
4. Document the skill in this file

---

**Note**: The agent currently has all logic in `agent.py`. Skills modules are being extracted to make the codebase more modular and maintainable.
