"""
Research Memory System v1.0

Tracks what the agent has researched across runs, enabling:
- Incremental research (only research what's changed)
- Research depth scoring (surface vs deep)
- Fact verification with timestamps and confidence decay
- Resume from where last run left off
- Anti-stale-data safeguards

Data is stored in docs/research/ directory:
  docs/research/state.json          — global research state (queue, last run info)
  docs/research/tickers/{TICKER}.json — per-ticker research ledger
  docs/research/facts/{TICKER}_facts.json — verified facts with timestamps

Usage:
    from skills.research_memory import ResearchMemory
    
    mem = ResearchMemory()
    mem.start_run()
    
    # Check if ticker needs research
    if mem.needs_research("NVDA", min_depth=5):
        depth = mem.get_research_depth("NVDA")
        gaps = mem.get_research_gaps("NVDA")
        # ... do research, focusing on gaps ...
        mem.record_research("NVDA", depth=7, facts=[...], catalysts=[...])
    
    # Get research summary for LLM context
    summary = mem.get_ticker_summary("NVDA")
    
    mem.end_run()
"""

import os
import json
import datetime
import math
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
RESEARCH_DIR = BASE_DIR / "docs" / "research"
TICKER_DIR = RESEARCH_DIR / "tickers"
FACTS_DIR = RESEARCH_DIR / "facts"
STATE_FILE = RESEARCH_DIR / "state.json"

# Confidence half-life by fact type (days)
# Based on research from SmartVector (arXiv:2604.20598), Prism (arXiv:2604.19795),
# TradingGPT (arXiv:2309.03736), mem0 production system, and Zep temporal knowledge graphs.
# Key principle: half-life = time for confidence to decay to 50% without refresh.
CONFIDENCE_HALF_LIFE = {
    # Ultra-fast decay (minutes to hours) — market-moving data
    "price": 1,              # 1 day — prices stale after market close; intraday: 15-30 min
    "options": 1,            # 1 day — IV, OI, Greeks change rapidly
    "news": 1,               # 1 day — news impact decays 60-80% in first hour (event studies)
    
    # Fast decay (1-7 days) — sentiment and flow data
    "sentiment": 3,          # 3 days — news sentiment fully absorbed by market in ~12 hours, residual fades in 3
    "technical": 3,          # 3 days — RSI, MACD derived from price; weekly indicators: 5-10 days
    "insider": 7,            # 7 days — Form 4 filings priced in quickly; 13F: 30 days
    
    # Medium decay (7-30 days) — thesis and catalyst data
    "thesis": 14,            # 14 days — re-evaluate investment case biweekly (was 7, too aggressive)
    "catalyst": 14,          # 14 days — pre-catalyst slow decay; post-catalyst: immediate drop
    "risk": 14,              # 14 days — risk factors evolve with news cycle (was 7)
    "macro": 14,             # 14 days — macro regime changes monthly (was 7)
    "sector": 14,            # 14 days — sector rotation cycles: 2-8 weeks
    
    # Slow decay (30-90 days) — fundamental data
    "fundamentals": 30,      # 30 days — ratios change quarterly; growth estimates decay faster
    "institutional": 30,     # 30 days — 13F filings quarterly; monthly estimates: 14 days
    "earnings": 90,          # 90 days — quarterly earnings valid until next report (was 30, too short)
    "guidance": 60,          # 60 days — forward guidance valid until next earnings (was 30)
    
    # Very slow decay (60-180 days) — structural data
    "competitive": 90,       # 90 days — competitive landscape shifts quarterly (was 60)
    "moat": 90,              # 90 days — moat assessment changes slowly (was 30, too short)
}

# Research depth levels
DEPTH_SURFACE = 1      # Price, basic news
DEPTH_BASIC = 3        # + Fundamentals, earnings
DEPTH_MODERATE = 5     # + Peer comparison, technicals, sentiment
DEPTH_DEEP = 7         # + DCF, competitive landscape, insider/institutional
DEPTH_COMPREHENSIVE = 9  # + Contrarian analysis, thesis evolution, risk deep-dive


