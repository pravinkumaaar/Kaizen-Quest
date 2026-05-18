"""
YouTube Stock Recommendation Parser v1.0

Parses YouTube channels (ZipTrader, Tom Nash, etc.) to extract stock ticker
recommendations from video titles, descriptions, and transcripts.

Features:
- Tracks already-reviewed videos to avoid reprocessing
- Age-based confidence decay (older videos = less relevant)
- Consensus detection across channels
- False positive filtering
- Both API and scraping fallbacks

Setup:
    1. Go to https://console.cloud.google.com/
    2. Create a new project (or select existing)
    3. Enable "YouTube Data API v3" in APIs & Services -> Library
    4. Create an API key in APIs & Services -> Credentials
    5. Set environment variable: export YOUTUBE_API_KEY="your-key-here"
    
    Without API key, the parser falls back to web scraping (slower but works).

Usage:
    from skills.youtube_parser import YouTubeStockParser
    
    parser = YouTubeStockParser()
    picks = parser.get_channel_picks("ZipTrader", max_videos=10)
    all_picks = parser.get_all_channel_picks({"ZipTrader": None, "Tom Nash": None})
"""

import re
import json
import datetime
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
YOUTUBE_DATA_FILE = BASE_DIR / "docs" / "youtube_watchlist.json"
YOUTUBE_REVIEWED_FILE = BASE_DIR / "docs" / "youtube_reviewed.json"

TICKER_PATTERN = re.compile(r'\$([A-Z]{1,5})\b|\b([A-Z]{2,5})\b')

FALSE_POSITIVES = {
    'A', 'I', 'IT', 'BE', 'DO', 'GO', 'NO', 'ON', 'OR', 'SO', 'TO', 'UP', 'US', 'WE',
    'ALL', 'AND', 'ARE', 'BUT', 'CAN', 'DAY', 'DID', 'FOR', 'GET', 'HAD', 'HAS', 'HER',
    'HIM', 'HIS', 'HOW', 'ITS', 'LET', 'MAN', 'NEW', 'NOT', 'NOW', 'OLD', 'ONE', 'OUR',
    'OUT', 'OWN', 'PUT', 'SAY', 'SHE', 'THE', 'TOO', 'TOP', 'TRY', 'TWO', 'USE', 'WAY',
    'WHO', 'YES', 'YET', 'YOU', 'CEO', 'CFO', 'COO', 'EPS', 'ETF', 'IPO', 'ROI', 'RSI',
    'MACD', 'GDP', 'CPI', 'FED', 'SEC', 'FDA', 'USA', 'NYSE', 'NASDAQ', 'SPY', 'QQQ',
    'IWM', 'DIA', 'VTI', 'VOO', 'ARKK', 'BTC', 'ETH', 'AI', 'EDIT', 'HTML', 'HTTP',
    'HTTPS', 'URL', 'API', 'SQL', 'CSS', 'XML', 'JSON', 'CSV', 'PDF', 'UK', 'EU', 'JP',
    'CN', 'IN', 'BR', 'MX', 'CA', 'DE', 'FR', 'KR', 'TW', 'MON', 'TUE', 'WED', 'THU',
    'FRI', 'SAT', 'SUN', 'JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP',
    'OCT', 'NOV', 'DEC', 'AM', 'PM', 'EST', 'PST', 'CST', 'MST', 'UTC', 'GMT', 'EDT',
    'BUY', 'SELL', 'HOLD', 'LONG', 'SHORT', 'CALL', 'PUT', 'BULL', 'BEAR', 'HIGH',
    'LOW', 'OPEN', 'CLOSE', 'EARN', 'FREE', 'BEST', 'EVER', 'JUST', 'LIKE', 'LOOK',
    'MAKE', 'MUCH', 'NEED', 'NEXT', 'ONLY', 'OVER', 'REAL', 'SHOW', 'THAN', 'THEM',
    'THEN', 'THEY', 'THIS', 'VERY', 'WANT', 'WELL', 'WHAT', 'WHEN', 'WILL', 'WITH',
    'WORK', 'YEAR', 'ALSO', 'BACK', 'BEEN', 'BEFORE', 'BETWEEN', 'BOTH', 'COME',
    'COULD', 'DURING', 'EACH', 'EARLY', 'EVEN', 'FIRST', 'FROM', 'GIVE', 'GOOD',
    'GREAT', 'GROUP', 'HELP', 'HERE', 'HOME', 'INTO', 'KNOW', 'LARGE', 'LAST', 'LATE',
    'LESS', 'LIFE', 'LINE', 'LITTLE', 'LONG', 'MANY', 'MIGHT', 'MORE', 'MOST', 'MUST',
    'NAME', 'NEAR', 'NEVER', 'NUMBER', 'OFF', 'OFTEN', 'OTHER', 'PART', 'PEOPLE',
    'PLACE', 'POINT', 'RIGHT', 'RUN', 'SAME', 'SHOULD', 'SINCE', 'SMALL', 'SOME',
    'STILL', 'SUCH', 'TAKE', 'THAT', 'THEIR', 'THERE', 'THESE', 'THINK', 'THOSE',
    'THOUGH', 'THREE', 'THROUGH', 'TIME', 'UNDER', 'UNTIL', 'WATER', 'WHERE', 'WHICH',
    'WHILE', 'WORLD', 'WOULD', 'WRITE', 'VERY',
}

