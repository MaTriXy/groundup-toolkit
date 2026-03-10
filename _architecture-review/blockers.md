# Blockers & Risks

Items that need human decision or are too risky to execute autonomously.

---

## Critical — Needs Human Action

### 1. ~~Google cookies in git history~~ — FALSE ALARM
- **File:** `skills/meeting-bot/google-cookies.json`
- **Issue:** File exists on disk but was **never committed** to git history (gitignored from the start)
- **Status:** RESOLVED — no action needed

---

## Low — Remaining Items

### 3. Server deployment sync
- **Issue:** All local repo changes need to be deployed to server (77.42.93.149)
- **Action:** Copy updated scripts to `/root/` and `/root/.openclaw/scripts/` on server
- **Status:** Ready — all changes committed

---

## Resolved

- **deck-analyzer deprecation** — Deprecation notice added to SKILL.md
- **vc-automation/linkedin-api-helper.py** — Deleted (non-functional)
- **whatsapp-healthcheck.sh** — Deleted (redundant)
- **whatsapp-watchdog.sh** — Deleted (escalation merged into health-check.sh)
- **HubSpot stage IDs** — Added `stages` to config.yaml, reminders.py reads from config with fallback
- **Opt-in handler** — Replaced source-code regex modification with JSON file (`data/meeting-brief-optin.json`)
- **SQLite context managers** — All connections in scout.py and radar.py now use `with` blocks
- **State file consolidation** — All state files now use `data/` directory (content-writer, deal-analyzer, meeting-bot, health-alerts)
- **gws-auth migration** — All scripts migrated from `gog` to `gws-auth` CLI; `get_google_access_token()` uses gws-auth credentials
- **Google cookies in git history** — False alarm; file was never committed (gitignored from start)
