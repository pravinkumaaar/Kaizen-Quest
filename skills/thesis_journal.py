"""
Thesis Journal v1.0

Tracks the agent's investment theses, research, and learnings over time.
Enables continuous learning by maintaining a structured record of:
- Investment theses for each position
- Entry rationale and expected catalysts
- Outcome tracking (what worked, what didn't)
- Pattern recognition across trades

This helps the agent:
1. Remember why it bought something
2. Learn from past mistakes
3. Identify recurring patterns in successful trades
4. Build institutional knowledge over time

Usage:
    from skills.thesis_journal import ThesisJournal
    
    journal = ThesisJournal()
    journal.record_thesis("AAPL", "AI ecosystem leader", catalysts=["iPhone cycle", "Services growth"])
    journal.record_outcome("AAPL", "WIN", "AI narrative drove 40% gain")
    insights = journal.get_insights()
"""

import json
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
JOURNAL_FILE = BASE_DIR / "docs" / "THESIS_JOURNAL.json"


class ThesisJournal:
    def __init__(self):
        self.entries = self._load()
    
    def _load(self):
        if JOURNAL_FILE.exists():
            try:
                return json.loads(JOURNAL_FILE.read_text())
            except Exception:
                return {"theses": [], "outcomes": [], "insights": [], "stats": {}}
        return {"theses": [], "outcomes": [], "insights": [], "stats": {}}
    
    def _save(self):
        JOURNAL_FILE.write_text(json.dumps(self.entries, indent=2))
    
    def record_ticker(self, ticker, thesis, catalysts, entry_price, 
                       conviction, sector, strategy="long"):
        """Record a new investment thesis."""
        entry = {
            "ticker": ticker.upper(),
            "thesis": thesis,
            "catalysts": catalysts if isinstance(catalysts, list) else [catalysts],
            "entry_price": entry_price,
            "conviction": conviction,
            "sector": sector,
            "strategy": strategy,
            "date": datetime.datetime.now().strftime("%Y-%m-%d"),
            "status": "active",
        }
        self.entries["theses"].append(entry)
        self._save()
        return entry
    
    def record_outcome(self, ticker, result, notes="", exit_price=None):
        """Record the outcome of a thesis."""
        # Find the matching thesis
        for thesis in reversed(self.entries["theses"]):
            if thesis["ticker"] == ticker.upper() and thesis["status"] == "active":
                thesis["status"] = "closed"
                outcome = {
                    "ticker": ticker.upper(),
                    "result": result,  # WIN, LOSS, PARTIAL
                    "notes": notes,
                    "entry_price": thesis.get("entry_price", 0),
                    "exit_price": exit_price,
                    "thesis_date": thesis.get("date", ""),
                    "outcome_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                }
                if exit_price and thesis.get("entry_price"):
                    outcome["return_pct"] = round((exit_price - thesis["entry_price"]) / thesis["entry_price"] * 100, 1)
                self.entries["outcomes"].append(outcome)
                self._save()
                return outcome
        return None
    
    def get_active_theses(self):
        """Get all active (open) theses."""
        return [t for t in self.entries["theses"] if t["status"] == "active"]
    
    def get_insights(self):
        """Generate insights from historical outcomes."""
        outcomes = self.entries.get("outcomes", [])
        if not outcomes:
            return {"message": "No outcomes recorded yet"}
        
        wins = [o for o in outcomes if o["result"] == "WIN"]
        losses = [o for o in outcomes if o["result"] == "LOSS"]
        total = len(outcomes)
        
        # Sector performance
        sector_results = {}
        for o in outcomes:
            # Find matching thesis for sector
            for t in self.entries["theses"]:
                if t["ticker"] == o["ticker"]:
                    sector = t.get("sector", "Unknown")
                    if sector not in sector_results:
                        sector_results[sector] = {"wins": 0, "total": 0}
                    sector_results[sector]["total"] += 1
                    if o["result"] == "WIN":
                        sector_results[sector]["wins"] += 1
                    break
        
        # Conviction calibration
        high_conv_wins = sum(1 for o in wins if any(t.get("conviction", 0) >= 8 for t in self.entries["theses"] if t["ticker"] == o["ticker"]))
        high_conv_total = sum(1 for o in outcomes if any(t.get("conviction", 0) >= 8 for t in self.entries["theses"] if t["ticker"] == o["ticker"]))
        
        insights = {
            "total_trades": total,
            "wins": len(wins),
            "losses": len(losses),
            "win_rate": round(len(wins) / total * 100, 1) if total > 0 else 0,
            "avg_return": round(sum(o.get("return_pct", 0) for o in outcomes) / total, 1) if total > 0 else 0,
            "sector_performance": {s: {"win_rate": round(v["wins"]/v["total"]*100, 1), "trades": v["total"]} for s, v in sector_results.items() if v["total"] >= 2},
            "high_conviction_accuracy": round(high_conv_wins / high_conv_total * 100, 1) if high_conv_total > 0 else 0,
            "recent_outcomes": outcomes[-5:],
        }
        return insights
    
    def format_report(self):
        """Format the journal as a readable report."""
        lines = []
        lines.append("## 📓 Thesis Journal")
        lines.append(f"*{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*")
        lines.append("")
        
        # Active theses
        active = self.get_active_theses()
        if active:
            lines.append(f"### Active Theses ({len(active)})")
            for t in active:
                lines.append(f"- **{t['ticker']}** ({t.get('sector', 'N/A')}): {t['thesis']}")
                lines.append(f"  Entry: ${t.get('entry_price', 'N/A')} | Conviction: {t.get('conviction', 'N/A')}/10 | Date: {t.get('date', 'N/A')}")
                if t.get("catalysts"):
                    lines.append(f"  Catalysts: {', '.join(t['catalysts'][:3])}")
            lines.append("")
        
        # Insights
        insights = self.get_insights()
        if "message" not in insights:
            lines.append("### Performance Insights")
            lines.append(f"- Total Trades: {insights['total_trades']} | Win Rate: {insights['win_rate']}% | Avg Return: {insights['avg_return']}%")
            lines.append(f"- High Conviction (8+) Accuracy: {insights['high_conviction_accuracy']}%")
            if insights.get("sector_performance"):
                lines.append("- Sector Performance:")
                for sector, data in sorted(insights["sector_performance"].items(), key=lambda x: -x[1]["win_rate"]):
                    lines.append(f"  - {sector}: {data['win_rate']}% win rate ({data['trades']} trades)")
            lines.append("")
        
        return "\n".join(lines)


# Module-level functions for easy access
_journal = None

def get_journal():
    global _journal
    if _journal is None:
        _journal = ThesisJournal()
    return _journal

def record_thesis(ticker, thesis, catalysts, entry_price, conviction, sector):
    return get_journal().record_ticker(ticker, thesis, catalysts, entry_price, conviction, sector)

def record_outcome(ticker, result, notes="", exit_price=None):
    return get_journal().record_outcome(ticker, result, notes, exit_price)

def get_insights():
    return get_journal().get_insights()

def format_journal_report():
    return get_journal().format_report()



