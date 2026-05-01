#!/usr/bin/env python3
"""
Personal AI Agent v2.2
- News digest across AI, tech, finance, geopolitics, science
- Long-term & swing investment ideas (stocks, ETFs, crypto, metals)
- Options intelligence (LEAPS, asymmetric plays, covered calls, puts)
- Learning recommendations with rotating weekly themes
- Self-improving memory system
- Portfolio CSV import from Yahoo Finance (watchlist auto-updated)
- Live options data via Polygon.io or Alpaca
- Efficient rating-based feedback loop
- Free models first (Qwen, Llama), fallback to DeepSeek Chat (cheaper, high quality)
"""

import os
import sys
import json
import time
import csv
import datetime
import feedparser
import requests
import yfinance as yf
from pathlib import Path
from openai import OpenAI
from io import StringIO

# ─────────────────────────────────────────────
# SKILLS IMPORTS (Modular like Claude Code)
# ─────────────────────────────────────────────
# Import skill modules for better organization
# These can be used independently or called from main agent
try:
    from skills.portfolio_analysis import analyze_portfolio_weightage, suggest_rebalancing
    from skills.market_sentiment import get_market_sentiment, analyze_macro_trends
    from skills.crypto_tracker import fetch_crypto_prices, analyze_crypto_portfolio
    from skills.options_intelligence import fetch_options_snapshot, get_options_ideas
    from skills.news_research import fetch_rss, tavily_search, finnhub_news
    from skills.learning_curator import get_or_create_weekly_theme, generate_learning_content
    from skills.recommendation_tracker import clear_active_recommendations as clear_recs, parse_and_store_recommendations, update_recommendation_performance
    from skills.alpaca_trading import get_account_info, get_positions, get_portfolio_history
    from skills.benchmark_tracker import get_index_prices, compare_to_benchmarks, update_benchmark_log, get_performance_summary
    from skills.clickup_integration import create_recommendation_task, send_daily_summary, get_active_recommendations
    from skills.memory_manager import init_memory_system, update_hot_memory, get_memory_for_run
    SKILLS_AVAILABLE = True
    print("[✓] Skills modules loaded successfully")
except ImportError as e:
    SKILLS_AVAILABLE = False
    print(f"[!] Skills modules not available: {e}")
    print("[!] Running with built-in functions (skills will be added soon)")

# ---------------------------------------------------------------------------
# UTILITY: Clear active recommendations
# ---------------------------------------------------------------------------
def clear_active_recommendations():
    """Reset the RECOMMENDATIONS.md file to a clean state.
    Keeps the file but removes any existing active recommendation entries.
    This is called at the start of each run to ensure a fresh list.
    """
    try:
        # Preserve any static sections (e.g., headers) but remove the active list
        content = RECOMMENDATIONS_FILE.read_text(encoding="utf-8") if RECOMMENDATIONS_FILE.exists() else ""
        # Remove the "## Active Recommendations" section if present
        if "## Active Recommendations" in content:
            parts = content.split("## Active Recommendations")
            # Keep everything before the header and add a fresh placeholder
            new_content = parts[0] + "## Active Recommendations\n<!-- Agent will update this section with current recommendations -->\n"
        else:
            new_content = "## Active Recommendations\n<!-- Agent will update this section with current recommendations -->\n"
        RECOMMENDATIONS_FILE.write_text(new_content, encoding="utf-8")
        log("✓ Cleared active recommendations")
    except Exception as e:
        log_error("Failed to clear recommendations", e)

# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "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")
TAVILY_API_KEY     = os.environ.get("TAVILY_API_KEY", "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")
FINNHUB_API_KEY    = os.environ.get("FINNHUB_API_KEY", "d7kj3h9r01qiqbcuk1ugd7kj3h9r01qiqbcuk1v0")
POLYGON_API_KEY    = os.environ.get("POLYGON_API_KEY", "Ojx6p343h5SwBVq_0ZOntf_dbpcm5EAy")  # For live options
ALPACA_API_KEY     = os.environ.get("ALPACA_API_KEY", "")   # Alternative options source

# ─────────────────────────────────────────────
# MODEL CONFIGURATION (Comprehensive Free Models + Smart Routing)
# ─────────────────────────────────────────────

# Comprehensive list of free models on OpenRouter (in order of preference)
# Updated April 2026 - includes frontier-adjacent models with 262K+ context
# NOTE: Models are tested and verified to be available
FREE_MODELS = [
    # Latest OpenRouter free models (updated April 2026 - 33 models available)
    "openrouter/owl-alpha",                           # Owl Alpha - OpenRouter's latest
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",  # NVIDIA Nemotron reasoning
    "poolside/laguna-xs.2:free",                      # Poolside Laguna XS.2
    "poolside/laguna-m.1:free",                       # Poolside Laguna M.1
    "inclusionai/ling-2.6-1t:free",                  # InclusionAI Ling 2.6
    "tencent/hunyuan-3-preview:free",                  # Tencent Hunyuan 3
    "baidu/qianfan-ocr-fast:free",                   # Baidu Qianfan OCR
    "google/gemma-4-26b-a4b-it:free",                # Google Gemma 4
    "google/gemma-4-31b-it:free",                  # Google Gemma 4 31B
    "nvidia/nemotron-3-super-120b-a12b:free",        # NVIDIA Nemotron 120B
    "minimax/minimax-m2.5:free",                    # MiniMax M2.5
    "openrouter/free",                             # OpenRouter default free
    "liquid/lfm-2.5-1.2b-thinking:free",            # Liquid LFM 2.5 Thinking
    "liquid/lfm-2.5-1.2b-instruct:free",           # Liquid LFM 2.5 Instruct
    "nvidia/nemotron-3-nano-30b-a3b:free",          # NVIDIA Nemotron 30B
    "nvidia/nemotron-nano-12b-v2-vl:free",           # NVIDIA Nemotron Nano 12B
    "qwen/qwen3-next-80b-a3b-instruct:free",         # Qwen3 Next 80B
    "nvidia/nemotron-nano-9b-v2:free",              # NVIDIA Nemotron Nano 9B
    "meta-llama/llama-3.3-70b-instruct:free",       # Llama 3.3 fallback
    "mistralai/mistral-large:free",                  # Mistral Large fallback
    "mistralai/mixtral-8x7b-instruct:free",         # Mixtral fallback
]

# Value-optimized paid models by task type
# DeepSeek Chat is best value for general tasks (5x cheaper than reasoning)
STANDARD_MODELS = [
    "deepseek/deepseek-chat",                     # Best value: fast, cheap, good quality
]

# Reasoning models - ONLY used for complex analysis tasks
REASONING_MODELS = [
    "deepseek/deepseek-reasoner",                 # Deep reasoning when needed
]

# Task complexity routing
TASK_COMPLEXITY = {
    "news_digest": "simple",              # Just summarizing news
    "market_data": "simple",              # Fetching prices
    "investment_ideas": "moderate",       # Needs analysis but not deep reasoning
    "options_ideas": "moderate",          # Technical but standard strategies
    "learning_topic": "moderate",         # Educational but straightforward
    "self_reflect": "complex",            # Deep analysis of performance patterns
}

# Track models that returned permanent errors this run (e.g., 404, 402)
UNAVAILABLE_MODELS = set()

def get_models_for_task(task_type: str = "general") -> list:
    """
    Get appropriate model list based on task complexity.
    
    Simple tasks: Use all free models, fallback to standard paid
    Moderate tasks: Free models, standard paid, avoid reasoning
    Complex tasks: Free/standard, then reasoning model if needed
    """
    complexity = TASK_COMPLEXITY.get(task_type, "moderate")
    
    if complexity == "simple":
        # Simple tasks: just use free models + cheap standard
        models = FREE_MODELS + STANDARD_MODELS
        return [m for m in models if m not in UNAVAILABLE_MODELS]
    
    elif complexity == "moderate":
        # Moderate tasks: free models + standard paid (skip expensive reasoning)
        models = FREE_MODELS + STANDARD_MODELS
        return [m for m in models if m not in UNAVAILABLE_MODELS]
    
    else:  # complexity == "complex"
        # Complex tasks: free → standard → reasoning (if really needed)
        models = FREE_MODELS + STANDARD_MODELS + REASONING_MODELS
        return [m for m in models if m not in UNAVAILABLE_MODELS]

BASE_DIR      = Path(__file__).parent
MEMORY_FILE   = BASE_DIR / "docs" / "MEMORY.md"
LEARNING_FILE = BASE_DIR / "docs" / "LEARNINGS.md"
CONTEXT_FILE  = BASE_DIR / "docs" / "CONTEXT.md"
RECOMMENDATIONS_FILE = BASE_DIR / "docs" / "RECOMMENDATIONS.md"
PORTFOLIO_FILE = BASE_DIR / "docs" / "PORTFOLIO.md"
RATINGS_FILE  = BASE_DIR / "docs" / "RATINGS.md"
WEEKLY_THEMES_FILE = BASE_DIR / "docs" / "WEEKLY_THEMES.md"
RSS_CACHE_FILE = BASE_DIR / "cache" / "rss_cache.json"
RSS_CACHE_DURATION = 3600  # 1 hour cache for RSS feeds
REPORTS_DIR   = BASE_DIR / "REPORTS"
HISTORY_DIR   = BASE_DIR / "HISTORY"
LOG_FILE      = BASE_DIR / "logs" / "agent.log"

# ─────────────────────────────────────
# CLAUDE-CODE STYLE SKILLS SYSTEM
# ─────────────────────────────────────
# Skills are markdown instruction files in .claude/skills/
# The agent reads these before each task (like Claude Code)

def load_skill(skill_name: str) -> str:
    """Load a skill's markdown instructions from .claude/skills/ folder."""
    skill_path = BASE_DIR / ".claude" / "skills" / f"{skill_name}.SKILL.md"
    if skill_path.exists():
        return skill_path.read_text(encoding="utf-8")
    return ""

# Pre-load all skills at startup for efficiency
SKILLS = {}
SKILL_NAMES = [
    "portfolio-analysis",
    "market-sentiment", 
    "crypto-tracker",
    "news-researcher",
    "options-intelligence",
    "learning-curator",
    "investment-analyst",
    "recommendation-tracker"
]

for skill_name in SKILL_NAMES:
    skill_content = load_skill(skill_name)
    if skill_content:
        SKILLS[skill_name] = skill_content

print(f"[✓] Loaded {len(SKILLS)} skills from .claude/skills/")

