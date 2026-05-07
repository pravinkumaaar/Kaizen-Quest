"""
Telegram Bot Skill v2.0 - 100% Free

Runs locally or 24/7 on fly.io free tier.
LLM: free OpenRouter only. Falls to commands if unavailable.

FIXES in v2.0:
- Long messages are now SPLIT into multiple Telegram messages instead of truncated
- /price command reliability improved with better error handling
- /portfolio and /report send multi-part responses
- Added /earnings command for upcoming earnings
- Added /sectors command for sector overview
"""

import os, json, requests, time, re, sys
from pathlib import Path
BASE_DIR = Path(__file__).parent.parent
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
API = f"https://api.telegram.org/bot{TOKEN}"
CID_FILE = BASE_DIR / "cache" / "telegram_chat_ids.json"

# Telegram hard limit is 4096 characters per message
TELEGRAM_MAX_CHARS = 4000  # Leave some safety margin

def _ids():
    try:
        return json.loads(CID_FILE.read_text()).get("ids", []) if CID_FILE.exists() else []
    except:
        return []

def _save(c):
    ids = _ids()
    if c not in ids:
        ids.append(c)
        CID_FILE.parent.mkdir(exist_ok=True)
        CID_FILE.write_text(json.dumps({"ids": ids}))

def _send_raw(cid, txt):
    """Send a single message to a Telegram chat. Returns True on success."""
    if not TOKEN:
        return False
    try:
        r = requests.post(
            f"{API}/sendMessage",
            json={"chat_id": cid, "text": txt, "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=15
        )
        return r.ok
    except:
        return False

def send(cid, txt):
    """
    Send a message to Telegram, automatically splitting into multiple messages
    if the text exceeds Telegram's 4096 character limit.

    Splits on paragraph boundaries (double newlines) when possible to keep
    messages readable. Falls back to hard splits at TELEGRAM_MAX_CHARS.
    """
    if not TOKEN or not txt:
        return

    # If it fits in one message, send it directly
    if len(txt) <= TELEGRAM_MAX_CHARS:
        _send_raw(cid, txt)
        return

    # Split into chunks that fit within the limit
    chunks = _split_message(txt, TELEGRAM_MAX_CHARS)

    total = len(chunks)
    for i, chunk in enumerate(chunks):
        if total > 1:
            # Add part indicator for multi-message responses
            prefix = f"📄 <i>Part {i+1}/{total}</i>\n\n"
            if len(prefix) + len(chunk) > TELEGRAM_MAX_CHARS:
                chunk = chunk[:TELEGRAM_MAX_CHARS - len(prefix) - 3] + "..."
            chunk = prefix + chunk
        _send_raw(cid, chunk)
        # Small delay between messages to avoid rate limiting
        if i < total - 1:
            time.sleep(0.3)

def _split_message(text, max_chars):
    """
    Split text into chunks that fit within max_chars.
    Tries to split on paragraph boundaries, then line breaks, then hard split.
    HTML-aware: avoids splitting in the middle of <pre>...</pre> blocks.
    """
    if len(text) <= max_chars:
        return [text]

    chunks = []
    remaining = text

    while remaining:
        if len(remaining) <= max_chars:
            chunks.append(remaining)
            break

        # Try to split on paragraph boundary (double newline)
        split_pos = remaining.rfind('\n\n', 0, max_chars)

        if split_pos == -1 or split_pos < max_chars // 3:
            # No good paragraph split, try single newline
            split_pos = remaining.rfind('\n', 0, max_chars)

        if split_pos == -1 or split_pos < max_chars // 3:
            # No good line break, hard split at max_chars
            split_pos = max_chars

        chunk = remaining[:split_pos].rstrip()
        
        # HTML tag balancing: check for unclosed tags
        import re
        # Find all opening and closing tags
        opens = re.findall(r'<(pre|b|i|u|s|code|blockquote)[^>]*>', chunk)
        closes = re.findall(r'</(pre|b|i|u|s|code|blockquote)>', chunk)
        
        # If we have unclosed <pre> tags, close them and add opening tag to next chunk
        pre_opens = chunk.count('<pre>')
        pre_closes = chunk.count('</pre>')
        if pre_opens > pre_closes:
            chunk += '\n</pre>'
            remaining = '<pre>\n' + remaining[split_pos:].lstrip()
        else:
            remaining = remaining[split_pos:].lstrip()
        
        # Balance other inline tags
        for tag in ['b', 'i', 'u', 's', 'code']:
            tag_opens = chunk.count(f'<{tag}>')
            tag_closes = chunk.count(f'</{tag}>')
            if tag_opens > tag_closes:
                chunk += f'</{tag}>'
                remaining = f'<{tag}>' + remaining
        
        if chunk:
            chunks.append(chunk)

    return chunks

def broadcast(txt):
    for c in _ids():
        send(c, txt)

def send_report_via_telegram(report_text):
    if not TOKEN:
        return 0
    preview = report_text[:3000]
    if len(report_text) > 3000:
        preview += "\n\n<i>... (Use /report for full text split into multiple messages)</i>"
    broadcast(preview)
    return len(_ids())

def get_up(off=0):
    if not TOKEN:
        return []
    try:
        r = requests.get(f"{API}/getUpdates", params={"offset": off, "timeout": 30}, timeout=35)
        return r.json().get("result", []) if r.ok else []
    except:
        return []

# ── Commands (no LLM, always work) ──
def cmd_start():
    return (
        "🚀 <b>Kaizen Quest Agent</b>\n\n"
        "<b>Commands:</b>\n"
        "/portfolio — Your holdings\n"
        "/recommendations — Investment ideas\n"
        "/market — Market snapshot\n"
        "/price TICKER — Live price (e.g. /price AAPL)\n"
        "/buy TICKER — Stock analysis\n"
        "/report — Latest report\n"
        "/earnings — Upcoming earnings\n"
        "/sectors — Sector overview\n"
        "/help — All commands\n\n"
        "You can also just type a ticker symbol!"
    )

def cmd_help():
    return (
        "📋 <b>All Commands:</b>\n\n"
        "/portfolio — Portfolio holdings & analysis\n"
        "/recommendations — Current investment ideas\n"
        "/market — SPY, QQQ, IWM, GLD prices\n"
        "/price TICKER — Live price & change\n"
        "/buy TICKER — Full stock analysis\n"
        "/report — Latest intelligence report\n"
        "/earnings — Upcoming earnings calendar\n"
        "/sectors — Sector performance overview\n"
        "/help — This list\n\n"
        "<i>Long responses are automatically split into multiple messages.</i>"
    )

def cmd_portfolio():
    p = BASE_DIR / "docs" / "PORTFOLIO.md"
    if not p.exists():
        return "📊 No portfolio yet. Add portfolio CSV files to the portfolios/ folder."
    text = p.read_text()
    # Split into sections for better Telegram rendering
    lines = text.split('\n')
    header = []
    table_lines = []
    in_table = False
    for line in lines:
        if line.startswith('| ') and '---' not in line:
            in_table = True
            table_lines.append(line)
        elif not in_table:
            header.append(line)
    
    # Build output in chunks that split well
    output = f"📊 <b>Portfolio</b>\n\n"
    output += '\n'.join(header[:10]) + '\n\n'  # First part of header
    
    # Add table in chunks
    if table_lines:
        output += "<b>Top Holdings:</b>\n"
        for tl in table_lines[:30]:  # Top 30 positions
            # Simplify table rows for Telegram
            parts = [x.strip() for x in tl.split('|') if x.strip()]
            if len(parts) >= 4:
                ticker = parts[0].replace('**', '')
                shares = parts[1] if len(parts) > 1 else ''
                price = parts[2] if len(parts) > 2 else ''
                value = parts[3] if len(parts) > 3 else ''
                pnl = parts[4] if len(parts) > 4 else ''
                output += f"• <b>{ticker}</b>: {shares} @ {price} = {value} ({pnl})\n"
    
    return output

def cmd_recs():
    p = BASE_DIR / "docs" / "RECOMMENDATIONS.md"
    if not p.exists():
        return "💡 No recommendations yet. Run the agent to generate ideas."
    text = p.read_text()
    return f"💡 <b>Recommendations</b>\n\n{text}"

def cmd_market():
    try:
        import yfinance as yf
        lines = ["📈 <b>Market Snapshot</b>\n"]
        for ticker, name in [("SPY", "S&P 500"), ("QQQ", "Nasdaq 100"), ("IWM", "Russell 2000"), ("GLD", "Gold"), ("SLV", "Silver")]:
            try:
                tk = yf.Ticker(ticker)
                price = tk.fast_info.last_price
                prev = tk.fast_info.previous_close
                if price and prev:
                    chg = ((price - prev) / prev) * 100
                    emoji = "🟢" if chg >= 0 else "🔴"
                    lines.append(f"{emoji} <b>{name}</b> ({ticker}): ${price:.2f} ({chg:+.2f}%)")
                elif price:
                    lines.append(f"⚪ <b>{name}</b> ({ticker}): ${price:.2f}")
            except Exception:
                continue
        return "\n".join(lines) if len(lines) > 1 else "❌ Could not fetch market data."
    except Exception as e:
        return f"❌ Market data error: {str(e)[:80]}"

def cmd_price(args):
    """Get live price for a ticker. Usage: /price AAPL"""
    if not args or not args.strip():
        return "❌ <b>Usage:</b> /price TICKER\n\nExample: <code>/price AAPL</code>"

    ticker = args.strip().upper().split()[0]  # Take first word only
    if not ticker.isalpha() or len(ticker) > 5:
        return f"❌ Invalid ticker: <code>{ticker}</code>\n\nExample: <code>/price AAPL</code>"

    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        price = t.fast_info.last_price
        prev = t.fast_info.previous_close

        if not price:
            # Try alternative price fields
            try:
                info = t.info
                price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose')
            except Exception:
                pass

        if not price:
            return f"❌ No price data for <b>{ticker}</b>. Market may be closed or ticker may be invalid."

        change_str = ""
        if prev and prev > 0:
            chg = ((price - prev) / prev) * 100
            emoji = "🟢" if chg >= 0 else "🔴"
            change_str = f"\n{emoji} Change: {chg:+.2f}%"

        # Get extra context
        extra = ""
        try:
            info = t.info
            name = info.get('longName', '')
            sector = info.get('sector', '')
            if name:
                extra += f"\n🏢 {name}"
            if sector:
                extra += f"\n📂 {sector}"
        except Exception:
            pass

        return (
            f"{'🟢' if change_str and '+' in change_str else '🔴' if change_str else '⚪'} "
            f"<b>{ticker}</b>\n\n"
            f"💰 <b>Price:</b> ${price:.2f}"
            f"{change_str}"
            f"{extra}\n\n"
            f"<i>Not financial advice.</i>"
        )
    except Exception as e:
        return f"❌ Error fetching <b>{ticker}</b>: {str(e)[:100]}"

def cmd_report():
    rs = sorted((BASE_DIR / "REPORTS").glob("*.md"), reverse=True) if (BASE_DIR / "REPORTS").exists() else []
    if not rs:
        return "📝 No reports yet. Run the agent to generate one."
    text = rs[0].read_text()
    # Return full report — send() will split into multiple messages if needed
    return f"📝 <b>Latest Report</b> ({rs[0].stem})\n\n{text}"

def cmd_buy(args):
    """Get stock analysis. Usage: /buy AAPL"""
    if not args or not args.strip():
        return "❌ <b>Usage:</b> /buy TICKER\n\nExample: <code>/buy AAPL</code>"

    ticker = args.strip().upper().split()[0]
    try:
        import yfinance as yf
        t = yf.Ticker(ticker)
        price = t.fast_info.last_price

        if not price:
            try:
                info = t.info
                price = info.get('currentPrice') or info.get('regularMarketPrice')
            except Exception:
                pass

        if not price:
            return f"❌ No data for <b>{ticker}</b>."

        i = t.info
        pe = i.get("trailingPE", "N/A")
        mc = i.get("marketCap", 0)
        mc_s = f"${mc/1e9:.1f}B" if mc > 1e9 else f"${mc/1e6:.0f}M" if mc else "N/A"
        name = i.get('longName', ticker)
        sector = i.get('sector', 'N/A')
        industry = i.get('industry', '')
        high52 = i.get('fiftyTwoWeekHigh', '')
        low52 = i.get('fiftyTwoWeekLow', '')

        range_str = ""
        if high52 and low52:
            range_str = f"\n📊 52wk Range: ${low52:.2f} - ${high52:.2f}"

        return (
            f"📊 <b>{name} ({ticker})</b>\n\n"
            f"💰 <b>Price:</b> ${price:.2f}\n"
            f"📂 <b>Sector:</b> {sector}"
            f"{' — ' + industry if industry else ''}\n"
            f"🏢 <b>Market Cap:</b> {mc_s}\n"
            f"📈 <b>P/E:</b> {pe}"
            f"{range_str}\n\n"
            f"<i>Not financial advice. Verify before acting.</i>"
        )
    except Exception as e:
        return f"❌ Error analyzing <b>{ticker}</b>: {str(e)[:100]}"

def cmd_earnings():
    """Show upcoming earnings from the broad watchlist."""
    try:
        import yfinance as yf
        from datetime import date, timedelta

        today = date.today()
        lines = ["📅 <b>Upcoming Earnings (Next 14 Days)</b>\n"]

        tickers = [
            "NVDA", "AMD", "AAPL", "MSFT", "GOOGL", "META", "AMZN", "TSLA",
            "JPM", "GS", "V", "MA", "JNJ", "PFE", "UNH", "LLY",
            "WMT", "COST", "HD", "NKE", "XOM", "CVX",
            "CRM", "NOW", "SNOW", "PLTR", "NFLX", "DIS"
        ]

        found = 0
        for ticker in tickers:
            try:
                t = yf.Ticker(ticker)
                info = t.info
                earnings_ts = info.get('earningsTimestamp') or info.get('earningsDate')
                if not earnings_ts:
                    continue

                if isinstance(earnings_ts, (int, float)):
                    earnings_dt = date.fromtimestamp(earnings_ts)
                elif isinstance(earnings_ts, str):
                    try:
                        earnings_dt = date.fromisoformat(earnings_ts[:10])
                    except ValueError:
                        continue
                else:
                    continue

                days_until = (earnings_dt - today).days
                if 0 <= days_until <= 14:
                    status = "🔴 TODAY" if days_until == 0 else f"in {days_until}d"
                    lines.append(f"  {status} — <b>{ticker}</b> ({earnings_dt})")
                    found += 1
            except Exception:
                continue

        if found == 0:
            lines.append("  No major earnings in the next 14 days.")

        lines.append("\n<i>Data from yfinance. Verify with company IR pages.</i>")
        return "\n".join(lines)
    except Exception as e:
        return f"❌ Earnings data error: {str(e)[:80]}"

def cmd_sectors():
    """Show sector ETF performance."""
    try:
        import yfinance as yf
        lines = ["🏭 <b>Sector Performance</b>\n"]

        sectors = [
            ("XLK", "Tech"), ("XLF", "Financial"), ("XLE", "Energy"),
            ("XLV", "Healthcare"), ("XLI", "Industrial"), ("XLP", "Consumer Staples"),
            ("XLY", "Consumer Disc."), ("XLU", "Utilities"), ("XLRE", "Real Estate"),
            ("XLC", "Comm Services"), ("XLB", "Materials")
        ]

        for ticker, name in sectors:
            try:
                tk = yf.Ticker(ticker)
                price = tk.fast_info.last_price
                prev = tk.fast_info.previous_close
                if price and prev:
                    chg = ((price - prev) / prev) * 100
                    emoji = "🟢" if chg >= 0 else "🔴"
                    lines.append(f"{emoji} <b>{name}</b> ({ticker}): ${price:.2f} ({chg:+.2f}%)")
                elif price:
                    lines.append(f"⚪ <b>{name}</b> (${price:.2f})")
            except Exception:
                continue

        return "\n".join(lines) if len(lines) > 1 else "❌ Could not fetch sector data."
    except Exception as e:
        return f"❌ Sector data error: {str(e)[:80]}"

def handle(cid, text):
    text = text.strip()

    if text.startswith("/"):
        parts = text.split(maxsplit=1)
        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Map commands to handler functions
        command_map = {
            "/start": cmd_start,
            "/help": cmd_help,
            "/portfolio": cmd_portfolio,
            "/recommendations": cmd_recs,
            "/market": cmd_market,
            "/report": cmd_report,
            "/earnings": cmd_earnings,
            "/sectors": cmd_sectors,
        }

        if cmd in command_map:
            return command_map[cmd]()
        if cmd in ("/buy", "/analyze"):
            return cmd_buy(args)
        if cmd == "/price":
            return cmd_price(args)

        return f"❓ Unknown command: <code>{cmd}</code>\n\nSend /help for available commands."

    # Natural language handling
    tl = text.lower()
    if any(w in tl for w in ["hi", "hello", "hey"]):
        return "👋 Hi! Send /help to see what I can do."
    if any(w in tl for w in ["thanks", "thank"]):
        return "👍 You're welcome!"

    # Try to extract ticker symbols from free text
    tickers = [
        w.strip(",.!?$")
        for w in text.upper().split()
        if re.match(r'^[A-Z]{1,5}$', w.strip(",.!?$"))
        and w.strip(",.!?$") not in {
            'THE', 'AND', 'FOR', 'THIS', 'THAT', 'WITH', 'WHAT', 'WHEN',
            'WHERE', 'WHY', 'HOW', 'HAVE', 'ARE', 'WAS', 'NOT', 'BUT',
            'YOU', 'ALL', 'CAN', 'OUT', 'BUY', 'SELL', 'HOLD', 'NEWS',
            'ABOUT', 'TELL', 'ME', 'SHOW', 'GET', 'WHAT', 'YOUR'
        }
    ]

    if not tickers:
        return "🤖 Ask about a stock (e.g. /price AAPL) or use /help for commands."

    # Try LLM analysis first
    try:
        sys.path.insert(0, str(BASE_DIR))
        from agent import call_llm
        r = call_llm(
            "You analyze stocks briefly. Give BUY/HOLD/AVOID with 1-sentence reason. Direct. Not financial advice.",
            f'User: "{text}". Ticker(s): {", ".join(tickers[:3])}',
            max_tokens=300,
            task_type="simple"
        )
        if r and not r.startswith("[LLM"):
            return f"🤖 <b>Quick Take</b>\n\n{r}\n\n<i>Not financial advice.</i>"
    except Exception:
        pass

    # Fallback to basic data
    try:
        return f"⚠️ AI busy. Here's basic data:\n\n{cmd_buy(tickers[0])}"
    except Exception:
        pass

    return "⚠️ Service temporarily unavailable. Try /help for commands."

def run_forever():
    last = 0
    ok = '✅' if TOKEN else '❌'
    print(f"[Bot] Token: {ok}")
    if not TOKEN:
        print("[Bot] Get token from @BotFather, set TELEGRAM_BOT_TOKEN")
        return
    print("[Bot] ✅ Ready! 💰 $0 | ⏸ Ctrl+C to stop")
    print("[Bot] 📄 Long messages auto-split into multiple parts\n")
    while True:
        try:
            for u in get_up(last + 1):
                uid = u.get("update_id", 0)
                if uid > last:
                    last = uid
                m = u.get("message", {})
                c = m.get("chat", {}).get("id")
                t = m.get("text", "")
                if c and t:
                    _save(c)
                    r = handle(c, t)
                    send(c, r)
            time.sleep(1)
        except KeyboardInterrupt:
            print("\n[Bot] Stopped ✅")
            break
        except Exception as e:
            print(f"[Bot] Error: {e}")
            time.sleep(5)

def start_bot():
    print("=" * 55)
    print("  🤖 Kaizen Quest Telegram Bot v2.0 (100% Free)")
    print("=" * 55)
    print("  Run: python3 skills/telegram_bot.py")
    print("  Cost: $0 | LLM: Free OpenRouter | Data: yfinance")
    print("  Fix: Long messages now split into multiple parts")
    print()
    run_forever()

__all__ = ['send', 'broadcast', 'send_report_via_telegram', 'handle', 'start_bot']
if __name__ == "__main__":
    start_bot()