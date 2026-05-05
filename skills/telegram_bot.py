"""
Telegram Bot Skill v1.0 - 100% Free

Runs locally or 24/7 on fly.io free tier.
LLM: free OpenRouter only. Falls to commands if unavailable.
"""

import os, json, requests, time, re, sys
from pathlib import Path
BASE_DIR = Path(__file__).parent.parent
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
API = f"https://api.telegram.org/bot{TOKEN}"
CID_FILE = BASE_DIR / "cache" / "telegram_chat_ids.json"

def _ids():
    try: return json.loads(CID_FILE.read_text()).get("ids", []) if CID_FILE.exists() else []
    except: return []
def _save(c):
    ids=_ids()
    if c not in ids: ids.append(c); CID_FILE.parent.mkdir(exist_ok=True); CID_FILE.write_text(json.dumps({"ids":ids}))
def send(cid,txt):
    if not TOKEN: return
    if len(txt)>4000: txt=txt[:4000]+"\n\n... (truncated)"
    try: requests.post(f"{API}/sendMessage",json={"chat_id":cid,"text":txt,"parse_mode":"HTML","disable_web_page_preview":True},timeout=10)
    except: pass
def broadcast(txt):
    for c in _ids(): send(c,txt)
def send_report_via_telegram(report_text):
    if not TOKEN: return 0
    d=report_text[:2000]
    if len(report_text)>2000: d+="\n\n<i>...Full report in REPORTS/ folder</i>"
    broadcast(d); return len(_ids())
def get_up(off=0):
    if not TOKEN: return []
    try: r=requests.get(f"{API}/getUpdates",params={"offset":off,"timeout":30},timeout=35); return r.json().get("result",[]) if r.ok else []
    except: return []

# ── Commands (no LLM, always work) ──
def cmd_start(): return "🚀 <b>Kaizen Quest Agent</b>\n\n/help - All\n/portfolio - Holdings\n/recommendations - Ideas\n/market - Markets\n/buy TICKER - Analysis\n/price TICKER - Price\n/report - Latest\n\nAsk about any stock!"
def cmd_help(): return "📋 Commands:\n/portfolio\n/buy TICKER\n/price TICKER\n/market\n/recommendations\n/report"
def cmd_portfolio():
    p=BASE_DIR/"docs"/"PORTFOLIO.md"
    return f"📊 <b>Portfolio</b>\n\n<pre>{p.read_text()[:3000]}</pre>" if p.exists() else "📊 No portfolio yet."
def cmd_recs():
    p=BASE_DIR/"docs"/"RECOMMENDATIONS.md"
    return f"💡 <b>Recommendations</b>\n\n{p.read_text()[:3000]}" if p.exists() else "💡 None yet."
def cmd_market():
    try:
        import yfinance as yf
        l=["📈 <b>Markets</b>"]
        for t,n in [("SPY","S&P 500"),("QQQ","Nasdaq"),("IWM","Russell"),("GLD","Gold")]:
            try: tk=yf.Ticker(t); p=tk.fast_info.last_price; pc=tk.fast_info.previous_close
            except: continue
            if p and pc: c=((p-pc)/pc)*100; l.append(f"{'🟢' if c>=0 else'🔴'} {n}: ${p:.2f} ({c:+.2f}%)")
        return "\n".join(l)
    except Exception as e: return f"❌ {str(e)[:80]}"
def cmd_price(a):
    if not a: return "❌ /price TICKER"
    try:
        import yfinance as yf; t=yf.Ticker(a.strip().upper()); p=t.fast_info.last_price; pc=t.fast_info.previous_close
        if not p: return "❌ No data."
        c=((p-pc)/pc)*100 if pc else 0
        return f"{'🟢' if c>=0 else'🔴'} <b>{a.upper()}:</b> ${p:.2f} ({c:+.2f}%)"
    except Exception as e: return f"❌ {str(e)[:80]}"
def cmd_report():
    rs=sorted((BASE_DIR/"REPORTS").glob("*.md"),reverse=True) if (BASE_DIR/"REPORTS").exists() else []
    return f"📝 <b>Latest Report</b>\n\n{rs[0].read_text()[:4000]}" if rs else "📝 No reports yet."