# ─────────────────────────────────────────────
# LOGGING (CLEAN & CONCISE)
# ─────────────────────────────────────────────
def log(msg: str, level: str = "INFO"):
    """Log to console and file with clean formatting. Skip error spam unless critical."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timestamp}] {level}: {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def log_error(msg: str, error: Exception = None, verbose: bool = False):
    """Log errors cleanly — skip noise from model failures."""
    if error and not verbose:
        error_str = str(error)[:80]  # Truncate long errors
        log(f"{msg} ({error_str})", level="ERROR")
    elif verbose:
        log(f"{msg}: {error}", level="ERROR")
    else:
        log(msg, level="ERROR")


# ─────────────────────────────────────────────
# LLM CLIENT (OpenRouter — free models first)
# ─────────────────────────────────────────────
_client = None
def get_client():
    global _client
    if _client is None:
        _client = OpenAI(
            api_key=OPENROUTER_API_KEY or "no-key",
            base_url="https://openrouter.ai/api/v1",
        )
    return _client

def call_llm(system: str, user: str, max_tokens: int = 2000, task_type: str = "general", model: str = None) -> str:
    """
    Call LLM with intelligent model routing:
    1. Try all free models first (comprehensive list)
    2. Fall back to standard paid model (DeepSeek Chat - best value)
    3. Only use reasoning model for complex tasks if needed
    4. Clean error handling — no verbose error spam
    
    Args:
        system: System prompt
        user: User message
        max_tokens: Max tokens to generate
        task_type: Task type for intelligent routing (affects model selection)
        model: Override model selection (optional)
    """
    if not OPENROUTER_API_KEY:
        return "[ERROR: OPENROUTER_API_KEY not set]"
    
    # If a specific model was requested but it's known to be unavailable, skip
    if model and model in UNAVAILABLE_MODELS:
        model_name = model.split('/')[-1]
        log(f"⚠ {model_name}: Previously marked unavailable, skipping", level="WARN")
        return f"[LLM unavailable: {model_name} marked unavailable]"

    # Get model list based on task complexity
    if model:
        models_to_try = [model]
    else:
        models_to_try = get_models_for_task(task_type)
    
    last_error = None
    
    for attempt, m in enumerate(models_to_try):
        try:
            resp = get_client().chat.completions.create(
                model=m,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                extra_headers={"HTTP-Referer": "https://github.com/personal-ai-agent"},
            )
            
            # Success — log which model worked (only if fallback happened)
            if attempt > 0:
                model_name = m.split('/')[-1]
                log(f"✓ Model {model_name} succeeded (after {attempt} attempt(s))")
            
            return resp.choices[0].message.content.strip()
            
        except Exception as e:
            last_error = e
            error_str = str(e)
            model_name = m.split('/')[-1]
            
            # Parse specific error codes cleanly
            if 'Error code: 429' in error_str or '429' in error_str:
                log(f"⚠ {model_name}: Rate limited (429)", level="WARN")
                # brief backoff on rate limits
                time.sleep(2)
            elif 'Error code: 402' in error_str or '402' in error_str:
                log(f"⚠ {model_name}: Spend limit exceeded (402)", level="WARN")
                # mark as unavailable for this run
                UNAVAILABLE_MODELS.add(m)
            elif 'Error code: 404' in error_str or '404' in error_str or 'model not found' in error_str.lower():
                log(f"⚠ {model_name}: Model not available (404)", level="WARN")
                # mark as unavailable for this run
                UNAVAILABLE_MODELS.add(m)
            else:
                # Log other errors but keep it concise
                log(f"⚠ {model_name}: Failed, trying next...", level="WARN")
            
            # If this was the last model, return graceful error
            if attempt == len(models_to_try) - 1:
                return f"[LLM unavailable after {len(models_to_try)} attempts]"
            
            time.sleep(1)  # Brief wait before retry
    
    return "[LLM unavailable]"

def summarize_text(text: str, context: str = "general", max_tokens: int = 300) -> str:
    """Summarize text to reduce token usage in subsequent calls."""
    if len(text) < 1000:  # If already short, return as-is
        return text
    prompt = f"Summarize the following {context} in 200-300 words, keeping key facts, insights, and actionable points:\n\n{text}"
    return call_llm(
        system="You are a concise summarizer. Extract key information without losing important details.",
        user=prompt,
        max_tokens=max_tokens,
    )


# ─────────────────────────────────────────────
# MASTER SYSTEM PROMPT
# ─────────────────────────────────────────────
# System prompt optimized for quality + token efficiency (~180 tokens)
SYSTEM = """You are a razor-sharp personal intelligence agent for an aggressive investor in Jersey City, NJ.
Think like a hedge fund analyst crossed with a Renaissance scholar — connect dots across domains, think in decades not days.

INVESTMENT PHILOSOPHY:
- Long-term and swing investor (weeks to years). NO intraday trades ever.
- Options: defined-risk only, minimum 2-week expiry (prefer 30-90 days or LEAPS 6mo-2yr)
- Options allocation: max 10% of portfolio
- NEVER recommend letting options expire ITM or any leverage
- Always label: "Not financial advice. Verify before acting."
- Recommendations can be BUY, SELL, or HOLD/CASH if no good opportunities exist.

CRITICAL RULE — COMPANY NAMES:
- When recommending a ticker, ALWAYS verify the correct company name using your knowledge.
- NEVER make up company names. If unsure, just use the ticker without a company name.
- Example: RR is Richtech Robotics (not Rolls-Royce). TEM is Tempus AI (not Templeton).
- Mismatched ticker→company names destroy credibility.

