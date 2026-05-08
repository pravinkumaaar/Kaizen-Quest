"""
News Research Skill v2.0

Handles all news-related functionality:
- RSS feed aggregation with staleness filtering
- News summarization
- Cross-domain pattern recognition
- Web search via Tavily
- Finnhub news integration

FIXES in v2.0:
- Reduced cache duration to 20 minutes (was 3600s but stale anyway)
- Added strict staleness filter: articles older than 48h are dropped
- Added more diverse, higher-quality feeds including real-time sources
- Added published-date parsing to ensure freshness
- Deduplication of articles across feeds
"""

import feedparser
import requests
import time
import json
import re
from pathlib import Path
from datetime import datetime, timedelta

# Config
TAVILY_API_KEY = None
FINNHUB_API_KEY = None
BASE_DIR = None
RSS_CACHE_FILE = None

# Maximum age of articles to include (in hours)
# Reduced to 24h to prevent stale articles from persisting across runs
MAX_ARTICLE_AGE_HOURS = 24

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

# RSS Feeds — expanded with more diverse, higher-quality, real-time sources
RSS_FEEDS = {
    "🤖 AI & Tech": [
        "https://techcrunch.com/feed/",
        "https://www.theverge.com/rss/index.xml",
        "https://arstechnica.com/feed/",
        "https://www.wired.com/feed/tag/ai/latest/rss",
        "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
        "https://feeds.bbci.co.uk/news/technology/rss.xml",
        "https://www.technologyreview.com/feed/",
        "https://www.axios.com/feed/",
    ],
    "📈 Markets & Finance": [
        "https://feeds.marketwatch.com/marketwatch/topstories",
        "https://www.cnbc.com/id/100003114/device/rss/rss.html",
        "https://feeds.a.dj.com/rss/RSSMarketsMain.xml",
        "https://oilprice.com/rss/main",
        "https://www.reuters.com/markets/rss/",
        "https://feeds.finance.yahoo.com/rss/2.0/headline?s=^GSPC&region=US&lang=en-US",
        "https://www.ft.com/rss/home",
        "https://seekingalpha.com/market_currents.xml",
    ],
    "🌍 Geopolitics": [
        "https://foreignpolicy.com/feed/",
        "https://feeds.bbci.co.uk/news/world/rss.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
        "https://www.reuters.com/world/rss/",
        "https://www.aljazeera.com/xml/rss/all.xml",
        "https://www.economist.com/finance-and-economics/rss.xml",
    ],
    "🔬 Science & Health": [
        "https://www.sciencedaily.com/rss/top.xml",
        "https://feeds.nature.com/nature/rss/current",
        "https://www.sciencemag.org/rss/news_current.xml",
        "https://rss.nytimes.com/services/xml/rss/nyt/Science.xml",
        "https://www.statnews.com/feed/",
    ],
    "💡 Business & Ideas": [
        "https://a16z.com/feed/",
        "https://rss.nytimes.com/services/xml/rss/nyt/Business.xml",
        "https://hbr.org/rss/feed",
        "https://www.fastcompany.com/feed",
    ],
}

def _parse_date(date_str):
    """Try to parse an RSS date string into a datetime. Returns None if unparseable."""
    if not date_str:
        return None
    # Common RSS date formats — order matters, try most specific first
    formats = [
        "%a, %d %b %Y %H:%M:%S %z",
        "%a, %d %b %Y %H:%M:%S GMT",
        "%a, %d %b %Y %H:%M:%S",
        "%Y-%m-%dT%H:%M:%S%z",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f%z",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%d",
        "%d %b %Y",
        "%a, %d %b %Y",  # e.g. "Thu, 22 Jan 2026" — date only, no time
        "%b %d, %Y",     # e.g. "Jan 22, 2026"
    ]
    # Clean up common variations
    cleaned = date_str.strip()
    for fmt in formats:
        try:
            return datetime.strptime(cleaned, fmt)
        except ValueError:
            continue
    # Try feedparser's parsed date
    try:
        import email.utils
        ts = email.utils.mktime_tz(email.utils.parsedate_tz(cleaned))
        if ts:
            return datetime.fromtimestamp(ts)
    except Exception:
        pass
    return None