def cmd_buy(a):
    if not a: return "❌ /buy TICKER"
    try:
        import yfinance as yf; t=yf.Ticker(a.strip().upper()); p=t.fast_info.last_price
        if not p: return "❌ No data."
        i=t.info; pe=i.get("trailingPE","N/A"); mc=i.get("marketCap",0)
        mc_s=f"${mc/1e9:.1f}B" if mc>1e9 else f"${mc/1e6:.0f}M" if mc else "N/A"
        return f"📊 <b>{i.get('longName',a.upper())} ({a.upper()})</b>\n\n💰 ${p:.2f}\n📂 {i.get('sector','N/A')}\n🏢 {mc_s}\n📈 P/E: {pe}\n\n<i>Not financial advice.</i>"
    except Exception as e: return f"❌ {str(e)[:80]}"

def handle(cid,text):
    text=text.strip()
    if text.startswith("/"):
        parts=text.split(maxsplit=1); cmd,a=parts[0].lower(),(parts[1] if len(parts)>1 else "")
        tbl={"/start":cmd_start,"/help":cmd_help,"/portfolio":cmd_portfolio,"/recommendations":cmd_recs,"/market":cmd_market,"/report":cmd_report}
        if cmd in tbl: return tbl[cmd]()
        if cmd in ("/buy","/analyze"): return cmd_buy(a)
        if cmd=="/price": return cmd_price(a)
        return "❓ Send /help"
    tl=text.lower()
    if any(w in tl for w in ["hi","hello","hey"]): return "👋 Send /help"
    if any(w in tl for w in ["thanks","thank"]): return "👍 Welcome!"
    tickers=[w.strip(",.!?$") for w in text.upper().split() if re.match(r'^[A-Z]{1,5}$',w.strip(",.!?$")) and w.strip(",.!?$") not in {'THE','AND','FOR','THIS','THAT','WITH','WHAT','WHEN','WHERE','WHY','HOW','HAVE','ARE','WAS','NOT','BUT','YOU','ALL','CAN','OUT'}]
    if not tickers: return "🤖 Ask about a stock or use /help"
    try:
        sys.path.insert(0,str(BASE_DIR))
        from agent import call_llm
        r=call_llm("You analyze stocks briefly. Give BUY/HOLD/AVOID with 1-sentence reason. Direct. Not financial advice.",f'User: "{text}". Ticker(s): {", ".join(tickers[:3])}',max_tokens=300,task_type="simple")
        if r and not r.startswith("[LLM"): return f"🤖 <b>Quick Take</b>\n\n{r}\n\n<i>Not financial advice.</i>"
    except: pass
    try: return f"⚠️ Free AI busy.\n\n<b>{tickers[0]}</b> data:\n{cmd_buy(tickers[0])}\n\nUse /price {tickers[0]} for live quotes."
    except: pass
    return "⚠️ Free AI unavailable. Use /help"

def run_forever():
    last=0
    ok='✅' if TOKEN else '❌'
    print(f"[Bot] Token: {ok}")
    if not TOKEN: print("[Bot] Get token from @BotFather, set TELEGRAM_BOT_TOKEN"); return
    print("[Bot] ✅ Ready! 💰 $0 | ⏸ Ctrl+C to stop\n")
    while True:
        try:
            for u in get_up(last+1):
                uid=u.get("update_id",0)
                if uid>last: last=uid
                m=u.get("message",{}); c=m.get("chat",{}).get("id"); t=m.get("text","")
                if c and t: _save(c); r=handle(c,t); send(c,r)
            time.sleep(1)
        except KeyboardInterrupt: print("\n[Bot] Stopped ✅"); break
        except Exception as e: print(f"[Bot] Error: {e}"); time.sleep(5)

def start_bot():
    print("="*50)
    print("  🤖 Kaizen Quest Telegram Bot (100% Free)")
    print("="*50)
    print("  Run: python3 skills/telegram_bot.py")
    print("  Cost: $0 | LLM: Free OpenRouter | Data: yfinance")
    print()
    run_forever()

__all__=['send','broadcast','send_report_via_telegram','handle','start_bot']
if __name__=="__main__": start_bot()