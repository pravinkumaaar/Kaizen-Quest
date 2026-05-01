"""
Learning Curator Skill

Manages the weekly learning theme system:
- Rotating weekly themes
- Daily deep-dives
- Educational content curation
- Learning progress tracking
"""

import re
from pathlib import Path
from datetime import datetime, timedelta

BASE_DIR = None
WEEKLY_THEMES_FILE = None

def init_learning_skill(base_dir=None):
    """Initialize with config from main agent."""
    global BASE_DIR, WEEKLY_THEMES_FILE
    if base_dir:
        BASE_DIR = Path(base_dir)
        WEEKLY_THEMES_FILE = BASE_DIR / "WEEKLY_THEMES.md"

# Theme rotation
THEME_ROTATION = [
    {
        'theme': 'Macroeconomics: How the World Economy Really Works',
        'subtopics': [
            'Day 1: Money & Inflation - What Makes Your Savings Worth Less',
            'Day 2: Interest Rates & The Fed - How Central Banks Control Everything',
            'Day 3: Supply & Demand - The Force Behind Every Price',
            'Day 4: Recessions & Business Cycles - Why Booms Turn to Busts',
            'Day 5: Currencies & Trade - Why the Dollar Matters Globally',
            'Day 6: Geopolitics & Economics - When Politics Changes Markets',
            'Day 7: Investment Implications - How to Profit from Economic Cycles'
        ]
    },
    {
        'theme': 'History Repeats: Lessons from Past Bubbles & Crashes',
        'subtopics': [
            'Day 1: Tulip Mania 1637 - The First Bubble',
            'Day 2: The Dot-Com Crash 2000 - Tech Hubris',
            'Day 3: The 2008 Financial Crisis - Systemic Risk',
            'Day 4: Crypto Winter 2022 - Modern Manias',
            'Day 5: Pattern Recognition - How to Spot Bubbles Early',
            'Day 6: Survivor Bias - Why We Ignore Lessons',
            'Day 7: Building Anti-Fragile Portfolios - Learning from History'
        ]
    },
    {
        'theme': 'Artificial Intelligence: The Technology Reshaping Everything',
        'subtopics': [
            'Day 1: From Narrow AI to General AI - The Holy Grail',
            'Day 2: Deep Learning Explosion - How Neural Networks Work',
            'Day 3: AI in Medicine - Cancer Detection & Drug Discovery',
            'Day 4: AI in Finance - Algorithmic Trading & Risk Management',
            'Day 5: AI Alignment - The Problem of Values & Control',
            'Day 6: The AI Arms Race - Geopolitical Implications',
            'Day 7: Investment Plays - How to Profit from the AI Revolution'
        ]
    },
    {
        'theme': 'Energy & Climate: The Next Mega-Trend',
        'subtopics': [
            'Day 1: The Physics of Energy - Why We Need More Than We Think',
            'Day 2: Fossil Fuels in Decline - When Peak Oil Finally Comes',
            'Day 3: Renewables Revolution - Solar, Wind, Battery Breakthroughs',
            'Day 4: Nuclear Energy - Fission & Fusion\'s Comeback',
            'Day 5: The Grid Problem - Storage & Distribution Challenges',
            'Day 6: Climate Finance - Carbon Credits & Green Bonds',
            'Day 7: Energy Investing - Who Wins in the Transition'
        ]
    },
    {
        'theme': 'Human Longevity & Biohacking - Living Longer, Better',
        'subtopics': [
            'Day 1: Why We Age - The Biology of Aging',
            'Day 2: Senescent Cells & Senolytics - Removing the Damage',
            'Day 3: Cellular Reprogramming - Yamanaka Factors & De-Aging',
            'Day 4: Metabolic Health - Glucose, Insulin, Ketones',
            'Day 5: Sleep, Exercise, Fasting - The Unglamorous Basics',
            'Day 6: Supplements & Biomarkers - What Actually Works',
            'Day 7: Biotech Investing - The Companies Racing to Extend Life'
        ]
    }
]

def get_or_create_weekly_theme() -> dict:
    """Manage rotating weekly theme system."""
    if not WEEKLY_THEMES_FILE or not WEEKLY_THEMES_FILE.exists():
        return create_initial_theme()
    
    try:
        content = WEEKLY_THEMES_FILE.read_text()
        theme_match = re.search(r'\*\*📌 Theme:\*\* (.+?)(?:\n|$)', content)
        week_match = re.search(r'\*\*Duration:\*\* Week of (\d{4}-\d{2}-\d{2})', content)
        
        theme_name = theme_match.group(1) if theme_match else 'Unspecified'
        week_start = week_match.group(1) if week_match else datetime.now().date().isoformat()
        
        today_date = datetime.now().date()
        week_date = datetime.fromisoformat(week_start).date()
        days_elapsed = (today_date - week_date).days
        
        if days_elapsed >= 7:
            return rotate_to_next_theme()
        
        return {
            'theme': theme_name,
            'week_start': week_start,
            'days_completed': days_elapsed,
            'subtopics': []
        }
    except Exception:
        return create_initial_theme()

