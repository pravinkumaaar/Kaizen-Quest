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
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

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
    from skills.news_research import fetch_rss, tavily_search, finnhub_news, finnhub_earnings_surprise
    from skills.earnings_intelligence import get_comprehensive_earnings_intelligence, init_earnings_skill
    from skills.market_foresight import get_market_foresight, init_foresight_skill
    from skills.learning_curator import get_or_create_weekly_theme, generate_learning_content
    from skills.recommendation_tracker import clear_active_recommendations as clear_recs, parse_and_store_recommendations, update_recommendation_performance
    from skills.alpaca_trading import get_account_info, get_positions, get_portfolio_history
    from skills.benchmark_tracker import get_index_prices, compare_to_benchmarks, update_benchmark_log, get_performance_summary, calculate_portfolio_performance
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
    from skills.portfolio_manager import (init_portfolio_manager, get_alpaca_portfolio_snapshot,
                                           review_all_positions, generate_portfolio_report,
                                           generate_urgent_alert, generate_once_in_a_lifetime_alert,
                                           TARGET_ALLOCATION)
    from skills.smart_money_tracker import (get_smart_money_summary, generate_smart_money_report,
                                             get_hedge_fund_consensus, get_congressional_trades,
                                             get_insider_trades, init_smart_money_skill)
    from skills.sector_rotation import (analyze_sector_rotation, analyze_cap_rotation,
                                         detect_emerging_themes, generate_sector_report,
                                         get_macro_rotation_signals, get_sector_momentum_score,
                                         analyze_subsector_momentum, init_sector_skill)
    from skills.benchmark_tracker import (generate_full_report as generate_benchmark_report,
                                           compute_all_metrics, cumulative_return_chart,
                                           metrics_comparison_table, analyze_small_cap_cycle,
                                           analyze_sector_leadership, analyze_macro_indicators)
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
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
TAVILY_API_KEY     = os.environ.get("TAVILY_API_KEY")
FINNHUB_API_KEY    = os.environ.get("FINNHUB_API_KEY")
POLYGON_API_KEY    = os.environ.get("POLYGON_API_KEY")
ALPACA_API_KEY     = os.environ.get("ALPACA_API_KEY")
ALPACA_SECRET_KEY  = os.environ.get("ALPACA_SECRET_KEY")
CLICKUP_API_KEY    = os.environ.get("CLICKUP_API_KEY")
CLICKUP_LIST_ID    = os.environ.get("CLICKUP_LIST_ID")
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

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
    import time
    
    # SOURCE 1: Finnhub (most reliable — works after hours)
    if FINNHUB_API_KEY:
        try:
            r = requests.get(
                f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}",
                timeout=10
            )
            if r.status_code == 200 and r.text:
                data = r.json()
                p = data.get("c", 0)
                pc = data.get("pc", 0)
                if p and float(p) > 0:
                    return float(p), float(pc) if pc and float(pc) > 0 else None
            elif r.status_code == 429:
                time.sleep(1)  # Rate limited — wait and try fallback
        except Exception:
            pass

    # SOURCE 2: yfinance fast_info (with retry)
    for attempt in range(2):
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
            if attempt == 0:
                time.sleep(0.5)
        finally:
            sys.stderr = old_stderr

    # SOURCE 3: yfinance info() — includes postMarketPrice
    old_stderr = sys.stderr
    sys.stderr = StringIO()
    try:
        t = yf.Ticker(ticker)
        info = t.info
        if info:
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


def _yf_price(ticker):
    """Quick price lookup with yfinance + Finnhub fallback. Returns dict with price, prev_close, change_pct."""
    import time
    # Try yfinance up to 2 times
    for attempt in range(2):
        try:
            old_stderr = sys.stderr
            sys.stderr = StringIO()
            try:
                t = yf.Ticker(ticker)
                fi = t.fast_info
                p = fi.last_price
                pc = fi.previous_close
                if p and p > 0:
                    chg = ((p - pc) / pc * 100) if pc and pc > 0 else 0
                    return {"price": float(p), "prev_close": float(pc) if pc else 0, "change_pct": float(chg)}
            finally:
                sys.stderr = old_stderr
        except Exception:
            if attempt == 0:
                time.sleep(1)  # Brief pause before retry
            continue
    
    # Fallback to Finnhub
    if FINNHUB_API_KEY:
        try:
            r = requests.get(
                f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}",
                timeout=10
            )
            if r.status_code == 200:
                data = r.json()
                p = data.get("c", 0)
                pc = data.get("pc", 0)
                if p and p > 0:
                    chg = ((p - pc) / pc * 100) if pc and pc > 0 else 0
                    return {"price": float(p), "prev_close": float(pc), "change_pct": float(chg)}
        except Exception:
            pass
    
    return {"price": 0, "prev_close": 0, "change_pct": 0}


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
    # Add small delays to avoid rate limits (Finnhub: 60 calls/min free tier)
    for i, ticker in enumerate(stock_tickers):
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
        # Rate limit: pause every 10 tickers
        if (i + 1) % 10 == 0:
            import time
            time.sleep(1)

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
# ─────────────────────────────────────────────
# COMPREHENSIVE EARNINGS INTELLIGENCE
# ─────────────────────────────────────────────
#
# Covers 3 layers:
#   1. PORTFOLIO earnings — your actual holdings
#   2. RELATED/SUPPLY CHAIN earnings — companies in the same ecosystem as your holdings
#      (e.g. if you own NVDA → also watch TSM, ASML, MU, MRVL, etc.)
#   3. SECTOR EXCITEMENT — the most anticipated earnings in sectors you're invested in,
#      including emerging companies you may not own or know about yet
#
# Uses Finnhub earnings calendar (free tier) which covers ~5000 companies per query.

# Supply chain / ecosystem mapping: if you own a key company, also watch these related tickers
SUPPLY_CHAIN_MAP = {
    # AI / Semiconductors ecosystem
    "NVDA": ["TSM", "ASML", "MU", "MRVL", "AVGO", "AMAT", "LRCX", "KLAC", "SNPS", "CDNS", "ARM"],
    "AMD":  ["TSM", "MU", "MRVL", "AVGO", "QCOM", "SWKS", "QRVO", "MRAM"],
    "INTC": ["TSM", "ASML", "AMAT", "LRCX", "KLAC", "MRVL"],
    "AVGO": ["TSM", "MRVL", "SWKS", "QRVO", "QCOM"],
    "QCOM": ["TSM", "SWKS", "QRVO", "MRVL", "MU"],
    "MU":   ["TSM", "ASML", "AMAT", "LRCX", "KLAC"],
    "TSM":  ["ASML", "AMAT", "LRCX", "KLAC"],
    "AMAT": ["LRCX", "KLAC", "ASML", "TSM"],
    "LRCX": ["AMAT", "KLAC", "ASML", "TSM"],
    "MRVL": ["TSM", "AVGO", "MU", "QCOM"],
    # Cloud / SaaS ecosystem
    "MSFT": ["SNOW", "DDOG", "MDB", "NET", "CRM", "NOW", "WDAY", "ZS", "CRWD", "OKTA", "PANW"],
    "GOOG": ["SNOW", "DDOG", "MDB", "NET", "ZM", "TEAM", "HUBS", "VEEV"],
    "AMZN": ["SNOW", "DDOG", "MDB", "NET", "SHOP", "WIX", "SQ", "MELI"],
    "CRM":  ["NOW", "WDAY", "HUBS", "ZM", "TEAM", "DOCU", "PLTR"],
    "SNOW": ["DDOG", "MDB", "PLTR", "NET", "MSFT"],
    "PLTR": ["SNOW", "DDOG", "AI", "CRM", "MSFT"],
    "DDOG": ["SNOW", "MDB", "NET", "MSFT", "GOOG"],
    "NET":  ["DDOG", "SNOW", "MSFT", "GOOG", "AMZN"],
    "AI":   ["PLTR", "SNOW", "DDOG", "MSFT", "GOOG", "AMZN"],
    "MDB":  ["SNOW", "DDOG", "NET", "MSFT"],
    # Mega-Cap Tech ecosystem
    "AAPL": ["QCOM", "SWKS", "QRVO", "MU", "AVGO", "TSM", "TXN"],
    "META": ["SNAP", "PINS", "TTD", "ROKU", "GOOG", "MSFT"],
    "TSLA": ["F", "GM", "RIVN", "LCID", "NIO", "XPEV", "LI", "ALV", "APTV"],
    # Finance ecosystem
    "JPM":  ["BAC", "WFC", "C", "GS", "MS", "BLK", "SCHW", "COIN"],
    "V":    ["MA", "PYPL", "SQ", "AFRM", "GPN", "FI"],
    "MA":   ["V", "PYPL", "SQ", "AFRM", "GPN"],
    "GS":   ["JPM", "MS", "BLK", "SCHW"],
    "COIN": ["MARA", "RIOT", "MSTR", "SQ", "HOOD"],
    # Healthcare / Pharma ecosystem
    "JNJ":  ["PFE", "MRK", "ABBV", "LLY", "BMY", "GILD", "AMGN", "REGN", "VRTX", "BIIB"],
    "PFE":  ["JNJ", "MRK", "ABBV", "LLY", "BMY", "GILD", "AMGN", "REGN", "MRNA", "BNTX"],
    "LLY":  ["JNJ", "PFE", "MRK", "ABBV", "NVO", "REGN", "VRTX", "BIIB"],
    "ABBV": ["JNJ", "PFE", "MRK", "LLY", "BMY", "GILD", "AMGN", "REGN", "VRTX"],
    "UNH":  ["CI", "HUM", "ELV", "MOH", "CNC"],
    "REGN": ["VRTX", "BIIB", "GILD", "AMGN", "JNJ", "PFE"],
    "VRTX": ["REGN", "BIIB", "GILD", "AMGN", "JNJ"],
    "GILD": ["REGN", "VRTX", "BIIB", "AMGN", "JNJ", "PFE"],
    "AMGN": ["REGN", "VRTX", "BIIB", "GILD", "JNJ", "PFE"],
    "MRK":  ["JNJ", "PFE", "ABBV", "LLY", "BMY", "GILD", "AMGN", "REGN"],
    "BMY":  ["JNJ", "PFE", "MRK", "ABBV", "LLY", "GILD", "AMGN", "REGN"],
    "NVO":  ["LLY", "JNJ", "PFE", "MRK", "ABBV"],
    "MRNA": ["PFE", "BNTX", "JNJ", "MRK", "GILD"],
    "BNTX": ["PFE", "MRNA", "JNJ", "MRK"],
    # Consumer / Retail ecosystem
    "WMT":  ["TGT", "COST", "DG", "DLTR", "AMZN", "SHOP"],
    "COST": ["WMT", "TGT", "DG", "DLTR", "AMZN"],
    "AMZN": ["WMT", "TGT", "SHOP", "WIX", "MELI", "SE", "ETSY"],
    "HD":   ["LOW", "TSCO", "WMT", "AMZN"],
    "NKE":  ["ADDYY", "LULU", "DECK", "ONON", "CROX", "SKX", "COLM"],
    "SBUX": ["MCD", "DPZ", "YUM", "CMG", "WING"],
    "MCD":  ["SBUX", "DPZ", "YUM", "CMG", "WING"],
    "LULU": ["NKE", "ADDYY", "DECK", "ONON", "COLM"],
    "DECK": ["NKE", "LULU", "ONON", "SKX", "COLM"],
    "CMG":  ["SBUX", "MCD", "YUM", "WING", "DPZ"],
    "TGT":  ["WMT", "COST", "DG", "DLTR", "AMZN"],
    "LOW":  ["HD", "TSCO", "WMT", "AMZN"],
    "DG":   ["WMT", "TGT", "COST", "DLTR"],
    "DLTR": ["WMT", "TGT", "COST", "DG"],
    "SHOP": ["AMZN", "WIX", "SQ", "MELI", "ETSY", "SE"],
    # Energy ecosystem
    "XOM":  ["CVX", "COP", "EOG", "PXD", "SLB", "BKR", "HAL", "OXY", "MPC", "VLO", "PSX"],
    "CVX":  ["XOM", "COP", "EOG", "PXD", "SLB", "BKR", "HAL", "OXY"],
    "SLB":  ["BKR", "HAL", "XOM", "CVX", "COP", "EOG", "PXD"],
    "COP":  ["XOM", "CVX", "EOG", "PXD", "SLB", "BKR"],
    "EOG":  ["XOM", "CVX", "COP", "PXD", "SLB", "BKR"],
    "PXD":  ["XOM", "CVX", "COP", "EOG", "SLB", "BKR"],
    "OXY":  ["XOM", "CVX", "COP", "EOG", "PXD"],
    "MPC":  ["VLO", "PSX", "XOM", "CVX", "DK", "PAR"],
    "VLO":  ["MPC", "PSX", "XOM", "CVX", "DK"],
    # Industrials / Defense ecosystem
    "CAT":  ["DE", "URI", "PCAR", "CMI", "AME", "ETN", "PH", "ITW", "DOV", "IR"],
    "BA":   ["LMT", "RTX", "NOC", "GD", "HII", "TDY", "TXT", "SPR", "HEI", "CW"],
    "LMT":  ["RTX", "NOC", "GD", "BA", "HII", "TDY", "TXT", "SPR", "HEI"],
    "RTX":  ["LMT", "NOC", "GD", "BA", "HII", "TDY", "TXT", "SPR"],
    "NOC":  ["LMT", "RTX", "GD", "BA", "HII", "TDY"],
    "GD":   ["LMT", "RTX", "NOC", "BA", "HII", "TDY"],
    "DE":   ["CAT", "URI", "PCAR", "CMI", "AME", "AGCO"],
    "URI":  ["CAT", "DE", "PCAR", "CMI", "AME"],
    # Media / Entertainment ecosystem
    "NFLX": ["DIS", "WBD", "PARA", "FOXA", "LYV", "ROKU", "SPOT", "TME"],
    "DIS":  ["NFLX", "WBD", "PARA", "FOXA", "LYV", "ROKU"],
    "SPOT": ["NFLX", "DIS", "ROKU", "TME", "WMG"],
    "ROKU": ["NFLX", "DIS", "SPOT", "TTD", "WBD"],
    "TTD":  ["ROKU", "SPOT", "NFLX", "DIS", "META", "GOOG"],
    # Payments / FinTech ecosystem
    "SQ":   ["PYPL", "AFRM", "COIN", "HOOD", "MA", "V", "GPN", "FI", "WU"],
    "PYPL": ["SQ", "AFRM", "MA", "V", "GPN", "FI", "WU", "COIN"],
    "AFRM": ["SQ", "PYPL", "MA", "V", "COIN", "UPST", "SOFI"],
    "COIN": ["HOOD", "SQ", "MARA", "RIOT", "MSTR", "PYPL"],
    "HOOD": ["COIN", "SQ", "PYPL", "AFRM", "SOFI"],
    "SOFI": ["AFRM", "UPST", "COIN", "HOOD", "SQ", "PYPL"],
    "UPST": ["AFRM", "SOFI", "SQ", "PYPL"],
    # EV / Auto ecosystem
    "F":    ["GM", "TSLA", "RIVN", "LCID", "NIO", "XPEV", "LI", "ALV", "APTV", "BWA"],
    "GM":   ["F", "TSLA", "RIVN", "LCID", "NIO", "XPEV", "LI", "ALV", "APTV"],
    "RIVN": ["LCID", "F", "GM", "TSLA", "NIO", "XPEV", "LI"],
    "NIO":  ["XPEV", "LI", "TSLA", "F", "GM", "RIVN", "LCID"],
    "XPEV": ["NIO", "LI", "TSLA", "F", "GM", "RIVN", "LCID"],
    "LI":   ["NIO", "XPEV", "TSLA", "F", "GM", "RIVN", "LCID"],
    "ALV":  ["APTV", "BWA", "F", "GM", "TSLA"],
    "APTV": ["ALV", "BWA", "F", "GM", "TSLA"],
    # Real Estate ecosystem
    "PLD":  ["AMT", "EQIX", "DLR", "SPG", "O", "WELL", "VTR", "PSA", "EXR", "AVB"],
    "AMT":  ["EQIX", "SBAC", "PLD", "DLR", "SPG"],
    # Telecom ecosystem
    "TMUS": ["T", "VZ", "CMCSA", "CHTR", "LUMN"],
    # Biotech ecosystem
    "BIIB": ["REGN", "VRTX", "GILD", "AMGN", "JNJ", "PFE"],
    # Crypto-adjacent
    "MSTR": ["COIN", "MARA", "RIOT", "SQ", "HOOD"],
    "MARA": ["RIOT", "COIN", "MSTR", "SQ"],
    "RIOT": ["MARA", "COIN", "MSTR", "SQ"],
    # Additional high-interest tickers (not in supply chain map but always worth watching)
    # These are added automatically in the function below
}