def _is_fresh(date_str, max_hours=MAX_ARTICLE_AGE_HOURS):
    """Check if an article is fresh enough to include.
    Returns False (exclude) if date can't be parsed — better to skip stale content."""
    pub_date = _parse_date(date_str)
    if pub_date is None:
        # Can't parse date — exclude it to be safe (don't show potentially stale news)
        return False
    # Make timezone-naive comparison
    now = datetime.utcnow()
    if pub_date.tzinfo:
        pub_date = pub_date.replace(tzinfo=None)
    age = now - pub_date
    return age < timedelta(hours=max_hours)

def fetch_rss(max_per_feed: int = 5, cache_duration: int = 1200) -> dict:
    """Fetch RSS feeds with caching and strict freshness filtering.
    
    Cache duration reduced to 20 minutes (1200s) for more current news.
    Articles older than 24 hours are filtered out.
    Duplicate articles across feeds are deduplicated.
    Cache is validated for staleness before use.
    """
    # Check cache
    if RSS_CACHE_FILE and RSS_CACHE_FILE.exists():
        try:
            cache_data = json.loads(RSS_CACHE_FILE.read_text())
            cache_time = cache_data.get("timestamp", 0)
            if time.time() - cache_time < cache_duration:
                # Validate cache freshness — check if any articles are too old
                cache_age_hours = (time.time() - cache_time) / 3600
                if cache_age_hours < 1:  # Only use cache if < 1 hour old for extra freshness
                    return cache_data["data"]
        except Exception:
            pass
    
    # Fetch fresh
    results = {}
    seen_titles = set()  # For deduplication
    now_str = datetime.now().strftime("%Y-%m-%d")
    
    for category, urls in RSS_FEEDS.items():
        items = []
        for url in urls:
            try:
                feed = feedparser.parse(url)
                
                # Sort entries by published date (newest first) to avoid stale content
                def _entry_date_key(entry):
                    """Extract sortable date from feed entry. Returns 0 for unparseable dates (sorted to bottom)."""
                    pub = entry.get("published_parsed") or entry.get("updated_parsed")
                    if pub:
                        try:
                            import calendar
                            ts = calendar.timegm(pub)
                            if ts > 0:
                                return ts
                        except Exception:
                            pass
                    # Try parsing the published string as fallback
                    pub_str = entry.get("published", "") or entry.get("updated", "")
                    if pub_str:
                        parsed = _parse_date(pub_str)
                        if parsed:
                            import calendar
                            try:
                                return calendar.timegm(parsed.timetuple())
                            except Exception:
                                pass
                    return 0  # Unparseable dates sort to bottom
                
                sorted_entries = sorted(feed.entries, key=_entry_date_key, reverse=True)
                
                for entry in sorted_entries[:max_per_feed]:
                    title = entry.get("title", "").strip()
                    if not title:
                        continue
                    
                    # Deduplication: skip if we've seen this title
                    title_key = title.lower().strip()
                    if title_key in seen_titles:
                        continue
                    
                    # Freshness check: skip articles older than MAX_ARTICLE_AGE_HOURS
                    published_raw = entry.get("published", "") or entry.get("updated", "") or entry.get("pubDate", "")
                    if published_raw and not _is_fresh(published_raw):
                        continue
                    
                    seen_titles.add(title_key)
                    
                    summary = entry.get("summary", entry.get("description", ""))
                    summary = re.sub(r'<[^>]+>', '', summary)[:250]
                    published = published_raw[:16] if published_raw else now_str
                    
                    items.append(f"• {title} [{published}]\n  {summary}…")
            except Exception:
                pass
        results[category] = items[:10]
    
    # Cache results
    if RSS_CACHE_FILE:
        try:
            RSS_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
            cache_data = {"timestamp": time.time(), "data": results}
            RSS_CACHE_FILE.write_text(json.dumps(cache_data, ensure_ascii=False))
        except Exception:
            pass
    
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

