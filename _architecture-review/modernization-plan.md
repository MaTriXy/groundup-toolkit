# Modernization Plan

Step-by-step plan to reorganize and improve the codebase, prioritized by impact and risk.

---

## Proposed Folder Structure

```
groundup-toolkit/
├── lib/                          # Shared libraries (existing, expanded)
│   ├── __init__.py
│   ├── config.py                 # Config singleton (existing)
│   ├── config.js                 # JS config -- REWRITE to read YAML
│   ├── safe_url.py               # SSRF protection (existing)
│   ├── claude.py                 # NEW: Shared Claude API client
│   ├── brave.py                  # NEW: Shared Brave Search client
│   ├── whatsapp.py               # NEW: Shared WhatsApp sender
│   ├── email.py                  # NEW: Shared email sender (gog/gws-auth)
│   ├── hubspot.py                # NEW: Shared HubSpot operations
│   └── gws.py                    # NEW: Google Workspace helper (from server migration)
├── skills/                       # OpenClaw skills (existing structure)
│   ├── content-writer/
│   ├── deal-analyzer/
│   ├── deck-analyzer/            # DEPRECATE (subsumed by deal-analyzer)
│   ├── deal-automation/
│   ├── deal-logger/
│   ├── founder-scout/
│   ├── google-workspace/
│   ├── keep-on-radar/
│   ├── linkedin/
│   ├── meeting-bot/              # CLEAN UP dead JS files
│   ├── meeting-reminders/
│   ├── ping-teammate/
│   └── vc-automation/
├── scripts/                      # Cron jobs and system scripts
│   ├── email-to-deal-automation.py   # REFACTOR: split concerns
│   ├── health-check.sh               # KEEP + absorb watchdog
│   ├── daily-maintenance.sh
│   ├── load-env.sh
│   ├── run-scheduled.sh
│   ├── meeting-brief-optin-handler.py
│   └── whatsapp-watchdog.sh           # REMOVE (merge into health-check)
│                                      # whatsapp-healthcheck.sh REMOVED
├── exports/                      # Standalone modules for external use
│   └── deal-analyzer/
├── services/                     # Systemd service files
│   └── linkedin-browser.service
├── cron/
│   └── crontab.example           # UPDATE with missing jobs
├── docs/                         # UPDATE all docs
├── config.example.yaml
├── .env.example
├── install.sh
└── README.md                     # UPDATE with full skill list
```

---

## Migration Steps (In Order)

### Phase 1: Security Fixes [Critical]

**Step 1.1: Remove Google cookies from git history**
- What: Delete `skills/meeting-bot/google-cookies.json` from git history using `git filter-repo` or BFG
- Why: Real authentication cookies are committed to the repo
- Outcome: Cookie values no longer accessible in git history
- Verify `.gitignore` includes `google-cookies.json` (it does)

**Step 1.2: Fix `lib/config.js` PII exposure**
- What: Rewrite `lib/config.js` to read from `config.yaml` using `js-yaml` (already installed). Remove hardcoded names, emails, phones, and HubSpot IDs.
- Why: Real PII committed to git
- Outcome: JS config is dynamic, no PII in source code
- Files changed: `lib/config.js`

**Step 1.3: Fix LinkedIn shell injection**
- What: Change line 34 of `skills/linkedin/linkedin` from `print(urllib.parse.quote('$QUERY'))` to `print(urllib.parse.quote(sys.argv[1]))` with `"$QUERY"` passed as an argument.
- Why: Shell injection via single-quote in search query
- Outcome: Arbitrary code execution prevented
- Files changed: `skills/linkedin/linkedin`

### Phase 2: Create Shared Service Layer [High]

**Step 2.1: Create `lib/claude.py`**
- What: Extract Claude API client with configurable retry logic (1-5 attempts), exponential backoff for 429/529, configurable model/max_tokens/timeout.
- Why: Duplicated 5 times with inconsistent retry behavior
- Outcome: Single source of truth for Claude calls. All skills get retry protection.
- Files changed: New `lib/claude.py`. Update imports in: `writer.py`, `deal-analyzer/analyzer.py`, `deck-analyzer/analyzer.py`, `scout.py`, `radar.py`

**Step 2.2: Create `lib/brave.py`**
- What: Extract Brave Search client function.
- Why: Duplicated 3 times identically
- Outcome: Single implementation
- Files changed: New `lib/brave.py`. Update: `writer.py`, `deal-analyzer/analyzer.py`, `radar.py`

**Step 2.3: Create `lib/whatsapp.py`**
- What: Extract WhatsApp sender with configurable account, retries, delay.
- Why: Duplicated 5 times with inconsistent `--account` usage
- Outcome: Consistent WhatsApp behavior across all skills
- Files changed: New `lib/whatsapp.py`. Update: `writer.py`, `deal-analyzer/analyzer.py`, `scout.py`, `radar.py`, `reminders.py`