# Video age decay: confidence multiplier based on video age
VIDEO_AGE_DECAY = {
    1: 1.0, 3: 0.95, 7: 0.85, 14: 0.70, 30: 0.50, 60: 0.30, 90: 0.15, 180: 0.05,
}


def _get_age_confidence(published_at_str):
    """Get confidence multiplier based on video age."""
    if not published_at_str:
        return 0.5
    try:
        pub_date = datetime.datetime.fromisoformat(published_at_str.replace('Z', '+00:00'))
        now = datetime.datetime.now(datetime.timezone.utc)
        age_days = (now - pub_date).days
        thresholds = sorted(VIDEO_AGE_DECAY.keys())
        for threshold in thresholds:
            if age_days <= threshold:
                return VIDEO_AGE_DECAY[threshold]
        return VIDEO_AGE_DECAY[thresholds[-1]]
    except Exception:
        return 0.5


class YouTubeStockParser:
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
        self._load_reviewed()
    
    def _load_reviewed(self):
        self.reviewed = {}
        if YOUTUBE_REVIEWED_FILE.exists():
            try:
                self.reviewed = json.loads(YOUTUBE_REVIEWED_FILE.read_text())
            except Exception:
                self.reviewed = {}
    
    def _save_reviewed(self):
        YOUTUBE_REVIEWED_FILE.parent.mkdir(parents=True, exist_ok=True)
        YOUTUBE_REVIEWED_FILE.write_text(json.dumps(self.reviewed, indent=2, default=str))
    
    def is_video_reviewed(self, video_id):
        return video_id in self.reviewed
    
    def mark_video_reviewed(self, video_id, channel, tickers_found=None, title=""):
        self.reviewed[video_id] = {
            "channel": channel, "title": title,
            "reviewed_at": datetime.datetime.now().isoformat(),
            "tickers_found": tickers_found or [],
        }
    
    def get_unreviewed_videos(self, videos, channel_name):
        return [v for v in videos if v.get("video_id") and not self.is_video_reviewed(v["video_id"])]
    
    def get_reviewed_stats(self):
        total = len(self.reviewed)
        channels = {}
        for vid, data in self.reviewed.items():
            ch = data.get("channel", "unknown")
            channels[ch] = channels.get(ch, 0) + 1
        return {"total_reviewed": total, "by_channel": channels}
    
    def _extract_tickers(self, text):
        if not text:
            return []
        matches = TICKER_PATTERN.findall(text)
        tickers = set()
        for m in matches:
            ticker = m[0] or m[1]
            if ticker and ticker not in FALSE_POSITIVES and len(ticker) >= 1:
                tickers.add(ticker)
        return sorted(tickers)
    
    def get_channel_videos_api(self, channel_id, max_results=10):
        if not self._youtube:
            return []
        try:
            request = self._youtube.search().list(
                part="snippet", channelId=channel_id,
                maxResults=max_results, order="date", type="video",
            )
            response = request.execute()
            return [{
                "video_id": item["id"]["videoId"],
                "title": item["snippet"]["title"],
                "description": item["snippet"]["description"],
                "published_at": item["snippet"]["publishedAt"],
            } for item in response.get("items", [])]
        except Exception:
            return []
    
    def get_channel_videos_scrape(self, channel_handle, max_results=10):
        """Scrape videos from a YouTube channel page, extracting titles from page HTML."""
        try:
            import requests
            url = f"https://www.youtube.com/@{channel_handle}/videos"
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code != 200:
                return []
            
            # Extract video IDs and titles from the page HTML
            # YouTube embeds video data in a JSON structure within the page
            videos = []
            
            # Try to find videoRenderer objects in the page source
            # Pattern: "videoId":"XXXXX","title":{"runs":[{"text":"TITLE"}]}
            video_patterns = re.findall(
                r'"videoId":"([a-zA-Z0-9_-]{11})".*?"title":\{"runs":\[\{"text":"([^"]+)"\}\]',
                r.text
            )
            
            seen = set()
            for vid, title in video_patterns:
                if vid not in seen and len(videos) < max_results:
                    seen.add(vid)
                    # Also try to extract published time
                    pub_match = re.search(
                        r'"videoId":"' + re.escape(vid) + r'".*?"publishedTimeText":\{"simpleText":"([^"]+)"\}',
                        r.text
                    )
                    published = pub_match.group(1) if pub_match else ""
                    videos.append({
                        "video_id": vid,
                        "title": title,
                        "description": "",
                        "published_at": published,
                    })
            
            # Fallback: if no titles found, just get video IDs
            if not videos:
                video_ids = re.findall(r'"videoId":"([a-zA-Z0-9_-]{11})"', r.text)
                seen = set()
                for vid in video_ids:
                    if vid not in seen and len(videos) < max_results:
                        seen.add(vid)
                        videos.append({
                            "video_id": vid,
                            "title": "",
                            "description": "",
                            "published_at": "",
                        })
            
            return videos
        except Exception:
            return []
    
    def _get_video_title(self, video_id):
        """Get video title from YouTube page or oembed API."""
        try:
            # Try oembed API first (lightweight, no JS required)
            import requests
            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            r = requests.get(oembed_url, timeout=10)
            if r.status_code == 200:
                import json
                data = json.loads(r.text)
                return data.get("title", "")
        except Exception:
            pass
        
        # Fallback: scrape the video page
        try:
            import requests
            r = requests.get(
                f"https://www.youtube.com/watch?v={video_id}",
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
                timeout=10
            )
            if r.status_code == 200:
                # Try multiple patterns
                for pattern in [r'<title>([^<]+)</title>', r'"title":"([^"]+)"']:
                    m = re.search(pattern, r.text)
                    if m:
                        title = m.group(1).replace(" - YouTube", "").strip()
                        if title:
                            return title
        except Exception:
            pass
        return ""
    
    def get_transcript(self, video_id):
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            ytt_api = YouTubeTranscriptApi()
            transcript_list = ytt_api.list(video_id)
            try:
                transcript = transcript_list.find_manually_created_transcript(['en'])
            except Exception:
                transcript = transcript_list.find_generated_transcript(['en'])
            return " ".join(snippet.text for snippet in transcript.fetch())
        except Exception:
            return ""
    
    def extract_tickers_from_video(self, video_id, title="", description="", include_transcript=True):
        tickers_found = {}
        for t in self._extract_tickers(title):
            tickers_found[t] = {"source": "title", "confidence": "high"}
        for t in self._extract_tickers(description):
            if t not in tickers_found:
                tickers_found[t] = {"source": "description", "confidence": "medium"}
        if include_transcript:
            transcript = self.get_transcript(video_id)
            if transcript:
                for t in self._extract_tickers(transcript):
                    if t not in tickers_found:
                        tickers_found[t] = {"source": "transcript", "confidence": "medium"}
        return tickers_found
    
    def get_channel_picks(self, channel_name, channel_id=None, max_videos=10, include_transcripts=False, skip_reviewed=True):
        videos = []
        if channel_id and self._youtube:
            videos = self.get_channel_videos_api(channel_id, max_videos)
        if not videos:
            videos = self.get_channel_videos_scrape(channel_name, max_videos)
        if skip_reviewed:
            videos = self.get_unreviewed_videos(videos, channel_name)
        
        results = []
        for video in videos:
            tickers = self.extract_tickers_from_video(video["video_id"], title=video.get("title", ""), description=video.get("description", ""), include_transcript=include_transcripts)
            filtered = {t: info for t, info in tickers.items() if t not in FALSE_POSITIVES and len(t) >= 1}
            age_confidence = _get_age_confidence(video.get("published_at", ""))
            self.mark_video_reviewed(video["video_id"], channel_name, tickers_found=list(filtered.keys()), title=video.get("title", ""))
            if filtered:
                results.append({
                    "channel": channel_name, "video_id": video["video_id"],
                    "title": video.get("title", ""),
                    "url": f"https://www.youtube.com/watch?v={video['video_id']}",
                    "published_at": video.get("published_at", ""),
                    "age_confidence": age_confidence,
                    "tickers": filtered, "ticker_list": list(filtered.keys()),
                })
        self._save_reviewed()
        return results
    
    def get_all_channel_picks(self, channels, max_videos=5, include_transcripts=False):
        all_results, ticker_channels, ticker_age = [], {}, {}
        for name, channel_id in channels.items():
            try:
                picks = self.get_channel_picks(name, channel_id, max_videos, include_transcripts)
                all_results.extend(picks)
                for pick in picks:
                    for ticker in pick.get("ticker_list", []):
                        if ticker not in ticker_channels:
                            ticker_channels[ticker] = []
                        ticker_channels[ticker].append(name)
                        age_conf = pick.get("age_confidence", 0.5)
                        if ticker not in ticker_age or age_conf > ticker_age[ticker]:
                            ticker_age[ticker] = age_conf
            except Exception:
                continue
        consensus = {t: chs for t, chs in ticker_channels.items() if len(chs) >= 2}
        return {"results": all_results, "ticker_channels": ticker_channels, "ticker_age_confidence": ticker_age, "consensus_tickers": consensus, "timestamp": datetime.datetime.now().isoformat()}
    
    def save_watchlist(self, picks_data, path=None):
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
        path = path or YOUTUBE_DATA_FILE
        if path.exists():
            try:
                return json.loads(path.read_text())
            except Exception:
                pass
        return {}


def get_youtube_picks(channels=None, max_videos=5):
    if channels is None:
        channels = {"ZipTrader": None, "Tom Nash": None}
    parser = YouTubeStockParser()
    results = parser.get_all_channel_picks(channels, max_videos=max_videos)
    parser.save_watchlist(results)
    return results