def finnhub_news(n: int = 10) -> str:
    """Finnhub general market news (free tier: 60 req/min).
    Fetches from multiple endpoints for broader coverage."""
    if not FINNHUB_API_KEY:
        return "[Finnhub not configured]"
    
    all_items = []
    seen_headlines = set()
    
    # Endpoint 1: General news
    try:
        r = requests.get(
            "https://finnhub.io/api/v1/news",
            params={"category": "general", "token": FINNHUB_API_KEY},
            timeout=15
        )
        for item in r.json()[:n]:
            headline = item.get("headline", "").strip()
            if headline and headline.lower() not in seen_headlines:
                seen_headlines.add(headline.lower())
                ts = item.get("datetime", 0)
                time_str = ""
                if ts:
                    try:
                        time_str = datetime.fromtimestamp(ts).strftime("%b %d %H:%M")
                    except Exception:
                        pass
                summary = item.get("summary", "")[:200]
                src = item.get("source", "")
                all_items.append(f"• {headline} [{src} {time_str}]\n  {summary}")
    except Exception:
        pass
    
    # Endpoint 2: Company news for major tickers (market movers)
    for ticker in ["SPY", "NVDA", "AAPL", "TSLA", "AMD", "MSFT", "GOOGL", "META", "AMZN", "JPM"]:
        try:
            r = requests.get(
                "https://finnhub.io/api/v1/company-news",
                params={
                    "symbol": ticker,
                    "from": (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d"),
                    "to": datetime.now().strftime("%Y-%m-%d"),
                    "token": FINNHUB_API_KEY
                },
                timeout=10
            )
            for item in r.json()[:2]:
                headline = item.get("headline", "").strip()
                if headline and headline.lower() not in seen_headlines:
                    seen_headlines.add(headline.lower())
                    ts = item.get("datetime", 0)
                    time_str = ""
                    if ts:
                        try:
                            time_str = datetime.fromtimestamp(ts).strftime("%b %d %H:%M")
                        except Exception:
                            pass
                    summary = item.get("summary", "")[:150]
                    all_items.append(f"• {headline} [{ticker} {time_str}]\n  {summary}")
        except Exception:
            continue
    
    if all_items:
        return "\n".join(all_items[:n + 5])
    return "[Finnhub unavailable]"

def finnhub_earnings_surprise(n: int = 10) -> str:
    """Fetch recent earnings surprises from Finnhub — companies that beat/missed estimates."""
    if not FINNHUB_API_KEY:
        return ""
    try:
        r = requests.get(
            "https://finnhub.io/api/v1/calendar/earnings",
            params={
                "from": (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d"),
                "to": datetime.now().strftime("%Y-%m-%d"),
                "token": FINNHUB_API_KEY
            },
            timeout=15
        )
        items = r.json().get("earningsCalendar", [])
        results = []
        for e in items[:n]:
            ticker = e.get("symbol", "")
            eps_est = e.get("epsEstimate", "")
            eps_actual = e.get("epsActual", "")
            rev_est = e.get("revenueEstimate", "")
            rev_actual = e.get("revenueActual", "")
            hour = e.get("hour", "")
            if eps_actual or rev_actual:
                surprise_parts = []
                if eps_est and eps_actual:
                    try:
                        diff = (float(eps_actual) - float(eps_est)) / abs(float(eps_est)) * 100
                        surprise_parts.append(f"EPS {'beat' if diff > 0 else 'missed'} by {abs(diff):.1f}%")
                    except (ValueError, ZeroDivisionError):
                        pass
                if rev_est and rev_actual:
                    try:
                        diff = (float(rev_actual) - float(rev_est)) / float(rev_est) * 100
                        surprise_parts.append(f"Rev {'beat' if diff > 0 else 'missed'} by {abs(diff):.1f}%")
                    except (ValueError, ZeroDivisionError):
                        pass
                surprise_str = ", ".join(surprise_parts) if surprise_parts else "reported"
                results.append(f"  📊 {ticker} — {surprise_str} ({hour})")
        if results:
            return "**📊 Recent Earnings Surprises:**\n" + "\n".join(results) + "\n"
    except Exception:
        pass
    return ""

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
    'finnhub_earnings_surprise',
    'generate_news_digest',
    'RSS_FEEDS'
]