COMMUNICATION STYLE:
- Direct. No hedging for the sake of it. Say what you actually think.
- Teach frameworks, not just answers. Explain WHY so they build mental models.
- Connect ideas across AI, economics, history, science, human behavior.
- Numbers and specifics beat vague generalities."""


# ─────────────────────────────────────────────
# PORTFOLIO IMPORT (from Yahoo Finance CSV)
# ─────────────────────────────────────────────
def import_portfolio_csv(filepath: str = "portfolio.csv") -> dict:
    """
    Import portfolio from single CSV exported from Yahoo Finance.
    Expected columns: Symbol, Shares, Purchase Price, Date (optional)
    
    Returns: {
        'total': portfolio markdown for PORTFOLIO.md,
        'holdings': list of {ticker, shares, cost_basis, purchase_price}
    }
    """
    portfolio_path = Path(filepath)
    if not portfolio_path.exists():
        log(f"Portfolio CSV not found: {filepath}", level="WARN")
        return {"total": "[No portfolio CSV loaded]", "holdings": []}
    
    holdings = []
    total_cost_basis = 0
    
    try:
        with open(portfolio_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                ticker = row.get('Symbol', '').strip().upper()
                try:
                    # Yahoo Finance CSV uses 'Quantity' column; support both 'Shares' and 'Quantity'
                    shares_raw = row.get('Shares') or row.get('Quantity') or '0'
                    shares = float(shares_raw)
                    price_raw = row.get('Purchase Price') or row.get('Cost Basis') or '0'
                    price = float(price_raw)
                    if ticker and shares and price:
                        cost_basis = shares * price
                        total_cost_basis += cost_basis
                        holdings.append({
                            'ticker': ticker,
                            'shares': shares,
                            'purchase_price': price,
                            'cost_basis': cost_basis,
                            'date': row.get('Date', 'N/A')
                        })
                except ValueError:
                    continue
        
        # Build portfolio markdown
        markdown = "## Current Holdings\n\n"
        for h in holdings:
            markdown += f"- **{h['ticker']}**: {h['shares']:.2f} shares @ ${h['purchase_price']:.2f} (${h['cost_basis']:,.0f} cost basis)\n"
        
        markdown += f"\n**Total Cost Basis:** ${total_cost_basis:,.0f}\n"
        
        log(f"✓ Loaded portfolio: {len(holdings)} holdings, ${total_cost_basis:,.0f} cost basis")
        
        return {"total": markdown, "holdings": holdings}
    
    except Exception as e:
        log_error(f"Failed to import portfolio CSV", e)
        return {"total": "[Portfolio import failed]", "holdings": []}


def import_multiple_portfolios(portfolio_files: list = None) -> dict:
    """
    Import and consolidate holdings from multiple portfolio CSVs.
    If portfolio_files is None, auto-discover from portfolios/ folder.
    
    Consolidates duplicate tickers by summing shares and calculating weighted average cost basis.
    
    Returns: {
        'total': consolidated portfolio markdown for PORTFOLIO.md,
        'holdings': list of {ticker, shares, cost_basis, purchase_price, sources: count}
    }
    """
    # Auto-discover portfolio files if not specified
    if portfolio_files is None:
        portfolio_files = []
        portfolios_dir = BASE_DIR / "portfolios"
        
        # Look for portfolio1.csv through portfolio4.csv in portfolios/ folder
        for i in range(1, 5):
            path = portfolios_dir / f"portfolio{i}.csv"
            if path.exists():
                portfolio_files.append(str(path))
        
        # Also check root directory for backward compatibility
        if not portfolio_files:
            for i in range(1, 5):
                path = BASE_DIR / f"portfolio{i}.csv"
                if path.exists():
                    portfolio_files.append(str(path))
        
        if not portfolio_files:
            log("No portfolio files found (portfolio1.csv, portfolio2.csv, etc.)", level="WARN")
            return {"total": "[No portfolio CSV files loaded]", "holdings": []}
    
    # Load all portfolios and consolidate by ticker
    consolidated = {}  # ticker -> {shares, total_cost_basis, sources, prices_list}
    total_portfolios = 0
    
    for filepath in portfolio_files:
        portfolio_path = Path(filepath)
        if not portfolio_path.exists():
            log(f"Portfolio file not found: {filepath}", level="WARN")
            continue
        
        try:
            with open(portfolio_path, 'r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    ticker = row.get('Symbol', '').strip().upper()
                    try:
                        # Support both 'Shares' and 'Quantity' column names
                        shares_raw = row.get('Shares') or row.get('Quantity') or '0'
                        shares = float(shares_raw)
                        price_raw = row.get('Purchase Price') or row.get('Cost Basis') or '0'
                        price = float(price_raw)
                        if ticker and shares and price:
                            cost_basis = shares * price
                            
                            # Add to consolidated holdings
                            if ticker not in consolidated:
                                consolidated[ticker] = {
                                    'shares': 0,
                                    'total_cost_basis': 0,
                                    'sources': 0,
                                    'prices_list': []
                                }
                            
                            consolidated[ticker]['shares'] += shares
                            consolidated[ticker]['total_cost_basis'] += cost_basis
                            consolidated[ticker]['sources'] += 1
                            consolidated[ticker]['prices_list'].append(price)
                    except ValueError:
                        continue
            
            total_portfolios += 1
        
        except Exception as e:
            log_error(f"Failed to load portfolio {filepath}", e)
            continue
    
    if not consolidated:
        return {"total": "[No holdings found in portfolio files]", "holdings": []}
    
    # Convert consolidated dict to holdings list with weighted average cost basis
    holdings = []
    total_cost_basis = 0
    
    for ticker in sorted(consolidated.keys()):
        data = consolidated[ticker]
        shares = data['shares']
        total_cb = data['total_cost_basis']
        avg_price = total_cb / shares if shares > 0 else 0
        
        total_cost_basis += total_cb
        
        holdings.append({
            'ticker': ticker,
            'shares': shares,
            'purchase_price': avg_price,
            'cost_basis': total_cb,
            'sources': data['sources']
        })
    
    # Build consolidated portfolio markdown
    markdown = f"## Consolidated Holdings ({total_portfolios} portfolios)\n\n"
    markdown += "| Ticker | Shares | Avg Price | Cost Basis | From |\n"
    markdown += "|--------|--------|-----------|-----------|------|\n"
    
    for h in holdings:
        markdown += f"| **{h['ticker']}** | {h['shares']:.2f} | ${h['purchase_price']:.2f} | ${h['cost_basis']:,.0f} | {h['sources']} portfolio(s) |\n"
    
    markdown += f"\n**Total Consolidated:**\n"
    markdown += f"- Unique Tickers: {len(holdings)}\n"
    markdown += f"- Total Shares (all): {sum(h['shares'] for h in holdings):.2f}\n"
    markdown += f"- Total Cost Basis: ${total_cost_basis:,.0f}\n"
    markdown += f"- Source Portfolios: {total_portfolios}\n"
    
    unique_with_dupes = sum(1 for h in holdings if h['sources'] > 1)
    if unique_with_dupes > 0:
        markdown += f"- Consolidated Tickers (across portfolios): {unique_with_dupes}\n"
    
    log(f"✓ Loaded {total_portfolios} portfolios: {len(holdings)} unique holdings, ${total_cost_basis:,.0f} total cost basis")
    if unique_with_dupes > 0:
        log(f"  → {unique_with_dupes} tickers consolidated from multiple portfolios")
    
    return {"total": markdown, "holdings": holdings}


# ─────────────────────────────────────────────
# FREE DATA SOURCES
# ─────────────────────────────────────────────

# RSS Feeds — completely free, unlimited
RSS_FEEDS = {
    "🤖 AI & Tech": [
        "https://venturebeat.com/category/ai/feed/",
        "https://arstechnica.com/ai/feed",
        "https://techcrunch.com/feed/",
        "https://news.ycombinator.com/rss",
    ],
    "📈 Markets & Finance": [
        "https://thedailyupside.com/feed/",
        "https://oilprice.com/rss/main",
        "https://feeds.marketwatch.com/marketwatch/topstories",
    ],
    "🌍 Geopolitics": [
        "https://foreignpolicy.com/feed/",
        "https://www.economist.com/finance-and-economics/rss.xml",
    ],
    "🔬 Science & Health": [
        "https://www.sciencedaily.com/rss/top.xml",
        "https://feeds.nature.com/nature/rss/current",
    ],
    "💡 Business & Ideas": [
        "https://a16z.com/feed/",
        "https://www.npr.org/rss/rss.php?id=1006",  # Planet Money
    ],
}

def fetch_rss(max_per_feed: int = 4) -> dict:
    """Fetch RSS feeds with 1-hour cache."""
    # Check cache
    if RSS_CACHE_FILE.exists():
        try:
            cache_data = json.loads(RSS_CACHE_FILE.read_text())
            cache_time = cache_data.get("timestamp", 0)
            if time.time() - cache_time < RSS_CACHE_DURATION:
                log("Using cached RSS feeds")
                return cache_data["data"]
        except Exception:
            pass
    
    # Fetch fresh
    results = {}
    for category, urls in RSS_FEEDS.items():
        items = []
        for url in urls:
            try:
                feed = feedparser.parse(url)
                for entry in feed.entries[:max_per_feed]:
                    title   = entry.get("title", "").strip()
                    summary = entry.get("summary", entry.get("description", ""))
                    # Strip HTML tags
                    import re
                    summary = re.sub(r'<[^>]+>', '', summary)[:250]
                    published = entry.get("published", "")[:16]
                    if title:
                        items.append(f"• {title} [{published}]\n  {summary}…")
            except Exception:
                pass
        results[category] = items[:10]
    
    # Cache the results
    cache_data = {"timestamp": time.time(), "data": results}
    RSS_CACHE_FILE.write_text(json.dumps(cache_data))
    log("Cached fresh RSS feeds")
    return results

def fetch_crypto_prices(cryptos: list = ["BTC-USD", "ETH-USD", "XRP-USD"]) -> dict:
    """Fetch crypto prices from yfinance or CoinGecko (FREE)"""
    import requests
    result = {}
    for crypto in cryptos:
        try:
            # Try yfinance first
            t = yf.Ticker(crypto)
            price = t.fast_info.last_price
            # Fallback to CoinGecko if yfinance fails
            if price is None:
                symbol = crypto.split('-')[0].lower()
                r = requests.get(f"https://api.coingecko.com/api/v3/simple/price?ids={symbol}&vs_currencies=usd")
                data = r.json()
                price = data.get(symbol, {}).get('usd')
            result[crypto] = price
        except Exception:
            pass
    return result

def fetch_market_data() -> str:
    """Pull prices + % change for watchlist: consolidated portfolio holdings sorted by biggest movers + indices."""
    
    # Load portfolio holdings to use as primary watchlist
    portfolio_tickers = []
    portfolio_costs = {}  # ticker -> cost_basis for weighting
    try:
        portfolios_dir = BASE_DIR / "portfolios"
        if portfolios_dir.exists():
            for i in range(1, 5):
                portfolio_csv = portfolios_dir / f"portfolio{i}.csv"
                if portfolio_csv.exists():
                    with open(portfolio_csv, 'r') as f:
                        reader = csv.DictReader(f)
                        for row in reader:
                            ticker = row.get('Symbol', '').strip().upper()
                            if ticker and ticker not in portfolio_tickers:
                                portfolio_tickers.append(ticker)
                                # Track cost basis for weighting
                                try:
                                    qty = float(row.get('Quantity', row.get('Shares', 0)))
                                    price = float(row.get('Purchase Price', 0))
                                    if ticker in portfolio_costs:
                                        portfolio_costs[ticker] += qty * price
                                    else:
                                        portfolio_costs[ticker] = qty * price
                                except ValueError:
                                    pass
    except Exception:
        pass
    
    # Fetch prices for ALL portfolio tickers + key indices
    all_tickers = portfolio_tickers + ["SPY", "QQQ", "IWM", "VTI", "GLD", "SLV"]
    all_tickers = list(dict.fromkeys(all_tickers))  # Remove duplicates while preserving order
    
    ticker_data = []
    crypto_tickers = [t for t in portfolio_tickers if t.endswith("-USD")]
    stock_tickers = [t for t in all_tickers if not t.endswith("-USD")]
    
    # Fetch stock prices
    for ticker in stock_tickers:
        try:
            price = None
            prev = None
            
            if FINNHUB_API_KEY:
                try:
                    r = requests.get(
                        f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}",
                        timeout=10
                    )
                    data = r.json()
                    price = data.get("c")
                    prev = data.get("pc")
                except Exception:
                    pass
            
            if price is None:
                old_stderr = sys.stderr
                sys.stderr = StringIO()
                try:
                    t = yf.Ticker(ticker)
                    info = t.fast_info
                    price = info.last_price
                    prev = info.previous_close
                except Exception:
                    pass
                finally:
                    sys.stderr = old_stderr
            
            if price and prev:
                chg = ((price - prev) / prev) * 100
                weight = portfolio_costs.get(ticker, 0)
                ticker_data.append({
                    'ticker': ticker,
                    'price': price,
                    'change': chg,
                    'is_index': ticker in ["SPY", "QQQ", "IWM", "VTI", "GLD", "SLV"],
                    'weight': weight
                })
        except Exception:
            pass
    
    # Fetch crypto prices
    crypto_prices = fetch_crypto_prices(crypto_tickers if crypto_tickers else ["BTC-USD", "ETH-USD", "XRP-USD"])
    for crypto, price in crypto_prices.items():
        if price:
            try:
                t = yf.Ticker(crypto)
                prev = t.fast_info.previous_close
                chg = ((price - prev) / prev * 100) if prev else 0
                weight = portfolio_costs.get(crypto, 0)
                ticker_data.append({
                    'ticker': crypto,
                    'price': price,
                    'change': chg,
                    'is_index': False,
                    'weight': weight,
                    'is_crypto': True
                })
            except Exception:
                ticker_data.append({
                    'ticker': crypto,
                    'price': price,
                    'change': 0,
                    'is_index': False,
                    'weight': portfolio_costs.get(crypto, 0),
                    'is_crypto': True
                })
    
    # Sort portfolio tickers by absolute change (biggest movers first) for watchlist
    portfolio_data = [t for t in ticker_data if not t.get('is_index')]
    portfolio_data.sort(key=lambda x: abs(x['change']), reverse=True)
    
    # Top movers from portfolio (show top 12 biggest movers + top 3 by weight if not already shown)
    top_movers = portfolio_data[:12]
    shown_tickers = {t['ticker'] for t in top_movers}
    
    # Add top by weight if not already in movers
    by_weight = sorted([t for t in portfolio_data if t['ticker'] not in shown_tickers], 
                       key=lambda x: x['weight'], reverse=True)
    top_weight = by_weight[:3]
    
    lines = []
    lines.append(f"\n  [📊 Your Portfolio — Biggest Movers Today ({len(portfolio_tickers)} total holdings)]")
    for t in top_movers + top_weight:
        arrow = "▲" if t['change'] >= 0 else "▼"
        tag = " 💰" if t['weight'] > 0 and t in top_weight and t not in top_movers[:12] else ""
        lines.append(f"    {t['ticker']:<10} ${t['price']:>9.2f}  {arrow}{abs(t['change']):.2f}%{tag}")
    
    # Indices
    lines.append("\n  [Indices & Benchmarks]")
    indices = [t for t in ticker_data if t.get('is_index')]
    indices.sort(key=lambda x: abs(x['change']), reverse=True)
    for t in indices:
        arrow = "▲" if t['change'] >= 0 else "▼"
        lines.append(f"    {t['ticker']:<10} ${t['price']:>9.2f}  {arrow}{abs(t['change']):.2f}%")
    
    return "\n".join(lines)

def tavily_search(query: str, n: int = 4) -> str:
    """Tavily web search — free tier: 1,000/month."""
    if not TAVILY_API_KEY:
        return "[Tavily not configured]"
    try:
        r = requests.post(
            "https://api.tavily.com/search",
            json={"api_key": TAVILY_API_KEY, "query": query,
                  "max_results": n, "search_depth": "basic"},
            timeout=20
        )
        results = r.json().get("results", [])
        return "\n".join(
            f"• {x.get('title','')}\n  {x.get('content','')[:280]}"
            for x in results
        ) or "No results."
    except Exception as e:
        log_error("Tavily search failed", e)
        return "[Tavily unavailable]"

def finnhub_news(n: int = 8) -> str:
    """Finnhub general market news — free tier: 60 req/min."""
    if not FINNHUB_API_KEY:
        return "[Finnhub not configured]"
    try:
        r = requests.get(
            "https://finnhub.io/api/v1/news",
            params={"category": "general", "token": FINNHUB_API_KEY},
            timeout=15
        )
        items = r.json()[:n]
        return "\n".join(
            f"• {x.get('headline','')}\n  {x.get('summary','')[:200]}"
            for x in items
        )
    except Exception as e:
        log_error("Finnhub news fetch failed", e)
        return "[Finnhub unavailable]"


# ─────────────────────────────────────────────
# LIVE OPTIONS DATA (Polygon.io or Alpaca)
# ─────────────────────────────────────────────
def fetch_options_snapshot_polygon(tickers: list) -> str:
    """
    Fetch live options data from Polygon.io (recommended).
    Free tier: 5 API calls/min.
    Requires POLYGON_API_KEY from environment.
    """
    if not POLYGON_API_KEY:
        return fetch_options_snapshot_yfinance(tickers)  # Fallback to yfinance
    
    lines = []
    today = datetime.date.today()
    min_expiry = today + datetime.timedelta(days=14)
    
    for ticker in tickers:
        try:
            # Get options contracts for this ticker
            r = requests.get(
                f"https://api.polygon.io/v3/snapshot/options/{ticker}",
                params={"apikey": POLYGON_API_KEY},
                timeout=10
            )
            
            if r.status_code != 200:
                continue
            
            data = r.json().get("results", {})
            if not data:
                continue
            
            # Get current price
            t = yf.Ticker(ticker)
            price = t.fast_info.last_price
            if not price:
                continue
            
            lines.append(f"\n{ticker} @ ${price:.2f}")
            
            # Parse option chain data
            options = data.get("options", [])
            
            # Filter to relevant expirations
            expirations = {}
            for opt in options:
                exp_date = opt.get("expiration_date", "")
                if exp_date and datetime.date.fromisoformat(exp_date) >= min_expiry:
                    if exp_date not in expirations:
                        expirations[exp_date] = {"calls": [], "puts": []}
                    
                    opt_type = opt.get("option_type", "").lower()
                    strike = opt.get("strike_price", 0)
                    
                    # Store ATM options (within 5% of price)
                    if abs(strike - price) / price < 0.05:
                        bid = opt.get("bid", None)
                        ask = opt.get("ask", None)
                        iv = opt.get("implied_volatility", None)
                        
                        data_point = {
                            "strike": strike,
                            "bid": bid,
                            "ask": ask,
                            "iv": iv
                        }
                        
                        if opt_type == "call":
                            expirations[exp_date]["calls"].append(data_point)
                        else:
                            expirations[exp_date]["puts"].append(data_point)
            
            # Show top 2 expirations
            for exp_date in sorted(expirations.keys())[:2]:
                days_out = (datetime.date.fromisoformat(exp_date) - today).days
                lines.append(f"  Expiry {exp_date} ({days_out}d):")
                
                exp_data = expirations[exp_date]
                
                if exp_data["calls"]:
                    call = exp_data["calls"][0]
                    iv_str = f" IV={call['iv']:.0%}" if call.get('iv') else ""
                    lines.append(f"    ATM Call: bid=${call['bid']:.2f} ask=${call['ask']:.2f}{iv_str}")
                
                if exp_data["puts"]:
                    put = exp_data["puts"][0]
                    iv_str = f" IV={put['iv']:.0%}" if put.get('iv') else ""
                    lines.append(f"    ATM Put:  bid=${put['bid']:.2f} ask=${put['ask']:.2f}{iv_str}")
        
        except Exception as e:
            log_error(f"Polygon options for {ticker} failed", e)
            continue
    
    return "\n".join(lines) if lines else fetch_options_snapshot_yfinance(tickers)

def fetch_options_snapshot_yfinance(tickers: list) -> str:
    """
    Free fallback: Fetch options chain summary for key tickers via yfinance.
    Updated with current market data.
    """
    lines = []
    today = datetime.date.today()
    min_expiry = today + datetime.timedelta(days=14)

    for ticker in tickers:
        try:
            old_stderr = sys.stderr
            sys.stderr = StringIO()
            try:
                t = yf.Ticker(ticker)
                price = t.fast_info.last_price
                exps  = t.options
            finally:
                sys.stderr = old_stderr

            if not exps or not price:
                continue

            # Filter to expiries ≥ 2 weeks out
            valid_exps = [e for e in exps
                          if datetime.date.fromisoformat(e) >= min_expiry]

            if not valid_exps:
                continue

            # Show next 2 valid expiries (prefer 30-90 day, then LEAPS)
            target_exps = []
            for e in valid_exps:
                days_out = (datetime.date.fromisoformat(e) - today).days
                if 14 <= days_out <= 400:
                    target_exps.append(e)
                if len(target_exps) >= 2:
                    break

            # Also grab a LEAPS if available
            for e in valid_exps:
                days_out = (datetime.date.fromisoformat(e) - today).days
                if days_out > 180 and e not in target_exps:
                    target_exps.append(e)
                    break

            lines.append(f"\n{ticker} @ ${price:.2f}")
            lines.append(f"  Available expiries (≥2wk): {', '.join(valid_exps[:6])}")

            # For each target expiry, show ATM options
            for exp in target_exps[:2]:
                try:
                    sys.stderr = StringIO()
                    try:
                        chain = t.option_chain(exp)
                    finally:
                        sys.stderr = old_stderr
                        
                    days_out = (datetime.date.fromisoformat(exp) - today).days

                    # Find ATM call (strike closest to current price)
                    calls = chain.calls.copy()
                    calls['diff'] = abs(calls['strike'] - price)
                    atm_call = calls.nsmallest(1, 'diff').iloc[0]

                    # Find ATM put
                    puts = chain.puts.copy()
                    puts['diff'] = abs(puts['strike'] - price)
                    atm_put = puts.nsmallest(1, 'diff').iloc[0]

                    lines.append(f"  Expiry {exp} ({days_out}d out):")
                    lines.append(f"    ATM Call ${atm_call['strike']:.0f}: "
                                 f"bid=${atm_call['bid']:.2f} ask=${atm_call['ask']:.2f} "
                                 f"IV={atm_call['impliedVolatility']:.0%}")
                    lines.append(f"    ATM Put  ${atm_put['strike']:.0f}: "
                                 f"bid=${atm_put['bid']:.2f} ask=${atm_put['ask']:.2f} "
                                 f"IV={atm_put['impliedVolatility']:.0%}")
                except Exception:
                    pass

        except Exception:
            pass

    return "\n".join(lines) if lines else "[Options data unavailable]"

# Choose based on available API keys
def fetch_options_snapshot(tickers: list) -> str:
    """Route to best available options data source."""
    if POLYGON_API_KEY:
        return fetch_options_snapshot_polygon(tickers)
    else:
        return fetch_options_snapshot_yfinance(tickers)


# ─────────────────────────────────────────────
# MEMORY SYSTEM
# ─────────────────────────────────────────────
def read_file(path: Path, max_chars: int = None) -> str:
    try:
        text = path.read_text(encoding="utf-8") if path.exists() else ""
        if max_chars and len(text) > max_chars:
            text = "...[truncated]\n" + text[-max_chars:]
        return text
    except Exception:
        return ""

def load_memory() -> str:
    """Load memory efficiently - only last 1500 chars of learnings, last 5 ratings."""
    # Only load last portions to save tokens
    memory_full = read_file(MEMORY_FILE)
    context = read_file(CONTEXT_FILE)
    
    # Only last 1000 chars of memory
    memory_summary = memory_full[-1000:] if len(memory_full) > 1000 else memory_full
    
    # Only last 5 ratings
    ratings_full = read_file(RATINGS_FILE)
    ratings_lines = ratings_full.strip().split('\n')
    last_ratings = '\n'.join(ratings_lines[-5:]) if ratings_lines else ""
    
    # Only last 1500 chars of learnings
    learnings_full = read_file(LEARNING_FILE)
    learnings_summary = learnings_full[-1500:] if len(learnings_full) > 1500 else learnings_full
    
    # Only active recommendations (not entire history)
    recs_full = read_file(RECOMMENDATIONS_FILE)
    if "## Active Recommendations" in recs_full:
        recs_summary = recs_full.split("## Active Recommendations")[1][:800]
    else:
        recs_summary = recs_full[:800]
    
    return f"""=== MEMORY (last 1000 chars) ===
{memory_summary}

