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
    from skills.portfolio_analysis import analyze_portfolio_weightage
    from skills.market_sentiment import get_market_sentiment, analyze_macro_trends
    from skills.crypto_tracker import fetch_crypto_prices, analyze_crypto_portfolio
    from skills.options_intelligence import fetch_options_snapshot, get_options_ideas
    from skills.news_research import fetch_rss, tavily_search, finnhub_news
    from skills.learning_curator import get_or_create_weekly_theme, generate_learning_content
    from skills.recommendation_tracker import clear_active_recommendations as clear_recs, parse_and_store_recommendations, update_recommendation_performance
    from skills.alpaca_trading import get_account_info, get_positions, get_portfolio_history
    from skills.benchmark_tracker import get_index_prices, compare_to_benchmarks, update_benchmark_log, get_performance_summary
    from skills.clickup_integration import create_recommendation_task, send_daily_summary, get_active_recommendations
    from skills.memory_manager import init_memory_system, update_hot_memory, get_memory_for_run, update_warm_memory
    from skills.enhanced_trading import (calculate_kelly_criterion,
                                         calculate_position_size,
                                         detect_options_imbalances,
                                         generate_options_strategy_prompt)
    from skills.telegram_bot import send_report_via_telegram
    from skills.paper_trader import (execute_from_recommendation, get_paper_portfolio_summary,
                                      format_portfolio_report, get_trade_performance,
                                      get_paper_portfolio, save_paper_portfolio)
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
ALPACA_API_KEY     = os.environ.get("ALPACA_API_KEY", "PKQPPHGBKHMRBLDY6HKSXKXA3Y")
ALPACA_SECRET_KEY  = os.environ.get("ALPACA_SECRET_KEY", "7vq32opSfSvDhwp5qttV6o7SePyfrfTfVffS7zTKiDZp")
CLICKUP_API_KEY    = os.environ.get("CLICKUP_API_KEY", "pk_210064579_GKJGK3ZL7YXS46SKMB4GZ7UBDR61JRLE")
CLICKUP_LIST_ID    = os.environ.get("CLICKUP_LIST_ID", "901416047336")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8636007397:AAHNNsTemjFJujygybFCBMWELLdYfLk6xjc")

# ─────────────────────────────────────
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
    """Fetch crypto prices from CoinGecko (FREE, no API key) with yfinance fallback."""
    import requests
    result = {}
    for crypto in cryptos:
        price = None
        try:
            # Try yfinance first
            old_stderr = sys.stderr
            sys.stderr = StringIO()
            try:
                t = yf.Ticker(crypto)
                price = t.fast_info.last_price
            except Exception:
                price = None
            finally:
                sys.stderr = old_stderr
        except Exception:
            pass

        # Fallback to CoinGecko (free, no key, very reliable)
        if not price:
            try:
                symbol = crypto.split('-')[0].lower()
                # Map common symbols to CoinGecko IDs
                cg_id = {"btc": "bitcoin", "eth": "ethereum", "xrp": "ripple"}.get(symbol, symbol)
                r = requests.get(
                    f"https://api.coingecko.com/api/v3/simple/price?ids={cg_id}&vs_currencies=usd",
                    timeout=10
                )
                data = r.json()
                price = data.get(cg_id, {}).get('usd')
            except Exception:
                pass

        if price:
            result[crypto] = price
    return result

def _get_live_price_yf(ticker):
    """
    Get the most current price for a ticker using multiple sources.
    Priority: Finnhub (most reliable) > yfinance fast_info > yfinance info
    Works during market hours AND after hours.
    Returns (price, prev_close) or (None, None).
    """
    # SOURCE 1: Finnhub (most reliable — works after hours)
    if FINNHUB_API_KEY:
        try:
            r = requests.get(
                f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}",
                timeout=10
            )
            data = r.json()
            p = data.get("c", 0)
            pc = data.get("pc", 0)
            if p and float(p) > 0:
                return float(p), float(pc) if pc and float(pc) > 0 else None
        except Exception:
            pass

    # SOURCE 2: yfinance fast_info
    old_stderr = sys.stderr
    sys.stderr = StringIO()
    try:
        t = yf.Ticker(ticker)
        fi = t.fast_info
        p = fi.last_price
        pc = fi.previous_close
        if p and p > 0:
            return float(p), float(pc) if pc and pc > 0 else None
    except Exception:
        pass
    finally:
        sys.stderr = old_stderr

    # SOURCE 3: yfinance info() — includes postMarketPrice
    sys.stderr = StringIO()
    try:
        t = yf.Ticker(ticker)
        info = t.info
        p = (info.get('postMarketPrice') or
             info.get('currentPrice') or
             info.get('regularMarketPrice') or
             info.get('previousClose'))
        pc = (info.get('regularMarketPreviousClose') or
              info.get('previousClose'))
        if p and float(p) > 0:
            return float(p), float(pc) if pc and float(pc) > 0 else None
    except Exception:
        pass
    finally:
        sys.stderr = old_stderr

    return None, None


