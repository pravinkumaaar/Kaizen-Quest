"""
Memory Manager Skill

Manages the growing knowledge base efficiently:
- Tiered memory: Hot (last 3 runs), Warm (weekly summary), Cold (archived)
- Automatic compression and summarization
- Token-efficient loading
"""

import json
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = Path(__file__).parent.parent
MEMORY_DIR = BASE_DIR / "docs" / "memory"
HOT_MEMORY_FILE = MEMORY_DIR / "hot.json"
WARM_MEMORY_FILE = MEMORY_DIR / "warm.json"
ARCHIVE_DIR = MEMORY_DIR / "archive"

def init_memory_system():
    """Initialize memory directories."""
    MEMORY_DIR.mkdir(exist_ok=True)
    ARCHIVE_DIR.mkdir(exist_ok=True)

def compress_run_output(run_data: dict) -> dict:
    """
    Compress a run's output into a compact summary.
    Reduces token usage by ~80% while preserving key information.
    """
    return {
        "date": run_data.get("date", ""),
        "model": run_data.get("model", ""),
        "rating": run_data.get("rating", 0),
        "top_recommendations": [
            {
                "ticker": r.get("ticker", ""),
                "action": r.get("action", ""),
                "conviction": r.get("conviction", 0),
                "thesis": r.get("thesis", "")[:100]  # Truncate long theses
            }
            for r in run_data.get("recommendations", [])[:3]  # Top 3 only
        ],
        "key_learnings": run_data.get("learnings", [])[:5],  # Top 5 learnings
        "portfolio_summary": {
            "total_value": run_data.get("portfolio_value", 0),
            "top_holding": run_data.get("top_holding", ""),
            "concentration": run_data.get("concentration", 0)
        },
        "benchmarks": run_data.get("benchmarks", {})
    }

def update_hot_memory(run_data: dict):
    """Keep last 3 runs in hot memory (always loaded)."""
    init_memory_system()
    
    hot = []
    if HOT_MEMORY_FILE.exists():
        hot = json.loads(HOT_MEMORY_FILE.read_text())
    
    # Add new run
    compressed = compress_run_output(run_data)
    hot.append(compressed)
    
    # Keep only last 3 runs
    hot = hot[-3:]
    
    HOT_MEMORY_FILE.write_text(json.dumps(hot, indent=2))

def update_warm_memory():
    """
    Create weekly summary from hot memory.
    Loaded weekly to provide context without full history.
    """
    init_memory_system()
    
    if not HOT_MEMORY_FILE.exists():
        return
    
    hot = json.loads(HOT_MEMORY_FILE.read_text())
    
    if len(hot) < 3:
        return  # Not enough data yet
    
    # Aggregate learnings
    all_learnings = []
    all_recommendations = []
    avg_rating = 0
    
    for run in hot:
        all_learnings.extend(run.get("key_learnings", []))
        all_recommendations.extend(run.get("top_recommendations", []))
        avg_rating += run.get("rating", 0)
    
    avg_rating = avg_rating / len(hot) if hot else 0
    
    warm = {
        "week_of": datetime.now().strftime("%Y-%m-%d"),
        "runs_summarized": len(hot),
        "avg_rating": round(avg_rating, 1),
        "top_learnings": all_learnings[:10],  # Top 10 across all runs
        "active_recommendations": [
            r for r in all_recommendations 
            if r.get("conviction", 0) >= 8
        ],
        "patterns_noted": extract_patterns(all_learnings)
    }
    
    WARM_MEMORY_FILE.write_text(json.dumps(warm, indent=2))

def extract_patterns(learnings: list) -> list:
    """Extract recurring patterns from learnings."""
    # Simple pattern extraction - can be enhanced with NLP
    patterns = []
    keywords = ["momentum", "earnings", "sector", "rotation", "overbought", "oversold", 
                "support", "resistance", "breakout", "volume", "trend"]
    
    for learning in learnings:
        learning_lower = learning.lower()
        for keyword in keywords:
            if keyword in learning_lower:
                patterns.append(f"{keyword}: {learning[:80]}")
                break
    
    return list(set(patterns))[:5]  # Unique patterns, max 5

def get_memory_for_run() -> str:
    """
    Get memory context for current run.
    Returns compressed memory string for LLM context.
    """
    init_memory_system()
    
    memory_parts = []
    
    # Hot memory (last 3 runs)
    if HOT_MEMORY_FILE.exists():
        hot = json.loads(HOT_MEMORY_FILE.read_text())
        if hot:
            memory_parts.append("=== RECENT RUNS (Last 3) ===")
            for run in hot:
                memory_parts.append(f"\n[{run.get('date', 'N/A')}] Rating: {run.get('rating', 'N/A')}/10")
                memory_parts.append(f"Top picks: {', '.join([r.get('ticker', '') for r in run.get('top_recommendations', [])])}")
                if run.get('key_learnings'):
                    memory_parts.append(f"Key learnings: {'; '.join(run['key_learnings'][:3])}")
    
    # Warm memory (weekly summary)
    if WARM_MEMORY_FILE.exists():
        warm = json.loads(WARM_MEMORY_FILE.read_text())
        if warm:
            memory_parts.append(f"\n=== WEEKLY SUMMARY ({warm.get('week_of', 'N/A')}) ===")
            memory_parts.append(f"Avg rating: {warm.get('avg_rating', 'N/A')}/10")
            if warm.get('patterns_noted'):
                memory_parts.append(f"Patterns: {'; '.join(warm['patterns_noted'][:3])}")
    
    return "\n".join(memory_parts) if memory_parts else "[No memory data yet]"

def archive_old_data():
    """Archive data older than 30 days to cold storage."""
    init_memory_system()
    
    # Archive old recommendations from RECOMMENDATIONS.md
    recs_file = BASE_DIR / "docs" / "RECOMMENDATIONS.md"
    if recs_file.exists():
        content = recs_file.read_text()
        # Keep only active recommendations, archive the rest
        # This is a simplified version - can be enhanced
        pass

__all__ = [
    'init_memory_system',
    'update_hot_memory',
    'update_warm_memory',
    'get_memory_for_run',
    'archive_old_data',
    'compress_run_output'
]