=== CURRENT CONTEXT & GOALS ===
{context}

=== PORTFOLIO HOLDINGS ===
{read_file(PORTFOLIO_FILE)}

=== ACTIVE RECOMMENDATIONS (last 800 chars) ===
{recs_summary}

=== AGENT RATINGS (last 5) ===
{last_ratings}

=== RECENT LEARNINGS (last 1500 chars) ===
{learnings_summary}
"""

def save_learnings(new_entry: str):
    existing = read_file(LEARNING_FILE)
    updated  = existing + f"\n\n## Run: {NOW}\n{new_entry}"
    if len(updated) > 18000:
        updated = "...[older entries archived in HISTORY/]\n\n" + updated[-18000:]
    LEARNING_FILE.write_text(updated, encoding="utf-8")


def get_company_info(ticker: str) -> dict:
    """Fetch real company name and info from yfinance to prevent mismatches."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        return {
            'name': info.get('longName', info.get('shortName', ticker)),
            'sector': info.get('sector', 'Unknown'),
            'industry': info.get('industry', 'Unknown')
        }
    except Exception:
        return {'name': ticker, 'sector': 'Unknown', 'industry': 'Unknown'}


def parse_and_store_recommendations(investments_text: str, model_used: str = "unknown"):
    """Parse investment ideas and store high-conviction ones (8+/10) in RECOMMENDATIONS.md"""
    import re
    
    trackable = []
    # Flexible regex to match various LLM output formats:
    # ### [1] TICKER — Thesis
    # ### [1] **TICKER (Company)** — Thesis
    # Only match valid stock tickers (1-5 letters, not common words)
    pattern = r'### \[\d+\]\s*(?:\*\*)?([A-Z]{1,5})(?:\s*\([^)]*\))?(?:\*\*)?\s*[—–\-]\s*.*?\n\n(.*?)(?=(?:### \[|\Z))'
    
    matches = list(re.finditer(pattern, investments_text, re.DOTALL))
    
    for match in matches:
        ticker = match.group(1).strip().upper()
        content = match.group(2)
        
        # Skip invalid tickers - strict validation
        if not ticker or len(ticker) < 1 or len(ticker) > 5:
            continue
        # Skip common words that might be mistaken as tickers
        if ticker in ['ASSET', 'TYPE', 'LEAPS', 'STOCK', 'ETF', 'CRYPTO', 'SELL', 'BUY', 'HOLD', 'THE', 'AND', 'FOR', 'YOU', 'WITH', 'THIS', 'THAT']:
            continue
        # Validate ticker format (letters only)
        if not ticker.isalpha():
            continue
        
        # Extract conviction score - look for multiple patterns
        conviction = '5'
        for conv_pattern in [
            r'\*\*Conviction:\*\*\s*(\d+)',
            r'\*\*Conviction Score:\*\*\s*(\d+)',
            r'Conviction:\s*(\d+)/10',
            r'(\d+)/10'
        ]:
            conv_match = re.search(conv_pattern, content)
            if conv_match:
                conviction = conv_match.group(1)
                break
        
        # Extract track indicator
        track_match = re.search(r'\*\*Track:\*\*\s*(Yes|No)', content)
        should_track = track_match and track_match.group(1) == 'Yes' if track_match else False
        
        # Extract price info - multiple patterns to handle LLM output variations
        current_price = 'N/A'
        for price_pattern in [
            r'\*\*Type/Price:\*\*\s*[\w\s]+\s*@\s*\$?([\d,.]+)',  # **Type/Price:** Stock @ $X.XX
            r'@\s*\$?([\d,.]+)',  # @ $X.XX or @ X.XX
            r'\*\*Current Price:\*\*\s*\$?([\d,.]+)',  # **Current Price:** $X.XX
            r'Price:\s*\$?([\d,.]+)',  # Price: $X.XX
        ]:
            price_match = re.search(price_pattern, content)
            if price_match:
                current_price = price_match.group(1).replace(',', '')
                break
        
        # Extract target price
        target_price = 'N/A'
        for target_pattern in [
            r'\*\*Entry/Target:\*\*\s*\$?[\d,.]+\s*→\s*\$?([\d,.]+)',  # **Entry/Target:** $X → $Y
            r'Target:\s*\$?([\d,.]+)',  # Target: $X
            r'→\s*\$?([\d,.]+)',  # → $X
        ]:
            target_match = re.search(target_pattern, content)
            if target_match:
                target_price = target_match.group(1).replace(',', '')
                break
        
        # Track if conviction >= 8 or explicitly marked
        try:
            conv_int = int(conviction)
        except ValueError:
            conv_int = 5
        
        if should_track or conv_int >= 8:
            trackable.append({
                'date': TODAY,
                'ticker': ticker,
                'entry_price': current_price,
                'target': target_price,
                'conviction': conviction,
                'status': 'Active',
                'current_price': current_price,
                'performance': '0%'
            })
    
    if trackable:
        existing = read_file(RECOMMENDATIONS_FILE)
        new_entries = "\n".join([
            f"- {r['date']} | {r['ticker']} | ${r['entry_price']} | ${r['target']} | {r['conviction']}/10 | {r['status']} | ${r['current_price']} | {r['performance']}"
            for r in trackable
        ])
        
        # Update active section - append to existing
        if "## Active Recommendations" in existing:
            # Insert before the comment placeholder
            updated = existing.replace(
                "<!-- Agent will update this section with current recommendations -->",
                f"{new_entries}\n<!-- Agent will update this section with current recommendations -->"
            )
        else:
            updated = existing + f"\n\n## Active Recommendations\n{new_entries}\n<!-- Agent will update this section with current recommendations -->\n"
        
        RECOMMENDATIONS_FILE.write_text(updated, encoding="utf-8")
        log(f"Tracked {len(trackable)} high-conviction (8+) ideas: {[r['ticker'] for r in trackable]} (model: {model_used})")


