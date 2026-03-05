# Architecture Issues

All structural, code quality, and security issues found during the review, organized by category and priority.

---

## Security

### [Critical] Real Google Auth Cookies Committed to Git
- **File:** `skills/meeting-bot/google-cookies.json` (275 lines)
- **Details:** Contains 18 real Google authentication cookies (SID, HSID, SSID, APISID, SAPISID, NID, etc.) for the assistant's Google account. These cookies grant full access to Gmail, Google Meet, Google Drive, and all Google services.
- **Impact:** Anyone with repo access has the assistant's full Google session. Even if expired, the cookie values may reveal session patterns.
- **Fix:** Delete from git history (`git filter-branch` or `git filter-repo`), add to `.gitignore` (already listed but file was committed before the ignore rule).

### [Critical] Hardcoded PII in `lib/config.js`
- **File:** `lib/config.js` (lines 9-28)
- **Details:** Real names, email addresses, phone numbers, and HubSpot owner IDs for all 5 team members are hardcoded and committed to git. The file is NOT in `.gitignore`.
- **Impact:** PII exposure. Contact information for the entire team is in the public/shared repo.
- **Fix:** Rewrite to read from `config.yaml`. Add `lib/config.js` to `.gitignore` or make it dynamic.

### [High] Shell Injection in LinkedIn Skill
- **File:** `skills/linkedin/linkedin` (line 34)
- **Details:** `$QUERY` is interpolated into a Python single-quoted string: `print(urllib.parse.quote('$QUERY'))`. A query containing a single quote breaks Python syntax and allows arbitrary code execution.
- **Example:** `linkedin search "test'; import os; os.system('rm -rf /');"` would execute the injected code.
- **Fix:** Pass `$QUERY` via `sys.argv` instead of string interpolation: `python3 -c "import sys, urllib.parse; print(urllib.parse.quote(sys.argv[1]))" "$QUERY"`

### [Medium] DNS TOCTOU in SSRF Protection
- **File:** `lib/safe_url.py` (lines 46-52 vs 79)
- **Details:** `is_safe_url()` resolves DNS and checks IPs, then `safe_request()` makes a separate HTTP request that triggers a second DNS resolution. An attacker with DNS control could return a safe IP first, then a malicious IP.
- **Fix:** Pin the resolved IP and connect directly, or use `requests` hooks to verify the connection IP.

### [Medium] Dead JS Files Lack SSRF Protection
- **Files:** 10 files in `skills/meeting-bot/` (force-click-join.js, force-join.js, etc.)
- **Details:** All accept meeting URLs without validation. If accidentally invoked, they would navigate to arbitrary URLs.
- **Fix:** Delete the dead files (see Duplicates Report).