def fetch_market_data() -> str:
    """
    Pull prices + % change for watchlist: consolidated portfolio holdings sorted by biggest movers + indices.
    
    FIXED: Uses robust multi-source price fetching that works after market hours.
    Never falls back to purchase price — clearly labels data source.
    """
    now = datetime.datetime.now()
    market_status = "OPEN 🟢" if IS_MARKET_OPEN else "CLOSED 🔴 (after-hours/delayed data)"

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
    all_tickers = list(dict.fromkeys(all_tickers))

    ticker_data = []
    crypto_tickers = [t for t in portfolio_tickers if t.endswith("-USD")]
    stock_tickers = [t for t in all_tickers if not t.endswith("-USD")]

    # Fetch stock prices using robust multi-source method
    for ticker in stock_tickers:
        try:
            price, prev = _get_live_price_yf(ticker)

            if price and prev and prev > 0:
                chg = ((price - prev) / prev) * 100
                weight = portfolio_costs.get(ticker, 0)
                ticker_data.append({
                    'ticker': ticker,
                    'price': price,
                    'change': chg,
                    'is_index': ticker in ["SPY", "QQQ", "IWM", "VTI", "GLD", "SLV"],
                    'weight': weight
                })
            elif price:
                # Have price but no prev_close — still show it
                weight = portfolio_costs.get(ticker, 0)
                ticker_data.append({
                    'ticker': ticker,
                    'price': price,
                    'change': None,
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
                prev = _get_live_price_yf(crypto)[1]
                chg = ((price - prev) / prev * 100) if prev and prev > 0 else None
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
                    'change': None,
                    'is_index': False,
                    'weight': portfolio_costs.get(crypto, 0),
                    'is_crypto': True
                })

    # Sort portfolio tickers by absolute change (biggest movers first) for watchlist
    portfolio_data = [t for t in ticker_data if not t.get('is_index')]
    # Sort: items with change first (by abs), then items without change
    with_change = [t for t in portfolio_data if t['change'] is not None]
    without_change = [t for t in portfolio_data if t['change'] is None]
    with_change.sort(key=lambda x: abs(x['change']), reverse=True)

    top_movers = with_change[:12]
    shown_tickers = {t['ticker'] for t in top_movers}

    # Add top by weight if not already in movers
    remaining = [t for t in with_change + without_change if t['ticker'] not in shown_tickers]
    remaining.sort(key=lambda x: x['weight'], reverse=True)
    top_weight = remaining[:3]

    lines = []
    lines.append(f"\n  [📊 Your Portfolio — Biggest Movers Today ({len(portfolio_tickers)} total holdings) | Market: {market_status}]")
    for t in top_movers + top_weight:
        if t['change'] is not None:
            arrow = "▲" if t['change'] >= 0 else "▼"
            chg_str = f"{arrow}{abs(t['change']):.2f}%"
        else:
            chg_str = "N/A"
        tag = " 💰" if t['weight'] > 0 and t in top_weight and t not in top_movers[:12] else ""
        lines.append(f"    {t['ticker']:<10} ${t['price']:>9.2f}  {chg_str}{tag}")

    # Indices
    lines.append("\n  [Indices & Benchmarks]")
    indices = [t for t in ticker_data if t.get('is_index')]
    indices_with_change = [t for t in indices if t['change'] is not None]
    indices_without_change = [t for t in indices if t['change'] is None]
    indices_with_change.sort(key=lambda x: abs(x['change']), reverse=True)
    for t in indices_with_change + indices_without_change:
        if t['change'] is not None:
            arrow = "▲" if t['change'] >= 0 else "▼"
            lines.append(f"    {t['ticker']:<10} ${t['price']:>9.2f}  {arrow}{abs(t['change']):.2f}%")
        else:
            lines.append(f"    {t['ticker']:<10} ${t['price']:>9.2f}  N/A")

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


# NOTE: Options data functions are DELEGATED to skills/options_intelligence.py
# to avoid duplication. The skill versions use correct API parameters and better error handling.
# Your Polygon key (from Massive) is valid but the free tier doesn't include options snapshot data.
# Options will use yfinance as the primary free source, with clear error messages when unavailable.

def fetch_options_snapshot(tickers):
    """Delegate to skill module."""
    try:
        from skills.options_intelligence import fetch_options_snapshot as _fetch
        return _fetch(tickers)
    except Exception as e:
        log_error("Options snapshot failed", e)
        return f"[Options data unavailable: {str(e)[:80]}]"

def fetch_options_snapshot_polygon(tickers):
    """Delegate to skill module."""
    try:
        from skills.options_intelligence import fetch_options_snapshot_polygon as _fetch
        result, _ = _fetch(tickers)
        return result or "[Options data unavailable from Polygon]"
    except Exception as e:
        return f"[Polygon options unavailable: {str(e)[:80]}]"

def fetch_options_snapshot_yfinance(tickers):
    """Delegate to skill module."""
    try:
        from skills.options_intelligence import fetch_options_snapshot_yfinance as _fetch
        result, _ = _fetch(tickers)
        return result or "[Options data unavailable from yfinance]"
    except Exception as e:
        return f"[yfinance options unavailable: {str(e)[:80]}]"

# ─────────────────────────────────────────────
# EARNINGS CHECKER
# ─────────────────────────────────────────────
def check_upcoming_earnings(tickers):
    """
    Check if any portfolio holdings have upcoming or recent earnings.
    Uses Finnhub earnings calendar API (works even when yfinance is down).
    Returns a formatted string with earnings info for the LLM.
    """
    earnings_info = []
    today = datetime.date.today()

    for ticker in tickers[:15]:  # Check top holdings
        # METHOD 1: Try Finnhub earnings calendar
        if FINNHUB_API_KEY:
            try:
                from_date = (today - datetime.timedelta(days=2)).isoformat()
                to_date = (today + datetime.timedelta(days=14)).isoformat()
                r = requests.get(
                    f"https://finnhub.io/api/v1/calendar/earnings",
                    params={
                        "from": from_date,
                        "to": to_date,
                        "symbol": ticker,
                        "token": FINNHUB_API_KEY
                    },
                    timeout=10
                )
                data = r.json()
                earnings_list = data.get("earningsCalendar", [])
                for e in earnings_list:
                    earnings_date = e.get("date", "")
                    if earnings_date:
                        try:
                            e_dt = datetime.date.fromisoformat(earnings_date)
                            days_until = (e_dt - today).days
                            if -2 <= days_until <= 14:
                                hour = e.get("hour", "")
                                eps_est = e.get("epsEstimate", "")
                                rev_est = e.get("revenueEstimate", "")
                                status = "REPORTED" if days_until < 0 else "TODAY" if days_until == 0 else f"in {days_until}d"
                                detail = f" ({hour})" if hour else ""
                                if eps_est:
                                    detail += f" EPS est: ${eps_est}"
                                earnings_info.append(
                                    f"  🔔 {ticker} — Earnings {status} ({earnings_date}){detail}"
                                )
                        except ValueError:
                            continue
            except Exception:
                pass

        # METHOD 2: Try yfinance as fallback
        if not any(ticker in e for e in earnings_info):
            try:
                old_stderr = sys.stderr
                sys.stderr = StringIO()
                try:
                    t = yf.Ticker(ticker)
                    info = t.info
                    earnings_ts = info.get('earningsTimestamp') or info.get('earningsDate')
                    if earnings_ts:
                        if isinstance(earnings_ts, (int, float)):
                            earnings_dt = datetime.datetime.fromtimestamp(earnings_ts).date()
                        elif isinstance(earnings_ts, str):
                            try:
                                earnings_dt = datetime.date.fromisoformat(earnings_ts[:10])
                            except ValueError:
                                continue
                        else:
                            continue

                        days_until = (earnings_dt - today).days
                        if -2 <= days_until <= 7:
                            status = "REPORTED" if days_until < 0 else "TODAY" if days_until == 0 else f"in {days_until}d"
                            price = info.get('currentPrice') or info.get('regularMarketPrice')
                            earnings_info.append(
                                f"  🔔 {ticker} — Earnings {status} ({earnings_dt})"
                                + (f" @ ${price:.2f}" if price else "")
                            )
                except Exception:
                    pass
                finally:
                    sys.stderr = old_stderr
            except Exception:
                continue

    if earnings_info:
        return "**📅 Earnings Alerts (Portfolio Holdings):**\n" + "\n".join(earnings_info) + "\n"
    return ""


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


