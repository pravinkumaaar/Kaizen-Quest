"""
News Research Skill

Handles all news-related functionality:
- RSS feed aggregation
- News summarization
- Cross-domain pattern recognition
- Web search via Tavily
- Finnhub news integration
"""

import feedparser
import requests
import time
import json
import re
from pathlib import Path
from datetime import datetime

# Config
TAVILY_API_KEY = None
FINNHUB_API_KEY = None
BASE_DIR = None
RSS_CACHE_FILE = None

def init_news_skill(tavily_key=None, finnhub_key=None, base_dir=None):
    """Initialize with config from main agent."""
    global TAVILY_API_KEY, FINNHUB_API_KEY, BASE_DIR, RSS_CACHE_FILE
    if tavily_key:
        TAVILY_API_KEY = tavily_key
    if finnhub_key:
        FINNHUB_API_KEY = finnhub_key
    if base_dir:
        BASE_DIR = Path(base_dir)
        RSS_CACHE_FILE = BASE_DIR / "cache" / "rss_cache.json"

# RSS Feeds
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
        "https://www.npr.org/rss/rss.php?id=1006",
    ],
}

def fetch_rss(max_per_feed: int = 4, cache_duration: int = 3600) -> dict:
    """Fetch RSS feeds with caching."""
    # Check cache
    if RSS_CACHE_FILE and RSS_CACHE_FILE.exists():
        try:
            cache_data = json.loads(RSS_CACHE_FILE.read_text())
            cache_time = cache_data.get("timestamp", 0)
            if time.time() - cache_time < cache_duration:
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
                    title = entry.get("title", "").strip()
                    summary = entry.get("summary", entry.get("description", ""))
                    summary = re.sub(r'<[^>]+>', '', summary)[:250]
                    published = entry.get("published", "")[:16]
                    if title:
                        items.append(f"• {title} [{published}]\n  {summary}…")
            except Exception:
                pass
        results[category] = items[:10]
    
    # Cache results
    if RSS_CACHE_FILE:
        cache_data = {"timestamp": time.time(), "data": results}
        RSS_CACHE_FILE.write_text(json.dumps(cache_data))
    
    return results

def tavily_search(query: str, n: int = 4) -> str:
    """Tavily web search (free tier: 1,000/month)."""
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
    except Exception:
        return "[Tavily unavailable]"

def finnhub_news(n: int = 8) -> str:
    """Finnhub general market news (free tier: 60 req/min)."""
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
    except Exception:
        return "[Finnhub unavailable]"

def generate_news_digest(rss_data: dict, finnhub_data: str, memory: str = "") -> str:
    """Generate a formatted news digest."""
    digest = "## 📰 Daily Intelligence Digest\n\n"
    
    for category, items in rss_data.items():
        digest += f"### {category}\n"
        for item in items[:5]:
            digest += f"{item}\n\n"
    
    if finnhub_data and finnhub_data != "[Finnhub not configured]":
        digest += "### 📈 Market News (Finnhub)\n"
        digest += f"{finnhub_data}\n\n"
    
    return digest

__all__ = [
    'init_news_skill',
    'fetch_rss',
    'tavily_search',
    'finnhub_news',
    'generate_news_digest',
    'RSS_FEEDS'
]
