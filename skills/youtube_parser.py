"""
YouTube Stock Recommendation Parser v1.0

Parses YouTube channels (ZipTrader, Tom Nash, etc.) to extract stock ticker
recommendations from video titles, descriptions, and transcripts.

Data Sources:
- YouTube Data API v3: Search videos, get metadata (10,000 quota units/day)
- youtube-transcript-api: Get video transcripts (no API key needed)
- Direct scraping: Fallback for transcript extraction

Usage:
    from skills.youtube_parser import YouTubeStockParser
    
    parser = YouTubeStockParser()
    
    # Get recent stock picks from a channel
    picks = parser.get_channel_picks("ZipTrader", max_videos=10)
    
    # Get picks from multiple channels
    all_picks = parser.get_all_channel_picks({
        "ZipTrader": "UC...channel_id...",
        "Tom Nash": "UC...channel_id...",
    })
    
    # Extract tickers from a specific video
    tickers = parser.extract_tickers_from_video("video_id")
"""

import re
import json
import datetime
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
YOUTUBE_DATA_FILE = BASE_DIR / "docs" / "youtube_watchlist.json"

# Common stock ticker pattern: 1-5 uppercase letters, often preceded by $
# Excludes common words that happen to be uppercase
TICKER_PATTERN = re.compile(r'\$([A-Z]{1,5})\b|\b([A-Z]{2,5})\b')

# Words that look like tickers but aren't
FALSE_POSITIVES = {
    'A', 'I', 'IT', 'BE', 'DO', 'GO', 'NO', 'ON', 'OR', 'SO', 'TO', 'UP', 'US', 'WE',
    'ALL', 'AND', 'ARE', 'BUT', 'CAN', 'DAY', 'DID', 'FOR', 'GET', 'HAD', 'HAS', 'HER',
    'HIM', 'HIS', 'HOW', 'ITS', 'LET', 'MAN', 'NEW', 'NOT', 'NOW', 'OLD', 'ONE', 'OUR',
    'OUT', 'OWN', 'PUT', 'SAY', 'SHE', 'THE', 'TOO', 'TOP', 'TRY', 'TWO', 'USE', 'WAY',
    'WHO', 'YES', 'YET', 'YOU', 'CEO', 'CFO', 'COO', 'EPS', 'ETF', 'IPO', 'ROI', 'RSI',
    'MACD', 'P/E', 'GDP', 'CPI', 'FED', 'SEC', 'FDA', 'USA', 'NYSE', 'NASDAQ', 'SPY',
    'QQQ', 'IWM', 'DIA', 'VTI', 'VOO', 'ARKK', 'BITCOIN', 'BTC', 'ETH', 'AI', 'EDIT',
    'HTML', 'HTTP', 'HTTPS', 'URL', 'API', 'SQL', 'CSS', 'XML', 'JSON', 'CSV', 'PDF',
    'USA', 'UK', 'EU', 'JP', 'CN', 'IN', 'BR', 'MX', 'CA', 'DE', 'FR', 'KR', 'TW',
    'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN', 'JAN', 'FEB', 'MAR', 'APR', 'MAY',
    'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC', 'AM', 'PM', 'EST', 'PST', 'CST',
    'MST', 'UTC', 'GMT', 'EST', 'EDT', 'BUY', 'SELL', 'HOLD', 'LONG', 'SHORT', 'CALL',
    'PUT', 'BULL', 'BEAR', 'HIGH', 'LOW', 'OPEN', 'CLOSE', 'EARN', 'FREE', 'BEST',
    'EVER', 'JUST', 'LIKE', 'LOOK', 'MAKE', 'MUCH', 'NEED', 'NEXT', 'ONLY', 'OVER',
    'REAL', 'SHOW', 'THAN', 'THEM', 'THEN', 'THEY', 'THIS', 'VERY', 'WANT', 'WELL',
    'WHAT', 'WHEN', 'WILL', 'WITH', 'WORK', 'YEAR', 'ALSO', 'BACK', 'BEEN', 'BEFORE',
    'BETWEEN', 'BOTH', 'COME', 'COULD', 'DURING', 'EACH', 'EARLY', 'EVEN', 'FIRST',
    'FROM', 'GIVE', 'GOOD', 'GREAT', 'GROUP', 'HELP', 'HERE', 'HOME', 'INTO', 'JUST',
    'KNOW', 'LARGE', 'LAST', 'LATE', 'LESS', 'LIFE', 'LINE', 'LITTLE', 'LONG', 'MANY',
    'MIGHT', 'MORE', 'MOST', 'MUCH', 'MUST', 'NAME', 'NEAR', 'NEVER', 'NUMBER', 'OFF',
    'OFTEN', 'OTHER', 'PART', 'PEOPLE', 'PLACE', 'POINT', 'RIGHT', 'RUN', 'SAME',
    'SHOULD', 'SINCE', 'SMALL', 'SOME', 'STILL', 'SUCH', 'TAKE', 'THAN', 'THAT', 'THEIR',
    'THERE', 'THESE', 'THINK', 'THOSE', 'THOUGH', 'THREE', 'THROUGH', 'TIME', 'UNDER',
    'UNTIL', 'WATER', 'WHERE', 'WHICH', 'WHILE', 'WORLD', 'WOULD', 'WRITE',
}


