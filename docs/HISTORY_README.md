# 📁 HISTORY Folder — Daily Archive

## Purpose
The `HISTORY/` folder stores **complete daily archives** of all agent runs. It's a daily cumulative log.

## Structure
```
HISTORY/
  2026-04-22.md     ← All runs from April 22 (appended throughout the day)
  2026-04-23.md     ← All runs from April 23
  ...
```

## How It Works
- **Each day** = one file (e.g., `2026-04-22.md`)
- **Each run** = appended as a new section in that day's file with a timestamp (e.g., Run 1736 at 17:36 UTC)
- **Automatic archival**: The agent appends reports to the current day's history file in `HISTORY_DIR / f"{TODAY}.md"`

## Why Keep History?
1. **Debugging**: Track all runs throughout the day and see how thinking evolved
2. **Performance Review**: Compare early morning runs vs late-day runs
3. **Pattern Recognition**: Identify what ideas were mentioned multiple times across runs
4. **Backup**: If a specific REPORTS/*.md file is deleted, the full content is still in HISTORY
5. **Replay**: Review what the agent was saying about specific tickers across time

## Querying History
To find all mentions of a ticker (e.g., PLTR) across the day:
```bash
grep -n "PLTR" HISTORY/2026-04-22.md
```

To count how many runs happened on a specific day:
```bash
grep "Run [0-9]" HISTORY/2026-04-22.md | wc -l
```

## Size Management
- The HISTORY folder grows ~1-3 MB per day (depending on run frequency and content length)
- Archive older files to cold storage if needed (recommend keeping last 30 days in HISTORY/)
- You can safely delete HISTORY files without affecting future runs — REPORTS/ is your primary archive

## Key Difference: HISTORY vs REPORTS
| Aspect | HISTORY | REPORTS |
|--------|---------|---------|
| **Structure** | 1 file per day, all runs concatenated | 1 file per run (timestamp in filename) |
| **Lookup** | Search within daily file | Find specific run by timestamp |
| **Size** | Larger (all day's runs) | Smaller (single run) |
| **Use Case** | Daily review, debugging, pattern analysis | Sharing, specific run reference |

---
**Next time you're confused about what the agent was thinking at a specific time, check HISTORY!**