def create_initial_theme() -> dict:
    """Create the first weekly theme."""
    initial_theme = {
        'theme': 'The AI Revolution: How Large Language Models Work',
        'week_start': datetime.now().date().isoformat(),
        'days_completed': 0,
        'subtopics': [
            'Day 1: Transformer Architecture - The Foundation',
            'Day 2: Attention Mechanisms - How AI Focuses on What Matters',
            'Day 3: Training & Scaling Laws - Why Bigger = Better (Sometimes)',
            'Day 4: Tokens & Embeddings - How AI Understands Language',
            'Day 5: Reasoning vs Memorization - What LLMs Actually Do',
            'Day 6: Hallucinations & Limitations - When AI Gets It Wrong',
            'Day 7: The Economic Impact - AI as Infrastructure'
        ]
    }
    
    if WEEKLY_THEMES_FILE:
        theme_content = f"""# 📚 Weekly Learning Themes

## Current Theme (Week of {initial_theme['week_start']})

**📌 Theme:** {initial_theme['theme']}

**Duration:** Week of {initial_theme['week_start']}
**Status:** In Progress (Day 1 of 7)

### Daily Deep Dives:
"""
        for subtopic in initial_theme['subtopics']:
            theme_content += f"\n- [ ] {subtopic}"
        
        WEEKLY_THEMES_FILE.write_text(theme_content, encoding="utf-8")
    
    return initial_theme

def rotate_to_next_theme() -> dict:
    """Rotate to a new weekly theme."""
    rotation_index = datetime.now().isocalendar()[1] % len(THEME_ROTATION)
    next_theme_data = THEME_ROTATION[rotation_index]
    
    new_theme = {
        'theme': next_theme_data['theme'],
        'week_start': datetime.now().date().isoformat(),
        'days_completed': 0,
        'subtopics': next_theme_data['subtopics']
    }
    
    if WEEKLY_THEMES_FILE:
        theme_content = f"""# 📚 Weekly Learning Themes

## Current Theme (Week of {new_theme['week_start']})

**📌 Theme:** {new_theme['theme']}

**Duration:** Week of {new_theme['week_start']}
**Status:** In Progress (Day 1 of 7)

### Daily Deep Dives:
"""
        for subtopic in new_theme['subtopics']:
            theme_content += f"\n- [ ] {subtopic}"
        
        theme_content += "\n\n---\n*New theme rotates each week. Archive your learnings.*\n"
        WEEKLY_THEMES_FILE.write_text(theme_content, encoding="utf-8")
    
    return new_theme

def get_today_subtopic() -> str:
    """Get today's learning subtopic based on day of week."""
    current_theme = get_or_create_weekly_theme()
    day_of_week = datetime.now().weekday()
    subtopics = current_theme.get('subtopics') or []
    
    if not subtopics:
        return "Learning: General topic"
    
    index = day_of_week % len(subtopics)
    return subtopics[index]

def generate_learning_content(theme_data: dict, digest: str = "") -> str:
    """Generate learning recommendation based on current theme."""
    theme = theme_data.get('theme', 'Learning')
    days_completed = theme_data.get('days_completed', 0)
    subtopic = get_today_subtopic()
    
    content = "## 📚 Learning Recommendation\n\n"
    content += f"**This Week's Theme:** {theme}\n\n"
    content += f"**Today's Focus (Day {days_completed + 1}):** {subtopic}\n\n"
    content += "### Why This Matters:\n"
    content += "- Build mental models that compound over time\n"
    content += "- Understand the 'why' behind market movements\n"
    content += "- Connect dots across disciplines (AI, economics, history)\n\n"
    content += "### Action Items:\n"
    content += "1. Read/watch 1-2 resources on today's topic\n"
    content += "2. Write down 3 key takeaways\n"
    content += "3. Connect to your current investments/interests\n"
    
    return content

__all__ = [
    'init_learning_skill',
    'get_or_create_weekly_theme',
    'rotate_to_next_theme',
    'get_today_subtopic',
    'generate_learning_content',
    'THEME_ROTATION'
]