def update_recommendation_performance():
    """Update prices and performance of tracked recommendations"""
    existing = read_file(RECOMMENDATIONS_FILE)
    lines = existing.split('\n')
    updated_lines = []
    
    for line in lines:
        if line.startswith('- ') and ' | ' in line:
            parts = line[2:].split(' | ')
            if len(parts) >= 7:
                date, ticker, entry_str, target_str, conviction, status, current_str, perf = parts[:8]
                
                if status == 'Active':
                    try:
                        # Get current price
                        if FINNHUB_API_KEY and ticker.upper() not in ['BTC-USD', 'ETH-USD']:
                            r = requests.get(f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}", timeout=10)
                            data = r.json()
                            current_price = data.get("c", 0)
                        else:
                            t = yf.Ticker(ticker)
                            current_price = t.fast_info.last_price or 0
                        
                        if current_price and entry_str.startswith('$'):
                            entry_price = float(entry_str[1:])
                            if entry_price > 0:
                                change_pct = ((current_price - entry_price) / entry_price) * 100
                                perf = f"{change_pct:+.1f}%"
                        
                        current_str = f"${current_price:.2f}" if current_price else current_str
                        
                        # Check if target hit or stop loss
                        if target_str.startswith('$'):
                            target_price = float(target_str[1:])
                            if current_price >= target_price * 0.95:  # Within 5% of target
                                status = 'Target Hit'
                        
                        line = f"- {date} | {ticker} | {entry_str} | {target_str} | {conviction} | {status} | {current_str} | {perf}"
                    except Exception as e:
                        log_error(f"Error updating {ticker}", e)
        
        updated_lines.append(line)
    
    updated_content = '\n'.join(updated_lines)
    RECOMMENDATIONS_FILE.write_text(updated_content, encoding="utf-8")


# ─────────────────────────────────────────────
# RATING-BASED FEEDBACK (EFFICIENT TOKEN USAGE)
# ─────────────────────────────────────────────
def add_rating(rating: int, notes: str = ""):
    """
    Add a rating (1-10) to RATINGS.md.
    Called after user reviews the report.
    Minimal token cost but maximizes learning.
    """
    if not (1 <= rating <= 10):
        return
    
    existing = read_file(RATINGS_FILE)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"{timestamp}: {rating}/10"
    if notes:
        entry += f" — {notes[:100]}"  # Keep notes concise
    
    updated = existing + "\n" + entry
    if len(updated) > 5000:
        updated = "...[older ratings archived]\n" + updated[-5000:]
    
    RATINGS_FILE.write_text(updated, encoding="utf-8")

def get_recent_ratings(n: int = 10) -> list:
    """Get last N ratings for reflection."""
    ratings = read_file(RATINGS_FILE)
    recent = []
    if ratings:
        lines = ratings.split('\n')
        for line in lines[-n:]:
            if ':' in line and '/10' in line:
                recent.append(line.strip())
    return recent

def calculate_avg_rating() -> str:
    """Calculate average of last 10 ratings."""
    recent = get_recent_ratings(10)
    if not recent:
        return "N/A"
    
    scores = []
    for r in recent:
        try:
            score = int(r.split('/10')[0].split()[-1])
            scores.append(score)
        except:
            pass
    
    if scores:
        return f"{sum(scores)/len(scores):.1f}/10"
    return "N/A"


# ─────────────────────────────────────────────
# WEEKLY LEARNING THEMES (ROTATING SYSTEM)
# ─────────────────────────────────────────────
def get_or_create_weekly_theme() -> dict:
    """
    Manage a rotating weekly theme system.
    One broad topic per week, daily deep dives into details.
    
    Returns: {
        'theme': 'Theme title',
        'week_start': 'YYYY-MM-DD',
        'days_completed': 0-7,
        'subtopics': ['subtopic1', 'subtopic2', ...]
    }
    """
    if not WEEKLY_THEMES_FILE.exists():
        # Initialize with first theme
        initial_theme = {
            'theme': 'The AI Revolution: How Large Language Models Work',
            'week_start': TODAY,
            'days_completed': 0,
            'subtopics': [
                'Day 1: Transformer Architecture - The Foundation',
                'Day 2: Attention Mechanisms - How AI Focuses on What Matters',
                'Day 3: Training & Scaling Laws - Why Bigger = Better (Sometimes)',
                'Day 4: Tokens & Embeddings - How AI Understands Language',
                'Day 5: Reasoning vs Memorization - What LLMs Actually Do',
                'Day 6: Hallucinations & Limitations - When AI Gets It Wrong',
                'Day 7: The Economic Impact - AI as Infrastructure'
            ]
        }
        theme_content = f"""# 📚 Weekly Learning Themes

## Current Theme (Week of {TODAY})

**📌 Theme:** {initial_theme['theme']}

**Duration:** Week of {TODAY}
**Status:** In Progress (Day 1 of 7)

### Daily Deep Dives:
"""
        for i, subtopic in enumerate(initial_theme['subtopics'], 1):
            theme_content += f"\n- [ ] {subtopic}"
        
        WEEKLY_THEMES_FILE.write_text(theme_content, encoding="utf-8")
        return initial_theme
    
    # Read existing theme
    try:
        content = WEEKLY_THEMES_FILE.read_text()
        
        # Parse current theme from file
        import re
        theme_match = re.search(r'\*\*📌 Theme:\*\* (.+?)(?:\n|$)', content)
        week_match = re.search(r'\*\*Duration:\*\* Week of (\d{4}-\d{2}-\d{2})', content)
        
        theme_name = theme_match.group(1) if theme_match else 'Unspecified'
        week_start = week_match.group(1) if week_match else TODAY
        
        # Count days since theme started
        from datetime import datetime
        today_date = datetime.fromisoformat(TODAY)
        week_date = datetime.fromisoformat(week_start)
        days_elapsed = (today_date - week_date).days
        
        # If more than 7 days, it's time for a new theme
        if days_elapsed >= 7:
            # Rotate to next theme
            new_theme = rotate_to_next_theme()
            return new_theme
        
        return {
            'theme': theme_name,
            'week_start': week_start,
            'days_completed': days_elapsed,
            'subtopics': []
        }
    except Exception:
        return {
            'theme': 'Learning',
            'week_start': TODAY,
            'days_completed': 0,
            'subtopics': []
        }