# Sector classification for broad earnings discovery
# Maps sector names to representative ETFs and key tickers for sector-level analysis
SECTOR_CLASSIFICATION = {
    "Technology": {
        "etf": "XLK",
        "keywords": ["technology", "software", "semiconductor", "hardware", "it services", "electronics"],
        "extras": ["ANUBIS", "AI", "MDB", "WDAY", "ZS", "CRWD", "OKTA", "PANW", "NET", "COUR", "UDMY", "BIRD", "DLO", "GTLB", "S", "PATH", "ASAN", "BL", "DV", "NCNO", "SUMO", "QLYS", "TENB", "VRNS", "RPD", "SWI", "BLKB", "ALTR", "APPN", "MSTR", "RIOT", "MARA"],
    },
    "Communication Services": {
        "etf": "XLC",
        "keywords": ["communication", "media", "entertainment", "advertising", "social", "telecom"],
        "extras": ["TTD", "ROKU", "MTCH", "BMBL", "RBLX", "U", "DKNG", "PENN", "FUN", "MSGS", "MANU", "FWONA", "LYV", "SIRI", "TME", "WMG", "NWSA", "FOXA", "PARA", "WBD", "LGF.A", "AMC"],
    },
    "Consumer Discretionary": {
        "etf": "XLY",
        "keywords": ["consumer", "retail", "automotive", "restaurant", "travel", "luxury", "e-commerce"],
        "extras": ["LULU", "DECK", "ONON", "COLM", "CROX", "SKX", "NKE", "ADDYY", "CMG", "WING", "DPZ", "YUM", "SBUX", "MCD", "ABNB", "BKNG", "RCL", "CCL", "NCLH", "MAR", "HLT", "WH", "ETSY", "WIX", "SE", "MELI", "CPNG", "GLBE", "DTC", "OLPX", "REAL", "CART", "RIVN", "LCID", "FSR", "GOEV", "WKHS", "RIDE", "FFIE", "ARVL", "LCID", "LEV", "XL", "ZEV"],
    },
    "Consumer Staples": {
        "etf": "XLP",
        "keywords": ["staples", "food", "beverage", "household", "personal care", "tobacco"],
        "extras": ["DG", "DLTR", "TGT", "WMT", "COST", "ACI", "KR", "CASY", "IMKTA", "NGVT", "PFGC", "USFD", "UNFI", "ANDE", "CALM", "TSN", "PPC", "HRL", "CAG", "CPB", "GIS", "HSY", "KHC", "MKC", "SJM", "CL", "PG", "CHD", "CLX", "EL", "KMB", "COTY", "ELF", "IPAR", "NUS", "USNA", "HLF", "NHTC", "MED", "NATR", "RELV", "MTEX"],
    },
    "Financials": {
        "etf": "XLF",
        "keywords": ["financial", "bank", "insurance", "asset management", "fintech", "broker", "capital markets"],
        "extras": ["COIN", "HOOD", "SOFI", "UPST", "AFRM", "LC", "OPFI", "NU", "NUVB", "NUWE", "V", "MA", "AXP", "DFS", "SYF", "ALLY", "COF", "BAC", "WFC", "C", "GS", "MS", "JPM", "BK", "STT", "TFC", "USB", "PNC", "RF", "CFG", "HBAN", "FITB", "KEY", "MTB", "CMA", "ZION", "WAL", "PACW", "SIVB", "SBNY", "FRC", "PACW", "EWBC", "UMPQ", "BANF", "FFIN", "TCBI", "SFBS", "ABCB", "AUB", "BKU", "BOH", "CBSH", "CFR", "CHCO", "CTBI", "CVBF", "EBC", "EFSC", "EGBN", "ESNT", "FBK", "FFBC", "FFWM", "FHB", "FISI", "FLIC", "FMBH", "FULT", "GABC", "GBCI", "GSBC", "HAFC", "HBNC", "HBT", "HFWA", "HWC", "HOMB", "HTLF", "HTBK", "IBCP", "IBOC", "INDB", "ISBC", "LBAI", "LKFN", "MBCN", "MCB", "MCBC", "MOFG", "MPB", "MSBI", "MTG", "NMIH", "NRIM", "NWBI", "OCFC", "OFG", "ONB", "OPBK", "ORI", "OZK", "PB", "PFBC", "PFIS", "PFS", "PPBI", "PRK", "PSTG", "QCRH", "RBCAA", "RBNC", "RNST", "SASR", "SBCF", "SBFG", "SBSI", "SF", "SFBS", "SFNC", "SFST", "SHBI", "SIVB", "SLM", "SMBK", "SMBC", "SMMF", "SNV", "SPFI", "SRCE", "SSB", "STBA", "STEL", "STL", "STLD", "TCBI", "TCBK", "TCF", "TCOM", "THFF", "TMP", "TRMK", "TRST", "TSC", "UBSI", "UCBI", "UCBIO", "UHT", "UMBF", "UMPQ", "UNB", "UNTY", "USB", "UVSP", "VBTX", "VLY", "WABC", "WAFD", "WAL", "WASH", "WBS", "WD", "WFC", "WTBA", "WTFC", "ZION"],
    },
    "Healthcare": {
        "etf": "XLV",
        "keywords": ["healthcare", "pharma", "biotech", "medical", "drug", "hospital", "health"],
        "extras": ["NVO", "MRNA", "BNTX", "TXN", "KRYS", "SRPT", "BMRN", "INCY", "HALO", "EXEL", "NBIX", "ALNY", "ARWR", "NTLA", "BEAM", "EDIT", "CRSP", "VRTX", "REGN", "GILD", "AMGN", "BIIB", "VTRS", "PBH", "PRGO", "TEVA", "ZTS", "IDXX", "WST", "TFX", "PEN", "GMED", "NUVA", "ARVN", "TMDX", "INSP", "IRTC", "ABMD", "BSX", "EW", "DXCM", "PODD", "SWAV", "LMAT", "AXNX", "KIDS", "CNMD", "UFPI", "ICUI", "HAE", "ATR", "RMD", "STE", "ZBH", "SYK", "BSX", "MDT", "ABT", "DHR", "TMO", "A", "LH", "DGX", "IQV", "MTD", "WAT", "PKI", "BIO", "TECH", "CTLT", "MEDP", "NVCR", "HOLX", "ISRG", "INTU", "EW", "PEN", "GMED", "NUVA", "ARVN", "TMDX", "INSP", "IRTC", "ABMD", "BSX", "EW", "DXCM", "PODD", "SWAV", "LMAT", "AXNX", "KIDS", "CNMD", "UFPI", "ICUI", "HAE", "ATR", "RMD", "STE", "ZBH", "SYK", "BSX", "MDT", "ABT", "DHR", "TMO", "A", "LH", "DGX", "IQV", "MTD", "WAT", "PKI", "BIO", "TECH", "CTLT", "MEDP", "NVCR", "HOLX", "ISRG", "INTU", "EW"],
    },
    "Energy": {
        "etf": "XLE",
        "keywords": ["energy", "oil", "gas", "drilling", "refining", "pipeline", "solar", "wind", "renewable", "clean energy"],
        "extras": ["BKR", "HAL", "OXY", "MPC", "VLO", "PSX", "DK", "PAR", "SUN", "CVI", "DINO", "VTLE", "GPRE", "CLNE", "BLDP", "FCEL", "PLUG", "BE", "ICLN", "QCLN", "PBW", "LIT", "REMX", "URA", "SMH", "XME", "KRE", "XOP", "IEO", "OIH", "XES"],
    },
    "Industrials": {
        "etf": "XLI",
        "keywords": ["industrial", "aerospace", "defense", "machinery", "construction", "engineering", "transportation", "logistics"],
        "extras": ["DE", "URI", "PCAR", "CMI", "AME", "ETN", "PH", "ITW", "DOV", "IR", "DAL", "AAL", "UAL", "LUV", "CCJ", "NEM", "GOLD", "AEM", "WPM", "FNV", "KGC", "AGI", "AUY", "HMY", "GFI", "EDR", "OR", "IAG", "FRES", "LAC", "SQM", "ALB", "LTHM", "PLL", "MP", "CRML", "SGML", "CHPT", "BLNK", "EVGO", "ABNB", "R", "CAR", "HTZ", "Avis", "DHT", "EURN", "NAT", "SFL", "INSW", "TK", "TNK", "STNG", "FRO", "GNK", "GOGL", "SB", "CMRE", "NETI", "GRIN", "PANL", "ZIM", "MATX", "BWXT", "ESLT", "RADA", "KTOS", "AVAV", "MOG.A", "HXL", "TGI", "MRCY", "DRS", "ACHR", "JOBY", "VLDR", "EH", "ASTR", "RKLB", "SPIR", "MNTS", "LILM", "SDRD"],
    },
    "Materials": {
        "etf": "XLB",
        "keywords": ["materials", "chemical", "mining", "metal", "steel", "gold", "silver", "lithium", "rare earth"],
        "extras": ["CCJ", "NEM", "GOLD", "AEM", "WPM", "FNV", "KGC", "AGI", "AUY", "HMY", "GFI", "EDR", "OR", "IAG", "FRES", "LAC", "SQM", "ALB", "LTHM", "PLL", "MP", "CRML", "SGML", "LIN", "APD", "ECL", "SHW", "FCX", "NUE", "STLD", "CLF", "X", "MT", "PKX", "SCCO", "RIO", "BHP", "VALE", "TECK", "HBM", "CENX", "KALU", "CSTM", "WOR", "TGLS", "ZWS", "IEX", "DOV", "GGG", "LECO", "EMR", "ROP", "OTIS", "PH", "CARR", "TT", "JCI", "HON", "MMM", "GE", "HWM", "CAT", "DE", "PCAR", "CMI", "AME", "ETN", "ITW", "IR", "DAL", "AAL", "UAL", "LUV"],
    },
    "Real Estate": {
        "etf": "XLRE",
        "keywords": ["real estate", "reit", "property", "housing", "commercial"],
        "extras": ["DLR", "EQIX", "SBAC", "SPG", "O", "WELL", "VTR", "PSA", "EXR", "AVB", "EQR", "MAA", "UDR", "CPT", "BXP", "VNO", "SLG", "HIW", "DECU", "KRC", "JBGS", "HPP", "BDN", "PGRE", "ALEX", "CMCT", "OPI", "UNIT", "LTC", "NHI", "OHI", "MPW", "HR", "PEAK", "SBRA", "CTRE", "GMRE", "CHCT", "DHC", "RHP", "PK", "SHO", "PEB", "DRH", "HST", "APLE", "CLDT", "RLJ", "RHP", "ILPT", "SELF", "GRTA", "LAND", "MDRR", "ALEX", "BRT", "CDR", "FPI", "NXRT", "ROIC", "RPAI", "RPT", "SKT", "TCO", "UBA", "WRI", "XAN", "AAT", "ADC", "AKR", "ALX", "ALEX", "APTS", "BFS", "BRSP", "BXP", "CBL", "CDR", "CHCT", "CLDT", "CMCT", "CPT", "CTRE", "CUZ", "CXW", "DHC", "DLR", "DRH", "EPR", "EQR", "EXR", "FPI", "GMRE", "GRTA", "HPP", "HST", "HT", "IIPR", "ILPT", "JBGS", "JLL", "KRC", "LAMR", "LAND", "LTC", "MAA", "MDRR", "MPW", "NHI", "NNN", "NRE", "NRZ", "NTST", "NXRT", "O", "OHI", "OPI", "PEAK", "PEB", "PK", "PLD", "PSA", "PSB", "REG", "REXR", "RHP", "RLJ", "ROIC", "RPAI", "RPT", "RWT", "SBRA", "SELF", "SHO", "SKT", "SLG", "SPG", "STAG", "STOR", "TCO", "UBA", "UDR", "UNIT", "VICI", "VNO", "VTR", "WELL", "WPC", "WRI", "XAN"],
    },
    "Utilities": {
        "etf": "XLU",
        "keywords": ["utility", "electric", "water", "gas utility", "power", "renewable energy"],
        "extras": ["NEE", "DUK", "SO", "D", "AEP", "EXC", "SRE", "XEL", "ED", "PEG", "AWK", "ES", "ETR", "FE", "ES", "CNP", "NI", "LNT", "EIX", "PPL", "AES", "AGR", "AMPS", "ARIS", "AQN", "ATO", "AVA", "BKH", "BEP", "BEPC", "CEG", "CIG", "CMS", "CPK", "CTRA", "CWEN", "DTE", "EAI", "EBR", "EVRG", "FLNC", "FCEL", "GPRE", "HE", "IDA", "KEN", "KEP", "KMI", "LNG", "MGEE", "MNTN", "NFG", "NGG", "NJR", "NOVA", "NRG", "NTG", "NWE", "OGE", "OGS", "OPAL", "ORA", "OTTR", "PCG", "PCYO", "PNM", "PNW", "PPA", "PRP", "PPL", "RGCO", "RNW", "RUG", "SBS", "SJI", "SM", "SMLP", "SPH", "SR", "SWX", "TAC", "TPIC", "TPH", "TRGP", "TS", "UGI", "UMC", "UTL", "VGAS", "VIA", "VIST", "VST", "WEC", "WTRG", "WTRU", "XEL", "ZNH"],
    },
}


