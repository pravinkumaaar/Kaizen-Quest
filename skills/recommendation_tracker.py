"""
Recommendation Tracker Skill

Manages investment recommendations:
- Parse and store high-conviction ideas
- Track performance (P&L)
- Update prices automatically
- Clear/reset recommendations
"""

import sys
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

def parse_and_store_recommendations(investments_text: str, model_used: str = "unknown"):
    """Parse investment ideas and store high-conviction ones (8+/10) in RECOMMENDATIONS.md"""
    trackable = []
    # Flexible regex to match various LLM output formats:
    # ### [1] TICKER — Thesis or ### [1] **TICKER (Company)** — Thesis
    pattern = r'### \[\d+\]\s*(?:\*\*)?([A-Z]{1,5})(?:\s*\([^)]*\))?(?:\*\*)?\s*[—–\-]\s*.*?\n\n(.*?)(?=(?:### \[|\Z))'

    matches = list(re.finditer(pattern, investments_text, re.DOTALL))

    for match in matches:
        ticker = match.group(1).strip().upper()
        content = match.group(2)

        # Skip invalid tickers - strict validation
        if not ticker or len(ticker) < 1 or len(ticker) > 5:
            continue
        if ticker in ['ASSET', 'TYPE', 'LEAPS', 'STOCK', 'ETF', 'CRYPTO', 'SELL', 'BUY', 'HOLD', 'THE', 'AND', 'FOR', 'YOU', 'WITH', 'THIS', 'THAT']:
            continue
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
            r'\*\*Type/Price:\*\*\s*[\w\s]+\s*@\s*\$?([\d,.]+)',
            r'@\s*\$?([\d,.]+)',
            r'\*\*Current Price:\*\*\s*\$?([\d,.]+)',
            r'Price:\s*\$?([\d,.]+)',
        ]:
            price_match = re.search(price_pattern, content)
            if price_match:
                current_price = price_match.group(1).replace(',', '')
                break

        # Extract target price
        target_price = 'N/A'
        for target_pattern in [
            r'\*\*Entry/Target:\*\*\s*\$?[\d,.]+\s*→\s*\$?([\d,.]+)',
            r'Target:\s*\$?([\d,.]+)',
            r'→\s*\$?([\d,.]+)',
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
                "<!-- Agent will update this section with current recommendations -->",
                f"{new_entries}\n<!-- Agent will update this section with current recommendations -->"
            )
        else:
            updated = existing + f"\n\n## Active Recommendations\n{new_entries}\n<!-- Agent will update this section with current recommendations -->\n"

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