# NOTE: parse_and_store_recommendations and update_recommendation_performance
# are now DELEGATED to skills/recommendation_tracker.py to avoid duplication.
# The skill versions are called from main() after skills are initialized.

def parse_and_store_recommendations(investments_text: str, model_used: str = "unknown"):
    """Delegate to skill module."""
    try:
        from skills.recommendation_tracker import parse_and_store_recommendations as _store
        return _store(investments_text, model_used)
    except Exception as e:
        log_error("Recommendation tracking failed", e)
        return []

def update_recommendation_performance():
    """Delegate to skill module."""
    try:
        from skills.recommendation_tracker import update_recommendation_performance as _update
        return _update()
    except Exception as e:
        log_error("Recommendation performance update failed", e)


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
    DELEGATES to skills.portfolio_analysis for robust multi-source price fetching.
    Uses current market values (not cost basis) for portfolio % calculations.
    """
    try:
        from skills.portfolio_analysis import analyze_portfolio_weightage as _analyze
        result = _analyze()
        if result and result.get('total_holdings', 0) > 0:
            log(f"✓ Portfolio analysis: {result.get('data_quality', 'unknown')}")
            return result
    except Exception as e:
        log_error("Skill portfolio analysis failed, using built-in", e)

    # FALLBACK: Built-in analysis (same logic as skill, kept for resilience)
    portfolio_data = import_multiple_portfolios()
    holdings = portfolio_data.get('holdings', [])

    if not holdings:
        return {
            'total_holdings': 0,
            'weighted_summary': 'No portfolio data loaded',
            'top_positions': [],
            'concentration_ratio': 0,
            'total_value': 0,
            'total_cost_basis': 0,
            'total_unrealized_pnl': 0,
            'total_unrealized_pnl_pct': 0,
            'data_quality': 'no_data'
        }

    total_cost = sum(h['cost_basis'] for h in holdings)
    weighted_holdings = []
    api_errors = 0

    for h in holdings:
        try:
            current_price = None
            prev_close = None

            # Try yfinance with multiple fallbacks
            old_stderr = sys.stderr
            sys.stderr = StringIO()
            try:
                t = yf.Ticker(h['ticker'])
                fi = t.fast_info
                p = fi.last_price
                pc = fi.previous_close
                if p and p > 0:
                    current_price = float(p)
                    prev_close = float(pc) if pc and pc > 0 else None
            except Exception:
                pass
            finally:
                sys.stderr = old_stderr

            # Try yfinance info() for postMarketPrice
            if current_price is None:
                sys.stderr = StringIO()
                try:
                    t = yf.Ticker(h['ticker'])
                    info = t.info
                    p = (info.get('postMarketPrice') or info.get('currentPrice') or
                         info.get('regularMarketPrice'))
                    pc = info.get('regularMarketPreviousClose')
                    if p and float(p) > 0:
                        current_price = float(p)
                        prev_close = float(pc) if pc and float(pc) > 0 else None
                except Exception:
                    pass
                finally:
                    sys.stderr = old_stderr

            if current_price is None or current_price == 0:
                current_price = None
                api_errors += 1

            if current_price is not None:
                current_value = h['shares'] * current_price
                weighted_holdings.append({
                    'ticker': h['ticker'],
                    'shares': h['shares'],
                    'cost_basis': h['cost_basis'],
                    'purchase_price': h['purchase_price'],
                    'current_price': current_price,
                    'current_value': current_value,
                    'prev_close': prev_close,
                    'sources': h.get('sources', 1)
                })
        except Exception as e:
            log_error(f"Error analyzing {h['ticker']}", e)
            continue

    if not weighted_holdings:
        return {
            'total_holdings': 0,
            'weighted_summary': 'No price data available',
            'top_positions': [],
            'concentration_ratio': 0,
            'total_value': 0,
            'total_cost_basis': total_cost,
            'total_unrealized_pnl': 0,
            'total_unrealized_pnl_pct': 0,
            'data_quality': 'all_failed'
        }

    total_current_value = sum(wh['current_value'] for wh in weighted_holdings)

    for wh in weighted_holdings:
        wh['portfolio_pct'] = (wh['current_value'] / total_current_value * 100) if total_current_value > 0 else 0
        wh['unrealized_pnl'] = wh['current_value'] - wh['cost_basis']
        wh['unrealized_pnl_pct'] = ((wh['current_price'] - wh['purchase_price']) / wh['purchase_price'] * 100) if wh['purchase_price'] > 0 else 0
        wh['day_change'] = ((wh['current_price'] - wh['prev_close']) / wh['prev_close'] * 100) if wh.get('prev_close') and wh['prev_close'] > 0 else None

    weighted_holdings.sort(key=lambda x: x['portfolio_pct'], reverse=True)

    top_5 = weighted_holdings[:5]
    top_5_pct = sum(h['portfolio_pct'] for h in top_5)
    total_unrealized_pnl = total_current_value - total_cost
    total_unrealized_pnl_pct = ((total_current_value - total_cost) / total_cost * 100) if total_cost > 0 else 0

    if api_errors > 0:
        log(f"⚠ Portfolio analysis: {api_errors}/{len(holdings)} tickers had no live price")

    summary = f"**Portfolio Analysis ({len(weighted_holdings)} holdings):**\n"
    summary += f"- Total Cost Basis: ${total_cost:,.0f}\n"
    summary += f"- Total Current Value: ${total_current_value:,.0f}\n"
    summary += f"- Total Unrealized P&L: ${total_unrealized_pnl:+,.0f} ({total_unrealized_pnl_pct:+.1f}%)\n"
    summary += f"- Top 5 positions: {top_5_pct:.1f}% of portfolio\n"
    summary += f"- Concentration risk: {'HIGH' if top_5_pct > 60 else 'MODERATE' if top_5_pct > 40 else 'LOW'}\n\n"
    summary += "| Ticker | % Portfolio | Current Price | Today's Move | Unrealized P&L |\n"
    summary += "|--------|-------------|---------------|--------------|----------------|\n"
    for h in weighted_holdings[:10]:
        day_str = f"{h['day_change']:+.2f}%" if h.get('day_change') is not None else "N/A"
        summary += (f"| {h['ticker']} | {h['portfolio_pct']:.1f}% "
                    f"| ${h['current_price']:.2f} "
                    f"| {day_str} "
                    f"| ${h.get('unrealized_pnl', 0):+,.0f} ({h.get('unrealized_pnl_pct', 0):+.1f}%) |\n")

    return {
        'total_holdings': len(weighted_holdings),
        'weighted_summary': summary,
        'top_positions': weighted_holdings,
        'concentration_ratio': top_5_pct,
        'total_value': total_current_value,
        'total_cost_basis': total_cost,
        'total_unrealized_pnl': total_unrealized_pnl,
        'total_unrealized_pnl_pct': total_unrealized_pnl_pct,
        'data_quality': f'{api_errors} errors'
    }

# Cache for market sentiment to avoid repeated API calls during one run
_market_sentiment_cache = None

def get_market_sentiment() -> str:
    """
    Analyze market sentiment using VIX, market breadth, and economic indicators.
    Uses Finnhub as primary source (reliable), yfinance as fallback.
    Caches result to avoid rate limits during a single agent run.
    Returns: fear/greed assessment and market timing context.
    """
    global _market_sentiment_cache
    if _market_sentiment_cache is not None:
        return _market_sentiment_cache

    log("  → Analyzing market sentiment...")

    vix_price, vix_prev = 0.0, 0.0
    spy_price, spy_prev = 0.0, 0.0
    qqq_price, qqq_prev = 0.0, 0.0
    source = "none"

    # PRIMARY: Finnhub with retry logic for rate limits
    if FINNHUB_API_KEY:
        for attempt in range(3):  # Retry up to 3 times
            try:
                for symbol in ["SPY", "QQQ"]:
                    r = requests.get(
                        f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_API_KEY}",
                        timeout=15
                    )
                    if r.status_code == 429:
                        time.sleep(2 * (attempt + 1))  # Exponential backoff
                        continue
                    data = r.json()
                    p = data.get("c", 0)
                    pc = data.get("pc", 0)
                    if isinstance(p, (int, float)) and float(p) > 0:
                        if symbol == "SPY":
                            spy_price, spy_prev = float(p), float(pc) if pc else 0.0
                        elif symbol == "QQQ":
                            qqq_price, qqq_prev = float(p), float(pc) if pc else 0.0
                    time.sleep(0.5)  # Rate limit buffer between calls

                # Try VIX index first, fall back to VIXY ETF
                r_vix = requests.get(
                    f"https://finnhub.io/api/v1/quote?symbol=%5EVIX&token={FINNHUB_API_KEY}",
                    timeout=15
                )
                vix_data = r_vix.json()
                vix_raw = vix_data.get("c", 0)
                if isinstance(vix_raw, (int, float)) and float(vix_raw) > 0:
                    vix_price = float(vix_raw)
                    vix_prev = float(vix_data.get("pc", 0))
                else:
                    time.sleep(0.5)
                    r_vixy = requests.get(
                        f"https://finnhub.io/api/v1/quote?symbol=VIXY&token={FINNHUB_API_KEY}",
                        timeout=15
                    )
                    vixy_data = r_vixy.json()
                    vixy_raw = vixy_data.get("c", 0)
                    if isinstance(vixy_raw, (int, float)) and float(vixy_raw) > 0:
                        vix_price = float(vixy_raw)
                        vix_prev = float(vixy_data.get("pc", 0))

                source = "finnhub"
                break  # Success, exit retry loop
            except Exception:
                time.sleep(1)
                continue

    # FALLBACK: yfinance if Finnhub failed completely
    if vix_price == 0 and spy_price == 0:
        try:
            old_stderr = sys.stderr
            sys.stderr = StringIO()
            try:
                vix = yf.Ticker("^VIX")
                vix_price = float(vix.fast_info.last_price or 0)
                vix_prev = float(vix.fast_info.previous_close or 0)
                spy = yf.Ticker("SPY")
                spy_price = float(spy.fast_info.last_price or 0)
                spy_prev = float(spy.fast_info.previous_close or 0)
                qqq = yf.Ticker("QQQ")
                qqq_price = float(qqq.fast_info.last_price or 0)
                qqq_prev = float(qqq.fast_info.previous_close or 0)
                source = "yfinance"
            except Exception:
                pass
            finally:
                sys.stderr = old_stderr
        except Exception:
            pass

    # Calculate moves
    spy_move = ((spy_price - spy_prev) / spy_prev * 100) if spy_prev and spy_prev > 0 else 0
    qqq_move = ((qqq_price - qqq_prev) / qqq_prev * 100) if qqq_prev and qqq_prev > 0 else 0

    if vix_price == 0 and spy_price == 0:
        _market_sentiment_cache = "[Market sentiment unavailable — no data from Finnhub or yfinance]"
        return _market_sentiment_cache

    sentiment = ""
    if isinstance(vix_price, (int, float)) and vix_price > 0:
        if vix_price < 12:
            sentiment = f"**EXTREME GREED** (VIX: {vix_price:.1f})\n"
            sentiment += "Markets pricing in near-perfect outcomes. Complacency high.\n"
            sentiment += "**Action:** Take profits, trim concentrated positions, add hedges."
        elif vix_price < 16:
            sentiment = f"**GREED** (VIX: {vix_price:.1f})\n"
            sentiment += "Investors confident but not complacent.\n"
            sentiment += "**Action:** Steady accumulation, buy dips."
        elif vix_price < 20:
            sentiment = f"**NEUTRAL** (VIX: {vix_price:.1f})\n"
            sentiment += "Normal volatility. Mix of optimism and caution.\n"
            sentiment += "**Action:** Stick to high-conviction ideas."
        elif vix_price < 30:
            sentiment = f"**FEAR** (VIX: {vix_price:.1f})\n"
            sentiment += "Investors nervous but not panicked.\n"
            sentiment += "**Action:** Have dry powder ready, add to high-conviction on weakness."
        else:
            sentiment = f"**EXTREME FEAR** (VIX: {vix_price:.1f})\n"
            sentiment += "Markets pricing in significant downside.\n"
            sentiment += "**Action:** Contrarian buying opportunity for aggressive investors."
    else:
        sentiment = "[VIX data unavailable]\n"

    sentiment += f"\n**Today's Market Movement (via {source}):**\n"
    if isinstance(spy_price, (int, float)) and spy_price > 0:
        sentiment += f"- SPY: {spy_move:+.2f}% @ ${spy_price:.2f}\n"
    if isinstance(qqq_price, (int, float)) and qqq_price > 0:
        sentiment += f"- QQQ: {qqq_move:+.2f}% @ ${qqq_price:.2f}\n"

    _market_sentiment_cache = sentiment
    return sentiment

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
        
        # Identify underperforming positions (support both old and new key names)
        losers = [p for p in top_pos if p.get('unrealized_pnl_pct', p.get('unrealized_gain', 0)) < -10]
        if losers:
            suggestions += f"**Losing Positions ({len(losers)}):**\n"
            for p in losers[:5]:
                pct = p.get('unrealized_pnl_pct', p.get('unrealized_gain', 0))
                suggestions += f"- {p['ticker']}: {pct:+.1f}% | {p['portfolio_pct']:.1f}% of portfolio\n"
            suggestions += "Decision points: Are fundamentals intact? Or cut losses and redeploy?\n\n"
        
        # Identify strong performers
        winners = [p for p in top_pos if p.get('unrealized_pnl_pct', p.get('unrealized_gain', 0)) > 20]
        if winners:
            suggestions += f"**Top Performers ({len(winners)}):**\n"
            for p in winners[:5]:
                pct = p.get('unrealized_pnl_pct', p.get('unrealized_gain', 0))
                suggestions += f"- {p['ticker']}: {pct:+.1f}% | {p['portfolio_pct']:.1f}% of portfolio\n"
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

    # Use enhanced_trading for position sizing calculations
    position_sizing = ""
    total_value = portfolio_analysis.get('total_value', 0) if portfolio_analysis else 0
    if total_value > 0:
        try:
            from skills.enhanced_trading import calculate_position_size, calculate_kelly_criterion
            # Calculate position sizes for different conviction levels
            sizing_9 = calculate_position_size(total_value, 9)
            sizing_8 = calculate_position_size(total_value, 8)
            sizing_7 = calculate_position_size(total_value, 7)
            # Kelly example: 60% win prob, 3:1 reward/risk
            kelly_3x = calculate_kelly_criterion(0.60, 0.30, 0.10)
            kelly_2x = calculate_kelly_criterion(0.55, 0.20, 0.10)
            position_sizing = f"""