def _get_portfolio_tickers_set():
    """Helper: load all portfolio tickers into a set."""
    portfolio_set = set()
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
                            if ticker:
                                portfolio_set.add(ticker)
    except Exception:
        pass
    return portfolio_set


def _format_earning(e, today):
    """Format a single earnings calendar entry into a readable string."""
    ticker = e.get("symbol", "").upper()
    earnings_date = e.get("date", "")
    if not ticker or not earnings_date:
        return None
    try:
        e_dt = datetime.date.fromisoformat(earnings_date)
        days_until = (e_dt - today).days
    except ValueError:
        return None

    hour = e.get("hour", "")
    eps_est = e.get("epsEstimate", "")
    rev_est = e.get("revenueEstimate", "")

    if days_until < -2 or days_until > 21:
        return None

    status = "REPORTED" if days_until < 0 else "TODAY" if days_until == 0 else f"in {days_until}d"
    detail = f" ({hour})" if hour else ""
    if eps_est:
        try:
            detail += f" EPS est: ${float(eps_est):.2f}"
        except (ValueError, TypeError):
            detail += f" EPS est: ${eps_est}"
    if rev_est:
        try:
            rv = float(rev_est)
            if rv > 1e9:
                detail += f" Rev est: ${rv/1e9:.1f}B"
            else:
                detail += f" Rev est: ${rv/1e6:.0f}M"
        except (ValueError, TypeError):
            pass

    return f"  🔔 {ticker} — Earnings {status} ({earnings_date}){detail}", days_until


def _classify_sector(ticker, info):
    """Try to determine a company's sector from yfinance info."""
    sector = info.get('sector', '')
    industry = info.get('industry', '')
    return sector, industry


def get_comprehensive_earnings(days_ahead: int = 21):
    """
    Comprehensive earnings intelligence covering 3 layers:
    
    Layer 1: PORTFOLIO — your actual holdings
    Layer 2: RELATED/SUPPLY CHAIN — companies in the same ecosystem as your holdings
    Layer 3: SECTOR EXCITEMENT — most anticipated earnings in sectors you're invested in,
             including emerging companies you may not own or know about
    
    Uses Finnhub earnings calendar API (free tier) which returns ~5000 companies.
    Also uses yfinance for fallback on portfolio tickers.
    
    Returns a dict with:
        portfolio_earnings: str — formatted earnings for your holdings
        related_earnings: str — formatted earnings for supply chain / ecosystem companies
        sector_earnings: str — formatted earnings for exciting companies in your sectors
        all_earnings_flat: list — all raw earnings entries for LLM context
    """
    today = datetime.date.today()
    portfolio_tickers = _get_portfolio_tickers_set()

    # ── Build the set of related tickers from supply chain map ──
    related_tickers = set()
    for ticker in portfolio_tickers:
        if ticker in SUPPLY_CHAIN_MAP:
            for related in SUPPLY_CHAIN_MAP[ticker]:
                if related not in portfolio_tickers:
                    related_tickers.add(related)

    # ── Determine which sectors the portfolio is invested in ──
    portfolio_sectors = set()
    for ticker in portfolio_tickers:
        try:
            old_stderr = sys.stderr
            sys.stderr = StringIO()
            try:
                t = yf.Ticker(ticker)
                info = t.info
                sector = info.get('sector', '')
                if sector:
                    portfolio_sectors.add(sector)
            except Exception:
                pass
            finally:
                sys.stderr = old_stderr
        except Exception:
            pass

    # ── Fetch the full earnings calendar from Finnhub ──
    # The free tier returns ~5000 companies for a date range
    all_earnings = []
    if FINNHUB_API_KEY:
        try:
            from_date = (today - datetime.timedelta(days=2)).isoformat()
            to_date = (today + datetime.timedelta(days=days_ahead)).isoformat()
            r = requests.get(
                "https://finnhub.io/api/v1/calendar/earnings",
                params={"from": from_date, "to": to_date, "token": FINNHUB_API_KEY},
                timeout=15
            )
            data = r.json()
            all_earnings = data.get("earningsCalendar", [])
        except Exception:
            pass

    # ── Categorize earnings into 3 layers ──
    portfolio_earnings = []
    related_earnings = []
    sector_earnings = []
    seen_tickers = set()

    for e in all_earnings:
        ticker = e.get("symbol", "").upper()
        if ticker in seen_tickers:
            continue

        formatted = _format_earning(e, today)
        if formatted is None:
            continue
        entry_str, days_until = formatted

        if ticker in portfolio_tickers:
            portfolio_earnings.append(entry_str)
            seen_tickers.add(ticker)
        elif ticker in related_tickers:
            related_earnings.append(entry_str)
            seen_tickers.add(ticker)

    # ── Layer 3: Sector excitement — scan for companies in portfolio sectors ──
    # We need to identify which earnings belong to sectors we're invested in.
    # Strategy: for each sector we're in, check if any earnings tickers match
    # known sector tickers, or use yfinance to classify them.
    if portfolio_sectors and all_earnings:
        # Build a set of all tickers we've already captured
        captured = set()

        # First pass: match against known sector tickers from SECTOR_CLASSIFICATION
        sector_known_tickers = {}
        for sector_name, sector_data in SECTOR_CLASSIFICATION.items():
            if sector_name in portfolio_sectors:
                for t in sector_data.get("extras", []):
                    sector_known_tickers[t.upper()] = sector_name

        for e in all_earnings:
            ticker = e.get("symbol", "").upper()
            if ticker in seen_tickers or ticker in captured:
                continue
            if ticker in portfolio_tickers:
                continue

            formatted = _format_earning(e, today)
            if formatted is None:
                continue
            entry_str, days_until = formatted

            # Check if this ticker is a known sector ticker
            if ticker in sector_known_tickers:
                sector_name = sector_known_tickers[ticker]
                sector_earnings.append(f"{entry_str} [{sector_name}]")
                captured.add(ticker)
                continue

            # For high-revenue companies (>$1B rev estimate), try yfinance classification
            rev_est = e.get("revenueEstimate", "")
            try:
                if rev_est and float(rev_est) > 500_000_000:  # >$500M revenue
                    old_stderr = sys.stderr
                    sys.stderr = StringIO()
                    try:
                        t = yf.Ticker(ticker)
                        info = t.info
                        sector = info.get('sector', '')
                        if sector and sector in portfolio_sectors:
                            sector_earnings.append(f"{entry_str} [{sector}]")
                            captured.add(ticker)
                    except Exception:
                        pass
                    finally:
                        old_stderr = old_stderr
            except (ValueError, TypeError):
                pass

    # ── Fallback: yfinance for portfolio tickers Finnhub might have missed ──
    for ticker in portfolio_tickers:
        if ticker in seen_tickers:
            continue
        try:
            old_stderr = sys.stderr
            sys.stderr = StringIO()
            try:
                t = yf.Ticker(ticker)
                info = t.info
                earnings_ts = info.get('earningsTimestamp') or info.get('earningsDate')
                if earnings_ts:
                    if isinstance(earnings_ts, (int, float)):
                        earnings_dt = datetime.date.fromtimestamp(earnings_ts)
                    elif isinstance(earnings_ts, str):
                        try:
                            earnings_dt = datetime.date.fromisoformat(earnings_ts[:10])
                        except ValueError:
                            continue
                    else:
                        continue
                    days_until = (earnings_dt - today).days
                    if -2 <= days_until <= 14:
                        status = "REPORTED" if days_until < 0 else "TODAY" if days_until == 0 else f"in {days_until}d"
                        price = info.get('currentPrice') or info.get('regularMarketPrice')
                        portfolio_earnings.append(
                            f"  🔔 {ticker} — Earnings {status} ({earnings_dt})"
                            + (f" @ ${price:.2f}" if price else "")
                        )
                        seen_tickers.add(ticker)
            except Exception:
                pass
            finally:
                sys.stderr = old_stderr
        except Exception:
            pass

    # ── Build formatted output strings ──
    portfolio_str = ""
    if portfolio_earnings:
        portfolio_str = "**📅 Earnings — Your Portfolio Holdings:**\n" + "\n".join(portfolio_earnings) + "\n"

    related_str = ""
    if related_earnings:
        related_str = "**📅 Earnings — Related / Supply Chain Companies:**\n" + "\n".join(related_earnings) + "\n"

    sector_str = ""
    if sector_earnings:
        sector_str = "**📅 Earnings — Sector Excitement (Companies in Your Sectors You May Not Own):**\n" + "\n".join(sector_earnings) + "\n"

    return {
        "portfolio_earnings": portfolio_str,
        "related_earnings": related_str,
        "sector_earnings": sector_str,
        "all_earnings_flat": all_earnings,
    }


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
        max_tokens=3000,  # Increased for more detailed news analysis
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
    # This includes: options data, earnings alerts, market sentiment, foresight,
    # smart money signals, sector rotation, and benchmark comparison
    options_section = ""
    if options_context and options_context != "[Options data unavailable]":
        # Use full context — the LLM needs all of it for informed decisions
        # Truncate only if extremely long (leave room for other prompt sections)
        max_context = 4000
        truncated_context = options_context[:max_context] if len(options_context) > max_context else options_context
        options_section = f"""
ADDITIONAL MARKET INTELLIGENCE:
{truncated_context}
Use ALL of the above data (options, earnings, sentiment, foresight, smart money, sector rotation, benchmarks) to inform your stock recommendations."""
    
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
6. **MUST include at least 2 NEW stock ideas the user does NOT currently own** — scan the broad earnings watchlist, sector leaders, emerging players, and companies with upcoming catalysts. Do NOT just recommend existing holdings.
7. For portfolio positions: analyze by WEIGHT, suggest SELL/REDUCE for overvalued
8. Recommend HOLDING CASH if no compelling opportunities
9. Look for ONCE-IN-A-LIFETIME opportunities: extreme asymmetric plays, 50%+ upside potential, clear catalysts
10. EARNINGS AWARENESS: If a company has upcoming earnings (from the earnings alerts), factor that into the thesis — consider pre-earnings setups, post-earnings plays, or avoidance if too risky.
11. SECTOR ROTATION: If multiple companies in the same sector have upcoming earnings, consider sector-wide implications.
12. **OPTIONS RECOMMENDATIONS: For high-conviction ideas (8+), also suggest an options strategy** — long calls for bullish, long puts for bearish, spreads for defined risk, iron condors for range-bound. Include strike, expiry (min 14 DTE), and max risk.

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
        max_tokens=8000,  # Increased for comprehensive investment ideas with full thesis
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