### [Low] Cookie File Permissions Inconsistency
- **Files:** `skills/meeting-bot/setup-auth.js` writes cookies without `mode: 0o600`; `authenticate-bot.js` correctly uses `0o600`.
- **Fix:** Both should use restrictive permissions (or delete both -- they're dead code).

### [Low] Default Credentials in Scripts
- **Files:** `scripts/health-check.sh` (line 24-25), `skills/google-workspace/download-google-doc` (line 25)
- **Details:** Default alert email/account placeholders like `admin@yourcompany.com` and `assistant@yourcompany.com` would silently fail or send to wrong addresses.
- **Fix:** Fail with a clear error if required config is missing rather than using a placeholder.

---

## Architecture

### [High] No Shared Service Layer -- Logic Duplicated Across Skills
- **Details:** Core operations (Claude API calls, Brave Search, WhatsApp, email, HubSpot) are copy-pasted across 5+ files with inconsistent implementations (see Duplicates Report).
- **Impact:** Bug fixes must be applied N times. Retry logic exists in 2 of 5 Claude callers. Rate limit handling is inconsistent.
- **Fix:** Create `lib/claude.py`, `lib/brave.py`, `lib/whatsapp.py`, `lib/email.py`, `lib/hubspot.py`.

### [High] Python Source Code Modified at Runtime for Opt-In
- **Files:** `scripts/email-to-deal-automation.py` (lines 594, 624), `scripts/meeting-brief-optin-handler.py` (lines 70-88)
- **Details:** Opt-in/opt-out toggles work by regex-replacing Python source code (`opted_in = True` -> `opted_in = False`) in `meeting-brief-automation.py`. This is fragile, non-atomic in one implementation, and will break if the file structure changes.
- **Fix:** Move opt-in state to a JSON config file read at runtime.

### [High] Monolithic Scripts with Mixed Concerns
- **File:** `scripts/email-to-deal-automation.py` (1478 lines)
- **Details:** Single file handles email monitoring, deck extraction, HubSpot CRM operations, Claude AI analysis, WhatsApp session scanning, opt-in/opt-out processing, and notification delivery. This is effectively 5 services in one file.
- **Fix:** Split into: email scanner, deck processor, CRM service, opt-in handler, notification service.

### [High] Inconsistent Config Access Pattern
- **Details:** Most Python skills use `from lib.config import config`. But `deck-analyzer/analyzer.py` reads `ANTHROPIC_API_KEY` directly from `os.environ`. `vc-automation/research-founder` doesn't use config at all. `lib/config.js` is fully hardcoded.
- **Fix:** Standardize all skills to use `lib/config`.

### [Medium] No Concurrency Protection on Email-to-Deal
- **File:** `scripts/email-to-deal-automation.py`
- **Details:** Unlike founder-scout, keep-on-radar, and meeting-reminders (which all use `fcntl.flock`), email-to-deal has no file lock. If cron fires while a previous run is still processing, duplicate deals could be created.
- **Fix:** Add `fcntl.flock` at the start, consistent with other cron scripts.

### [Medium] Three Different State Persistence Locations
- **Details:**
  - `skills/content-writer/state.json` -- in the skill directory itself
  - `~/.groundup-toolkit/state/deal-analyzer-*.json` -- in home directory
  - `<toolkit-root>/data/*.db` -- in the toolkit data directory
- **Fix:** Standardize to `<toolkit-root>/data/` for all persistent state.

### [Medium] Conflicting Gateway Restart Mechanisms
- **Details:** Three scripts restart the WhatsApp gateway differently:
  - `health-check.sh`: `systemctl restart openclaw-gateway`
  - `whatsapp-watchdog.sh`: `pkill -f openclaw-gateway` + `nohup openclaw gateway`
  - `whatsapp-healthcheck.sh`: `openclaw gateway restart`
- **Impact:** The `pkill + nohup` approach bypasses systemd and creates an unmanaged process. Concurrent execution could leave the gateway in an inconsistent state.
- **Fix:** All should use `systemctl restart openclaw-gateway`.

### [Low] `package.json` Dependencies Are Stale
- **File:** `skills/meeting-bot/package.json`
- **Details:** Declares `puppeteer`, `puppeteer-extra`, `puppeteer-extra-plugin-stealth`, `puppeteer-extra-plugin-user-preferences` -- none of which are used by the active `camofox-join.js` (which uses `playwright-core` loaded from Camoufox).
- **Fix:** Remove dead dependencies. Add `playwright-core` if it should be formally declared.

---

## Code Quality

### [High] Bare `except:` Clauses
- **Files:**
  - `scripts/email-to-deal-automation.py` (lines 84, 1395, 1428)
  - `skills/meeting-reminders/reminders.py` (line 699)
- **Details:** `except:` without `Exception` catches `KeyboardInterrupt` and `SystemExit`, making the script impossible to interrupt cleanly.
- **Fix:** Change to `except Exception:`.

### [High] Hardcoded HubSpot Stage IDs
- **Files:**
  - `skills/keep-on-radar/radar.py` (line 45: `"1138024523"`)
  - `skills/meeting-reminders/reminders.py` (lines 492-500: hardcoded stage name map)
- **Details:** HubSpot pipeline stage IDs are environment-specific. These will break for any other HubSpot portal.
- **Fix:** Move to `config.yaml` (already has `hubspot.pipelines` section with stage names).

### [Medium] Dead Code
- **Files:**
  - `scripts/meeting-brief-optin-handler.py`: `create_opt_in_instructions()` defined but never called
  - `scripts/meeting-brief-optin-handler.py`: `json`, `timedelta` imported but never used
  - `scripts/email-to-deal-automation.py`: `safe_request` imported but never used; `glob`, `timedelta` imported twice
  - `skills/meeting-bot/camofox-join.js`: `firefox`, `launchOptions` imported but unused
  - `skills/meeting-bot/meeting-bot` (line 231): redundant `import shlex`
  - `skills/vc-automation/linkedin-api-helper.py`: largely non-functional (LinkedIn API limitations acknowledged in code)
  - 10 dead JS files in meeting-bot (see Duplicates Report)

### [Medium] Inconsistent Error Handling Across Skills
- **Details:**
  - `deal-analyzer`: 5-retry with exponential backoff on Claude 429/529
  - `founder-scout`: 3-retry on Claude 429
  - `content-writer`, `keep-on-radar`, `deck-analyzer`: No retry at all
  - All use broad `try/except Exception` with `print()` to stderr
  - No structured logging anywhere
- **Fix:** Shared Claude client with configurable retry. Consider `logging` module.

### [Medium] Hardcoded Timezone in Calendar Event Creation
- **File:** `skills/google-workspace/create-calendar-event` (line 69)
- **Details:** Uses `+02:00` (Israel Standard Time). During DST (March-October), Israel is `+03:00`. Events created in summer will be off by 1 hour.
- **Fix:** Use `pytz` or `zoneinfo` to determine the correct offset for `Asia/Jerusalem`.

### [Medium] Deprecated `datetime.utcnow()` Usage
- **Files:** `skills/google-workspace/get-my-calendar`, various other scripts
- **Details:** `datetime.utcnow()` is deprecated in Python 3.12+. Should use `datetime.now(timezone.utc)`.
- **Fix:** Replace with `datetime.now(timezone.utc)`.

### [Low] No Connection Pooling for HTTP Requests
- **Files:** All Python skills using `requests`
- **Details:** Every HTTP call creates a new TCP connection. The deal-analyzer makes 20+ HTTP calls per run (15 Brave searches + 13 Claude calls + HubSpot operations).
- **Fix:** Use `requests.Session()` for connection pooling within each skill run.

### [Low] SQLite Connections Without Context Managers
- **Files:** `skills/founder-scout/scout.py`, `skills/keep-on-radar/radar.py`
- **Details:** Database connections are opened/closed manually without `with` blocks, risking leaked connections on exceptions.
- **Fix:** Use `with sqlite3.connect(...) as conn:` pattern.

### [Low] Escaped Shebang
- **File:** `skills/google-workspace/google-workspace` (line 1: `#\!/bin/bash`)
- **Fix:** Change to `#!/bin/bash`.

---

## Documentation

### [Medium] README Missing Skills
- **Details:** README "What It Does" table and project structure tree do not include Content Writer, Deal Analyzer, Founder Scout, or the `exports/` directory.
- **Fix:** Update README to cover all skills.

### [Medium] LinkedIn Documentation Inconsistencies
- **Details:** Three different LinkedIn access methods documented:
  - `docs/services.md`: `li_at` cookie extraction to `~/.linkedin-mcp/session.json` (old)
  - `docs/architecture.md`: "MCP bridge" (old)
  - `skills/linkedin/SKILL.md`: Browser automation via CDP on port 18801 (current)
- **Fix:** Update all docs to reflect the current browser automation approach.

### [Medium] Gateway Startup Method Outdated
- **Details:** Multiple docs reference `nohup openclaw gateway &` but actual deployment uses a systemd service.
- **Fix:** Update docs to reference `systemctl start openclaw-gateway`.

### [Low] Camofox/Camoufox Naming Inconsistency
- **Details:** Called "Camofox" in meeting-bot SKILL.md, "Camoufox" in architecture.md and setup-guide.md.
- **Fix:** Standardize naming.

### [Low] SKILL.md Over-Promises for Deal Logger
- **File:** `skills/deal-logger/SKILL.md`
- **Details:** Documents multiple deal sources (file/API/env) and log targets (file/CRM/Notion), but the script only supports file-based I/O.
- **Fix:** Update SKILL.md to match actual implementation.

### [Low] Brave API Key Naming Inconsistency
- **Details:** Content-writer uses `BRAVE_API_KEY`; all other skills use `BRAVE_SEARCH_API_KEY`.
- **Fix:** Standardize to one name.

---

## Cron Jobs

### [Medium] Meeting Auto-Join High Frequency
- **Schedule:** `*/3 * * * *` (every 3 minutes)
- **Details:** If it launches browser automation each cycle, this is resource-intensive. The script does have dedup logic (12h window) but still makes calendar API calls every 3 minutes.
- **Fix:** Consider 5-minute interval. The -2 to +5 minute time window still catches meetings with a 5-min cron.

### [Medium] No Lockfile on Email-to-Deal
- **Details:** The 10-minute cron could overlap with a slow previous run (deck analysis + HubSpot operations can take minutes).
- **Fix:** Add `fcntl.flock` consistent with other scripts.

### [Low] No MAILTO in Crontab
- **File:** `cron/crontab.example`
- **Details:** No `MAILTO` directive. Cron output goes to default local mail, which piles up unread.
- **Fix:** Add `MAILTO=""` to suppress, or route to a monitored address.