POSITION SIZING REFERENCE (Portfolio: ${total_value:,.0f}):
- Conviction 9/10: {sizing_9.get('recommendation', 'N/A')}
- Conviction 8/10: {sizing_8.get('recommendation', 'N/A')}
- Conviction 7/10: {sizing_7.get('recommendation', 'N/A')}
- Kelly Criterion (60% win, 3:1 R/R): {kelly_3x*100:.1f}% of portfolio
- Kelly Criterion (55% win, 2:1 R/R): {kelly_2x*100:.1f}% of portfolio
USE THESE for all position sizing in recommendations."""
        except Exception:
            pass

    # Build portfolio context for the LLM
    portfolio_context = ""
    if portfolio_analysis:
        portfolio_context = f"""
YOUR PORTFOLIO CONTEXT:
{portfolio_analysis.get('weighted_summary', '')}

Concentration Ratio: {portfolio_analysis.get('concentration_ratio', 0):.1f}%
Top holdings need attention if this ratio is too high.

{analyze_rebalancing_opportunities(portfolio_analysis)}
{position_sizing}
"""

    # Add options context for cross-referencing
    options_section = ""
    if options_context and options_context != "[Options data unavailable]":
        options_section = f"""
OPTIONS MARKET CONTEXT:
{options_context[:800]}
Use options data (IV levels, unusual activity, earnings dates) to inform stock recommendations."""
    
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

Generate **3-5 Investment Ideas** using the STRUCTURED TRADE THESIS FRAMEWORK.

## MANDATORY TRADE THESIS FRAMEWORK

For EVERY trade idea, provide this structured analysis:

### THESIS (1 sentence)
[Clear, concise investment logic]

### BULL CASE (3 strongest reasons this goes up)
1. [Reason 1 - specific with data/catalysts]
2. [Reason 2 - specific with data/catalysts]
3. [Reason 3 - specific with data/catalysts]

### BEAR CASE (3 strongest reasons this goes wrong)
1. [Risk 1 - what could cause losses]
2. [Risk 2 - what could cause losses]
3. [Risk 3 - what could cause losses]

### RISK/REWARD ANALYSIS
- Entry Price: $X.XX
- Target Price: $Y.YY (upside: Z%)
- Stop Loss: $A.AA (downside: B%)
- Risk/Reward Ratio: [MUST be >= 3:1 to recommend]
- Win Probability: [X% based on analysis]
- Expected Value: [Win% * Upside - Loss% * Downside]
- Kelly Position Size: [calculated % of portfolio]

### PRE-MORTEM ANALYSIS
"This trade will fail if:"
1. [Specific failure condition 1]
2. [Specific failure condition 2]
3. [Specific failure condition 3]

### SCENARIO ANALYSIS
- Bull Case (25% prob): Stock reaches $X (+Y%)
- Base Case (50% prob): Stock reaches $A (+B%)
- Bear Case (25% prob): Stock drops to $C (-D%)
- Expected Return: [weighted average]

### EXIT CRITERIA
- Profit Target: Sell at $X or when [condition]
- Stop Loss: Sell at $A (B% below entry)
- Time Stop: Re-evaluate if thesis hasnt played out in [timeframe]
- Thesis Break: Exit immediately if [specific condition changes]

### PORTFOLIO FIT
- Sector: [sector] - Current exposure: X%
- Correlation to existing holdings: [low/medium/high]

## RULES
1. Only recommend trades where Risk/Reward >= 3:1
2. Expected Value must be strongly positive
3. Win probability >= 60% OR asymmetric upside (5x+)
4. Position size <= 10% of portfolio (use Kelly Criterion)
5. Must be able to articulate WHY this is a good trade
6. Scan BROAD market, not just current holdings
7. For portfolio positions: analyze by WEIGHT, suggest SELL/REDUCE for overvalued
8. Recommend HOLDING CASH if no compelling opportunities
9. Look for ONCE-IN-A-LIFETIME opportunities: extreme asymmetric plays, 50%+ upside potential, clear catalysts

For EACH idea output:
### [#] TICKER - Thesis
**Type/Price:** [Stock/ETF/Crypto] @ $X.XX
**Why:** 2-3 sentences, first-principles
**Bull Case:** 1. 2. 3.
**Bear Case:** 1. 2. 3.
**Risk/Reward:** X:1 | Win Prob: X% | EV: +X%
**Kelly Size:** X% of portfolio
**Entry/Target/Stop:** $X.XX -> $Y.YY / $Z.ZZ
**Pre-Mortem:** "Fails if: 1. 2. 3."
**Exit Criteria:** Profit at $X / Stop at $Z / Time stop: X weeks
**Horizon:** [Swing 2-8wk / Medium 3-12mo / Long 1-3yr]
**Conviction:** X/10 | **Track:** Yes/No
**Portfolio Fit:** [New/ADD/REDUCE/SELL/HOLD]

Not financial advice. Verify before acting.""".format(
            memory=memory_slice,
            market_data=market_data_slice,
            digest=digest_slice,
            portfolio_context=portfolio_context,
            options_section=options_section,
            once_in_a_lifetime_context=once_in_a_lifetime_context
        ),
        max_tokens=2500,
    )