Generate **2-4 Options Ideas** using the most advanced, research-backed strategies.

## AVAILABLE STRATEGIES (select best for each situation)

### DIRECTIONAL (High Conviction)
1. **ASYMMETRIC LONG CALLS** — Unlimited upside, defined risk. Best: low IV + high conviction + catalyst. Position: 2-3% of portfolio.
2. **ASYMMETRIC LONG PUTS** — Defined risk bearish. Best: low IV + clear downside thesis.
3. **CALL DEBIT SPREADS** — Buy ATM call, sell OTM at target. Reduces cost when IV is high.
4. **PUT DEBIT SPREADS** — Buy ATM put, sell OTM at support. Defined risk, lower cost.
5. **LEVERAGED OTM CALLS** — For conviction 9+. Cheaper entry, higher ROI if thesis plays.

### INCOME / RANGE-BOUND (High IV)
6. **IRON CONDORS** — Sell OTM call spread + OTM put spread. 70-80% probability of profit. Best: high IV rank.
7. **IRON BUTTERFLIES** — Narrower wings. Higher max profit, narrower zone. Best: earnings with expected small move.
8. **CALENDAR SPREADS** — Sell near-term, buy longer-term same strike. Profits from faster decay.
9. **COVERED CALLS** — Sell OTM calls on stocks already owned. Income generation.
10. **CASH-SECURED PUTS** — Sell OTM puts on stocks willing to own. Income + potential buying.

### VOLATILITY & ARBITRAGE
11. **STRADDLES/STRANGLES** — Buy call + put. Profits from large move either direction. Best: before earnings when IV low.
12. **RATIO SPREADS** — Buy 1 ATM, sell 2 OTM. Zero/negative cost, unlimited upside to short strike.
13. **DIAGONAL SPREADS** — Sell near-term OTM, buy longer-term further OTM. Directional + time decay.
14. **VOLATILITY ARBITRAGE** — Sell overpriced options (IV >> HV), buy underpriced (IV << HV).

## STRATEGY SELECTION RULES
- **Bullish + Low IV** → Long calls or call debit spreads
- **Bullish + High IV** → Covered calls or cash-secured puts
- **Bearish + Low IV** → Long puts or put debit spreads
- **Bearish + High IV** → Put credit spreads
- **Neutral + High IV** → Iron condors or iron butterflies
- **Neutral + Low IV** → Calendar spreads
- **High uncertainty** → Straddles/strangles
- **Mispricing detected** → Volatility arbitrage
- **Earnings approaching** → Straddles (buy) or iron condors (sell)

## RULES
- Defined-risk ONLY (long calls/puts, covered calls, LEAPS, credit spreads, iron condors)
- Min 14-day expiry, prefer 30-90 DTE or 6mo+ LEAPS
- Max 3% of portfolio per options trade
- NEVER let expire ITM — SELL before expiry
- NO leverage, NO naked, NO margin
- Every trade must have a clear EDGE

## FORMAT FOR EACH IDEA
### [Strategy Name] on [TICKER]
**Type:** [Long Call/Put/Spread/etc.]
**Why:** 1-2 sentences on the edge
**Strike/Expiry:** $X / [date, min 14 DTE]
**Max Risk:** $X (all you can lose)
**Target:** Sell @ $X or X% gain
**Probability of Profit:** X% (if applicable)
**Conviction:** X/10
**EXIT:** SELL before expiry, NEVER let ITM.

**IMPORTANT:** Include at least 1 strategy on a NEW ticker the user doesn't own (from the earnings watchlist or broad market scan). Also suggest 1 covered call or cash-secured put on existing holdings if appropriate.

Educational only. Verify with broker.*""".format(
            memory_summary=memory_summary,
            market_data=market_data_slice,
            digest_summary=digest_summary,
            options_context=options_context,
            earnings_section=earnings_section,
            sentiment_section=sentiment_section
        ),
        max_tokens=6000,  # Increased for detailed options strategies
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
        max_tokens=2500,  # Increased for deeper market reaction analysis
    )

def task_self_reflect(report: str, memory: str, snapshot: dict = None,
                         actions: list = None, foresight: dict = None) -> str:
    """
    Deep self-reflection for continuous improvement.
    Analyzes: recommendation quality, portfolio decisions, data accuracy,
    conviction calibration, risk management, and learning progression.
    """
    log("  → Deep self-reflection & learning...")
    
    recent_ratings = get_recent_ratings(10)
    avg_rating = calculate_avg_rating()
    
    # Determine improvement mode
    try:
        rating_val = float(avg_rating.split('/')[0]) if avg_rating != "N/A" else 5.0
    except (ValueError, IndexError):
        rating_val = 5.0
    improvement_mode = "LOW" if rating_val < 6 else "NORMAL" if rating_val < 8 else "HIGH"
    
    # Build rich context for reflection
    learnings_history = read_file(LEARNING_FILE, max_chars=2000)
    portfolio_summary = read_file(PORTFOLIO_FILE, max_chars=500)
    recs_summary = read_file(RECOMMENDATIONS_FILE, max_chars=500)
    
    # Portfolio performance context
    portfolio_context = ""
    if snapshot:
        portfolio_context = f"""
Portfolio: ${snapshot.get('total_value', 0):,.0f} | P&L: ${snapshot.get('total_pnl', 0):+,.0f} ({snapshot.get('total_pnl_pct', 0):+.1f}%)
Cash: {snapshot.get('allocation', {}).get('cash', 0):.0%} | Positions: {snapshot.get('num_positions', 0)}
Concentration: {snapshot.get('concentration_ratio', 0):.1f}%"""
    
    # Actions taken context
    actions_context = ""
    if actions:
        urgent = [a for a in actions if a.get('priority') == 'URGENT']
        high = [a for a in actions if a.get('priority') == 'HIGH']
        actions_context = f"\nActions taken: {len(urgent)} urgent, {len(high)} high priority"
        for a in urgent[:3]:
            actions_context += f"\n  • {a['type']} {a.get('symbol', '')}: {a['action']}"
    
    # Foresight context
    foresight_context = ""
    if foresight:
        foresight_context = f"\nMarket Foresight: {foresight.get('composite_score', 0)}/100 ({foresight.get('direction', 'neutral')})"
    
    return call_llm(
        system="""You are an AI investment agent conducting deep self-reflection. Your goal is to continuously improve recommendation quality, risk management, and portfolio performance.

Be brutally honest about mistakes. Identify specific patterns that led to good or bad outcomes. Propose concrete, actionable improvements. Reference specific data points, not vague generalities.

Focus areas:
1. RECOMMENDATION QUALITY: Were conviction scores calibrated correctly? Did high-conviction picks outperform? Were stop-losses set appropriately?
2. PORTFOLIO MANAGEMENT: Is cash being deployed efficiently? Are concentration risks managed? Is the asset allocation optimal?
3. DATA ACCURACY: Were there any stale prices, missing data, or hallucinated facts? How can data quality be improved?
4. RISK MANAGEMENT: Were stop-losses triggered appropriately? Is the portfolio protected against tail risks?
5. LEARNING PROGRESSION: Are we getting better over time? What recurring mistakes need systematic fixes?
6. OPPORTUNITY COST: What did we miss? What should we have bought/sold but didn't?""",
        user=f"""=== RUN CONTEXT ===
Date: {NOW}
Mode: {improvement_mode} (avg rating: {avg_rating})

=== REPORT SUMMARY (first 1500 chars) ===
{report[:1500]}

=== USER FEEDBACK ===
Recent ratings: {', '.join(recent_ratings[-5:]) if recent_ratings else 'None yet'}
Average: {avg_rating}

=== PORTFOLIO ===
{portfolio_context}
{actions_context}
{foresight_context}

=== ACTIVE RECOMMENDATIONS ===
{recs_summary}

=== LEARNING HISTORY (recent) ===
{learnings_history[-1000:]}

=== YOUR TASK ===
Write a comprehensive self-reflection (8-12 bullet points) covering:

**What Worked Well** (be specific — name tickers, data sources, strategies)
**What Didn't Work** (be specific — what was wrong and why)
**Conviction Calibration** (were 8+ conviction picks actually good? any false positives?)
**Missed Opportunities** (what should have been recommended but wasn't?)
**Data Quality Issues** (any stale prices, missing chains, hallucinated facts?)
**Risk Management** (are stop-losses set correctly? concentration managed?)
**Cash Deployment** (is idle cash being deployed efficiently? opportunity cost?)
**Process Improvements** (what systematic changes would improve next run?)

Format: markdown bullets with specific tickers, prices, and data points. Be actionable.
Today: {NOW}""",
        max_tokens=2500,  # Increased for comprehensive self-reflection
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


def _extract_smart_money_context(sm_summary):
    """Extract concise smart money signals for the LLM investment prompt."""
    lines = []
    hf = sm_summary.get("hedge_funds", {})
    if hf and hf.get("top_consensus"):
        top = hf["top_consensus"][:5]
        stocks = ", ".join([name for name, _ in top])
        lines.append(f"Top hedge fund consensus holdings: {stocks}")
    congress = sm_summary.get("congress", {})
    if congress and congress.get("ticker_consensus"):
        top = congress["ticker_consensus"][:5]
        tickers = ", ".join([t["ticker"] for t in top])
        lines.append(f"Congressional buying: {tickers}")
    insiders = sm_summary.get("insiders", {})
    if insiders and insiders.get("top_insider_buys"):
        top = insiders["top_insider_buys"][:5]
        tickers = ", ".join([t["ticker"] for t in top])
        lines.append(f"Strong insider buying: {tickers}")
    return "\n".join(lines) if lines else "No significant smart money signals."


def _extract_sector_context():
    """Extract concise sector rotation signals for the LLM investment prompt."""
    lines = []
    try:
        # Top/bottom sectors
        sector_data = analyze_sector_rotation()
        if sector_data.get("sectors"):
            top3 = sector_data["sectors"][:3]
            bottom3 = sector_data["sectors"][-3:]
            top_names = ", ".join([f"{s.get('name')} ({s.get('rs_score', 0):.1f})" for s in top3])
            bottom_names = ", ".join([f"{s.get('name')} ({s.get('rs_score', 0):.1f})" for s in bottom3])
            lines.append(f"Top sectors: {top_names}")
            lines.append(f"Weak sectors: {bottom_names}")
    except Exception:
        pass
    try:
        # Cap rotation
        cap = analyze_cap_rotation()
        for key, data in cap.items():
            label = key.replace("_", " ").title()
            lines.append(f"{label}: {data.get('signal', '')}")
    except Exception:
        pass
    try:
        # Emerging themes
        themes = detect_emerging_themes()
        if themes.get("themes"):
            hot = themes["themes"][:3]
            theme_names = ", ".join([f"{name} ({data['theme_score']:.0f})" for name, data in hot])
            lines.append(f"Hottest themes: {theme_names}")
    except Exception:
        pass
    return "\n".join(lines) if lines else "No significant sector signals."


def _extract_benchmark_context():
    """Extract concise benchmark comparison for the LLM investment prompt."""
    lines = []
    try:
        perf = get_performance_summary()
        if perf:
            lines.append(perf[:500])
    except Exception:
        pass
    try:
        # Small cap cycle
        spy = _yf_price("SPY", "3mo")
        iwm = _yf_price("IWM", "3mo")
        if spy is not None and iwm is not None and len(spy) > 21:
            ratio = iwm / spy
            change = (ratio.iloc[-1] / ratio.iloc[-21] - 1) * 100
            direction = "outperforming" if change > 0 else "underperforming"
            lines.append(f"Small caps {direction} large caps by {abs(change):.1f}% this month")
    except Exception:
        pass
    return "\n".join(lines) if lines else "Benchmark data unavailable."