**Step 2.4: Create `lib/email.py`**
- What: Extract email sender that handles temp file creation, proper escaping, and gog/gws-auth compatibility.
- Why: Duplicated 4+ times
- Outcome: Single email implementation
- Files changed: New `lib/email.py`. Update: `writer.py`, `deal-analyzer/analyzer.py`, `scout.py`, `radar.py`

**Step 2.5: Create `lib/hubspot.py`**
- What: Extract HubSpot operations (search company, create company, create deal, add note, move deal stage) using the Maton API gateway.
- Why: HubSpot API calls scattered across deal-analyzer, keep-on-radar, meeting-reminders, email-to-deal, deal-pass-automation
- Outcome: Centralized HubSpot access with consistent error handling
- Files changed: New `lib/hubspot.py`. Update callers incrementally.

### Phase 3: Clean Up Dead Code [High]

**Step 3.1: Delete dead meeting-bot JS files**
- What: Remove 10 prototype/test files: `force-click-join.js`, `force-join.js`, `headed-join.js`, `join-authenticated.js`, `join-current-meeting.js`, `join-now.js`, `setup-auth.js`, `stealth-join.js`, `test-join-fixed.js`, `test-join.js`
- Why: All are dead code superseded by `camofox-join.js`. Total 950 lines of unmaintained code with no SSRF protection.
- Outcome: Cleaner codebase, reduced confusion
- Also: Remove `puppeteer`/`puppeteer-extra` from `package.json`

**Step 3.2: Remove dead imports and functions**
- What: Clean up across files:
  - `email-to-deal-automation.py`: remove `safe_request` import, duplicate `glob`/`timedelta` imports
  - `meeting-brief-optin-handler.py`: remove `json`, `timedelta` imports; remove `create_opt_in_instructions()`
  - `camofox-join.js`: remove `firefox`, `launchOptions` imports
  - `meeting-bot`: remove redundant `import shlex` at line 231
- Why: Dead code clutters the codebase
- Outcome: Each file imports only what it uses

**Step 3.3: Deprecate deck-analyzer**
- What: Add deprecation notice to `skills/deck-analyzer/SKILL.md`. Point users to `deal-analyzer` with an `extract-only` mode.
- Why: deck-analyzer is a strict subset of deal-analyzer with less SSRF protection and no retry logic
- Outcome: Clear migration path; eventually remove deck-analyzer

**Step 3.4: Remove or archive `vc-automation/linkedin-api-helper.py`**
- What: The LinkedIn API helper is non-functional (acknowledged in the code itself). Remove or move to `docs/archive/`.
- Why: Misleading presence -- developers might try to use it
- Outcome: Only the working LinkedIn approach (browser automation) remains

### Phase 4: Consolidate Health Monitoring [Medium]

**Step 4.1: Remove `whatsapp-healthcheck.sh`**
- What: Delete `scripts/whatsapp-healthcheck.sh`
- Why: Strictly weaker than both `health-check.sh` (which has alerting) and `whatsapp-watchdog.sh` (which has send test + escalation)
- Outcome: One less redundant script

**Step 4.2: Merge watchdog escalation into health-check**
- What: Add Twilio phone call escalation to `health-check.sh` WhatsApp check. Add email cooldown. Standardize on `systemctl restart` for gateway.
- Why: Currently 3 scripts with 3 different restart mechanisms
- Outcome: Single health monitoring script with full escalation chain
- After: Remove `whatsapp-watchdog.sh` or reduce to send-test-only

**Step 4.3: Standardize `.env` loading**
- What: Create a minimal `scripts/source-env.sh` that properly handles quote-stripping, equals-in-values, and can be sourced by all bash scripts. Update all scripts to use it.
- Why: `.env` loading is duplicated 5+ times with different bugs in each
- Outcome: Consistent, correct environment loading

### Phase 5: Fix Structural Issues [Medium]

**Step 5.1: Add file lock to email-to-deal-automation**
- What: Add `fcntl.flock` at script start, consistent with founder-scout, keep-on-radar, and meeting-reminders.
- Why: 10-minute cron can overlap with slow deck processing
- Outcome: No duplicate deals from concurrent runs

**Step 5.2: Replace source-code opt-in with config file**
- What: Replace the regex-based modification of `meeting-brief-automation.py` with a JSON file (`data/meeting-brief-optin.json`) that stores `{email: opted_in}` mappings.
- Why: Modifying Python source code at runtime is fragile and error-prone
- Outcome: Safe, atomic opt-in/opt-out state management
- Also: Remove duplicate opt-in logic from `email-to-deal-automation.py`