def rotate_to_next_theme() -> dict:
    """Rotate to a new weekly theme."""
    THEME_ROTATION = [
        {
            'theme': 'Macroeconomics: How the World Economy Really Works',
            'subtopics': [
                'Day 1: Money & Inflation - What Makes Your Savings Worth Less',
                'Day 2: Interest Rates & The Fed - How Central Banks Control Everything',
                'Day 3: Supply & Demand - The Force Behind Every Price',
                'Day 4: Recessions & Business Cycles - Why Booms Turn to Busts',
                'Day 5: Currencies & Trade - Why the Dollar Matters Globally',
                'Day 6: Geopolitics & Economics - When Politics Changes Markets',
                'Day 7: Investment Implications - How to Profit from Economic Cycles'
            ]
        },
        {
            'theme': 'History Repeats: Lessons from Past Bubbles & Crashes',
            'subtopics': [
                'Day 1: Tulip Mania 1637 - The First Bubble',
                'Day 2: The Dot-Com Crash 2000 - Tech Hubris',
                'Day 3: The 2008 Financial Crisis - Systemic Risk',
                'Day 4: Crypto Winter 2022 - Modern Manias',
                'Day 5: Pattern Recognition - How to Spot Bubbles Early',
                'Day 6: Survivor Bias - Why We Ignore Lessons',
                'Day 7: Building Anti-Fragile Portfolios - Learning from History'
            ]
        },
        {
            'theme': 'Artificial Intelligence: The Technology Reshaping Everything',
            'subtopics': [
                'Day 1: From Narrow AI to General AI - The Holy Grail',
                'Day 2: Deep Learning Explosion - How Neural Networks Work',
                'Day 3: AI in Medicine - Cancer Detection & Drug Discovery',
                'Day 4: AI in Finance - Algorithmic Trading & Risk Management',
                'Day 5: AI Alignment - The Problem of Values & Control',
                'Day 6: The AI Arms Race - Geopolitical Implications',
                'Day 7: Investment Plays - How to Profit from the AI Revolution'
            ]
        },
        {
            'theme': 'Energy & Climate: The Next Mega-Trend',
            'subtopics': [
                'Day 1: The Physics of Energy - Why We Need More Than We Think',
                'Day 2: Fossil Fuels in Decline - When Peak Oil Finally Comes',
                'Day 3: Renewables Revolution - Solar, Wind, Battery Breakthroughs',
                'Day 4: Nuclear Energy - Fission & Fusion\'s Comeback',
                'Day 5: The Grid Problem - Storage & Distribution Challenges',
                'Day 6: Climate Finance - Carbon Credits & Green Bonds',
                'Day 7: Energy Investing - Who Wins in the Transition'
            ]
        },
        {
            'theme': 'Human Longevity & Biohacking - Living Longer, Better',
            'subtopics': [
                'Day 1: Why We Age - The Biology of Aging',
                'Day 2: Senescent Cells & Senolytics - Removing the Damage',
                'Day 3: Cellular Reprogramming - Yamanaka Factors & De-Aging',
                'Day 4: Metabolic Health - Glucose, Insulin, Ketones',
                'Day 5: Sleep, Exercise, Fasting - The Unglamorous Basics',
                'Day 6: Supplements & Biomarkers - What Actually Works',
                'Day 7: Biotech Investing - The Companies Racing to Extend Life'
            ]
        }
    ]
    
    # Pick next theme (cycle through rotation)
    rotation_index = datetime.datetime.now().isocalendar()[1] % len(THEME_ROTATION)
    next_theme_data = THEME_ROTATION[rotation_index]
    
    new_theme = {
        'theme': next_theme_data['theme'],
        'week_start': TODAY,
        'days_completed': 0,
        'subtopics': next_theme_data['subtopics']
    }
    
    # Update WEEKLY_THEMES_FILE
    theme_content = f"""# 📚 Weekly Learning Themes

## Current Theme (Week of {TODAY})

**📌 Theme:** {new_theme['theme']}

**Duration:** Week of {TODAY}
**Status:** In Progress (Day 1 of 7)

### Daily Deep Dives:
"""
    for i, subtopic in enumerate(new_theme['subtopics'], 1):
        checked = '✅' if i <= new_theme['days_completed'] else '[ ]'
        theme_content += f"\n- {checked} {subtopic}"
    
    theme_content += "\n\n---\n*New theme rotates each week. Archive your learnings.*\n"
    WEEKLY_THEMES_FILE.write_text(theme_content, encoding="utf-8")
    
    return new_theme


# ─────────────────────────────────────────────
# PORTFOLIO ANALYSIS & MARKET SENTIMENT
# ─────────────────────────────────────────────

def analyze_portfolio_weightage() -> dict:
    """
    Analyze portfolio holdings by weightage and volatility.
    Returns weighted positions sorted by portfolio % and news relevance.
    Uses current market values (not cost basis) for portfolio % calculations.
    """
    portfolio_data = import_multiple_portfolios()
    holdings = portfolio_data.get('holdings', [])
    
    if not holdings:
        return {
            'total_holdings': 0,
            'weighted_summary': 'No portfolio data loaded',
            'top_positions': [],
            'risk_assessment': ''
        }
    
    total_cost = sum(h['cost_basis'] for h in holdings)
    
    # PASS 1: Fetch all current prices and calculate current values
    weighted_holdings = []
    api_errors = 0
    for h in holdings:
        try:
            current_price = None
            prev_close = None
            
            # Try Finnhub first
            if FINNHUB_API_KEY and h['ticker'].upper() not in ['BTC-USD', 'ETH-USD', 'XRP-USD']:
                try:
                    r = requests.get(
                        f"https://finnhub.io/api/v1/quote?symbol={h['ticker']}&token={FINNHUB_API_KEY}",
                        timeout=10
                    )
                    data = r.json()
                    if data and data.get("c", 0) > 0:
                        current_price = data["c"]
                        prev_close = data.get("pc", None)
                except Exception as e:
                    pass
            
            # Fallback to yfinance
            if current_price is None or current_price == 0:
                old_stderr = sys.stderr
                sys.stderr = StringIO()
                try:
                    t = yf.Ticker(h['ticker'])
                    price = t.fast_info.last_price
                    if price and price > 0:
                        current_price = price
                        prev_close = t.fast_info.previous_close
                except Exception:
                    pass
                finally:
                    sys.stderr = old_stderr
            
            # Final fallback to purchase price
            if current_price is None or current_price == 0:
                current_price = h['purchase_price']
                prev_close = h['purchase_price']
                api_errors += 1
            
            if prev_close is None or prev_close == 0:
                prev_close = h['purchase_price']
            
            current_value = h['shares'] * current_price
            
            weighted_holdings.append({
                'ticker': h['ticker'],
                'shares': h['shares'],
                'cost_basis': h['cost_basis'],
                'purchase_price': h['purchase_price'],
                'current_price': current_price,
                'current_value': current_value,
                'prev_close': prev_close if prev_close else h['purchase_price'],
                'sources': h.get('sources', 1)
            })
        except Exception as e:
            log_error(f"Error analyzing {h['ticker']}", e)
            continue
    
    # Calculate total current value across all holdings
    total_current_value = sum(wh['current_value'] for wh in weighted_holdings)
    
    # Log API errors
    if api_errors > 0:
        log(f"⚠ Portfolio analysis: {api_errors}/{len(weighted_holdings)} tickers used purchase price (API failed)")
    
    # PASS 2: Calculate percentages and gains
    for wh in weighted_holdings:
        wh['portfolio_pct'] = (wh['current_value'] / total_current_value * 100) if total_current_value > 0 else 0
        wh['unrealized_gain'] = ((wh['current_price'] - wh['purchase_price']) / wh['purchase_price'] * 100) if wh['purchase_price'] > 0 else 0
        wh['day_change'] = ((wh['current_price'] - wh['prev_close']) / wh['prev_close'] * 100) if wh['prev_close'] > 0 else 0
    
    weighted_holdings.sort(key=lambda x: x['portfolio_pct'], reverse=True)
    
    top_5 = weighted_holdings[:5]
    top_5_pct = sum(h['portfolio_pct'] for h in top_5)
    
    summary = f"**Portfolio Analysis ({len(weighted_holdings)} holdings):**\n"
    summary += f"- Total Cost Basis: ${total_cost:,.0f}\n"
    summary += f"- Total Current Value: ${total_current_value:,.0f}\n"
    summary += f"- Top 5 positions: {top_5_pct:.1f}% of portfolio\n"
    summary += f"- Concentration risk: {'HIGH' if top_5_pct > 60 else 'MODERATE' if top_5_pct > 40 else 'LOW'}\n\n"
    summary += "| Ticker | % of Portfolio | Current Price | Today's Move | Unrealized P&L |\n"
    summary += "|--------|----------------|---------------|--------------|----------------|\n"
    for h in weighted_holdings[:10]:
        summary += f"| {h['ticker']} | {h['portfolio_pct']:.1f}% | ${h['current_price']:.2f} | {h['day_change']:+.2f}% | {h['unrealized_gain']:+.1f}% |\n"
    
    return {
        'total_holdings': len(weighted_holdings),
        'weighted_summary': summary,
        'top_positions': weighted_holdings,
        'concentration_ratio': top_5_pct,
        'total_value': total_current_value
    }

def get_market_sentiment() -> str:
    """
    Analyze market sentiment using VIX, market breadth, and economic indicators.
    Returns: fear/greed assessment and market timing context.
    """
    try:
        log("  → Analyzing market sentiment...")
        
        # Get VIX (fear gauge)
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        try:
            vix = yf.Ticker("^VIX")
            vix_price = vix.fast_info.last_price or 0
            vix_prev = vix.fast_info.previous_close or 0
        except Exception:
            vix_price = 0
            vix_prev = 0
        finally:
            sys.stderr = old_stderr
        
        # Get market index prices
        spy = yf.Ticker("SPY")
        spy_price = spy.fast_info.last_price or 0
        spy_prev = spy.fast_info.previous_close or 0
        
        qqq = yf.Ticker("QQQ")
        qqq_price = qqq.fast_info.last_price or 0
        qqq_prev = qqq.fast_info.previous_close or 0
        
        # Calculate moves
        spy_move = ((spy_price - spy_prev) / spy_prev * 100) if spy_prev > 0 else 0
        qqq_move = ((qqq_price - qqq_prev) / qqq_prev * 100) if qqq_prev > 0 else 0
        
        # Determine sentiment
        if vix_price == 0:
            sentiment = "[VIX data unavailable - cannot assess market sentiment]"
        elif vix_price < 12:
            sentiment = f"**EXTREME GREED** (VIX: {vix_price:.1f})\n"
            sentiment += "Markets are pricing in near-perfect outcomes. Complacency is high.\n"
            sentiment += "**Timing Assessment:** Elevated risk of sharp corrections. Consider defensive positioning.\n"
            sentiment += "**Action:** Take profits on winners, trim concentrated positions, add hedges."
        elif vix_price < 16:
            sentiment = f"**GREED** (VIX: {vix_price:.1f})\n"
            sentiment += "Investors are confident but not complacent. Reasonable risk appetite.\n"
            sentiment += "**Timing Assessment:** Good environment for buyable dips and sector rotation.\n"
            sentiment += "**Action:** Steady accumulation, look for weakness to add."
        elif vix_price < 20:
            sentiment = f"**NEUTRAL** (VIX: {vix_price:.1f})\n"
            sentiment += "Normal market volatility. Mix of optimism and caution.\n"
            sentiment += "**Timing Assessment:** Balanced - stick to high-conviction ideas.\n"
            sentiment += "**Action:** Continue with disciplined thesis-based trading."
        elif vix_price < 30:
            sentiment = f"**FEAR** (VIX: {vix_price:.1f})\n"
            sentiment += "Investors are nervous but not panicked. Some pain in the market.\n"
            sentiment += "**Timing Assessment:** Often creates opportunities for disciplined buyers.\n"
            sentiment += "**Action:** Have dry powder ready, add to high-conviction positions on weakness."
        else:
            sentiment = f"**EXTREME FEAR** (VIX: {vix_price:.1f})\n"
            sentiment += "Markets are pricing in significant downside risk. Panic selling possible.\n"
            sentiment += "**Timing Assessment:** Historically, extreme fear creates best long-term buying opportunities.\n"
            sentiment += "**Action:** Contrarian positions for aggressive investors, cash for conservative."
        
        sentiment += f"\n**Today's Market Movement:**\n"
        sentiment += f"- SPY: {spy_move:+.2f}% @ ${spy_price:.2f}\n"
        sentiment += f"- QQQ: {qqq_move:+.2f}% @ ${qqq_price:.2f}\n"
        
        return sentiment
    
    except Exception as e:
        log_error("Market sentiment analysis failed", e)
        return "[Market sentiment analysis unavailable]"