def build_and_save_report(market_data, digest, investments, options, learning,
                            market_sentiment="", portfolio_analysis_text="", market_reaction="",
                            earnings_alerts="", related_earnings="", sector_earnings="",
                            forward_analysis="", recent_surprises="",
                            foresight_score=0, foresight_direction="neutral",
                            foresight_outlook="", foresight_actions=None, foresight=None,
                            smart_money_report="", sector_rotation_report="",
                            benchmark_report="") -> str:
    if foresight_actions is None:
        foresight_actions = []
    if foresight is None:
        foresight = {}

    # Get recommendation updates
    rec_updates = read_file(RECOMMENDATIONS_FILE)
    if rec_updates:
        rec_section = "\n---\n# 📊 Recommendation Tracking & Decision Journal\n" + rec_updates[:2000] + "\n"
    else:
        rec_section = ""

    reaction_section = f"\n---\n\n## 📰 Why The Market Moved Today\n\n{market_reaction}\n" if market_reaction else ""

    # Market Foresight section with clear score interpretation
    foresight_emoji = "🟢" if foresight_score > 20 else "🔴" if foresight_score < -20 else "⚪"
    score_bar = "█" * max(0, (foresight_score + 100) // 5) + "░" * max(0, (100 - foresight_score) // 5)
    score_label = (
        "STRONG BULLISH" if foresight_score >= 60 else
        "BULLISH" if foresight_score >= 30 else
        "SLIGHTLY BULLISH" if foresight_score >= 10 else
        "NEUTRAL" if foresight_score > -10 else
        "SLIGHTLY BEARISH" if foresight_score > -30 else
        "BEARISH" if foresight_score > -60 else
        "STRONG BEARISH"
    )
    confidence = foresight.get("confidence", 0.5)
    conf_label = "HIGH" if confidence > 0.7 else "MEDIUM" if confidence > 0.4 else "LOW"
    
    foresight_section = (
        f"\n---\n\n## 🔮 Market Foresight Outlook\n\n"
        f"<b>Score: {foresight_score}/100</b> ({score_label}) | "
        f"<b>Confidence:</b> {conf_label} ({confidence:.0%})\n"
        f"`{score_bar}`\n\n"
        f"{foresight_outlook}\n\n"
    )
    
    # Add individual signal breakdown
    if foresight.get("signals"):
        foresight_section += "<b>Signal Breakdown:</b>\n"
        for sig in foresight["signals"]:
            sig_emoji = "🟢" if sig.get("score", 0) > 5 else "🔴" if sig.get("score", 0) < -5 else "⚪"
            foresight_section += f"  {sig_emoji} {sig['name']}: {sig['detail'][:100]}\n"
        foresight_section += "\n"
    
    if foresight_actions:
        foresight_section += "<b>Specific Actions:</b>\n"
        for action in foresight_actions[:7]:
            foresight_section += f"• {action}\n"

    # Earnings sections
    earnings_section = ""
    if earnings_alerts:
        earnings_section += f"\n---\n\n## 📅 Earnings — Your Portfolio Holdings\n\n{earnings_alerts}\n"
    if related_earnings:
        earnings_section += f"\n---\n\n## 📅 Earnings — Related / Supply Chain Companies\n\n{related_earnings}\n"
    if sector_earnings:
        earnings_section += f"\n---\n\n## 📅 Earnings — Comprehensive Sector Coverage\n\n{sector_earnings}\n"
    if forward_analysis:
        earnings_section += f"\n---\n\n## 🔮 Forward-Looking Earnings Analysis (Beat/Miss Predictions)\n\n{forward_analysis}\n"
    if recent_surprises:
        earnings_section += f"\n---\n\n## 📊 Recent Earnings Surprises\n\n{recent_surprises}\n"
    if not earnings_section:
        earnings_section = ""

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
{foresight_section}
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

---

{smart_money_report}

---

{sector_rotation_report}

---

{benchmark_report}

{rec_section}
---
*Generated by personal AI agent using free-tier APIs. Educational only. Not financial advice.*
*Options: Always sell/close contracts BEFORE expiration. Never let ITM options expire.*
"""
    # Save report in daily subfolder: REPORTS/2026-05-08/0852.md
    daily_dir = REPORTS_DIR / TODAY
    daily_dir.mkdir(parents=True, exist_ok=True)
    path = daily_dir / f"{RUN_LABEL}.md"
    path.write_text(report, encoding="utf-8")

    # Also update the daily history file
    hist = HISTORY_DIR / f"{TODAY}.md"
    with open(hist, "a", encoding="utf-8") as f:
        f.write(f"\n\n---\n## Run {RUN_LABEL} at {NOW}\n" + report)

    log(f"Report saved: {path}")
    return report


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────
def main():
    # Check for silent/alerts-only mode (set by __main__ or environment)
    # "alerts-only" = trade + alerts, no report/Telegram report (but still self-reflect)
    # "silent" = minimal run, skip everything non-essential
    global SILENT_MODE
    try:
        SILENT_MODE
    except NameError:
        _run_mode = os.environ.get("RUN_MODE", "")
        SILENT_MODE = _run_mode in ("silent", "alerts-only")
    
    # Initialize run metadata — always use US Eastern Time (owner is in Jersey City, NJ)
    global NOW, TODAY, RUN_LABEL, IS_MARKET_OPEN
    try:
        import pytz
        eastern = pytz.timezone('US/Eastern')
        now = datetime.datetime.now(eastern)
    except ImportError:
        # Fallback: assume system time is Eastern (user is in Jersey City)
        now = datetime.datetime.now()
    NOW = now.strftime("%Y-%m-%d %H:%M:%S ET")
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
            from skills.earnings_intelligence import init_earnings_skill
            from skills.market_foresight import init_foresight_skill
            from skills.options_strategies import init_options_skill as init_options_strategies_skill

            init_portfolio(finnhub_key=FINNHUB_API_KEY, base_dir=str(BASE_DIR))
            init_options_skill(polygon_key=POLYGON_API_KEY, base_dir=str(BASE_DIR))
            init_tracker_skill(base_dir=str(BASE_DIR), finnhub_key=FINNHUB_API_KEY)
            init_news_skill(tavily_key=TAVILY_API_KEY, finnhub_key=FINNHUB_API_KEY, base_dir=str(BASE_DIR))
            init_learning_skill(base_dir=str(BASE_DIR))
            init_earnings_skill(finnhub_key=FINNHUB_API_KEY, base_dir=str(BASE_DIR))
            init_foresight_skill(finnhub_key=FINNHUB_API_KEY, tavily_key=TAVILY_API_KEY, base_dir=str(BASE_DIR))
            init_options_strategies_skill(alpaca_key=ALPACA_API_KEY, alpaca_secret=ALPACA_SECRET_KEY,
                              finnhub_key=FINNHUB_API_KEY, base_dir=str(BASE_DIR))
            init_portfolio_manager(finnhub_key=FINNHUB_API_KEY, alpaca_key=ALPACA_API_KEY,
                                   alpaca_secret=ALPACA_SECRET_KEY, base_dir=str(BASE_DIR))
            # Initialize new skills
            init_smart_money_skill(finnhub_key=FINNHUB_API_KEY, base_dir=str(BASE_DIR))
            init_sector_skill(finnhub_key=FINNHUB_API_KEY, base_dir=str(BASE_DIR))
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
    # Use Eastern Time for consistency
    try:
        import pytz
        eastern = pytz.timezone('US/Eastern')
        run_hour = datetime.datetime.now(eastern).hour
    except ImportError:
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

    # 3b. Comprehensive earnings intelligence — portfolio + supply chain + sector + forward analysis
    log("📅 Running comprehensive earnings intelligence (full universe + forward analysis)...")
    earnings_data = get_comprehensive_earnings_intelligence(
        portfolio_tickers=all_portfolio_tickers, days_ahead=21
    )
    earnings_alerts = earnings_data["portfolio_earnings"]
    related_earnings = earnings_data["related_earnings"]
    sector_earnings = earnings_data["sector_earnings"]
    forward_analysis = earnings_data["forward_analysis"]
    recent_surprises = earnings_data["recent_surprises"]
    if earnings_alerts:
        log(f"✓ Portfolio earnings: {earnings_alerts[:100]}")
    if related_earnings:
        log(f"✓ Related/supply chain earnings: {related_earnings[:100]}")
    if sector_earnings:
        log(f"✓ Sector earnings: {sector_earnings[:100]}")
    if forward_analysis:
        log(f"✓ Forward analysis generated")
    if not (earnings_alerts or related_earnings or sector_earnings):
        log("  No upcoming earnings found across all layers")

    # 3c. Market Foresight Predictor — crash/bullish alerts
    log("🔮 Running market foresight predictor...")
    foresight = get_market_foresight()
    foresight_score = foresight["composite_score"]
    foresight_direction = foresight["direction"]
    log(f"[OK] Market Foresight Score: {foresight_score}/100 ({foresight_direction})")
    for sig in foresight["signals"]:
        if abs(sig.get("score", 0)) > 5:
            log(f"  → {sig['name']}: {sig['detail'][:120]}")

    if SKILLS_AVAILABLE:
        try:
            get_index_prices()
        except Exception:
            pass

    # 3d. Portfolio monitoring — CSV portfolio (user's real holdings) for alerts
    # 3d-2. Advanced CSV portfolio management — same 8-strategy system as Alpaca
    # Uses: trailing stops, thesis checks, momentum, risk parity, contrarian buys, etc.
    log("📊 Advanced CSV portfolio management (8-strategy system)...")
    csv_portfolio = analyze_portfolio_weightage()
    csv_total = csv_portfolio.get('total_value', 0)
    csv_cost = sum(h.get('cost_basis', 0) for h in csv_portfolio.get('top_positions', []))
    csv_pnl = csv_total - csv_cost
    csv_pnl_pct = (csv_pnl / csv_cost * 100) if csv_cost > 0 else 0
    concentration = csv_portfolio.get('concentration_ratio', 0)
    
    log(f"[OK] CSV Portfolio: ${csv_total:,.0f} | P&L: ${csv_pnl:+,.0f} ({csv_pnl_pct:+.1f}%) | "
        f"Concentration: {concentration:.1f}% | Positions: {csv_portfolio.get('total_holdings', 0)}")
    
    # Apply the same 8-strategy system to CSV portfolio
    from skills.portfolio_manager import get_position_fundamentals, review_all_positions
    csv_actions = []
    
    for pos in csv_portfolio.get('top_positions', []):
        ticker = pos.get('ticker', '')
        pnl_pct = pos.get('unrealized_pnl_pct', 0)
        pos_pct = pos.get('portfolio_pct', 0)
        shares = pos.get('shares', 0)
        avg_cost = pos.get('purchase_price', 0)
        current_price = pos.get('current_price', 0)
        
        # Get fundamentals for deeper analysis
        fundamentals = get_position_fundamentals(ticker)
        
        # Technical analysis
        try:
            import yfinance as yf
            old_stderr = __import__('sys').stderr
            __import__('sys').stderr = __import__('io').StringIO()
            try:
                t = yf.Ticker(ticker)
                hist = t.history(period="3mo")
                if hist is not None and len(hist) > 20:
                    recent_high = hist["Close"].rolling(20).max().iloc[-1]
                    pullback = ((current_price - recent_high) / recent_high * 100) if recent_high > 0 else 0
                    ma20 = hist["Close"].rolling(20).mean().iloc[-1]
                    ma50 = hist["Close"].rolling(50).mean().iloc[-1] if len(hist) >= 50 else ma20
                    uptrend = current_price > ma20 > ma50
                    downtrend = current_price < ma20 < ma50
                else:
                    pullback = 0; uptrend = True; downtrend = False
            finally:
                __import__('sys').stderr = old_stderr
        except Exception:
            pullback = 0; uptrend = True; downtrend = False
        
        # Thesis check
        thesis_intact = not fundamentals.get("consecutive_misses", False)
        thesis_broken = fundamentals.get("consecutive_misses", False) or fundamentals.get("below_200ma", False) and pnl_pct < -10
        
        # Trailing stop (dynamic)
        stop_pct = -10 if uptrend else (-7 if downtrend else -12)
        
        # Generate action
        action = None
        reason = ""
        
        # 1. Trailing stop hit
        if pullback <= stop_pct and pnl_pct < 0:
            action = "SELL"
            reason = f"Trailing stop: pulled back {pullback:.1f}% from 20-day high (stop: {stop_pct}%)"
        # 2. Thesis broken
        elif thesis_broken:
            action = "SELL"
            reason = "Thesis broken: consecutive misses or deteriorating fundamentals"
        # 3. Downtrend + loss = cut quickly
        elif downtrend and pnl_pct < -10:
            action = "SELL"
            reason = f"Downtrend + {pnl_pct:+.1f}% loss — cut before deeper damage"
        # 4. Concentration risk
        elif pos_pct > 20:
            action = "TRIM"
            reason = f"Concentration: {pos_pct:.1f}% of portfolio exceeds 20% max"
        # 5. Contrarian buy (average down on weakness, thesis intact)
        elif pnl_pct <= -20 and thesis_intact and not downtrend and pos_pct < 5:
            action = "BUY_MORE"
            reason = f"Down {pnl_pct:.1f}% but thesis intact — averaging down on weakness"
        # 6. Add to winner (uptrend, conviction, small position)
        elif uptrend and thesis_intact and pnl_pct > 10 and pos_pct < 8:
            action = "BUY_MORE"
            reason = f"Uptrend +{pnl_pct:.1f}%, only {pos_pct:.1f}% of portfolio — adding to winner"
        
        if action:
            csv_actions.append({
                "ticker": ticker,
                "action": action,
                "reason": reason,
                "pnl_pct": pnl_pct,
                "pos_pct": pos_pct,
                "shares": shares,
                "current_price": current_price,
            })
    
    # Log and alert on CSV actions
    if csv_actions:
        log(f"[OK] CSV portfolio actions generated: {len(csv_actions)} items")
        for a in csv_actions[:5]:
            emoji = {"SELL": "🛑", "TRIM": "✂️", "BUY_MORE": "➕"}.get(a["action"], "⚪")
            log(f"  {emoji} {a['action']} {a['ticker']}: {a['reason']}")
    
    # Telegram alerts for CSV portfolio actions
    urgent_csv = [a for a in csv_actions if a["action"] in ("SELL", "TRIM")]
    if urgent_csv:
        try:
            from skills.telegram_bot import broadcast
            alert_text = "📈 <b>PORTFOLIO ACTION REQUIRED</b>\n\n"
            for a in urgent_csv[:5]:
                emoji = "🛑" if a["action"] == "SELL" else "✂️"
                alert_text += f"{emoji} <b>{a['action']} {a['ticker']}</b>: {a['reason']}\n"
                alert_text += f"   P&L: {a['pnl_pct']:+.1f}% | Position: {a['pos_pct']:.1f}% of portfolio\n\n"
            alert_text += f"Portfolio: ${csv_total:,.0f} | P&L: {csv_pnl_pct:+.1f}%"
            broadcast(alert_text)
            log("[OK] 📈 CSV portfolio action alert sent to Telegram!")
        except Exception as e:
            log(f"[!] Failed to send CSV alert: {e}")
        except Exception as e:
            log(f"[!] Failed to send CSV portfolio alert: {e}")

    # 3d-2. Also monitor Alpaca paper trading (NO Telegram alerts — agent trades silently)
    log("📊 Monitoring Alpaca paper trading account...")
    try:
        alpaca_snapshot = get_alpaca_portfolio_snapshot()
        alpaca_cash_pct = alpaca_snapshot["allocation"]["cash"]
        log(f"[OK] Alpaca: ${alpaca_snapshot['total_value']:,.0f} | "
            f"Cash: {alpaca_cash_pct:.0%} | Positions: {alpaca_snapshot['num_positions']}")

        # Cash drag awareness — log opportunity cost
        if alpaca_cash_pct > 0.50:
            excess_cash = alpaca_snapshot["cash"] - (alpaca_snapshot["total_value"] * 0.15)
            # Estimate opportunity cost: if market returns ~10% annually, idle cash costs ~0.04% daily
            daily_opportunity_cost = excess_cash * 0.0004  # ~10% annual / 252 trading days
            log(f"  💰 CASH DRAG: {alpaca_cash_pct:.0%} cash (${alpaca_snapshot['cash']:,.0f}). "
                f"Excess: ${excess_cash:,.0f}. Est. daily opportunity cost: ${daily_opportunity_cost:.2f}")
            log(f"  → Agent should deploy excess cash into high-conviction picks to reduce drag")
    except Exception as e:
        log(f"[!] Alpaca monitoring failed: {e}")

    # 3e. Alpaca paper trading — no separate rebalancing needed
    # The agent's buy decisions in section 10b handle capital deployment intelligently
    # Sell decisions are made by the portfolio review in section 3d-2
    log("💼 Alpaca paper trading — buy/sell decisions handled by conviction-based trading in section 10")

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
        investment_context += f"\n\n⚠️ EARNINGS ALERT (Your Portfolio):\n{earnings_alerts}\nConsider earnings implications for any recommendations."
    if related_earnings:
        investment_context += f"\n\n⚠️ EARNINGS ALERT (Related / Supply Chain):\n{related_earnings}\nThese companies are in the same ecosystem as your holdings — their earnings can signal sector trends, supply chain health, and opportunities you may not own yet."
    if sector_earnings:
        investment_context += f"\n\n⚠️ EARNINGS ALERT (Comprehensive Sector Coverage):\n{sector_earnings}\nThese are companies in sectors you're invested in that could present new opportunities or signal sector-wide moves."
    if forward_analysis:
        investment_context += f"\n\n🔮 FORWARD-LOOKING EARNINGS ANALYSIS (Beat/Miss Predictions & Options Implications):\n{forward_analysis}\nUse these predictions to inform pre-earnings positioning and options strategies."
    if recent_surprises:
        investment_context += f"\n\n📊 RECENT EARNINGS SURPRISES:\n{recent_surprises}\nRecent beats/misses can indicate sector-wide trends and inform expectations for upcoming reporters."
    if market_sentiment:
        investment_context += f"\n\n🌡️ MARKET SENTIMENT:\n{market_sentiment}\nAdjust sizing/strategy based on VIX/fear-greed."

    # Add market foresight to investment context
    foresight_summary = f"\n\n🔮 MARKET FORESIGHT OUTLOOK (Score: {foresight_score}/100 — {foresight_direction}):\n{foresight['outlook']}\n\nKey Signals:\n"
    for sig in foresight["signals"]:
        if abs(sig.get("score", 0)) > 3:
            foresight_summary += f"• {sig['name']}: {sig['detail']}\n"
    foresight_summary += f"\nSuggested Actions:\n"
    for action in foresight["action_items"][:5]:
        foresight_summary += f"• {action}\n"
    investment_context += foresight_summary

    # Add smart money context (collected in section 4c)
    if smart_money_context:
        investment_context += f"\n\n🏦 SMART MONEY SIGNALS:\n{smart_money_context}\nUse these signals to validate or challenge your investment theses."

    # Add sector rotation context (collected in section 4d)
    if sector_context:
        investment_context += f"\n\n🔄 SECTOR ROTATION & THEMES:\n{sector_context}\nAlign your picks with sector momentum and emerging themes."

    # Add benchmark/performance context (collected in section 4e)
    if benchmark_context:
        investment_context += f"\n\n📊 PORTFOLIO vs BENCHMARKS:\n{benchmark_context}\nUnderstand your performance attribution and adjust allocation accordingly."

    # 4a. Investment ideas with everything: portfolio, options, earnings, sentiment, smart money, sectors, benchmarks
    investments = task_investment_ideas(
        market_data, digest_summary, memory, portfolio_analysis,
        options_context=investment_context
    )

    parse_and_store_recommendations(investments)

    # 4a-1. Immediately update recommendation performance (captures intraday moves)
    # This ensures that if MU was recommended at $640 and is now $663, we see +3.6% not 0.0%
    update_recommendation_performance()

    # 4a-2. Sync Alpaca holdings into recommendations with correct entry prices
    # This ensures NVDA, MU, VRT (actual Alpaca holdings) show live P&L with real entry prices
    # Split into two sections: "Alpaсa Holdings" (what we own) and "Watchlist" (recommendations we don't own yet)
    try:
        alpaca_snapshot = get_alpaca_portfolio_snapshot()
        alpaca_symbols = set()
        alpaca_rec_lines = []
        for pos in alpaca_snapshot["positions"]:
            if pos["type"] == "stock":
                sym = pos["symbol"]
                alpaca_symbols.add(sym)
                # Use actual Alpaca entry price and current P&L
                rec_line = (f"- {TODAY} | {sym} | ${pos['avg_entry']:.2f} | N/A | 8/10 | Active | "
                            f"${pos['current_price']:.2f} | {pos['unrealized_plpc']:+.1f}% | Long-term (Alpaca)")
                alpaca_rec_lines.append(rec_line)
                log(f"[OK] Alpaca holding: {sym} @ ${pos['avg_entry']:.2f} → ${pos['current_price']:.2f} ({pos['unrealized_plpc']:+.1f}%)")

        # Read current recommendations
        existing_recs = read_file(RECOMMENDATIONS_FILE) if RECOMMENDATIONS_FILE.exists() else ""

        # Separate: remove any old Alpaca entries, keep non-Alpaca recommendations
        all_lines = existing_recs.split('\n') if existing_recs else []
        non_alpaca_lines = []
        in_active = False
        for line in all_lines:
            if "## Active Recommendations" in line:
                in_active = True
                non_alpaca_lines.append(line)
                continue
            if in_active and line.startswith('- '):
                # Check if this is an Alpaca line or a recommendation line
                is_alpaca = '(Alpaca)' in line
                if not is_alpaca:
                    non_alpaca_lines.append(line)
            else:
                non_alpaca_lines.append(line)

        # Rebuild: Alpaca Holdings section + Watchlist section
        new_content = '\n'.join(non_alpaca_lines)

        # Add Alpaca Holdings section
        if alpaca_rec_lines:
            alpaca_section = "\n\n## 🏦 Alpaca Holdings (Actual Positions)\n"
            alpaca_section += "\n".join(alpaca_rec_lines)
            alpaca_section += "\n"
            # Insert before the Active Recommendations section
            if "## Active Recommendations" in new_content:
                new_content = new_content.replace("## Active Recommendations", alpaca_section + "\n## 📋 Watchlist Recommendations")
            else:
                new_content += alpaca_section

        RECOMMENDATIONS_FILE.write_text(new_content, encoding="utf-8")
        log(f"[OK] Recommendations synced: {len(alpaca_rec_lines)} Alpaca holdings + watchlist separated")
    except Exception as e:
        log(f"[!] Error syncing Alpaca positions: {e}")

    # 4b. Options ideas — pass the full investment_context so options strategies
    # benefit from earnings, sentiment, foresight, smart money, and sector data
    combined_earnings = ""
    if earnings_alerts:
        combined_earnings += earnings_alerts
    if related_earnings:
        combined_earnings += "\n" + related_earnings
    if sector_earnings:
        combined_earnings += "\n" + sector_earnings
    if not combined_earnings:
        combined_earnings = "No upcoming earnings."

    # 4c. Smart Money Tracking (hedge funds, congress, insiders)
    smart_money_context = ""
    smart_money_report = ""
    if SKILLS_AVAILABLE:
        try:
            log("🏦 Analyzing smart money activity...")
            sm_summary = get_smart_money_summary()
            smart_money_report = generate_smart_money_report(sm_summary)
            smart_money_context = _extract_smart_money_context(sm_summary)
            log("[OK] Smart money analysis complete")
        except Exception as e:
            log(f"[!] Smart money analysis failed: {e}")

    # 4d. Sector Rotation & Thematic Analysis
    sector_context = ""
    sector_rotation_report = ""
    if SKILLS_AVAILABLE:
        try:
            log("🔄 Analyzing sector rotation & emerging themes...")
            sector_rotation_report = generate_sector_report()
            sector_context = _extract_sector_context()
            log("[OK] Sector rotation analysis complete")
        except Exception as e:
            log(f"[!] Sector rotation analysis failed: {e}")

    # 4e. Benchmark Comparison & Performance Attribution
    benchmark_context = ""
    benchmark_report = ""
    if SKILLS_AVAILABLE:
        try:
            log("📊 Running benchmark comparison...")
            benchmark_report = generate_benchmark_report()
            benchmark_context = _extract_benchmark_context()
            log("[OK] Benchmark comparison complete")
        except Exception as e:
            log(f"[!] Benchmark comparison failed: {e}")

    # 4f. Enrich options context with all collected intelligence
    enriched_options_context = investment_context
    if smart_money_context:
        enriched_options_context += f"\n\n🏦 SMART MONEY:\n{smart_money_context}"
    if sector_context:
        enriched_options_context += f"\n\n🔄 SECTORS:\n{sector_context}"
    if benchmark_context:
        enriched_options_context += f"\n\n📊 BENCHMARKS:\n{benchmark_context}"

    options = task_options_ideas(
        market_data, digest_summary, memory,
        options_context=enriched_options_context,
        earnings_context=combined_earnings,
        market_sentiment=market_sentiment
    )

    # 4g. Learning and market reaction
    learning = task_learning(digest_summary, memory)
    market_reaction = task_market_reaction(market_data, digest_summary)

    # 5. Write report and send to Telegram (only in full mode — 3x/day)
    _run_mode = os.environ.get("RUN_MODE", "")
    if not SILENT_MODE:
        log("📝 Writing report...")
        report = build_and_save_report(
            market_data, digest, investments, options, learning,
            market_sentiment=market_sentiment,
            portfolio_analysis_text=portfolio_analysis.get('weighted_summary', ''),
            market_reaction=market_reaction,
            earnings_alerts=earnings_alerts,
            related_earnings=related_earnings,
            sector_earnings=sector_earnings,
            forward_analysis=forward_analysis,
            recent_surprises=recent_surprises,
            foresight_score=foresight_score,
            foresight_direction=foresight_direction,
            foresight_outlook=foresight["outlook"],
            foresight_actions=foresight["action_items"],
            foresight=foresight,
            smart_money_report=smart_money_report,
            sector_rotation_report=sector_rotation_report,
            benchmark_report=benchmark_report,
        )

        # 5b. Send report to Telegram (only in full mode — 3x/day)
        if SKILLS_AVAILABLE:
            try:
                sent = send_report_via_telegram(report)
                if sent:
                    log(f"[OK] Report sent to {sent} Telegram user(s)")
                else:
                    log("[!] Telegram: No users configured yet")
            except Exception as e:
                log(f"[!] Telegram send failed: {e}")
    else:
        # Both "silent" and "alerts-only" skip report generation and Telegram report
        # But the agent still trades, runs self-reflection, and sends urgent alerts
        log(f"📝 {_run_mode.upper()} mode — skipping report generation and Telegram report")
        report = ""

    # 5c. Send urgent Telegram alerts (foresight extremes, once-in-a-lifetime ops)
    # Runs in BOTH full and alerts-only modes — these are time-sensitive
    # Placed here AFTER investments is generated so we can scan it
    try:
        from skills.telegram_bot import broadcast
        # Foresight crash/bullish alerts
        if foresight.get("alert"):
            broadcast(foresight["alert"])
            log("[OK] 🚨 Foresight alert sent to Telegram!")
        # Once-in-a-lifetime opportunities from LLM investment ideas
        if investments and ("once-in-a-lifetime" in str(investments).lower() or "once in a lifetime" in str(investments).lower()):
            import re
            # Extract the full once-in-a-lifetime section — grab everything from the header
            # to the next major section header (## or #) or end of text
            otl_pattern = r'(?:ONCE-IN-A-LIFETIME|Once-in-a-lifetime)[^\n]*\n(.*?)(?:\n#{1,3}\s|\Z)'
            otl_match = re.search(otl_pattern, str(investments), re.DOTALL | re.IGNORECASE)
            if otl_match:
                # Get the full match including the header
                full_match = otl_match.group(0).strip()
                # Clean up: remove excessive whitespace but preserve structure
                full_match = re.sub(r'\n{3,}', '\n\n', full_match)
                # Truncate to Telegram-safe length (leave room for wrapper text)
                max_otl_len = 3500
                if len(full_match) > max_otl_len:
                    full_match = full_match[:max_otl_len] + "\n\n<i>... (truncated — use /report for full text)</i>"
                alert_text = f"⭐⭐⭐ <b>ONCE-IN-A-LIFETIME OPPORTUNITY</b> ⭐⭐⭐\n\n{full_match}\n\n<i>Review and act if you agree. Not financial advice.</i>"
                sent = broadcast(alert_text)
                if sent:
                    log(f"[OK] ⭐ Once-in-a-lifetime alert sent to {sent} Telegram user(s)!")
                else:
                    log("[!] Once-in-a-lifetime alert: no Telegram users configured")
            else:
                log("[!] Once-in-a-lifetime found in investments but regex couldn't extract — sending raw snippet")
                # Fallback: send a snippet around the keyword
                idx = str(investments).lower().find("once-in-a-lifetime")
                if idx == -1:
                    idx = str(investments).lower().find("once in a lifetime")
                if idx >= 0:
                    snippet = str(investments)[max(0, idx-100):idx+2000]
                    alert_text = f"⭐⭐⭐ <b>ONCE-IN-A-LIFETIME OPPORTUNITY</b> ⭐⭐⭐\n\n{snippet}\n\n<i>Review and act if you agree. Not financial advice.</i>"
                    broadcast(alert_text)
    except Exception as e:
        log(f"[!] Failed to send Telegram alerts: {e}")

    # 6. Deep self-reflection & continuous learning (ALWAYS runs — agent must learn from every run)
    log("🪞 Deep self-reflection & learning...")
    alpaca_snap = None
    try:
        alpaca_snap = get_alpaca_portfolio_snapshot()
    except Exception:
        pass
    reflection = task_self_reflect(
        report=report if report else "Alerts-only run — no full report generated",
        memory=memory, snapshot=alpaca_snap,
        foresight=foresight if 'foresight' in dir() else None
    )
    if reflection:
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
            # Use ALL holdings for cost basis, not just top_positions
            all_holdings = portfolio_analysis.get('top_positions', [])
            total_value = portfolio_analysis.get('total_value', 0)
            total_cost = sum(h.get('cost_basis', 0) for h in all_holdings)
            
            perf = calculate_portfolio_performance(total_value, total_cost)
            comparison = compare_to_benchmarks(perf.get('total_return_pct', 0))
            
            log(f"[OK] Portfolio: ${total_value:,.0f} value / ${total_cost:,.0f} cost = {perf['total_return_pct']:+.2f}% total return")
            
            for sym, data in comparison.get('indices', {}).items():
                log(f"  vs {sym} ({data['name']}): {data['return']:+.2f}% today → diff: {data['diff']:+.2f}%")
            
            outperformed = comparison.get('outperformed', [])
            if outperformed:
                log(f"[OK] Portfolio outperforming today: {', '.join(outperformed)}")
            
            update_benchmark_log(total_value, total_cost, [])
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

            # 10b. Deploy cash into high-conviction opportunities
            # Agent treats paper trading with same discipline as real trading — every dollar matters
            # Only buys when: conviction >= 8, positive expected value, and opportunity cost of cash > expected return
            acct = get_account_info()
            if "error" not in acct:
                available_cash = acct.get('cash', 0)
                portfolio_val = acct.get('portfolio_value', 100000)
                cash_pct = available_cash / portfolio_val if portfolio_val > 0 else 1.0
                log(f"  Cash available: ${available_cash:,.0f} ({cash_pct:.0%} of portfolio)")

                # Only deploy if cash is excessive (>30%) OR we have very high conviction (>8) ideas
                should_deploy = cash_pct > 0.30

                # Read watchlist recommendations
                recs_content = read_file(RECOMMENDATIONS_FILE)
                in_watchlist = False
                watchlist_lines = []
                for rec_line in recs_content.split('\n'):
                    if "## 📋 Watchlist Recommendations" in rec_line:
                        in_watchlist = True
                        continue
                    if "## 🏦 Alpaca Holdings" in rec_line or "## Active Recommendations" in rec_line:
                        in_watchlist = False
                        continue
                    if in_watchlist and rec_line.startswith('- ') and 'Active' in rec_line:
                        watchlist_lines.append(rec_line)

                trades_executed = 0
                for line in watchlist_lines:
                    parts = line[2:].split(' | ')
                    if len(parts) >= 5:
                        try:
                            conviction = int(parts[4].split('/')[0].strip())
                            ticker = parts[1].strip()
                            entry_str = parts[2].strip().replace('$', '').replace(',', '')
                            try:
                                entry_price = float(entry_str) if entry_str != 'N/A' else 0
                            except ValueError:
                                entry_price = 0

                            if entry_price <= 0:
                                continue

                            # Skip if already held
                            already_held = any(p['symbol'] == ticker for p in alpaca_positions)
                            if already_held:
                                continue

                            # STRICT: Only buy conviction 8+ (same as real trading)
                            # The agent must believe this will genuinely bring value
                            if conviction < 8:
                                log(f"  Skip {ticker}: conviction {conviction}/10 below 8+ threshold — cash is better deployed elsewhere")
                                continue

                            # Calculate position size: 5-8% of portfolio for conviction 8-9, 10% for 10/10
                            if conviction >= 10:
                                pct = 0.10
                            elif conviction >= 9:
                                pct = 0.08
                            else:
                                pct = 0.05
                            dollar_amount = portfolio_val * pct

                            # Don't deploy more than 50% of available cash in a single trade
                            dollar_amount = min(dollar_amount, available_cash * 0.50)

                            if dollar_amount < 500:
                                log(f"  Skip {ticker}: allocation ${dollar_amount:.0f} too small (min $500)")
                                continue

                            qty = max(1, int(dollar_amount / entry_price))

                            log(f"  → BUY {ticker}: conviction {conviction}/10, ${dollar_amount:,.0f} ({pct:.0%} of portfolio), x{qty} @ ${entry_price:.2f}")
                            trade_result = place_stock_order(ticker, qty, "buy", "market")
                            if trade_result.get("status") in ["FILLED", "submitted", "accepted", "new"]:
                                trades_executed += 1
                                log(f"[OK] Alpaca BUY: {ticker} x{qty} @ ${entry_price:.2f} (status: {trade_result.get('status')})")
                            elif trade_result.get("status") == "REJECTED":
                                log(f"[!] Alpaca BUY rejected for {ticker}: {trade_result.get('error', 'unknown')}")
                            else:
                                log(f"[!] Alpaca BUY uncertain for {ticker}: {trade_result}")
                        except (ValueError, IndexError):
                            continue

                if trades_executed == 0:
                    log(f"  No trades executed — agent didn't find conviction 8+ opportunities worth deploying cash")
                    if cash_pct > 0.50:
                        log(f"  ⚠️ Cash at {cash_pct:.0%} — agent is being selective, waiting for high-conviction setups")
                else:
                    log(f"[OK] Executed {trades_executed} Alpaca trade(s) this run")

            # 10c. Active position management — best-in-class long-term strategies
            # Combines: Buffett's "hold wonderful businesses", Dalio's risk parity,
            # Marks' "buy when there's blood in the streets", Howard Marks' market timing,
            # AQR's momentum + value, CMT trailing stops, Kelly position sizing
            log("  Managing existing Alpaca positions with research-backed strategies...")
            from skills.alpaca_trading import place_stock_order
            from skills.portfolio_manager import get_position_fundamentals
            positions_reviewed = 0

            for pos in alpaca_positions:
                if pos.get('type') != 'stock':
                    continue
                sym = pos['symbol']
                qty = int(pos.get('qty', 0))
                avg_entry = float(pos.get('avg_entry_price', 0))
                current = float(pos.get('current_price', 0))
                pnl_pct = float(pos.get('unrealized_plpc', 0)) * 100
                market_value = float(pos.get('market_value', 0))
                pos_pct = market_value / portfolio_val * 100 if portfolio_val > 0 else 0

                # ── GATHER INTELLIGENCE ──
                fundamentals = get_position_fundamentals(sym)

                # ── STRATEGY 1: TRAILING STOP (CMT-inspired) ──
                # Use ATR-based trailing stop instead of fixed -15%
                # If stock has pulled back >10% from recent highs, tighten stop
                # If stock is in strong uptrend, give it room to run
                try:
                    import yfinance as yf
                    t = yf.Ticker(sym)
                    hist = t.history(period="3mo")
                    if hist is not None and len(hist) > 20:
                        recent_high = hist["Close"].rolling(20).max().iloc[-1]
                        pullback_from_high = ((current - recent_high) / recent_high * 100) if recent_high > 0 else 0
                        # 20-day MA for trend direction
                        ma20 = hist["Close"].rolling(20).mean().iloc[-1]
                        ma50 = hist["Close"].rolling(50).mean().iloc[-1] if len(hist) >= 50 else ma20
                        uptrend = current > ma20 > ma50
                        downtrend = current < ma20 < ma50
                    else:
                        pullback_from_high = 0
                        uptrend = True
                        downtrend = False
                except Exception:
                    pullback_from_high = 0
                    uptrend = True
                    downtrend = False

                # ── STRATEGY 2: THESIS CHECK (Buffett-inspired) ──
                # "The stock market is a device for transferring money from the impatient to the patient"
                # Only sell if the investment thesis is fundamentally broken, not because of price alone
                thesis_intact = True
                thesis_broken = False

                # Check earnings trend — 2 consecutive misses = thesis at risk
                if fundamentals.get("consecutive_misses"):
                    thesis_intact = False
                    thesis_broken = True

                # Check if below 200-day MA with deteriorating fundamentals
                if fundamentals.get("below_200ma") and pnl_pct < -10:
                    thesis_intact = False

                # ── STRATEGY 3: RISK PARITY (Dalio-inspired) ──
                # No single position should risk more than 2% of total portfolio
                # If position has grown too large, trim to maintain balance
                max_position_pct = 15.0  # Max 15% in single position
                if pos_pct > max_position_pct:
                    excess_value = market_value - (portfolio_val * max_position_pct / 100)
                    trim_qty = max(1, int(excess_value / current))
                    log(f"  ⚖️ TRIM {sym}: {pos_pct:.1f}% of portfolio exceeds {max_position_pct}% max — selling {trim_qty} shares")
                    result = place_stock_order(sym, trim_qty, "sell", "market")
                    if result.get("status") in ["FILLED", "submitted", "accepted", "new"]:
                        log(f"[OK] TRIMMED {sym} x{trim_qty} (risk parity)")
                    continue

                # ── STRATEGY 4: MOMENTUM + VALUE (AQR-inspired) ──
                # Winners in uptrend → let them run (don't cap gains)
                # Losers in downtrend → cut quickly (don't average down blindly)
                if downtrend and pnl_pct < -10:
                    # Downtrend + loss = cut quickly (don't be a hero)
                    log(f"  🛑 SELL {sym}: downtrend + {pnl_pct:+.1f}% loss — cutting before deeper damage")
                    result = place_stock_order(sym, qty, "sell", "market")
                    if result.get("status") in ["FILLED", "submitted", "accepted", "new"]:
                        log(f"[OK] SOLD {sym} x{qty} (downtrend cut)")
                    continue

                # ── STRATEGY 5: CONTRARIAN BUY (Howard Marks / Seth Klarman) ──
                # "The best buying opportunities come when others are panicking"
                # If stock is down >20% on market noise (not fundamentals), consider averaging down
                if pnl_pct <= -20 and thesis_intact and not downtrend:
                    # Stock is down but thesis is intact — this is a buying opportunity
                    if pos_pct < 5.0:  # Only average down if position is still small
                        add_value = portfolio_val * 0.03  # Add 3% of portfolio
                        add_qty = max(1, int(add_value / current))
                        log(f"  💰 AVERAGE DOWN {sym}: down {pnl_pct:.1f}% but thesis intact — buying {add_qty} more at discount")
                        result = place_stock_order(sym, add_qty, "buy", "market")
                        if result.get("status") in ["FILLED", "submitted", "accepted", "new"]:
                            log(f"[OK] BOUGHT {sym} x{add_qty} more (averaging down on weakness)")
                        continue

                # ── STRATEGY 6: TRAILING STOP (dynamic, not fixed) ──
                # In uptrend: trail stop at -10% from recent high (give room to run)
                # In downtrend: trail stop at -7% from recent high (cut quickly)
                # In sideways: trail stop at -12% (moderate)
                if uptrend:
                    stop_pct = -10  # Give winners room to breathe
                elif downtrend:
                    stop_pct = -7   # Cut losers quickly
                else:
                    stop_pct = -12  # Moderate for sideways

                if pullback_from_high <= stop_pct and pnl_pct < 0:
                    log(f"  🛑 TRAILING STOP {sym}: pulled back {pullback_from_high:.1f}% from high (stop: {stop_pct}%)")
                    result = place_stock_order(sym, qty, "sell", "market")
                    if result.get("status") in ["FILLED", "submitted", "accepted", "new"]:
                        log(f"[OK] SOLD {sym} x{qty} (trailing stop)")
                    continue

                # ── STRATEGY 7: ADD TO WINNERS (Peter Lynch / Warren Buffett) ──
                # "If the company is still buying back stock, the CEO is still excited,
                #  and the thesis is intact, add on strength"
                # Add to positions that are: uptrend, thesis intact, conviction high, position small
                if uptrend and thesis_intact and pnl_pct > 10 and pos_pct < 8.0:
                    # Check if this is a high-conviction pick
                    wl_conviction = 0
                    for wl_line in watchlist_lines:
                        wl_parts = wl_line.split(' | ') if wl_line.startswith('- ') else []
                        if len(wl_parts) >= 5 and wl_parts[1].strip() == sym:
                            try:
                                wl_conviction = int(wl_parts[4].split('/')[0].strip())
                            except (ValueError, IndexError):
                                pass
                            break

                    if wl_conviction >= 8:
                        # Add up to 8% of portfolio for high-conviction winners
                        target_value = min(portfolio_val * 0.08, portfolio_val * 0.15 - market_value)
                        if target_value > 500:
                            add_qty = max(1, int(target_value / current))
                            log(f"  ➕ ADD TO WINNER {sym}: uptrend +{pnl_pct:.1f}%, conviction {wl_conviction}/10, only {pos_pct:.1f}% of portfolio")
                            result = place_stock_order(sym, add_qty, "buy", "market")
                            if result.get("status") in ["FILLED", "submitted", "accepted", "new"]:
                                log(f"[OK] BOUGHT {sym} x{add_qty} more (adding to winner)")
                            continue

                # ── STRATEGY 8: THESIS-BROKEN SELL (Buffett's "when the facts change") ──
                if thesis_broken:
                    log(f"  🛑 SELL {sym}: thesis broken (consecutive misses, deteriorating fundamentals)")
                    result = place_stock_order(sym, qty, "sell", "market")
                    if result.get("status") in ["FILLED", "submitted", "accepted", "new"]:
                        log(f"[OK] SOLD {sym} x{qty} (thesis broken)")
                    continue

                # ── DEFAULT: HOLD with trailing stop awareness ──
                log(f"  ✅ HOLD {sym}: {qty} shares, {pnl_pct:+.1f}% P&L, {pos_pct:.1f}% of portfolio | "
                    f"{'uptrend' if uptrend else 'downtrend' if downtrend else 'sideways'} | "
                    f"thesis {'intact' if thesis_intact else 'at risk'} | "
                    f"trailing stop at {stop_pct}% from high")
                positions_reviewed += 1

            log(f"  Reviewed {positions_reviewed} existing positions with full strategy engine")
            
            # 10c-2. OPPORTUNITY COST ANALYSIS — compare weak positions vs. better opportunities
            # "The cost of a thing is the amount of what I will give up to get it" — Warren Buffett
            # Even if stop-loss isn't hit, sitting on a weak position has real cost
            if len(watchlist_lines) > 0 and len(alpaca_positions) > 0:
                log("  Running opportunity cost analysis...")
                weak_positions = []
                for pos in alpaca_positions:
                    if pos.get('type') != 'stock': continue
                    pnl_pct = float(pos.get('unrealized_plpc', 0)) * 100
                    pos_pct = float(pos.get('market_value', 0)) / portfolio_val * 100 if portfolio_val > 0 else 0
                    # Identify weak positions: negative P&L, small position, no clear catalyst
                    if pnl_pct < -5 and pos_pct < 5:
                        weak_positions.append({
                            'symbol': pos['symbol'], 'pnl_pct': pnl_pct, 'pos_pct': pos_pct,
                            'value': float(pos.get('market_value', 0))
                        })
                
                if weak_positions:
                    weak_value = sum(w['value'] for w in weak_positions)
                    log(f"  ⚠️ Opportunity cost: {len(weak_positions)} weak positions tying up ${weak_value:,.0f}")
                    for wp in weak_positions:
                        log(f"    → {wp['symbol']}: {wp['pnl_pct']:.1f}% P&L, {wp['pos_pct']:.1f}% of portfolio")
                    log(f"  → This capital could be redeployed into {len(watchlist_lines)} high-conviction watchlist ideas")
                    log(f"  → Consider trimming weak positions even if stop-loss not hit — opportunity cost is real")

            # 10d. Advanced options strategies — research-backed, high-return, defined-risk
            from skills.options_strategies import (
                generate_options_strategies, format_options_report,
                get_options_chain, get_option_pricing, analyze_iv_rank, find_mispriced_options
            )
            from skills.alpaca_trading import find_option_symbol
            # Re-init options strategies skill for trading context (already initialized earlier)
            init_options_strategies_skill(
                alpaca_key=ALPACA_API_KEY, alpaca_secret=ALPACA_SECRET_KEY,
                finnhub_key=FINNHUB_API_KEY, base_dir=str(BASE_DIR)
            )
            
            options_executed = 0
            options_failed = 0
            
            # Generate advanced options strategies for high-conviction names
            # Focus on: existing Alpaca positions + top watchlist picks
            option_underlyings = []
            
            # Add existing Alpaca positions
            for pos in alpaca_positions:
                if pos.get('type') == 'stock':
                    option_underlyings.append(pos['symbol'])
            
            # Add top watchlist recommendations (conviction 8+)
            for wl_line in watchlist_lines:
                parts = wl_line.split(' | ') if wl_line.startswith('- ') else []
                if len(parts) >= 5:
                    try:
                        conv = int(parts[4].split('/')[0].strip())
                        ticker = parts[1].strip()
                        if conv >= 8 and ticker not in option_underlyings:
                            option_underlyings.append(ticker)
                    except (ValueError, IndexError):
                        pass
            
            # Limit to top 5 underlyings to avoid rate limits
            option_underlyings = option_underlyings[:5]
            
            all_options_strategies = []
            for underlying in option_underlyings:
                try:
                    price = _yf_price(underlying)["price"]
                    if price <= 0:
                        continue
                    
                    # Analyze IV rank
                    iv_analysis = analyze_iv_rank(underlying)
                    iv_rank = iv_analysis["iv_rank"] if iv_analysis else 50
                    
                    # Find mispriced options
                    mispriced = find_mispriced_options(underlying)
                    
                    # Determine direction from existing position or watchlist
                    direction = "neutral"
                    conviction = 7
                    for wl_line in watchlist_lines:
                        parts = wl_line.split(' | ') if wl_line.startswith('- ') else []
                        if len(parts) >= 5 and parts[1].strip() == underlying:
                            try:
                                conviction = int(parts[4].split('/')[0].strip())
                            except (ValueError, IndexError):
                                pass
                            # Check if bullish or bearish from the thesis
                            thesis = str(parts).lower()
                            if any(w in thesis for w in ['buy', 'bull', 'up', 'growth', 'beat']):
                                direction = "bullish"
                            elif any(w in thesis for w in ['sell', 'bear', 'down', 'miss', 'weak']):
                                direction = "bearish"
                            break
                    
                    # If we hold it and it's uptrend, direction is bullish
                    for pos in alpaca_positions:
                        if pos['symbol'] == underlying and pos.get('unrealized_plpc', 0) > 0:
                            direction = "bullish"
                    
                    # Generate strategies
                    strategies = generate_options_strategies(
                        underlying, conviction, direction, price
                    )
                    
                    if strategies:
                        all_options_strategies.extend(strategies)
                        log(f"  {underlying}: {len(strategies)} strategies generated (IV rank: {iv_rank:.0f}, {len(mispriced)} mispriced)")
                
                except Exception as e:
                    log(f"  [!] Error analyzing options for {underlying}: {e}")
                    continue
            
            # Execute the best options strategies (highest conviction, best risk/reward)
            for strat in sorted(all_options_strategies, key=lambda s: s.get('conviction', 0), reverse=True)[:3]:
                try:
                    underlying = strat.get('underlying', '')
                    option_info = strat.get('option', {})
                    
                    if not option_info:
                        # For multi-leg strategies, construct the order differently
                        log(f"  [!] Skipping {strat['strategy']} — complex multi-leg not yet automated")
                        continue
                    
                    option_symbol = option_info.get('symbol', '')
                    if not option_symbol:
                        # Find OCC symbol
                        strike = float(option_info.get('strike_price', 0))
                        occ_type = 'call' if 'call' in strat['strategy'].lower() else 'put'
                        dte = option_info.get('dte', 30)
                        option_symbol = find_option_symbol(underlying, occ_type, strike, dte)
                    
                    if not option_symbol:
                        log(f"  [!] Could not find OCC symbol for {strat['strategy']} on {underlying}")
                        options_failed += 1
                        continue
                    
                    # Position sizing: max 3% of portfolio per options trade
                    acct = get_account_info()
                    portfolio_val = acct.get('portfolio_value', 100000) if "error" not in acct else 100000
                    options_budget = portfolio_val * 0.03
                    
                    # Get option pricing
                    pricing = get_option_pricing([option_symbol])
                    opt_price = 0
                    if pricing.get(option_symbol):
                        snap = pricing[option_symbol]
                        opt_price = float(snap.get("latestTrade", {}).get("p", 0) or 
                                         snap.get("latestQuote", {}).get("ap", 0))
                    
                    if opt_price > 0:
                        max_contracts = max(1, int(options_budget / (opt_price * 100)))
                        qty = min(max_contracts, 2)  # Cap at 2 contracts
                    else:
                        qty = 1
                    
                    log(f"  → EXECUTE: {strat['strategy']} on {underlying} — {option_symbol} x{qty} (conviction: {strat.get('conviction', 'N/A')}/10)")
                    
                    trade_result = place_option_order(underlying, option_symbol, qty, "buy", "market")
                    
                    if trade_result.get("status") in ["FILLED", "submitted", "accepted", "new", "pending_new"]:
                        options_executed += 1
                        log(f"[OK] Options trade: BUY {option_symbol} x{qty} (status: {trade_result.get('status')})")
                    elif trade_result.get("status") == "REJECTED":
                        options_failed += 1
                        log(f"[!] Options trade REJECTED: {option_symbol} — {trade_result.get('error', 'unknown')}")
                    else:
                        options_failed += 1
                        log(f"[!] Options trade uncertain: {option_symbol} — {trade_result}")
                
                except Exception as e:
                    options_failed += 1
                    log(f"  [!] Error executing options strategy: {e}")
                    continue
            
            if trades_executed:
                log(f"[OK] Executed {trades_executed} Alpaca stock trade(s)")
            if options_executed:
                log(f"[OK] Executed {options_executed} Alpaca options trade(s)")
            if options_failed:
                log(f"[!] {options_failed} options trade(s) failed or skipped")
            if options_failed:
                log(f"[!] {options_failed} options trade(s) failed or skipped")
            if not options_executed and not options_failed and not trades_executed:
                log("  No trades executed this run (no high-conviction recommendations or Alpaca not configured)")

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
    import sys
    # Check for silent/alerts-only mode
    _run_mode = os.environ.get("RUN_MODE", "")
    if "--silent" in sys.argv or _run_mode in ("silent", "alerts-only"):
        SILENT_MODE = True
        if _run_mode == "alerts-only":
            print("[ALERTS-ONLY MODE] Trading + alerts active — no report generation, no Telegram report")
        else:
            print("[SILENT MODE] Running market-hours trading only — no report generation, no Telegram messages")
    else:
        SILENT_MODE = False
    main()