**Step 5.3: Fix bare `except:` clauses**
- What: Replace `except:` with `except Exception:` in email-to-deal-automation.py (lines 84, 1395, 1428) and reminders.py (line 699).
- Why: Bare except catches KeyboardInterrupt/SystemExit
- Outcome: Scripts can be interrupted cleanly

**Step 5.4: Move hardcoded HubSpot stage IDs to config**
- What: Replace `"1138024523"` in radar.py and hardcoded stage map in reminders.py with values from `config.hubspot_pipelines`.
- Why: Environment-specific values break portability
- Outcome: HubSpot stage IDs are configurable

**Step 5.5: Fix timezone in create-calendar-event**
- What: Replace hardcoded `+02:00` with proper timezone resolution using `zoneinfo.ZoneInfo('Asia/Jerusalem')` (Python 3.9+).
- Why: Events created during DST will be off by 1 hour
- Outcome: Correct event times year-round

### Phase 6: Standardize Persistence [Low]

**Step 6.1: Consolidate state file locations**
- What: Move `skills/content-writer/state.json` and `~/.groundup-toolkit/state/deal-analyzer-*.json` to `<toolkit-root>/data/`.
- Why: Three different state locations is confusing
- Outcome: All persistent state in `<toolkit-root>/data/`

**Step 6.2: Use SQLite context managers**
- What: Wrap SQLite connections in `with` blocks in `scout.py` and `radar.py`.
- Why: Prevent leaked connections on exceptions
- Outcome: Safer database handling

### Phase 7: Documentation Update [Low]

**Step 7.1: Update README**
- Add Content Writer, Deal Analyzer, Founder Scout to "What It Does" table
- Update project structure tree to include all directories
- Replace `nohup openclaw gateway &` with systemd reference

**Step 7.2: Update docs/services.md**
- Replace LinkedIn `li_at` cookie approach with browser automation (CDP port 18801)
- Update gateway startup to systemd

**Step 7.3: Update docs/architecture.md**
- Replace "MCP bridge" for LinkedIn with "browser automation via CDP"
- Add data flows for Deal Analyzer, Founder Scout, Keep on Radar

**Step 7.4: Update docs/skills.md**
- Add Deal Analyzer, Founder Scout, Keep on Radar

**Step 7.5: Update cron/crontab.example**
- Add Keep on Radar (monthly review, 2h reply checks)
- Add opt-in handler (if running as separate cron)
- Remove whatsapp-healthcheck
- Add `MAILTO=""` directive

**Step 7.6: Standardize naming**
- Pick one: "Camofox" or "Camoufox" -- use consistently
- Standardize Brave API key: `BRAVE_SEARCH_API_KEY` everywhere

### Phase 8: Port gws-auth Migration to Repo [Low]

**Step 8.1: Add `lib/gws.py` to repo**
- What: The server has been migrated from `gog` to `gws-auth` with a shared `lib/gws.py` module. Port this to the repository.
- Why: Keep repo and server in sync
- Outcome: Repo reflects the actual deployed state

**Step 8.2: Update all Python scripts to use gws-auth**
- What: Apply the same gog -> gws-auth migration that was done on the server
- Files: All Python files currently calling `gog` CLI

**Step 8.3: Update bash wrappers**
- What: Replace `gog` calls with `gws-auth` in google-workspace skill scripts
- Files: `google-workspace`, `calendar-for-user`, `download-google-doc`

---

## Priority Summary

| Priority | Steps | Impact |
|----------|-------|--------|
| **Critical** | 1.1, 1.2, 1.3 | Security fixes (credential leak, PII exposure, shell injection) |
| **High** | 2.1-2.5, 3.1-3.4 | Eliminate duplication, remove dead code, create service layer |
| **Medium** | 4.1-4.3, 5.1-5.5 | Consolidate monitoring, fix structural bugs |
| **Low** | 6.1-6.2, 7.1-7.6, 8.1-8.3 | Standardize persistence, update docs, sync with server |

---

## Estimated Scope

- **Phase 1 (Security):** 3 changes, ~1 hour
- **Phase 2 (Service Layer):** 5 new files + update 10+ existing files, ~4 hours
- **Phase 3 (Dead Code):** Delete 10+ files + clean imports, ~1 hour
- **Phase 4 (Health Monitoring):** Consolidate 3 scripts into 1, ~2 hours
- **Phase 5 (Structural):** 5 targeted fixes, ~2 hours
- **Phase 6 (Persistence):** 2 minor changes, ~30 min
- **Phase 7 (Docs):** 6 doc updates, ~1 hour
- **Phase 8 (gws-auth):** Port server migration to repo, ~3 hours