def analyze_rebalancing_opportunities(portfolio_analysis: dict) -> str:
    """
    Suggest rebalancing based on portfolio weightage and market conditions.
    """
    try:
        top_pos = portfolio_analysis.get('top_positions', [])
        concentration = portfolio_analysis.get('concentration_ratio', 0)
        
        if not top_pos:
            return "[No rebalancing analysis available]"
        
        suggestions = "## 🎯 Portfolio Rebalancing Assessment\n\n"
        
        # Check concentration
        if concentration > 65:
            suggestions += f"**⚠️ HIGH CONCENTRATION RISK:** Top 5 positions = {concentration:.1f}%\n"
            suggestions += "Recommendation: Consider reducing largest positions to 15-20% each, redeploy to:\n"
            suggestions += "- Underweight sectors (look for opportunities in your watchlist)\n"
            suggestions += "- Alternative assets (GLD, SLV for diversification)\n"
            suggestions += "- New conviction ideas (if quality ideas available at good prices)\n\n"
        elif concentration > 45:
            suggestions += f"**MODERATE CONCENTRATION:** Top 5 = {concentration:.1f}%\n"
            suggestions += "This is reasonable but monitor for excessive single-position risk.\n\n"
        else:
            suggestions += f"**✅ HEALTHY DIVERSIFICATION:** Top 5 = {concentration:.1f}%\n"
            suggestions += "Portfolio is well-balanced. Continue with disciplined additions.\n\n"
        
        # Identify underperforming positions
        losers = [p for p in top_pos if p['unrealized_gain'] < -10]
        if losers:
            suggestions += f"**Losing Positions ({len(losers)}):**\n"
            for p in losers[:3]:
                suggestions += f"- {p['ticker']}: {p['unrealized_gain']:+.1f}% | {p['portfolio_pct']:.1f}% of portfolio\n"
            suggestions += "Decision points: Are fundamentals intact? Or cut losses and redeploy?\n\n"
        
        # Identify strong performers
        winners = [p for p in top_pos if p['unrealized_gain'] > 20]
        if winners:
            suggestions += f"**Top Performers ({len(winners)}):**\n"
            for p in winners[:3]:
                suggestions += f"- {p['ticker']}: {p['unrealized_gain']:+.1f}% | {p['portfolio_pct']:.1f}% of portfolio\n"
            suggestions += "Consider: Lock in profits on winners > 50% if they've become too large?\n\n"
        
        return suggestions
    
    except Exception as e:
        log_error("Rebalancing analysis failed", e)
        return "[Rebalancing analysis unavailable]"


# ─────────────────────────────────────────────
# AGENT TASKS
# ─────────────────────────────────────────────

def task_news_digest(rss: dict, fin_news: str, memory: str) -> str:
    log("  → Generating news digest...")
    
    # Load news-researcher skill (Claude Code style)
    skill_instructions = SKILLS.get("news-researcher", "")
    
    # RSS feeds - top 4 items per category (quality + efficiency)
    raw = ""
    for cat, items in rss.items():
        raw += f"\n{cat}\n" + "\n".join(items[:4]) + "\n"
    
    # Smart token management: summarize memory but keep quality
    memory_summary = summarize_text(memory, "memory", 600)  # Slightly more for quality
    
    return call_llm(
        system=SYSTEM,
        user="""{skill_instructions}

Memory Summary:
{memory_summary}

RAW NEWS FEEDS:
{raw}

MARKET NEWS (Finnhub):
{fin_news}

Write a **Daily Intelligence Digest** with these exact sections:

## 🤖 AI & Tech Developments
3-5 key stories. For each: what happened + why it matters for investors/learners.

## 📈 Markets & Economics
What moved? Why? What macro forces are at play? Connect to Fed policy, rates, 
dollar strength, earnings, or geopolitical risk.

## 🌍 Geopolitics & Supply Chains
Conflicts, trade tensions, resource competition, sanctions. What's the investment 
implication — who wins, who loses?

## 🔬 Science & Health Signal
1-2 developments worth knowing. Longevity? Energy? Materials? Biotech?

## 💡 Cross-Domain Insight of the Day
One non-obvious connection across today's stories. The kind of pattern a 
first-principles thinker would spot.

Date: {now} | Be specific. Skip fluff. Every sentence should earn its place.""".format(
            skill_instructions=skill_instructions,
            memory_summary=memory_summary,
            raw=raw,
            fin_news=fin_news,
            now=NOW
        ),
        max_tokens=2000,  # Perfect sweet spot: quality + efficiency
    )

def task_investment_ideas(market_data: str, digest: str, memory: str, portfolio_analysis: dict = None, options_context: str = "") -> str:
    log("  → Generating investment ideas...")
    
    # Slice inputs before formatting to avoid format string syntax errors
    memory_slice = memory[:600]
    market_data_slice = market_data[:800]
    digest_slice = digest[:600]
    
    # Build portfolio context for the LLM
    portfolio_context = ""
    if portfolio_analysis:
        portfolio_context = f"""
YOUR PORTFOLIO CONTEXT:
{portfolio_analysis.get('weighted_summary', '')}

Concentration Ratio: {portfolio_analysis.get('concentration_ratio', 0):.1f}%
Top holdings need attention if this ratio is too high.

{analyze_rebalancing_opportunities(portfolio_analysis)}
"""
    
    # Add options context for cross-referencing
    options_section = ""
    if options_context and options_context != "[Options data unavailable]":
        options_section = f"""
OPTIONS MARKET CONTEXT:
{options_context[:500]}
Use options data (IV levels, unusual activity) to inform stock recommendations if relevant.
"""
    
    # Add once-in-a-lifetime opportunities context
    once_in_a_lifetime_context = ""
    if portfolio_analysis and portfolio_analysis.get('concentration_ratio', 0) > 0.6:
        once_in_a_lifetime_context = """
**ONCE-IN-A-LIFETIME OPPORTUNITIES TO CONSIDER**:
- Extreme asymmetric plays with 50%+ upside potential
- Positions with clear catalysts (regulatory approval, patent grant, etc.)
- Situations where fundamentals are dramatically improving
- Opportunities requiring minimal capital but offering outsized returns
- Must have conviction score of 10/10 and clear downside protection
"""
    
    return call_llm(
        system=SYSTEM,
        user="""Memory (summary):
{memory}

Market Data:
{market_data}

Digest (summary):
{digest}

{portfolio_context}

{options_section}

{once_in_a_lifetime_context}

Generate **3-5 Investment Ideas** (aggressive long-term/swing):

BROAD MARKET SCAN:
- First, scan for compelling opportunities across the broader market (not just current holdings)
- Look for: sector rotations, beaten-down quality names, emerging themes, earnings plays, catalyst-driven setups
- Only recommend non-portfolio stocks if they meet the conviction threshold (8+/10)

PORTFOLIO-AWARE:
- Analyze current holdings by WEIGHT. Largest positions matter most.
- SELL/REDUCE overvalued or overweight positions
- BUY/ACCUMULATE on underweight sectors with conviction
- Recommend HOLDING CASH if no compelling opportunities exist

For EACH idea (be concise):
### [#] TICKER — Thesis
**Type/Price:** [Stock/ETF/Crypto] @ $X.XX
**Why:** 2-3 sentences, first-principles
**Catalysts:** 1-2 key drivers
**Horizon:** [Swing 2-8wk/Medium 3-12mo/Long 1-3yr]
**Entry/Target:** $X.XX → $Y.YY (timeframe)
**Stop/Size:** $Z.XX / X% of portfolio
**Conviction:** X/10 | **Track:** Yes/No
**Portfolio Fit:** [New Position/ADD/REDUCE/SELL/HOLD]

⚠️ Not financial advice. Verify before acting.""".format(
            memory=memory_slice,
            market_data=market_data_slice,
            digest=digest_slice,
            portfolio_context=portfolio_context,
            options_section=options_section,
            once_in_a_lifetime_context=once_in_a_lifetime_context
        ),
        max_tokens=2500,
    )

def task_options_ideas(market_data: str, digest: str, memory: str) -> str:
    log("  → Generating options ideas...")
    # Get options data for key tickers
    options_context = fetch_options_snapshot(["SPY", "QQQ", "NVDA", "AAPL"])

    # Summarize memory and digest to save tokens
    memory_summary = summarize_text(memory, "memory", 300)
    digest_summary = digest[:500]  # Limit digest to 500 chars
    market_data_slice = market_data[:600]  # Slice before format call
    
    return call_llm(
        system=SYSTEM,
        user="""Memory (summary):
{memory_summary}

Market:
{market_data}

Digest:
{digest_summary}

Options Data:
{options_context}

Generate **2 Options Ideas** (STRICT rules):
- Defined-risk ONLY (long calls/puts, covered calls, LEAPS)
- Min 2wk expiry, prefer 30-90d or 6mo+ LEAPS
- Max 10% portfolio total
- NEVER let expire ITM - SELL before expiry
- NO leverage, NO naked, NO margin

For EACH:
### [Strategy] on [TICKER]
**Type/Underlying:** [Long Call/Put/Covered/LEAPS] @ $X
**Why:** 1-2 sentences
**Strike/Expiry:** $X / [date, min 2wk]
**Premium/Max Risk:** $X (all you can lose)
**Target:** Sell @ $X or X% premium gain
**⚠️ EXIT:** SELL before expiry, NEVER let ITM.

Suggest 1 **Covered Call** if owner holds underlying.

⚠️ Educational only. Verify with broker.*""".format(
            memory_summary=memory_summary,
            market_data=market_data_slice,
            digest_summary=digest_summary,
            options_context=options_context
        ),
        max_tokens=1200,  # Reduced from 1500
    )

def task_learning(digest: str, memory: str) -> str:
    log("  → Generating learning recommendation (weekly theme + daily deep dive)...")
    
    # Get current weekly theme
    current_theme = get_or_create_weekly_theme()
    
    # Get today's subtopic (based on day of week)
    day_of_week = datetime.datetime.now().weekday()  # 0=Mon, 6=Sun
    # Safely handle empty or missing subtopics to avoid modulo by zero
    subtopics = current_theme.get('subtopics') or []
    if not subtopics:
        day_index = 0
        today_subtopic = current_theme.get('theme', 'Learning') or "Learning"
    else:
        day_index = day_of_week % len(subtopics)
        today_subtopic = subtopics[day_index]
    
    theme_name = current_theme.get('theme', 'Learning')
    days_in_theme = current_theme.get('days_completed', 0)
    
    return call_llm(
        system=SYSTEM,
        user="""Memory:
{memory}

Today's themes: {digest}

---

## Weekly Learning Theme (Focus For This Week)

**Broad Topic:** {theme}

You're on **Day {day_num} of 7** exploring this topic.

**Today's Specific Focus:** {subtopic}

---

Generate a **Deep Dive for Today** on the specified subtopic. Structure:

## 📚 {subtopic}

**Why This Specific Aspect Matters:**
2-3 sentences on why THIS detail (not the whole topic) is important right now.
Connect to: investing, technology, or global events if relevant.

**The Core Concept (5-Minute Explainer):**
Explain this ONE aspect from first principles. Assume no background knowledge.
Use concrete examples. Make it vivid and memorable.

**The Counterintuitive Truth:**
What does everyone get wrong about this? What's the gap between popular 
understanding and reality?

**3 Resources (Progressively Deep):**
1. 📖 Entry Point: [Resource Type & Title] — Why start here
2. 🎯 Deep Dive: [Resource Type & Title] — Next level understanding  
3. 🔬 Expert Level: [Resource Type & Title] — For those who want mastery

**Today's Question to Sit With:**
One specific, thought-provoking question for reflection (no right answer).

**Practical Connection:**
One concrete way this connects to your life, investments, or decisions TODAY.

**Tomorrow's Preview:**
One sentence on what you'll explore tomorrow (build curiosity for the week ahead).

---

Make this engaging enough that the owner wants to continue the theme tomorrow.
Use vivid language. Cross-domain connections welcome. No fluff.""".format(
            memory=memory,
            digest=digest[:400],
            theme=theme_name,
            day_num=days_in_theme + 1,
            subtopic=today_subtopic
        ),
        max_tokens=2000,
    )

