"""
Recommendation Tracker & Decision Journal Skill v2.0

CONSOLIDATED: This module now handles BOTH recommendation tracking AND the decision journal.
Previously these were split across agent.py and this file, causing duplication and confusion.

Manages investment recommendations:
- Parse and store high-conviction ideas with conviction scores
- Track performance (P&L) using LIVE prices
- Update prices automatically
- Maintain decision journal with full history
- Link active recommendations to decision journal entries
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
DECISION_JOURNAL_FILE = None
FINNHUB_API_KEY = None

def init_tracker_skill(base_dir=None, finnhub_key=None):
    """Initialize with config from main agent."""
    global BASE_DIR, RECOMMENDATIONS_FILE, DECISION_JOURNAL_FILE, FINNHUB_API_KEY
    if base_dir:
        BASE_DIR = Path(base_dir)
        RECOMMENDATIONS_FILE = BASE_DIR / "docs" / "RECOMMENDATIONS.md"
        DECISION_JOURNAL_FILE = BASE_DIR / "docs" / "DECISION_JOURNAL.md"
    if finnhub_key:
        FINNHUB_API_KEY = finnhub_key


def _get_live_price(ticker):
    """Get current price using multiple fallback sources."""
    # Try yfinance fast_info first
    old_stderr = sys.stderr
    sys.stderr = StringIO()
    try:
        t = yf.Ticker(ticker)
        p = t.fast_info.last_price
        pc = t.fast_info.previous_close
        if p and p > 0:
            return float(p), float(pc) if pc and pc > 0 else None
    except Exception:
        pass
    finally:
        sys.stderr = old_stderr

    # Try yfinance info
    sys.stderr = StringIO()
    try:
        t = yf.Ticker(ticker)
        info = t.info
        p = info.get('postMarketPrice') or info.get('currentPrice') or info.get('regularMarketPrice')
        pc = info.get('regularMarketPreviousClose') or info.get('previousClose')
        if p and float(p) > 0:
            return float(p), float(pc) if pc and float(pc) > 0 else None
    except Exception:
        pass
    finally:
        sys.stderr = old_stderr

    return None, None


def clear_active_recommendations():
    """Reset RECOMMENDATIONS.md to clean state."""
    try:
        if RECOMMENDATIONS_FILE and RECOMMENDATIONS_FILE.exists():
            content = RECOMMENDATIONS_FILE.read_text(encoding="utf-8")
            if "## Active Recommendations" in content:
                parts = content.split("## Active Recommendations")
                new_content = parts[0] + "## Active Recommendations\n<!-- Agent will update this section with current recommendations -->\n"
            else:
                new_content = content + "\n\n## Active Recommendations\n<!-- Agent will update this section with current recommendations -->\n"
            RECOMMENDATIONS_FILE.write_text(new_content, encoding="utf-8")
    except Exception:
        pass


def parse_and_store_recommendations(investments_text, model_used="unknown"):
    """
    Parse investment ideas from LLM output and store high-conviction ones.
    
    Tracks recommendations with:
    - Conviction score (1-10)
    - Entry price (current market price, NOT cost basis)
    - Target price
    - Thesis summary
    - Status (Active/Target Hit/Stopped Out/Closed)
    
    Only tracks recommendations with conviction >= 7/10.
    """
    if not RECOMMENDATIONS_FILE:
        return []

    trackable = []

    # Match various LLM output formats
    # Format: ### [1] TICKER — Thesis or ### [1] **TICKER** — Thesis
    pattern = r'### \[\d+\]\s*(?:\*\*)?([A-Z][A-Z0-9.\-]{0,9})(?:\s*\([^)]*\))?(?:\*\*)?\s*[—–\-]\s*.*?\n(.*?)(?=(?:### \[|\Z))'

    matches = list(re.finditer(pattern, investments_text, re.DOTALL))

    for match in matches:
        ticker = match.group(1).strip().upper()
        content = match.group(2)

        # Skip invalid tickers
        if not ticker or len(ticker) > 10:
            continue
        skip_words = {'ASSET', 'TYPE', 'LEAPS', 'STOCK', 'ETF', 'CRYPTO', 'SELL', 'BUY', 'HOLD',
                      'THE', 'AND', 'FOR', 'YOU', 'WITH', 'THIS', 'THAT', 'CALL', 'PUT', 'LONG',
                      'SHORT', 'BULL', 'BEAR', 'HIGH', 'LOW', 'RISK', 'GAIN', 'LOSS'}
        if ticker in skip_words:
            continue

        # Extract conviction score — multiple patterns
        conviction = None
        for conv_pattern in [
            r'\*\*Conviction:\*\*\s*(\d+)',
            r'\*\*Conviction Score:\*\*\s*(\d+)',
            r'Conviction:\s*(\d+)/10',
            r'Conviction\s*(\d+)/10',
            r'(\d+)/10\s*conviction',
        ]:
            conv_match = re.search(conv_pattern, content, re.IGNORECASE)
            if conv_match:
                conviction = int(conv_match.group(1))
                break

        if conviction is None:
            conviction = 5  # Default if not found

        # Extract track indicator
        track_match = re.search(r'\*\*Track:\*\*\s*(Yes|No)', content, re.IGNORECASE)
        should_track = track_match and track_match.group(1).lower() == 'yes' if track_match else False

        # Extract current price — look for the LIVE price, not cost basis
        current_price = None
        for price_pattern in [
            r'\*\*Type/Price:\*\*\s*[\w\s]+\s*@\s*\$?([\d,.]+)',
            r'@\s*\$?([\d,.]+)',
            r'\*\*Current Price:\*\*\s*\$?([\d,.]+)',
            r'Entry Price:\s*\$?([\d,.]+)',
        ]:
            price_match = re.search(price_pattern, content)
            if price_match:
                try:
                    current_price = float(price_match.group(1).replace(',', ''))
                except ValueError:
                    pass
                break

        # If no price found in text, fetch it live
        if current_price is None:
            live_price, _ = _get_live_price(ticker)
            if live_price:
                current_price = live_price

        # Extract target price
        target_price = None
        for target_pattern in [
            r'\*\*Entry/Target:\*\*\s*\$?[\d,.]+\s*→\s*\$?([\d,.]+)',
            r'Target(?:\s*Price)?:\s*\$?([\d,.]+)',
            r'→\s*\$?([\d,.]+)',
            r'Target:\s*\$?([\d,.]+)',
        ]:
            target_match = re.search(target_pattern, content)
            if target_match:
                try:
                    target_price = float(target_match.group(1).replace(',', ''))
                except ValueError:
                    pass
                break

        # Extract stop loss
        stop_loss = None
        stop_match = re.search(r'Stop(?:\s*Loss)?:\s*\$?([\d,.]+)', content)
        if stop_match:
            try:
                stop_loss = float(stop_match.group(1).replace(',', ''))
            except ValueError:
                pass

        # Extract horizon
        horizon = 'Swing'
        horizon_match = re.search(r'\*\*Horizon:\*\*\s*(.+?)(?:\n|$)', content)
        if horizon_match:
            horizon = horizon_match.group(1).strip()

        # Extract thesis (first sentence after ticker)
        thesis = ''
        thesis_lines = content.strip().split('\n')
        for line in thesis_lines[:3]:
            line = line.strip().replace('**', '')
            if line and not line.startswith('Type/Price') and not line.startswith('Conviction'):
                thesis = line[:150]
                break

        # Track if conviction >= 7 or explicitly marked
        if should_track or conviction >= 7:
            # Calculate initial performance (will be 0.0 for same-day, but update_performance will fix it next run)
            trackable.append({
                'date': datetime.now().date().isoformat(),
                'ticker': ticker,
                'entry_price': current_price,
                'target_price': target_price,
                'stop_loss': stop_loss,
                'conviction': conviction,
                'thesis': thesis,
                'horizon': horizon,
                'status': 'Active',
                'current_price': current_price,
                'performance_pct': 0.0,
                'model': model_used
            })

    if trackable:
        # Update RECOMMENDATIONS.md with proper column headers
        existing = ""
        if RECOMMENDATIONS_FILE.exists():
            existing = RECOMMENDATIONS_FILE.read_text(encoding="utf-8")

        # Build entries with proper formatting
        header = ("| # | Ticker | Entry | Target | Conviction | Status | Current | P&L | Horizon | Source |"
                  "\n|---|--------|-------|--------|------------|--------|---------|-----|---------|--------|")
        
        rows = []
        for i, r in enumerate(trackable, 1):
            entry = f"${r['entry_price']:.2f}" if r.get('entry_price') else "Market"
            target = f"${r['target_price']:.2f}" if r.get('target_price') else "TBD"
            current = f"${r['current_price']:.2f}" if r.get('current_price') else "Fetching..."
            perf = f"{r.get('performance_pct', 0):+.1f}%"
            source = r.get('source', 'Watchlist')
            rows.append(
                f"| {i} | **{r['ticker']}** | {entry} | {target} | {r['conviction']}/10 | "
                f"{r['status']} | {current} | {perf} | {r.get('horizon', 'Medium')} | {source} |"
            )
        
        new_entries = header + "\n" + "\n".join(rows)

        # Also add Alpaca holdings section
        alpaca_section = ""
        try:
            from skills.alpaca_trading import get_account_info, get_all_positions_including_options
            acct = get_account_info()
            if "error" not in acct:
                positions = get_all_positions_including_options()
                if positions:
                    alpaca_header = ("\n\n## 🏦 Alpaca Paper Trading Holdings\n"
                                     "| Ticker | Qty | Avg Cost | Current | P&L |"
                                     "\n|--------|-----|----------|---------|-----|")
                    alpaca_rows = []
                    for pos in positions:
                        if pos.get('type') == 'stock':
                            _avg = float(pos.get('avg_entry', 0) or 0)
                            _qty = int(pos.get('qty', 0) or 0)
                            _cur = float(pos.get('current_price', 0) or 0)
                            _plpc = float(pos.get('unrealized_plpc', 0) or 0)
                            alpaca_rows.append(
                                f"| **{pos['symbol']}** | {_qty} | "
                                f"${_avg:.2f} | "
                                f"${_cur:.2f} | "
                                f"{_plpc:+.1f}% |"
                            )
                    if alpaca_rows:
                        alpaca_section = alpaca_header + "\n" + "\n".join(alpaca_rows)
        except Exception:
            pass

        full_content = f"# 📊 Recommendation Tracking & Decision Journal\n\n## 📋 Watchlist Recommendations\n{new_entries}{alpaca_section}\n"
        RECOMMENDATIONS_FILE.write_text(full_content, encoding="utf-8")

        # Also update DECISION_JOURNAL.md
        _update_decision_journal(trackable)

    return trackable


def _update_decision_journal(new_recommendations):
    """Add new recommendations to the decision journal."""
    if not DECISION_JOURNAL_FILE:
        return

    existing = ""
    if DECISION_JOURNAL_FILE.exists():
        existing = DECISION_JOURNAL_FILE.read_text(encoding="utf-8")

    journal_entries = "\n".join([
        (f"| {r['date']} | {r['ticker']} | BUY | "
         f"${r['entry_price']:.2f}" if r['entry_price'] else f"| {r['date']} | {r['ticker']} | BUY | N/A") +
        (f" | ${r['target_price']:.2f}" if r['target_price'] else " | N/A") +
        f" | {r['conviction']}/10 | {r['status']} | - | {r['thesis'][:80]} |"
        for r in new_recommendations
    ])

    if "## Decision Log" in existing:
        # Insert after the Decision Log header and table header
        lines = existing.split('\n')
        insert_idx = None
        for i, line in enumerate(lines):
            if line.startswith('| ---'):
                insert_idx = i + 1
                break
        if insert_idx is not None:
            lines.insert(insert_idx, journal_entries)
            updated = '\n'.join(lines)
        else:
            updated = existing + "\n" + journal_entries
    else:
        # Create the Decision Log section
        updated = existing + f"\n\n## Decision Log\n\n| Date | Ticker | Action | Entry | Target | Conviction | Status | Outcome | Notes |\n|------|--------|--------|-------|--------|------------|--------|---------|-------|\n{journal_entries}\n"

    DECISION_JOURNAL_FILE.write_text(updated, encoding="utf-8")


def update_recommendation_performance():
    """
    Update prices and performance of tracked recommendations using LIVE prices.
    Updates both RECOMMENDATIONS.md and DECISION_JOURNAL.md.
    """
    if not RECOMMENDATIONS_FILE or not RECOMMENDATIONS_FILE.exists():
        return

    existing = RECOMMENDATIONS_FILE.read_text(encoding="utf-8")
    lines = existing.split('\n')
    updated_lines = []
    changes_made = False

    for line in lines:
        # Handle both old format ("- date | ticker | ...") and new table format ("| # | Ticker | ...")
        is_old_format = line.startswith('- ') and ' | ' in line
        is_new_format = line.startswith('| ') and ' | ' in line and not line.startswith('| #') and not line.startswith('|---')
        
        if not (is_old_format or is_new_format):
            updated_lines.append(line)
            continue
        
        # Parse the line
        if is_old_format:
            parts = line[2:].split(' | ')
        else:
            parts = [p.strip() for p in line.split('|')[1:-1]]  # Skip empty first/last
        
        if len(parts) >= 7:
            try:
                # For old format: date, ticker, entry, target, conviction, status, current, perf
                # For new format: #, ticker, entry, target, conviction, status, current, perf, horizon, source
                if is_old_format:
                    date = parts[0].strip()
                    ticker = parts[1].strip()
                    entry_str = parts[2].strip()
                    target_str = parts[3].strip()
                    conviction = parts[4].strip()
                    status = parts[5].strip()
                    current_str = parts[6].strip()
                    perf = parts[7].strip() if len(parts) > 7 else "0%"
                else:
                    # New format: skip # (parts[0])
                    ticker = parts[1].strip().replace('**', '')
                    entry_str = parts[2].strip()
                    target_str = parts[3].strip()
                    conviction = parts[4].strip()
                    status = parts[5].strip()
                    current_str = parts[6].strip()
                    perf = parts[7].strip() if len(parts) > 7 else "0%"

                if status == 'Active':
                    # Get LIVE current price
                    live_price, _ = _get_live_price(ticker)

                    if live_price and entry_str.startswith('$'):
                        entry_price = float(entry_str[1:])
                        if entry_price > 0:
                            change_pct = ((live_price - entry_price) / entry_price) * 100
                            perf = f"{change_pct:+.1f}%"

                    if live_price:
                        current_str = f"${live_price:.2f}"

                    # Check if target hit
                    if target_str.startswith('$'):
                        target_price = float(target_str[1:])
                        if live_price and live_price >= target_price * 0.95:
                            status = 'Target Hit'
                            changes_made = True

                    # Reconstruct the line
                    if is_old_format:
                        line = f"- {date} | {ticker} | {entry_str} | {target_str} | {conviction} | {status} | {current_str} | {perf}"
                    else:
                        # Reconstruct table row preserving all columns
                        parts[5] = f" {status} "
                        parts[6] = f" {current_str} "
                        parts[7] = f" {perf} "
                        line = '| ' + ' | '.join(parts) + ' |'
                    
                    changes_made = True
            except Exception:
                pass

        updated_lines.append(line)

    updated_content = '\n'.join(updated_lines)
    RECOMMENDATIONS_FILE.write_text(updated_content, encoding="utf-8")

    # Also update decision journal with latest prices
    if changes_made:
        _sync_decision_journal_prices()


def _sync_decision_journal_prices():
    """Sync current prices and status to the decision journal."""
    if not DECISION_JOURNAL_FILE or not DECISION_JOURNAL_FILE.exists():
        return

    journal = DECISION_JOURNAL_FILE.read_text(encoding="utf-8")
    recs = RECOMMENDATIONS_FILE.read_text(encoding="utf-8") if RECOMMENDATIONS_FILE.exists() else ""

    # Build a map of ticker -> latest status/price from recommendations
    status_map = {}
    for line in recs.split('\n'):
        if line.startswith('- ') and ' | ' in line:
            parts = line[2:].split(' | ')
            if len(parts) >= 7:
                ticker = parts[1].strip()
                status = parts[5].strip()
                current = parts[6].strip()
                perf = parts[7].strip() if len(parts) > 7 else "-"
                status_map[ticker] = (status, current, perf)

    # Update journal entries
    lines = journal.split('\n')
    updated_lines = []
    for line in lines:
        if line.startswith('| ') and not line.startswith('| ---') and not line.startswith('| Date') and ' | ' in line:
            parts = line[2:].split(' | ')
            if len(parts) >= 7:
                ticker = parts[1].strip()
                if ticker in status_map:
                    status, current, perf = status_map[ticker]
                    parts[6] = f" {status} "
                    parts[7] = f" {perf} "
                    line = '|'.join(parts)
        updated_lines.append(line)

    DECISION_JOURNAL_FILE.write_text('\n'.join(updated_lines), encoding="utf-8")


def get_active_recommendations():
    """Return list of active recommendations."""
    if not RECOMMENDATIONS_FILE or not RECOMMENDATIONS_FILE.exists():
        return []

    content = RECOMMENDATIONS_FILE.read_text(encoding="utf-8")
    active = []
    in_active = False

    for line in content.split('\n'):
        if "## Active Recommendations" in line:
            in_active = True
            continue
        if in_active and line.startswith('- ') and ' | ' in line:
            parts = line[2:].split(' | ')
            if len(parts) >= 6 and parts[5].strip() == 'Active':
                active.append({
                    'date': parts[0].strip(),
                    'ticker': parts[1].strip(),
                    'entry': parts[2].strip(),
                    'target': parts[3].strip(),
                    'conviction': parts[4].strip(),
                    'status': parts[5].strip(),
                    'current': parts[6].strip() if len(parts) > 6 else 'N/A',
                    'performance': parts[7].strip() if len(parts) > 7 else '0%',
                })

    return active


__all__ = [
    'init_tracker_skill',
    'clear_active_recommendations',
    'parse_and_store_recommendations',
    'update_recommendation_performance',
    'get_active_recommendations',
]