class YouTubeStockParser:
    """Parse YouTube channels for stock ticker recommendations."""
    
    # Known channel handles/IDs (update with actual IDs)
    KNOWN_CHANNELS = {
        "ZipTrader": None,  # Will be resolved via search
        "Tom Nash": None,
        "Patrick Boyle": None,
    }
    
    def __init__(self, api_key=None):
        load_dotenv(override=False)
        self.api_key = api_key or __import__('os').environ.get("YOUTUBE_API_KEY", "")
        self._youtube = None
        if self.api_key:
            try:
                from googleapiclient.discovery import build
                self._youtube = build("youtube", "v3", developerKey=self.api_key)
            except Exception:
                pass
    
    def _extract_tickers(self, text):
        """Extract stock tickers from text, filtering false positives."""
        if not text:
            return []
        
        matches = TICKER_PATTERN.findall(text)
        tickers = set()
        for m in matches:
            ticker = m[0] or m[1]  # $TICKER or TICKER
            if ticker and ticker not in FALSE_POSITIVES and len(ticker) >= 1:
                tickers.add(ticker)
        return sorted(tickers)
    
    def get_channel_videos_api(self, channel_id, max_results=10):
        """Get recent videos from a channel using YouTube Data API v3."""
        if not self._youtube:
            return []
        
        try:
            # Use search.list (costs 100 quota units)
            request = self._youtube.search().list(
                part="snippet",
                channelId=channel_id,
                maxResults=max_results,
                order="date",
                type="video",
            )
            response = request.execute()
            
            videos = []
            for item in response.get("items", []):
                videos.append({
                    "video_id": item["id"]["videoId"],
                    "title": item["snippet"]["title"],
                    "description": item["snippet"]["description"],
                    "published_at": item["snippet"]["publishedAt"],
                })
            return videos
        except Exception:
            return []
    
    def get_channel_videos_scrape(self, channel_handle, max_results=10):
        """Get recent videos by scraping YouTube (no API key needed)."""
        try:
            import requests
            url = f"https://www.youtube.com/@{channel_handle}/videos"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            }
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                return []
            
            # Extract video IDs from page HTML
            video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', r.text)
            # Deduplicate while preserving order
            seen = set()
            unique_ids = []
            for vid in video_ids:
                if vid not in seen:
                    seen.add(vid)
                    unique_ids.append(vid)
                if len(unique_ids) >= max_results:
                    break
            
            # Get video details for each
            videos = []
            for vid in unique_ids:
                title = self._get_video_title(vid)
                videos.append({
                    "video_id": vid,
                    "title": title or "",
                    "description": "",
                    "published_at": "",
                })
            return videos
        except Exception:
            return []
    
    def _get_video_title(self, video_id):
        """Get video title from YouTube page."""
        try:
            import requests
            url = f"https://www.youtube.com/watch?v={video_id}"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
                "Accept-Language": "en-US,en;q=0.9",
            }
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                # Extract title from HTML
                title_match = re.search(r'<title>([^<]+)</title>', r.text)
                if title_match:
                    title = title_match.group(1).replace(" - YouTube", "").strip()
                    return title
        except Exception:
            pass
        return ""
    
    def get_transcript(self, video_id):
        """Get video transcript using youtube-transcript-api."""
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            ytt_api = YouTubeTranscriptApi()
            transcript_list = ytt_api.list(video_id)
            
            try:
                transcript = transcript_list.find_manually_created_transcript(['en'])
            except Exception:
                transcript = transcript_list.find_generated_transcript(['en'])
            
            fetched = transcript.fetch()
            return " ".join(snippet.text for snippet in fetched)
        except Exception:
            return ""
    
    def extract_tickers_from_video(self, video_id, title="", description="", include_transcript=True):
        """
        Extract stock tickers from a video's title, description, and optionally transcript.
        Returns list of (ticker, context) tuples.
        """
        tickers_found = {}
        
        # Extract from title (highest confidence)
        title_tickers = self._extract_tickers(title)
        for t in title_tickers:
            tickers_found[t] = {"source": "title", "confidence": "high"}
        
        # Extract from description
        desc_tickers = self._extract_tickers(description)
        for t in desc_tickers:
            if t not in tickers_found:
                tickers_found[t] = {"source": "description", "confidence": "medium"}
        
        # Extract from transcript (most comprehensive)
        if include_transcript:
            transcript = self.get_transcript(video_id)
            if transcript:
                trans_tickers = self._extract_tickers(transcript)
                for t in trans_tickers:
                    if t not in tickers_found:
                        tickers_found[t] = {"source": "transcript", "confidence": "medium"}
        
        return tickers_found
    
    def get_channel_picks(self, channel_name, channel_id=None, max_videos=10, include_transcripts=False):
        """
        Get stock picks from a YouTube channel.
        
        Returns list of dicts with video info and extracted tickers.
        """
        videos = []
        
        # Try API first, fall back to scraping
        if channel_id and self._youtube:
            videos = self.get_channel_videos_api(channel_id, max_videos)
        
        if not videos:
            videos = self.get_channel_videos_scrape(channel_name, max_videos)
        
        results = []
        for video in videos:
            tickers = self.extract_tickers_from_video(
                video["video_id"],
                title=video.get("title", ""),
                description=video.get("description", ""),
                include_transcript=include_transcripts,
            )
            
            # Filter out common false positives and index ETFs
            filtered = {t: info for t, info in tickers.items()
                       if t not in FALSE_POSITIVES and len(t) >= 1}
            
            if filtered:
                results.append({
                    "channel": channel_name,
                    "video_id": video["video_id"],
                    "title": video.get("title", ""),
                    "url": f"https://www.youtube.com/watch?v={video['video_id']}",
                    "published_at": video.get("published_at", ""),
                    "tickers": filtered,
                    "ticker_list": list(filtered.keys()),
                })
        
        return results
    
    def get_all_channel_picks(self, channels, max_videos=5, include_transcripts=False):
        """
        Get stock picks from multiple channels.
        
        Args:
            channels: Dict of {channel_name: channel_id_or_None}
            max_videos: Max videos per channel
            include_transcripts: Whether to fetch transcripts (slower but more thorough)
        
        Returns:
            Dict with aggregated results and consensus tickers
        """
        all_results = []
        ticker_channels = {}  # ticker -> list of channels mentioning it
        
        for name, channel_id in channels.items():
            try:
                picks = self.get_channel_picks(name, channel_id, max_videos, include_transcripts)
                all_results.extend(picks)
                
                for pick in picks:
                    for ticker in pick.get("ticker_list", []):
                        if ticker not in ticker_channels:
                            ticker_channels[ticker] = []
                        ticker_channels[ticker].append(name)
            except Exception:
                continue
        
        # Find consensus tickers (mentioned by multiple channels)
        consensus = {t: channels for t, channels in ticker_channels.items() if len(channels) >= 2}
        
        return {
            "results": all_results,
            "ticker_channels": ticker_channels,
            "consensus_tickers": consensus,
            "timestamp": datetime.datetime.now().isoformat(),
        }
    
    def save_watchlist(self, picks_data, path=None):
        """Save extracted picks to JSON file."""
        path = path or YOUTUBE_DATA_FILE
        path.parent.mkdir(parents=True, exist_ok=True)
        
        existing = {}
        if path.exists():
            try:
                existing = json.loads(path.read_text())
            except Exception:
                pass
        
        existing[picks_data.get("timestamp", "")] = picks_data
        path.write_text(json.dumps(existing, indent=2, default=str))
    
    def load_watchlist(self, path=None):
        """Load previously saved picks."""
        path = path or YOUTUBE_DATA_FILE
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                pass
        return {}


# Module-level convenience functions
def get_youtube_picks(channels=None, max_videos=5):
    """Quick function to get YouTube stock picks."""
    if channels is None:
        channels = {
            "ZipTrader": None,
            "Tom Nash": None,
        }
    
    parser = YouTubeStockParser()
    results = parser.get_all_channel_picks(channels, max_videos=max_videos)
    parser.save_watchlist(results)
    return results