def task_self_reflect(report: str, memory: str) -> str:
    """
    EFFICIENT SELF-REFLECTION:
    - Uses rating-based feedback (minimal tokens)
    - References recent ratings without full conversation
    - Learns from tracking, not verbose introspection
    """
    log("  → Self-reflecting on run quality (rating-based)...")
    
    recent_ratings = get_recent_ratings(10)
    avg_rating = calculate_avg_rating()
    
    # If avg_rating is low (<6), focus on improvement areas
    # If high (>7), focus on what's working
    improvement_mode = "LOW" if avg_rating != "N/A" and float(avg_rating.split('/')[0]) < 6 else "NORMAL"
    
    focus_prompt = "Focus on: What patterns caused low ratings? How to increase conviction accuracy?" if improvement_mode == "LOW" else ""
    
    return call_llm(
        system="You are an AI agent reviewing your own performance. Be specific and self-critical. Learn from user ratings and portfolio performance.",
        user="""Report generated this run (first 2000 chars):
{report}

Recent user ratings (last 10):
{ratings}

Average rating: {avg_rating}

Portfolio performance context:
{portfolio}

Recommendation tracking updates:
{recommendations}

{focus}

Write 3-5 bullet points for LEARNINGS.md about:
- What worked well in this run (be specific) - correlate with high ratings
- What could be improved (data sources? formatting? depth?) - learn from low ratings  
- Patterns noticed in portfolio performance vs recommendations
- How to increase conviction accuracy for 90-95% win rate goal
- Suggestions to make the next run better based on user feedback

Format: markdown bullets. Today: {now}""".format(
            report=report[:2000],
            learnings=read_file(LEARNING_FILE, max_chars=800),
            ratings='\n'.join(recent_ratings),
            avg_rating=avg_rating,
            portfolio=read_file(PORTFOLIO_FILE),
            recommendations=read_file(RECOMMENDATIONS_FILE, max_chars=1000),
            now=NOW,
            focus=focus_prompt
        ),
        max_tokens=400,
    )


# ─────────────────────────────────────────────
# REPORT ASSEMBLY & SAVING
# ─────────────────────────────────────────────
def task_market_reaction(market_data: str, digest: str) -> str:
    """Generate a brief summary explaining why the market moved today."""
    log("  → Analyzing market reaction...")
    market_slice = market_data[:600]
    digest_slice = digest[:400]
    return call_llm(
        system=SYSTEM,
        user=f"""Based on today's market data and news, write a brief 3-5 sentence summary explaining WHY the market moved the way it did today.

Market Data:
{market_slice}

News Summary:
{digest_slice}

Focus on:
- Why were indices up/down?
- What macro catalysts drove movement?
- Any sector-specific drivers?
- Keep it concise and insightful.

Format: A single paragraph with specific reasoning.""",
        max_tokens=300,
    )


def build_and_save_report(market_data, digest, investments, options, learning, market_sentiment="", portfolio_analysis_text="", market_reaction="") -> str:
    # Get recommendation updates
    rec_updates = read_file(RECOMMENDATIONS_FILE)
    if rec_updates:
        rec_section = "\n---\n# 📊 Recommendation Tracking\n" + rec_updates[:1500] + "\n"
    else:
        rec_section = ""
    
    reaction_section = f"\n---\n\n## 📰 Why The Market Moved Today\n\n{market_reaction}\n" if market_reaction else ""
    
    report = f"""# 🧠 Daily Intelligence Report
**{NOW}** | Run {RUN_LABEL} | Market {'Open 🟢' if IS_MARKET_OPEN else 'Closed 🔴'}

---

## 📊 Market Snapshot
```
{market_data}
```

---

## 🌡️ Market Sentiment & Timing
{market_sentiment}
{reaction_section}
---

{digest}

---

# 💼 Investment Ideas

{investments}

---

{portfolio_analysis_text}

---

# 🎯 Options Intelligence

{options}

---

{learning}

{rec_section}
---
*Generated by personal AI agent using free-tier APIs. Educational only. Not financial advice.*
*Options: Always sell/close contracts BEFORE expiration. Never let ITM options expire.*
"""
    path = REPORTS_DIR / f"{TODAY}-{RUN_LABEL}.md"
    path.write_text(report, encoding="utf-8")

    hist = HISTORY_DIR / f"{TODAY}.md"
    with open(hist, "a", encoding="utf-8") as f:
        f.write(f"\n\n---\n## Run {RUN_LABEL} at {NOW}\n" + report)

    log(f"Report saved: {path}")
    return report


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    # Initialize run metadata
    global NOW, TODAY, RUN_LABEL, IS_MARKET_OPEN
    now = datetime.datetime.now()
    NOW = now.strftime("%Y-%m-%d %H:%M:%S")
    TODAY = now.strftime("%Y-%m-%d")
    RUN_LABEL = now.strftime("%H%M")
    
    # Check if US stock market is open (9:30 AM - 4:00 PM ET, Mon-Fri)
    hour = now.hour
    minute = now.minute
    weekday = now.weekday()
    IS_MARKET_OPEN = (weekday < 5) and ((hour == 9 and minute >= 30) or (10 <= hour < 16))
    
    log("=" * 60)
    log(f"🤖 Agent v2.2 starting — Run {RUN_LABEL}")
    log(f"   Model Priority: Free (Qwen/Llama) → DeepSeek Chat")
    log(f"   Watchlist: Dynamic (portfolio) + Indices + Crypto")
    # Ensure we start with a clean recommendations section
    clear_active_recommendations()
    log(f"   Learning: Rotating weekly themes with daily deep dives")
    log("=" * 60)

    if SKILLS_AVAILABLE:
        try:
            init_memory_system()
            log("[OK] Tiered memory initialized")
        except Exception as e:
            log(f"[!] Memory init failed: {e}")

    # 0. Load portfolios from CSV (multiple portfolio consolidation)
    # Auto-discovers portfolio1.csv, portfolio2.csv, portfolio3.csv, portfolio4.csv
    portfolio_data = import_multiple_portfolios()
    if portfolio_data["holdings"]:
        PORTFOLIO_FILE.write_text(portfolio_data["total"], encoding="utf-8")
    elif (BASE_DIR / "portfolio.csv").exists():
        # Fallback: try single portfolio.csv if no portfolio1-4 found
        portfolio_data = import_portfolio_csv(str(BASE_DIR / "portfolio.csv"))
        if portfolio_data["holdings"]:
            PORTFOLIO_FILE.write_text(portfolio_data["total"], encoding="utf-8")
    
    if SKILLS_AVAILABLE:
        try:
            acct = get_account_info()
            if "error" not in acct:
                pass
        except Exception:
            pass

    # 1. Load memory
    log("📚 Loading memory...")
    if SKILLS_AVAILABLE:
        try:
            memory = get_memory_for_run()
        except Exception as e:
            memory = load_memory()
    else:
        memory = load_memory()

    # Update recommendation performance before generating new ideas
    log("📈 Updating recommendation tracking...")
    update_recommendation_performance()

    # 2. Collect data (all free)
    log("📡 Fetching RSS feeds...")
    rss = fetch_rss()

    log("💹 Fetching market data...")
    market_data = fetch_market_data()

    log("📰 Fetching Finnhub news...")
    fin_news = finnhub_news()

    # Optionally do a Tavily deep-dive on today's top story (conserve credits)
    run_hour = datetime.datetime.now().hour
    if run_hour in [11, 17]:  # only 2 of 5 runs use Tavily
        log("🔍 Tavily deep-dive (morning/evening run only)...")
        extra = tavily_search("latest AI model releases investment implications today", 3)
        fin_news = fin_news + "\n\nDEEP DIVE:\n" + extra

    # 3. Analyze portfolio and market sentiment
    log("📊 Analyzing portfolio positions by weightage...")
    portfolio_analysis = analyze_portfolio_weightage()
    
    log("🌡️  Analyzing market sentiment (fear/greed)...")
    market_sentiment = get_market_sentiment()

    if SKILLS_AVAILABLE:
        try:
            get_index_prices()
        except Exception:
            pass

    # 3. Generate content (sub-agents run sequentially)
    log("✍️  Running sub-agents...")
    digest      = task_news_digest(rss, fin_news, memory)
    digest_summary = summarize_text(digest, "news digest", 300)
    
    # Fetch options data early so both investment and options tasks can use it
    options_context = fetch_options_snapshot(["SPY", "QQQ", "NVDA", "AAPL", "PLTR", "TEM"])
    investments = task_investment_ideas(market_data, digest_summary, memory, portfolio_analysis, options_context)
    
    # Store trackable recommendations
    parse_and_store_recommendations(investments)
    
    options     = task_options_ideas(market_data, digest_summary, memory)
    learning    = task_learning(digest_summary, memory)
    market_reaction = task_market_reaction(market_data, digest_summary)

    # 4. Write report
    log("📝 Writing report...")
    report = build_and_save_report(
        market_data, 
        digest, 
        investments, 
        options, 
        learning,
        market_sentiment=market_sentiment,
        portfolio_analysis_text=portfolio_analysis.get('weighted_summary', ''),
        market_reaction=market_reaction
    )

    if SKILLS_AVAILABLE:
        try:
            send_daily_summary(report)
        except Exception:
            pass

    # 5. Self-reflect & update learnings (rating-based, efficient)
    log("🪞 Reflecting and updating LEARNINGS.md (rating-based)...")
    reflection = task_self_reflect(report, memory)
    save_learnings(reflection)

    if SKILLS_AVAILABLE:
        try:
            update_hot_memory({"date": TODAY})
        except Exception:
            pass

    log("✅ Agent run complete.")
    log(f"   Report: REPORTS/{TODAY}-{RUN_LABEL}.md")
    log(f"   Rate this run: add_rating(score, 'optional notes') in Python")


if __name__ == "__main__":
    main()