def task_options_ideas(market_data: str, digest: str, memory: str,
                        options_context: str = "", earnings_context: str = "",
                        market_sentiment: str = "") -> str:
    log("  → Generating options ideas...")
    if not options_context:
        options_context = fetch_options_snapshot(["SPY", "QQQ", "NVDA", "AAPL"])

    memory_summary = summarize_text(memory, "memory", 300)
    digest_summary = digest[:500]
    market_data_slice = market_data[:600]

    # Use enhanced_trading to detect options imbalances for top tickers
    options_imbalance_data = ""
    try:
        from skills.enhanced_trading import detect_options_imbalances
        for ticker in ["SPY", "QQQ", "NVDA", "AAPL", "PLTR"]:
            try:
                imb = detect_options_imbalances(ticker)
                if "error" not in imb:
                    options_imbalance_data += f"\n{ticker} @ ${imb.get('current_price', 0):.2f}:\n"
                    if imb.get('expirations'):
                        for exp, data in imb['expirations'].items():
                            options_imbalance_data += f"  {exp}: "
                            if data.get('put_call_volume_ratio'):
                                options_imbalance_data += f"P/C vol ratio={data['put_call_volume_ratio']:.2f} "
                            if data.get('avg_call_iv') and data.get('avg_put_iv'):
                                options_imbalance_data += f"Call IV={data['avg_call_iv']:.0%} Put IV={data['avg_put_iv']:.0%}"
                            options_imbalance_data += "\n"
            except Exception:
                continue
    except Exception:
        pass

    if options_imbalance_data:
        options_context += f"\n\n📊 OPTIONS IMBALANCE ANALYSIS:\n{options_imbalance_data}"

    # Build earnings section for options context
    earnings_section = ""
    if earnings_context and earnings_context != "No upcoming earnings.":
        earnings_section = f"""
⚠️ EARNINGS CALENDAR (CRITICAL FOR OPTIONS):
{earnings_context}
RULE: Avoid selling covered calls on stocks reporting earnings within 2 weeks.
RULE: Consider buying protective puts before earnings for large positions.
RULE: High IV before earnings = expensive options = favor selling premium."""

    # Build sentiment section
    sentiment_section = ""
    if market_sentiment and "unavailable" not in market_sentiment.lower():
        sentiment_section = f"""
🌡️ MARKET SENTIMENT:
{market_sentiment}
Use VIX level to guide strategy: High VIX = sell premium, Low VIX = buy protection."""

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
{earnings_section}
{sentiment_section}

