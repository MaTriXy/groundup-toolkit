# Migration Log

Chronological record of every change made during the rearchitecture.

---

## Phase 1: Establish New Structure

### 2026-03-05 — Created skeleton structure

**Added:**
- `_architecture-review/migration-log.md` (this file)
- `_architecture-review/blockers.md`
- `data/` directory (for consolidated state files)
- `lib/README.md`
- `skills/README.md`
- `scripts/README.md`
- `exports/README.md`
- `data/README.md`
- `services/README.md`
- `cron/README.md`
- `docs/README.md`

**No logic changes. No files moved.**

---

## Phase 2: Eliminate Duplicates

### 2026-03-05 — Created shared service layer

**New shared libraries:**
- `lib/claude.py` — Shared Claude API client (5-retry, 429/529 backoff, configurable model/tokens/timeout)
- `lib/brave.py` — Shared Brave Search client
- `lib/whatsapp.py` — Shared WhatsApp sender via openclaw CLI (with optional --account)
- `lib/email.py` — Shared email sender via gog CLI (temp file pattern)
- `lib/hubspot.py` — Shared HubSpot CRM operations via Maton API gateway (search, create, update, associate, notes)

**Updated consumers to use shared libraries:**
- `skills/content-writer/writer.py` — Removed local call_claude, brave_search, send_whatsapp, send_email (~120 lines)
- `skills/deal-analyzer/analyzer.py` — Removed local call_claude, brave_search, send_whatsapp, send_email; HubSpot functions now thin wrappers (~120 lines)
- `skills/founder-scout/scout.py` — Removed local call_claude, send_whatsapp, send_email (~95 lines)
- `skills/keep-on-radar/radar.py` — Removed local call_claude, brave_search, send_whatsapp, send_email, 4 HubSpot functions (~200 lines)
- `skills/meeting-reminders/reminders.py` — Replaced send_whatsapp_message with wrapper, 3 HubSpot functions replaced (~130 lines)

### 2026-03-05 — Deleted dead code

**Deleted 10 dead JS prototype files from meeting-bot (~950 lines):**
- force-click-join.js, force-join.js, headed-join.js, join-authenticated.js
- join-current-meeting.js, join-now.js, setup-auth.js, stealth-join.js
- test-join-fixed.js, test-join.js

**Cleaned dead dependencies:**
- `skills/meeting-bot/package.json` — Removed puppeteer, puppeteer-extra, puppeteer-extra-plugin-stealth, puppeteer-extra-plugin-user-preferences

**Cleaned dead imports:**
- `scripts/email-to-deal-automation.py` — Removed unused `safe_request` import
- `scripts/meeting-brief-optin-handler.py` — Removed unused `json`, `timedelta` imports; removed unused `create_opt_in_instructions()` function
- `skills/meeting-bot/camofox-join.js` — Removed unused `launchOptions`, `firefox` imports
- `skills/meeting-bot/meeting-bot` — Removed redundant `import shlex`, `import tempfile` inside function

**Deprecation and removal:**
- `skills/deck-analyzer/SKILL.md` — Added deprecation notice pointing to deal-analyzer
- `skills/vc-automation/linkedin-api-helper.py` — Deleted (non-functional)
- `scripts/whatsapp-healthcheck.sh` — Deleted (redundant, covered by health-check.sh)

---

## Phase 4: Fix Architectural Issues

### 2026-03-05 — Security fixes (Critical)

**Step 1.1: Google cookies in git history** — BLOCKED (see blockers.md). Requires `git filter-repo` force-push.

**Step 1.2: Fix `lib/config.js` PII exposure:**
- Rewrote `lib/config.js` to dynamically read `config.yaml` via Python yaml loader
- Removed all hardcoded names, emails, phone numbers, and HubSpot owner IDs
- Maintained backward-compat exports (teamMembers, christinaEmail, groundupDomain)
- Added .env loading matching config.py behavior

**Step 1.3: Fix LinkedIn shell injection:**
- `skills/linkedin/linkedin` line 34: Changed from `print(urllib.parse.quote('$QUERY'))` to `sys.argv[1]` with `"$QUERY"` passed as argument
- Prevents arbitrary code execution via single-quote injection

### 2026-03-05 — Code quality fixes

**Bare `except:` clauses → `except Exception:`:**
- `scripts/email-to-deal-automation.py` (lines 1395, 1428)
- `scripts/meeting-brief-optin-handler.py` (line 83)
- `skills/meeting-reminders/reminders.py` (line 557)

**Timezone fix:**
- `skills/google-workspace/create-calendar-event`: Replaced hardcoded `+02:00` with `zoneinfo.ZoneInfo('Asia/Jerusalem')` — handles DST correctly

**Escaped shebang:**
- `skills/google-workspace/google-workspace`: `#\!/bin/bash` → `#!/bin/bash`

**Concurrency protection:**
- `scripts/email-to-deal-automation.py`: Added `fcntl.flock` file lock to prevent overlapping cron runs

---

## Phase 5: Fix Cron Jobs

### 2026-03-05 — Updated crontab.example

- Added `MAILTO=""` directive to suppress unread cron mail
- Added Keep on Radar review (`0 9 15 * *`) and check-replies (`0 */2 * * *`)
- Added daily maintenance (`0 4 * * *`)
- Removed whatsapp-healthcheck.sh (script deleted in Phase 2)

---

## Phase 6: Consistency Pass

### 2026-03-05 — Naming and config consistency

- `skills/content-writer/SKILL.md`: `BRAVE_API_KEY` → `BRAVE_SEARCH_API_KEY`
- `docs/skills.md`: `BRAVE_API_KEY` → `BRAVE_SEARCH_API_KEY`
- `skills/meeting-bot/SKILL.md`: "Camofox" → "Camoufox" (correct product name)
