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

---

## Remaining Structural Fixes

### 2026-03-10 — Bare except, file lock, config consistency

**Bare `except:` → specific exceptions:**
- `scripts/email-to-deal-automation.py` line 1462: `except:` → `except OSError:`
- `scripts/email-to-deal-automation.py` line 1511: `except:` → `except Exception:`

**Concurrency protection:**
- `scripts/email-to-deal-automation.py`: Added `fcntl.flock(LOCK_EX | LOCK_NB)` in `main()`

**Config consistency:**
- `skills/deck-analyzer/analyzer.py`: `os.environ.get('ANTHROPIC_API_KEY')` → `config.anthropic_api_key`
- `scripts/meeting-brief-optin-handler.py`: `os.environ.get("WHATSAPP_ACCOUNT")` → `config.whatsapp_account`
- `skills/meeting-reminders/reminders.py`: Removed redundant `sys.path.insert`

### 2026-03-10 — Health monitoring consolidation

- `scripts/health-check.sh`: Added `escalate_phone_call()` with Twilio + 1-hour cooldown
- `scripts/health-check.sh`: Standardized all restarts to `systemctl --user restart openclaw-gateway`
- `scripts/health-check.sh`: Added phone escalation to WhatsApp failure paths

### 2026-03-10 — Delete whatsapp-watchdog.sh

- Deleted `scripts/whatsapp-watchdog.sh` (escalation merged into health-check.sh)
- Removed watchdog cron entry from `cron/crontab.example`

### 2026-03-10 — HubSpot stage IDs in config

- `config.example.yaml`: Added full `stages` map with labels and tips to pipeline config
- `lib/config.py`: Added `get_stage_map()` method to read stages from config
- `skills/meeting-reminders/reminders.py`: STAGE_MAP now loads from config with hardcoded fallback

### 2026-03-10 — Opt-in handler → JSON config

- Created `data/meeting-brief-optin.json` for opt-in state storage
- `scripts/meeting-brief-optin-handler.py`: Replaced regex source-code modification with JSON read/write
- `scripts/email-to-deal-automation.py`: Same — replaced regex source-code modification with JSON read/write
- Both use atomic file write (tempfile + os.replace) for safety

### 2026-03-10 — SQLite context managers

- `skills/founder-scout/scout.py`: All ScoutDatabase methods + 3 loose calls now use `with db._conn() as conn:`
- `skills/keep-on-radar/radar.py`: All RadarDatabase methods now use `with db._conn() as conn:`
- Both use `contextlib.closing(sqlite3.connect(...))` for safe cleanup on exceptions

### 2026-03-10 — Documentation updates

- `_architecture-review/service-map.md`: Full update reflecting current state
- `_architecture-review/refactor-summary.md`: Updated metrics and remaining items
- `_architecture-review/blockers.md`: Moved completed items to Resolved
- `lib/README.md`: Added gws.py and safe_log.py entries