Generate **2-3 Options Ideas** using PRICING IMBALANCE analysis + EARNINGS AWARENESS.

## OPTIONS STRATEGY FRAMEWORK

First, analyze the options data for PRICING IMBALANCES:
- IV Rank > 70: Options are EXPENSIVE -> Sell premium (covered calls, cash-secured puts, credit spreads)
- IV Rank < 30: Options are CHEAP -> Buy premium (LEAPS calls, debit spreads)
- Put/Call Ratio > 1.5: Extreme bearish sentiment -> Contrarian buy opportunity
- Put/Call Ratio < 0.5: Extreme bullish sentiment -> Consider taking profits
- IV > HV by 50%+: Options overpriced -> Sell volatility
- IV < HV by 30%+: Options underpriced -> Buy volatility

## STRATEGY TYPES (in order of priority)

### 1. ASYMMETRIC PLAYS (highest priority)
- Trades where upside is 5x+ the downside
- LEAPS calls on high-conviction growth stocks
- Must have clear catalyst and timeline
- Once-in-a-lifetime opportunities with massive upside

### 2. PREMIUM SELLING (consistent income)
- Covered calls on existing positions
- Cash-secured puts on stocks you want to own
- Only sell when IV Rank > 70 (expensive options)
- Target 1-2% monthly return with high probability

### 3. HIGH PROBABILITY TRADES
- Credit spreads on overbought/oversold conditions
- Iron condors on range-bound stocks
- Probability of profit > 70%

## RULES
- Defined-risk ONLY (long calls/puts, covered calls, LEAPS, credit spreads)
- Min 2wk expiry, prefer 30-90d or 6mo+ LEAPS
- Max 5% portfolio total in options
- NEVER let expire ITM - SELL before expiry
- NO leverage, NO naked, NO margin
- Every trade must have a clear EDGE (pricing imbalance)
- Look for pricing imbalances that present asymmetric opportunities

For EACH:
### [Strategy] on [TICKER]
**Type:** [Long Call/Put/Covered Call/LEAPS/Credit Spread]
**Edge:** [Why this has an edge - pricing imbalance]
**Why:** 1-2 sentences
**Strike/Expiry:** $X / [date]
**Premium/Max Risk:** $X (all you can lose)
**Target:** Sell @ $X or X% gain
**Probability of Profit:** X%
**EXIT:** SELL before expiry, NEVER let ITM.
**Conviction:** X/10

Suggest 1 **Covered Call** if owner holds underlying.

Educational only. Verify with broker.*""".format(
            memory_summary=memory_summary,
            market_data=market_data_slice,
            digest_summary=digest_summary,
            options_context=options_context,
            earnings_section=earnings_section,
            sentiment_section=sentiment_section
        ),
        max_tokens=1200,
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


def build_and_save_report(market_data, digest, investments, options, learning,
                            market_sentiment="", portfolio_analysis_text="", market_reaction="",
                            earnings_alerts="") -> str:
    # Get recommendation updates
    rec_updates = read_file(RECOMMENDATIONS_FILE)
    if rec_updates:
        rec_section = "\n---\n# 📊 Recommendation Tracking & Decision Journal\n" + rec_updates[:2000] + "\n"
    else:
        rec_section = ""

    reaction_section = f"\n---\n\n## 📰 Why The Market Moved Today\n\n{market_reaction}\n" if market_reaction else ""

    earnings_section = f"\n---\n\n## 📅 Earnings Alerts\n\n{earnings_alerts}\n" if earnings_alerts else ""

    report = f"""# 🧠 Daily Intelligence Report
**{NOW}** | Run {RUN_LABEL} | Market {'Open 🟢' if IS_MARKET_OPEN else 'Closed 🔴 (After-Hours)'}

---

## 📊 Market Snapshot
```
{market_data}
```

---

