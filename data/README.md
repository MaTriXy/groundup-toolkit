# data/ — Persistent State

All runtime state files (SQLite databases, JSON state, tracking files).

## Convention

- SQLite databases: `<skill-name>.db`
- JSON state: `<skill-name>-state.json`
- All files in this directory should be in .gitignore

## What belongs here

- SQLite databases (founder-scout, keep-on-radar, meeting-reminders)
- JSON state files (content-writer state, deal-analyzer tracking)
- Any persistent data that survives restarts

## What does NOT belong here

- Config files (goes in project root or config/)
- Temporary files (use /tmp)
- Log files (use system logging)
