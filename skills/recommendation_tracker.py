"""
Recommendation Tracker Skill

Manages investment recommendations:
- Parse and store high-conviction ideas
- Track performance (P&L)
- Update prices automatically
- Clear/reset recommendations
"""

import re
import requests
import yfinance as yf
from io import StringIO
from pathlib import Path
from datetime import datetime

BASE_DIR = None
RECOMMENDATIONS_FILE = None
FINNHUB_API_KEY = None

def init_tracker_skill(base_dir=None, finnhub_key=None):
    """Initialize with config from main agent."""
    global BASE_DIR, RECOMMENDATIONS_FILE, FINNHUB_API_KEY
    if base_dir:
        BASE_DIR = Path(base_dir)
        RECOMMENDATIONS_FILE = BASE_DIR / "RECOMMENDATIONS.md"
    if finnhub_key:
        FINNHUB_API_KEY = finnhub_key

def clear_active_recommendations():
    """Reset RECOMMENDATIONS.md to clean state."""
    try:
        if RECOMMENDATIONS_FILE and RECOMMENDATIONS_FILE.exists():
            content = RECOMMENDATIONS_FILE.read_text(encoding="utf-8")
            if "## Active Recommendations" in content:
                parts = content.split("## Active Recommendations")
                new_content = parts[0] + "## Active Recommendations\n<!-- Agent will update this section with current recommendations -->\n"
            else:
                new_content = "## Active Recommendations\n<!-- Agent will update this section with current recommendations -->\n"
            RECOMMENDATIONS_FILE.write_text(new_content, encoding="utf-8")
    except Exception:
        pass

def parse_and_store_recommendations(investments_text: str):
    """Parse investment ideas and store high-conviction ones (9+/10)."""
    trackable = []
    pattern = r'### \[\d+\] Asset: ([\w\-]+)\s*[—–].*?\n\n(.*?)(?=(?:### \[|\Z))'
    
    matches = re.finditer(pattern, investments_text, re.DOTALL)
    
    for match in matches:
        ticker = match.group(1).strip()
        content = match.group(2)
        
        if not ticker or len(ticker) > 6 or not any(c.isupper() for c in ticker):
            continue
        
        # Extract details
        price_match = re.search(r'\*\*Current Price:\*\*\s*\$?([\d.]+)', content)
        target_match = re.search(r'\*\*Target:\*\*\s*\$?([\d.]+)', content)
        conviction_match = re.search(r'\*\*Conviction Score:\*\*\s*(\d+)', content)
        track_match = re.search(r'\*\*Track This:\*\*\s*(Yes|No)', content)
        
        if not conviction_match:
            conviction_match = re.search(r'(\d+)/10', content)
        
        current_price = price_match.group(1) if price_match else 'N/A'
        target_price = target_match.group(1) if target_match else 'N/A'
        conviction = conviction_match.group(1) if conviction_match else '5'
        should_track = track_match and track_match.group(1) == 'Yes'
        
        # Store only 9+/10 conviction or explicitly tracked
        if should_track or int(conviction) >= 9:
            trackable.append({
                'date': datetime.now().date().isoformat(),
                'ticker': ticker,
                'entry_price': current_price,
                'target': target_price,
                'conviction': conviction,
                'status': 'Active',
                'current_price': current_price,
                'performance': '0%'
            })
    
    if trackable and RECOMMENDATIONS_FILE:
        existing = RECOMMENDATIONS_FILE.read_text(encoding="utf-8") if RECOMMENDATIONS_FILE.exists() else ""
        new_entries = "\n".join([
            f"- {r['date']} | {r['ticker']} | ${r['entry_price']} | ${r['target']} | {r['conviction']}/10 | {r['status']} | ${r['current_price']} | {r['performance']}"
            for r in trackable
        ])
        
        if "## Active Recommendations" in existing:
            updated = existing.replace(
                "## Active Recommendations\n<!-- Agent will update this section with current recommendations -->",
                f"## Active Recommendations\n{new_entries}\n<!-- Agent will update this section with current recommendations -->"
            )
        else:
            updated = existing + f"\n## Active Recommendations\n{new_entries}"
        
        RECOMMENDATIONS_FILE.write_text(updated, encoding="utf-8")

def update_recommendation_performance():
    """Update prices and performance of tracked recommendations."""
    if not RECOMMENDATIONS_FILE or not RECOMMENDATIONS_FILE.exists():
        return
    
    existing = RECOMMENDATIONS_FILE.read_text(encoding="utf-8")
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
                        current_price = None
                        if FINNHUB_API_KEY and ticker.upper() not in ['BTC-USD', 'ETH-USD']:
                            try:
                                r = requests.get(
                                    f"https://finnhub.io/api/v1/quote?symbol={ticker}&token={FINNHUB_API_KEY}",
                                    timeout=10
                                )
                                data = r.json()
                                current_price = data.get("c", 0)
                            except Exception:
                                pass
                        
                        if current_price is None:
                            old_stderr = sys.stderr
                            sys.stderr = StringIO()
                            try:
                                t = yf.Ticker(ticker)
                                current_price = t.fast_info.last_price or 0
                            except Exception:
                                pass
                            finally:
                                sys.stderr = old_stderr
                        
                        if current_price and entry_str.startswith('$'):
                            entry_price = float(entry_str[1:])
                            if entry_price > 0:
                                change_pct = ((current_price - entry_price) / entry_price) * 100
                                perf = f"{change_pct:+.1f}%"
                        
                        current_str = f"${current_price:.2f}" if current_price else current_str
                        
                        # Check if target hit
                        if target_str.startswith('$'):
                            target_price = float(target_str[1:])
                            if current_price >= target_price * 0.95:
                                status = 'Target Hit'
                        
                        line = f"- {date} | {ticker} | {entry_str} | {target_str} | {conviction} | {status} | {current_str} | {perf}"
                    except Exception:
                        pass
        
        updated_lines.append(line)
    
    updated_content = '\n'.join(updated_lines)
    RECOMMENDATIONS_FILE.write_text(updated_content, encoding="utf-8")

__all__ = [
    'init_tracker_skill',
    'clear_active_recommendations',
    'parse_and_store_recommendations',
    'update_recommendation_performance'
]