## 🌡️ Market Sentiment & Timing
{market_sentiment}
{reaction_section}
{earnings_section}
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

        # Initialize skills with API keys
        try:
            from skills.portfolio_analysis import init_skills as init_portfolio
            from skills.options_intelligence import init_options_skill
            from skills.recommendation_tracker import init_tracker_skill
            from skills.news_research import init_news_skill
            from skills.learning_curator import init_learning_skill

            init_portfolio(finnhub_key=FINNHUB_API_KEY, base_dir=str(BASE_DIR))
            init_options_skill(polygon_key=POLYGON_API_KEY, base_dir=str(BASE_DIR))
            init_tracker_skill(base_dir=str(BASE_DIR), finnhub_key=FINNHUB_API_KEY)
            init_news_skill(tavily_key=TAVILY_API_KEY, finnhub_key=FINNHUB_API_KEY, base_dir=str(BASE_DIR))
            init_learning_skill(base_dir=str(BASE_DIR))
            log("[OK] All skills initialized with API keys")
        except Exception as e:
            log(f"[!] Skills initialization failed: {e}")

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
    
    # 0b. Alpaca paper trading account check
    if SKILLS_AVAILABLE:
        try:
            acct = get_account_info()
            if "error" not in acct:
                log(f"[OK] Paper trading account: ${acct.get('portfolio_value', 0):,.2f} equity")
            else:
                log(f"[!] Alpaca not configured: {acct['error']}")
        except Exception:
            pass

    # 1. Load memory (tiered: hot → warm → cold)
    log("📚 Loading memory...")
    if SKILLS_AVAILABLE:
        try:
            memory = get_memory_for_run()
            if memory == "[No memory data yet]":
                memory = load_memory()
            log(f"[OK] Memory loaded: {len(memory)} chars")
        except Exception as e:
            log(f"[!] Memory manager failed, using built-in: {e}")
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

    # Extract portfolio tickers for options and earnings analysis
    all_portfolio_tickers = [h['ticker'] for h in portfolio_analysis.get('top_positions', [])]
    top_portfolio_tickers = all_portfolio_tickers[:5]

    log("🌡️  Analyzing market sentiment (fear/greed)...")
    market_sentiment = get_market_sentiment()

    # 3b. Check for upcoming/recent earnings in portfolio
    log("📅 Checking earnings calendar for portfolio holdings...")
    earnings_alerts = check_upcoming_earnings(all_portfolio_tickers)
    if earnings_alerts:
        log(f"✓ Earnings alerts found: {earnings_alerts[:100]}")
    else:
        log("  No upcoming earnings in the next 7 days for portfolio holdings")

    if SKILLS_AVAILABLE:
        try:
            get_index_prices()
        except Exception:
            pass

    # 4. Generate content (sub-agents run sequentially)
    log("✍️  Running sub-agents...")
    digest      = task_news_digest(rss, fin_news, memory)
    digest_summary = summarize_text(digest, "news digest", 300)

    # Fetch options data early with portfolio tickers included
    # Use skill module's fetch_options_snapshot for better reliability
    try:
        from skills.options_intelligence import fetch_options_snapshot as _fetch_options
        options_tickers = list(set(["SPY", "QQQ", "NVDA", "AAPL", "PLTR"] + top_portfolio_tickers))
        options_context = _fetch_options(options_tickers)
    except Exception:
        options_tickers = list(set(["SPY", "QQQ", "NVDA", "AAPL"] + top_portfolio_tickers))
        options_context = fetch_options_snapshot_yfinance(options_tickers)
        if not options_context or options_context == "[Options data unavailable]":
            options_context = "[Options data unavailable — both Polygon and yfinance failed. This may be due to after-hours data delays or API rate limits.]"

    # Build combined context for investment ideas with ALL data
    investment_context = options_context
    if earnings_alerts:
        investment_context += f"\n\n⚠️ EARNINGS ALERT:\n{earnings_alerts}\nConsider earnings implications for any recommendations."
    if market_sentiment:
        investment_context += f"\n\n🌡️ MARKET SENTIMENT:\n{market_sentiment}\nAdjust sizing/strategy based on VIX/fear-greed."

    # 4a. Investment ideas with everything: portfolio, options, earnings, sentiment
    investments = task_investment_ideas(
        market_data, digest_summary, memory, portfolio_analysis,
        options_context=investment_context
    )

    parse_and_store_recommendations(investments)

    # 4b. Options ideas with earnings + sentiment awareness
    options = task_options_ideas(
        market_data, digest_summary, memory,
        options_context=options_context,
        earnings_context=earnings_alerts or "No upcoming earnings.",
        market_sentiment=market_sentiment
    )

    # 4c. Learning and market reaction
    learning = task_learning(digest_summary, memory)
    market_reaction = task_market_reaction(market_data, digest_summary)

    # 5. Write report
    log("📝 Writing report...")
    report = build_and_save_report(
        market_data,
        digest,
        investments,
        options,
        learning,
        market_sentiment=market_sentiment,
        portfolio_analysis_text=portfolio_analysis.get('weighted_summary', ''),
        market_reaction=market_reaction,
        earnings_alerts=earnings_alerts
    )

    # 5. Send report to Telegram (free, non-blocking)
    if SKILLS_AVAILABLE:
        try:
            sent = send_report_via_telegram(report)
            if sent:
                log(f"[OK] Report sent to {sent} Telegram user(s)")
            else:
                log("[!] Telegram: No users configured yet (message the bot first)")
        except Exception as e:
            log(f"[!] Telegram send failed: {e}")

    # 6. Self-reflect & update learnings (rating-based, efficient)
    log("🪞 Reflecting and updating LEARNINGS.md (rating-based)...")
    reflection = task_self_reflect(report, memory)
    save_learnings(reflection)

    # 7. Update tiered memory system
    if SKILLS_AVAILABLE:
        try:
            run_data = {
                "date": TODAY,
                "rating": 0,  # Will be updated when user rates
                "recommendations": parse_and_store_recommendations.__defaults__ or [],
                "learnings": [],
                "portfolio_value": portfolio_analysis.get('total_value', 0),
                "concentration": portfolio_analysis.get('concentration_ratio', 0),
                "model": "free"
            }
            update_hot_memory(run_data)
            update_warm_memory()
            log("[OK] Tiered memory updated (hot + warm)")
        except Exception as e:
            log(f"[!] Memory update failed: {e}")

    # 8. Log benchmark comparison
    if SKILLS_AVAILABLE:
        try:
            perf = calculate_portfolio_performance(
                portfolio_analysis.get('total_value', 0),
                sum(h['cost_basis'] for h in portfolio_analysis.get('top_positions', []))
            )
            comparison = compare_to_benchmarks(perf.get('total_return_pct', 0))
            outperformed = comparison.get('outperformed', [])
            if outperformed:
                log(f"[OK] Portfolio outperforming: {', '.join(outperformed)}")
            update_benchmark_log(
                portfolio_analysis.get('total_value', 0),
                sum(h['cost_basis'] for h in portfolio_analysis.get('top_positions', [])),
                []
            )
            log("[OK] Benchmark log updated")
        except Exception as e:
            log(f"[!] Benchmark logging failed: {e}")

    # 9. Create ClickUp tasks for high-conviction recommendations (8+)
    if SKILLS_AVAILABLE:
        try:
            recs = read_file(RECOMMENDATIONS_FILE)
            active_lines = [l for l in recs.split('\n') if l.startswith('- ') and 'Active' in l]
            tasks_created = 0
            for line in active_lines:
                parts = line[2:].split(' | ')
                if len(parts) >= 5:
                    try:
                        conviction = int(parts[4].split('/')[0].strip())
                        if conviction >= 8:
                            ticker = parts[1].strip()
                            rec_data = {
                                "ticker": ticker,
                                "action": "BUY",
                                "thesis": f"Conviction {conviction}/10 - see report {TODAY}-{RUN_LABEL}",
                                "entry_price": parts[2].strip().replace('$', ''),
                                "target_price": parts[3].strip().replace('$', ''),
                                "stop_loss": "TBD",
                                "conviction": conviction,
                                "horizon": "Swing to Long-term"
                            }
                            result = create_recommendation_task(rec_data)
                            if "error" not in result:
                                tasks_created += 1
                    except (ValueError, IndexError):
                        continue
            if tasks_created:
                log(f"[OK] Created {tasks_created} ClickUp task(s) for high-conviction picks")
        except Exception as e:
            log(f"[!] ClickUp task creation failed: {e}")

    # 10. Execute trades on Alpaca for high-conviction recommendations (8+)
    if SKILLS_AVAILABLE:
        try:
            from skills.alpaca_trading import (place_stock_order, place_option_order,
                                                get_all_positions_including_options,
                                                get_trade_history)

            # 10a. Read Alpaca positions for learning/feedback
            alpaca_positions = get_all_positions_including_options()
            alpaca_trades = get_trade_history(limit=20)
            if alpaca_positions:
                log(f"[OK] Alpaca positions: {len(alpaca_positions)} holdings")
                for pos in alpaca_positions[:5]:
                    pl_str = f"{pos.get('unrealized_plpc', 0):+.1f}%" if pos.get('unrealized_plpc') else "N/A"
                    log(f"  → {pos['symbol']}: {pos['qty']} @ ${pos.get('avg_entry', 0):.2f} "
                        f"(current: ${pos.get('current_price', 0):.2f}, P&L: {pl_str}) [{pos['type']}]")
            if alpaca_trades:
                log(f"[OK] Recent Alpaca trades: {len(alpaca_trades)} fills")

            # 10b. Place new stock trades for high-conviction (8+) recommendations
            recs = read_file(RECOMMENDATIONS_FILE)
            active_lines = [l for l in recs.split('\n') if l.startswith('- ') and 'Active' in l]
            trades_executed = 0
            for line in active_lines:
                parts = line[2:].split(' | ')
                if len(parts) >= 5:
                    try:
                        conviction = int(parts[4].split('/')[0].strip())
                        if conviction >= 8:
                            ticker = parts[1].strip()
                            entry_str = parts[2].strip().replace('$', '').replace(',', '')
                            try:
                                entry_price = float(entry_str) if entry_str != 'N/A' else 0
                            except ValueError:
                                entry_price = 0
                            if entry_price > 0:
                                # Check if we already hold this position
                                already_held = any(p['symbol'] == ticker for p in alpaca_positions)
                                if already_held:
                                    log(f"  Already hold {ticker} in Alpaca, skipping")
                                    continue

                                # Calculate position size based on conviction
                                acct = get_account_info()
                                portfolio_val = acct.get('portfolio_value', 100000)
                                if conviction >= 9:
                                    pct = 0.08
                                elif conviction >= 8:
                                    pct = 0.05
                                else:
                                    pct = 0.03
                                dollar_amount = portfolio_val * pct
                                qty = max(1, int(dollar_amount / entry_price))

                                trade_result = place_stock_order(ticker, qty, "buy", "market")
                                if trade_result.get("status") in ["FILLED", "submitted", "accepted", "new"]:
                                    trades_executed += 1
                                    log(f"[OK] Alpaca trade: BUY {ticker} x{qty} @ ${entry_price:.2f} "
                                        f"(conviction: {conviction}/10, status: {trade_result.get('status')})")
                                elif trade_result.get("status") == "REJECTED":
                                    log(f"[!] Alpaca trade rejected for {ticker}: {trade_result.get('error', 'unknown')}")
                                else:
                                    log(f"[!] Alpaca trade uncertain for {ticker}: {trade_result}")
                    except (ValueError, IndexError):
                        continue

            # 10c. Place options trades from options intelligence section
            # Parse options ideas from the report text
            options_section = options if 'options' in dir() else ""
            option_trades = 0
            if options_section and "Options Ideas" in str(options_section):
                # Extract option trade ideas from the options text
                import re
                option_pattern = r'\*\*Type:\*\*\s*(Long Call|Long Put|Covered Call|LEAPS Call|Credit Spread|Bull Put Spread)\s*\n.*?\*\*Strike/Expiry:\*\*\s*\$?([\d,.]+)\s*/\s*(\w+\s+\d+,?\s*\d*)'
                for match in re.finditer(option_pattern, str(options_section), re.DOTALL):
                    opt_type = match.group(1)
                    strike = float(match.group(2).replace(',', ''))
                    expiry_str = match.group(3)
                    log(f"  Found options idea: {opt_type} @ ${strike} exp {expiry_str}")
                    # Note: Full options execution requires OCC symbol lookup via Alpaca's options chain API
                    # This is a placeholder for when options chain integration is complete
                    option_trades += 1

            if trades_executed:
                log(f"[OK] Executed {trades_executed} Alpaca stock trade(s)")
            if option_trades:
                log(f"[OK] Identified {option_trades} options trade ideas (execution requires options chain lookup)")

            # 10d. Read back updated positions after trading
            updated_positions = get_all_positions_including_options()
            if updated_positions:
                total_pl = sum(p.get('unrealized_pl', 0) for p in updated_positions)
                log(f"[OK] Updated Alpaca portfolio: {len(updated_positions)} positions, "
                    f"total unrealized P&L: ${total_pl:+,.0f}")
        except Exception as e:
            log(f"[!] Alpaca trade execution failed: {e}")

    log("✅ Agent run complete.")
    log(f"   Report: REPORTS/{TODAY}-{RUN_LABEL}.md")
    log(f"   Skills: {'✅ All active' if SKILLS_AVAILABLE else '⚠️  Built-in only (skills import failed)'}")
    log(f"   Rate this run: add_rating(score, 'optional notes') in Python")


if __name__ == "__main__":
    main()