class ResearchMemory:
    def __init__(self):
        self._ensure_dirs()
        self.state = self._load_state()
        self._current_run_tickers = set()
    
    def _ensure_dirs(self):
        RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
        TICKER_DIR.mkdir(parents=True, exist_ok=True)
        FACTS_DIR.mkdir(parents=True, exist_ok=True)
    
    def _load_state(self):
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text())
            except Exception:
                pass
        return {
            "total_runs": 0,
            "last_run": None,
            "last_run_tickers": [],
            "research_queue": [],
            "global_facts": {},
        }
    
    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2, default=str))
    
    def _ticker_file(self, ticker):
        return TICKER_DIR / f"{ticker.upper()}.json"
    
    def _load_ticker(self, ticker):
        f = self._ticker_file(ticker)
        if f.exists():
            try:
                return json.loads(f.read_text())
            except Exception:
                pass
        return self._default_ticker_data(ticker)
    
    def _save_ticker(self, ticker, data):
        self._ticker_file(ticker).write_text(json.dumps(data, indent=2, default=str))
    
    def _default_ticker_data(self, ticker):
        return {
            "ticker": ticker.upper(),
            "first_researched": None,
            "last_researched": None,
            "research_count": 0,
            "research_depth_score": 0,
            "last_research_type": None,
            "last_price": None,
            "catalysts": [],
            "facts": [],
            "thesis_history": [],
            "risks": [],
            "competitive_position": None,
            "data_sources_used": [],
            "research_gaps": [],
            "contrarian_signals": [],
        }
    
    # ─── Run Lifecycle ──────────────────────────────────────────────
    
    def start_run(self):
        """Mark the start of a research run."""
        self._current_run_tickers = set()
        self.state["total_runs"] = self.state.get("total_runs", 0) + 1
    
    def end_run(self):
        """Mark the end of a research run, save state."""
        self.state["last_run"] = datetime.datetime.now().isoformat()
        self.state["last_run_tickers"] = list(self._current_run_tickers)
        self._save_state()
    
    # ─── Research Tracking ──────────────────────────────────────────
    
    def needs_research(self, ticker, min_depth=5, max_age_hours=24):
        """Check if a ticker needs fresh research."""
        data = self._load_ticker(ticker)
        
        # Never researched
        if data["research_count"] == 0:
            return True
        
        # Below minimum depth
        if data["research_depth_score"] < min_depth:
            return True
        
        # Too old
        if data["last_researched"]:
            try:
                last = datetime.datetime.fromisoformat(data["last_researched"])
                age_hours = (datetime.datetime.now() - last).total_seconds() / 3600
                if age_hours > max_age_hours:
                    return True
            except Exception:
                return True
        
        return False
    
    def get_research_depth(self, ticker):
        """Get current research depth score (0-10)."""
        data = self._load_ticker(ticker)
        return data.get("research_depth_score", 0)
    
    def get_research_gaps(self, ticker):
        """Identify what's missing from current research."""
        data = self._load_ticker(ticker)
        gaps = []
        
        if data["research_depth_score"] < 3:
            gaps.extend(["fundamentals", "earnings", "basic_news"])
        if data["research_depth_score"] < 5:
            gaps.extend(["peer_comparison", "technical_analysis", "sentiment"])
        if data["research_depth_score"] < 7:
            gaps.extend(["dcf_valuation", "competitive_landscape", "insider_activity", "institutional_ownership"])
        if data["research_depth_score"] < 9:
            gaps.extend(["contrarian_analysis", "thesis_evolution", "risk_deep_dive", "moat_assessment"])
        
        # Check for stale facts
        stale_types = self._get_stale_fact_types(data)
        gaps.extend([f"refresh_{t}" for t in stale_types])
        
        return gaps
    
    def _get_stale_fact_types(self, data):
        """Find fact types that have expired confidence."""
        stale = []
        now = datetime.datetime.now()
        for fact in data.get("facts", []):
            ftype = fact.get("type", "unknown")
            last_verified = fact.get("last_verified", "")
            if not last_verified:
                stale.append(ftype)
                continue
            try:
                verified_time = datetime.datetime.fromisoformat(last_verified)
                age_days = (now - verified_time).days
                half_life = CONFIDENCE_HALF_LIFE.get(ftype, 7)
                confidence = 0.5 ** (age_days / half_life)
                if confidence < 0.3:
                    stale.append(ftype)
            except Exception:
                stale.append(ftype)
        return list(set(stale))
    
    def record_research(self, ticker, depth=5, facts=None, catalysts=None,
                         thesis=None, conviction=None, price=None, risks=None,
                         competitive=None, contrarian=None, sources=None):
        """Record research findings for a ticker."""
        data = self._load_ticker(ticker)
        now = datetime.datetime.now().isoformat()
        
        if not data["first_researched"]:
            data["first_researched"] = now
        data["last_researched"] = now
        data["research_count"] = data.get("research_count", 0) + 1
        data["research_depth_score"] = max(data.get("research_depth_score", 0), depth)
        data["last_research_type"] = "deep" if depth >= 7 else "moderate" if depth >= 5 else "basic"
        
        if price:
            data["last_price"] = price
        
        # Add/update facts with timestamps
        if facts:
            existing_facts = {f.get("claim", ""): f for f in data.get("facts", [])}
            for fact in facts:
                fact["first_verified"] = fact.get("first_verified", now)
                fact["last_verified"] = now
                fact["verification_count"] = fact.get("verification_count", 1)
                existing_facts[fact.get("claim", "")] = fact
            data["facts"] = list(existing_facts.values())
        
        # Update catalysts
        if catalysts:
            existing = {c.get("catalyst", ""): c for c in data.get("catalysts", [])}
            for c in catalysts:
                c["last_verified"] = now
                existing[c.get("catalyst", "")] = c
            data["catalysts"] = list(existing.values())
        
        # Record thesis evolution
        if thesis:
            data["thesis_history"].append({
                "date": now,
                "thesis": thesis,
                "conviction": conviction,
                "price_at_research": price,
            })
        
        # Update risks
        if risks:
            data["risks"] = risks
        
        # Update competitive position
        if competitive:
            data["competitive_position"] = competitive
        
        # Update contrarian signals
        if contrarian:
            data["contrarian_signals"] = contrarian
        
        # Track data sources
        if sources:
            data["data_sources_used"] = list(set(data.get("data_sources_used", []) + sources))
        
        self._save_ticker(ticker, data)
        self._current_run_tickers.add(ticker.upper())
    
    # ─── Fact Verification ──────────────────────────────────────────
    
    def get_fact_confidence(self, ticker, fact_type):
        """Get current confidence for a fact type (0-1)."""
        data = self._load_ticker(ticker)
        for fact in data.get("facts", []):
            if fact.get("type") == fact_type:
                try:
                    verified = datetime.datetime.fromisoformat(fact.get("last_verified", ""))
                    age_days = (datetime.datetime.now() - verified).days
                    half_life = CONFIDENCE_HALF_LIFE.get(fact_type, 7)
                    base = fact.get("initial_confidence", 0.8)
                    decayed = base * (0.5 ** (age_days / half_life))
                    boost = min(0.2, fact.get("verification_count", 0) * 0.05)
                    return min(1.0, decayed + boost)
                except Exception:
                    return 0.0
        return 0.0
    
    def is_fact_fresh(self, ticker, fact_type, max_age_hours=24):
        """Check if a fact type is still fresh."""
        data = self._load_ticker(ticker)
        for fact in data.get("facts", []):
            if fact.get("type") == fact_type:
                try:
                    verified = datetime.datetime.fromisoformat(fact.get("last_verified", ""))
                    age_hours = (datetime.datetime.now() - verified).total_seconds() / 3600
                    return age_hours < max_age_hours
                except Exception:
                    return False
        return False
    
    # ─── Change Detection ───────────────────────────────────────────
    
    def detect_changes(self, ticker, new_price=None, new_fundamentals=None):
        """Detect what's changed since last research."""
        data = self._load_ticker(ticker)
        changes = {
            "price_moved": False,
            "price_change_pct": 0,
            "new_catalysts": [],
            "expired_catalysts": [],
            "fundamental_shifts": [],
            "thesis_stale": False,
        }
        
        # Price change
        if new_price and data.get("last_price"):
            old = data["last_price"]
            if old > 0:
                pct = (new_price - old) / old * 100
                changes["price_moved"] = abs(pct) > 5  # >5% move is significant
                changes["price_change_pct"] = round(pct, 1)
        
        # Check thesis age
        if data.get("thesis_history"):
            last_thesis = data["thesis_history"][-1]
            try:
                thesis_date = datetime.datetime.fromisoformat(last_thesis.get("date", ""))
                age_days = (datetime.datetime.now() - thesis_date).days
                changes["thesis_stale"] = age_days > 14
            except Exception:
                changes["thesis_stale"] = True
        
        # Check for expired catalysts
        now = datetime.datetime.now()
        for c in data.get("catalysts", []):
            status = c.get("status", "active")
            if status == "expired":
                changes["expired_catalysts"].append(c.get("catalyst", ""))
        
        return changes
    
    # ─── Summary for LLM Context ────────────────────────────────────
    
    def get_ticker_summary(self, ticker, max_chars=1500):
        """Get a concise research summary for LLM context."""
        data = self._load_ticker(ticker)
        lines = []
        
        lines.append(f"## Research Memory: {ticker.upper()}")
        lines.append(f"Researched {data.get('research_count', 0)}x | Depth: {data.get('research_depth_score', 0)}/10 | Last: {data.get('last_researched', 'never')[:10]}")
        
        # Current thesis
        if data.get("thesis_history"):
            latest = data["thesis_history"][-1]
            lines.append(f"\n**Current Thesis:** {latest.get('thesis', 'N/A')}")
            lines.append(f"Conviction: {latest.get('conviction', '?')}/10 | Price at research: ${latest.get('price_at_research', 'N/A')}")
        
        # Active catalysts
        active_cats = [c for c in data.get("catalysts", []) if c.get("status") == "active"]
        if active_cats:
            lines.append(f"\n**Active Catalysts:**")
            for c in active_cats[:5]:
                lines.append(f"  - {c.get('catalyst', '')} (conf: {c.get('confidence', '?')}, src: {c.get('source', '?')})")
        
        # Key facts (high confidence only)
        high_conf_facts = []
        for f in data.get("facts", []):
            try:
                verified = datetime.datetime.fromisoformat(f.get("last_verified", ""))
                age_days = (datetime.datetime.now() - verified).days
                half_life = CONFIDENCE_HALF_LIFE.get(f.get("type", ""), 7)
                conf = 0.5 ** (age_days / half_life)
                if conf > 0.5:
                    high_conf_facts.append((conf, f))
            except Exception:
                pass
        high_conf_facts.sort(reverse=True)
        if high_conf_facts:
            lines.append(f"\n**Verified Facts (conf >50%):**")
            for conf, f in high_conf_facts[:8]:
                lines.append(f"  - [{f.get('type', '?')}] {f.get('claim', '')} (conf: {conf:.0%})")
        
        # Contrarian signals
        if data.get("contrarian_signals"):
            lines.append(f"\n**Contrarian Signals:**")
            for s in data["contrarian_signals"][:3]:
                lines.append(f"  ⚠️ {s.get('signal', '')} (sev: {s.get('severity', '?')})")
        
        # Research gaps
        gaps = self.get_research_gaps(ticker)
        if gaps:
            lines.append(f"\n**Research Gaps:** {', '.join(gaps[:6])}")
        
        # Data sources used
        if data.get("data_sources_used"):
            lines.append(f"\n**Sources Used:** {', '.join(data['data_sources_used'])}")
        
        result = "\n".join(lines)
        if len(result) > max_chars:
            result = result[:max_chars] + "\n... [truncated]"
        return result
    
    def get_research_queue(self, tickers, min_depth=5, max_per_run=5):
        """Prioritize which tickers to research this run."""
        needs_work = []
        for t in tickers:
            t = t.upper()
            if self.needs_research(t, min_depth=min_depth):
                depth = self.get_research_depth(t)
                # Prioritize: lower depth = higher priority
                needs_work.append((t, depth))
        
        # Sort by depth (ascending) then alphabetically
        needs_work.sort(key=lambda x: (x[1], x[0]))
        return [t for t, _ in needs_work[:max_per_run]]
    
    def get_global_summary(self, max_chars=2000):
        """Get a summary of all research for the run."""
        lines = []
        lines.append("## Global Research State")
        lines.append(f"Total runs: {self.state.get('total_runs', 0)}")
        lines.append(f"Last run: {self.state.get('last_run', 'never')}")
        
        # Count researched tickers
        if TICKER_DIR.exists():
            ticker_files = list(TICKER_DIR.glob("*.json"))
            lines.append(f"\nTickers researched: {len(ticker_files)}")
            
            # Deep researched (depth >= 7)
            deep = 0
            for f in ticker_files:
                try:
                    d = json.loads(f.read_text())
                    if d.get("research_depth_score", 0) >= 7:
                        deep += 1
                except Exception:
                    pass
            lines.append(f"Deep researched (7+): {deep}")
        
        result = "\n".join(lines)
        if len(result) > max_chars:
            result = result[:max_chars]
        return result


# Module-level convenience functions
_mem = None

def get_memory():
    global _mem
    if _mem is None:
        _mem = ResearchMemory()
    return _mem
