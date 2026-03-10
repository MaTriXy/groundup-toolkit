# Service Map

Complete reference for every service, skill, cron job, script, utility, and module in the GroundUp Toolkit.

---

## Core Libraries

### Config (Python)
- **File:** `lib/config.py` (268 lines)
- **Purpose:** Central Python configuration singleton. Loads `config.yaml` and `.env`, exposes all settings as properties.
- **Exposes:** `ToolkitConfig` class, `config` singleton instance with properties for assistant, team, HubSpot, scheduling, notifications, meeting bot, and API keys.
- **Depends on:** `pyyaml`, `config.yaml`, `.env`
- **Used by:** Every Python skill and script (content-writer, deal-analyzer, founder-scout, keep-on-radar, meeting-reminders, email-to-deal, meeting-brief-optin-handler, meeting-auto-join, meeting-bot, deal-pass-automation, get-my-calendar, create-calendar-event, calendar-for-user)
- **Notes:**
  - Hand-rolls `.env` parsing instead of using `python-dotenv`
  - `get_member_by_phone()` will `KeyError` if a member has no `phone` key
  - `reload()` does not re-read `.env`, only YAML
  - No validation of config.yaml structure
  - `founder_scout` config section has no accessor -- skills must reach into `config._data` directly

### Config (JavaScript)
- **File:** `lib/config.js`
- **Purpose:** Node.js equivalent of config.py. Reads config.yaml dynamically via Python subprocess.
- **Exposes:** `TOOLKIT_ROOT`, `config` object (assistant, team, credentials)
- **Depends on:** `config.yaml`, `.env`, Python3 subprocess
- **Used by:** `camofox-join.js`, `christina-scheduler` (external repo)
- **Notes:**
  - Dynamically reads config.yaml (no hardcoded PII)
  - Uses `execFileSync` for safe subprocess invocation

### Safe URL
- **File:** `lib/safe_url.py` (92 lines)
- **Purpose:** SSRF protection module. Validates URLs against domain allowlist and checks resolved IPs against private ranges.
- **Exposes:** `is_safe_url()`, `safe_request()`, `ALLOWED_DECK_DOMAINS` (12 domains)
- **Depends on:** `requests`, `socket`, `ipaddress`
- **Used by:** `deal-analyzer/analyzer.py`, `deck-analyzer/analyzer.py`, `email-to-deal-automation.py`
- **Notes:**
  - DNS TOCTOU vulnerability (check-then-use with separate resolution)
  - Only supports GET requests
  - `MAX_REDIRECTS = 5`

### Shared Claude Client
- **File:** `lib/claude.py`
- **Purpose:** Shared Claude API client with configurable retry logic (5 attempts), exponential backoff for 429/529 errors.
- **Exposes:** `call_claude(prompt, model, max_tokens, temperature, timeout, retries)`
- **Used by:** content-writer, deal-analyzer, founder-scout, keep-on-radar, meeting-reminders

### Shared Brave Search Client
- **File:** `lib/brave.py`
- **Purpose:** Brave Search API client.
- **Exposes:** `brave_search(query, count)`
- **Used by:** content-writer, deal-analyzer, keep-on-radar

### Shared WhatsApp Sender
- **File:** `lib/whatsapp.py`
- **Purpose:** WhatsApp message sender via openclaw CLI with retry logic.
- **Exposes:** `send_whatsapp(phone, message, account)`
- **Used by:** content-writer, deal-analyzer, founder-scout, keep-on-radar, meeting-reminders

### Shared Email Sender
- **File:** `lib/email.py`
- **Purpose:** Email sender via gws-auth CLI.
- **Exposes:** `send_email(to, subject, body, cc, bcc)`
- **Used by:** content-writer, deal-analyzer, founder-scout, keep-on-radar

### Shared HubSpot Client
- **File:** `lib/hubspot.py`
- **Purpose:** HubSpot CRM operations via Maton API gateway. Search, create, update companies/deals, add notes, manage associations.
- **Exposes:** `search_company()`, `create_company()`, `create_deal()`, `update_deal_stage()`, `add_note()`, `fetch_deals_by_stage()`, etc.
- **Used by:** deal-analyzer, keep-on-radar, meeting-reminders, email-to-deal

### Google Workspace Helper
- **File:** `lib/gws.py`
- **Purpose:** Google Workspace integration via gws-auth CLI. Gmail search/read/send/modify, calendar, drive.
- **Exposes:** `gws_gmail_search()`, `gws_gmail_thread_get()`, `gws_gmail_send()`, `gws_gmail_modify()`, `gws_gmail_attachment_download()`, `get_google_access_token()`
- **Used by:** email-to-deal, keep-on-radar, meeting-brief-optin-handler

### Safe Logging
- **File:** `lib/safe_log.py`
- **Purpose:** Logging utilities with PII redaction.
- **Exposes:** `sanitize_error()`, `safe_error()`

### Environment Loader
- **File:** `scripts/load-env.sh` (93 lines)
- **Purpose:** Security-focused env loader. Exports only whitelisted variables per job to limit blast radius.
- **Exposes:** Wrapper script -- not imported, used as `load-env.sh <job-name> <command>`
- **Depends on:** `.env` file
- **Used by:** Referenced in `founder-scout/SKILL.md` cron examples, `cron/crontab.example`
- **Notes:**
  - Only defines whitelists for 5 jobs: `meeting-reminders`, `meeting-bot`, `email-to-deal`, `founder-scout`, `watchdog`
  - Missing: `health-check`, `daily-maintenance`, `run-scheduled`, `meeting-brief-optin-handler`

---

## Skills

### Content Writer
- **File:** `skills/content-writer/writer.py` (1042 lines)
- **Entry point:** `skills/content-writer/content-writer` (41-line bash wrapper)
- **Purpose:** Generates LinkedIn posts, Substack notes, and newsletters in team members' authentic voice. Supports voice learning from submitted samples, "keep" flow for accepted content, and topic research via Brave Search.
- **Exposes:** `generate(message, sender_phone)`, `test()`, `main()`
- **Depends on:** `lib/config`, `requests`, Anthropic API (Sonnet for generation, Haiku for classification/voice analysis), Brave Search API, `gws-auth` CLI (email), `openclaw` CLI (WhatsApp)
- **Used by:** OpenClaw skill trigger (WhatsApp commands)
- **Notes:**
  - State file at `skills/content-writer/state.json` (non-standard location vs other skills using `~/.groundup-toolkit/state/` or `data/`)
  - Profile data in `skills/content-writer/profiles/<name>/` (voice.json, brand.json, audience.json, samples.json)
  - `call_claude()` has NO retry logic for 429 rate limits
  - `time` lazily imported inside `send_whatsapp()`
  - `send_email()` uses `gog gmail send --body-file` pattern

### Deal Analyzer
- **File:** `skills/deal-analyzer/analyzer.py` (2077 lines)
- **Entry point:** `skills/deal-analyzer/deal-analyzer` (79-line bash wrapper)
- **Purpose:** Full 12-section VC investment evaluation from pitch decks. 4-phase pipeline: Extract (Haiku) -> Research (Brave, ~15 queries) -> Analyze (Sonnet x12 parallel sections) -> Deliver (WhatsApp + email + Google Doc + HubSpot).
- **Exposes:** `quick_analyze()`, `deep_evaluate()`, `log_to_hubspot()`, `full_report()`, `run_demo()`, `demo_report()`, `demo_end()`, `test()`, `main()`
- **Depends on:** `lib/config`, `lib/safe_url`, `requests`, Anthropic API (Haiku + Sonnet), Brave Search API, HubSpot via Maton API, Google Drive API (creates Google Docs), Google OAuth2 (token refresh), `gws-auth` CLI (email), `openclaw` CLI (WhatsApp), Camofox browser (DocSend extraction)
- **Used by:** OpenClaw skill trigger, email-to-deal pipeline
- **Notes:**
  - Most complex file in the codebase (2077 lines)
  - `call_claude()` has robust 5-attempt retry for 429/529
  - State persisted to `~/.groundup-toolkit/state/deal-analyzer-state.json` and `deal-analyzer-demo.json`
  - `get_google_access_token()` duplicates logic that also exists in `lib/gws.py` on the server
  - Demo data has hardcoded dates evaluated at import time
  - No `requests.Session()` pooling despite 20+ HTTP calls per run

### Deck Analyzer [DEPRECATED]
- **File:** `skills/deck-analyzer/analyzer.py` (201 lines)
- **Entry point:** `skills/deck-analyzer/deck-analyzer` (150-line bash wrapper with inline Python)
- **Purpose:** Simpler deck extraction tool. Extracts 8 structured fields from pitch decks using Claude Haiku. No research phase, no multi-section analysis.
- **Exposes:** `extract_deck_links()`, `fetch_deck_content()`, `analyze_deck_with_claude()`, `parse_extracted_info()`, `format_company_description()`, `test_analyzer()`
- **Depends on:** `lib/config`, `lib/safe_url`, `requests`, Anthropic API (Haiku), `openclaw` CLI (browser for DocSend)
- **Used by:** Can be called standalone; functionality subsumed by deal-analyzer
- **Notes:**
  - **DEPRECATED** — Use deal-analyzer instead
  - NO retry logic on Claude calls
  - Less comprehensive redirect handling than deal-analyzer

### Founder Scout
- **File:** `skills/founder-scout/scout.py` (1232 lines)
- **Entry point:** `skills/founder-scout/founder-scout` (57-line bash wrapper)
- **Purpose:** Proactive discovery of Israeli tech founders. LinkedIn search rotation, profile analysis for startup signals (role changes, serial entrepreneurs, stealth-mode hints), weekly email/WhatsApp briefings.
- **Exposes:** `run_daily_scan()`, `run_weekly_briefing()`, `run_watchlist_update()`, `run_status()`, `run_add()`, `run_dismiss()`, `main()`
- **Depends on:** `lib/config`, `requests`, Anthropic API (Sonnet), LinkedIn browser automation (`openclaw browser`), `gws-auth` CLI (email), `openclaw` CLI (WhatsApp), SQLite
- **Used by:** Cron (daily scan, weekly briefing, Wed/Sat watchlist update)
- **Cron schedule:** `0 7 * * *` (scan), `0 8 * * 0` (briefing), `0 14 * * 3,6` (watchlist)
- **Notes:**
  - SQLite at `data/founder-scout.db` (tables: tracked_people, signal_history, scan_log, search_rotation, sent_profiles)
  - File lock at `data/founder-scout.lock`
  - Recipient emails loaded from `config._data['founder_scout']['recipient_emails']` (no accessor in config.py)
  - 3-attempt retry on Claude 429 errors
  - Not documented in README or docs/skills.md

### Keep on Radar
- **File:** `skills/keep-on-radar/radar.py` (828 lines)
- **Entry point:** `skills/keep-on-radar/keep-on-radar` (44-line bash wrapper)
- **Purpose:** Monthly review of HubSpot deals in "Keep on Radar" stage. Researches company updates via Brave+Claude, sends digest emails to deal owners, monitors Gmail for reply actions (pass, keep, note).
- **Exposes:** `run_review()`, `check_replies()`, `run_status()`, `run_pass()`, `main()`
- **Depends on:** `lib/config`, `requests`, Anthropic API (Sonnet + Haiku), Brave Search API, HubSpot via Maton API, `gws-auth` CLI (Gmail search/thread/send/modify), `openclaw` CLI (WhatsApp), SQLite
- **Used by:** Cron (monthly review, 2h reply checks), WhatsApp commands
- **Cron schedule:** `0 9 15 * *` (review), `0 */2 * * *` (check-replies)
- **Notes:**
  - SQLite at `data/keep-on-radar.db` (tables: radar_reviews, radar_actions)
  - File lock at `data/keep-on-radar.lock`
  - Hardcoded HubSpot stage ID `1138024523` for Keep on Radar
  - Legacy `run_gog_command()` still uses `shlex.split` on format strings
  - NO retry logic on Claude calls

### Meeting Reminders
- **File:** `skills/meeting-reminders/reminders.py` (894 lines)
- **Entry point:** `skills/meeting-reminders/meeting-reminders` (39-line bash wrapper)
- **Purpose:** WhatsApp reminders 5-20 minutes before meetings. Enriches external attendees with HubSpot deal context (company, deals, last note). Falls back to email if WhatsApp fails.
- **Exposes:** `process_meeting_reminders()`, `query_next_meeting()`, `main()`
- **Depends on:** `lib/config`, `requests`, `pytz`, HubSpot via Maton API, Google Calendar via `gws-auth` CLI, Gmail via `gws-auth` CLI (fallback), `openclaw` CLI (WhatsApp), optional `enrichment` module, SQLite
- **Used by:** Cron (every 5 minutes)
- **Cron schedule:** `*/5 * * * *`
- **Notes:**
  - SQLite at `data/meeting-reminders.db` (table: notified_meetings)
  - File lock at `data/meeting-reminders.lock`
  - Auto-cleans notifications older than 24h
  - Schema migration: detects old PK format and recreates table
  - Hardcoded HubSpot stage names in stage map (lines 492-500)
  - `send_whatsapp_message` includes `--account` flag (unique among skills)

### Meeting Bot
- **File:** `skills/meeting-bot/meeting-bot` (353-line Python script)
- **Purpose:** Processes completed meeting recordings. Searches Google Drive for recordings, downloads transcripts, uses Claude to extract action items, emails summaries.
- **Exposes:** Runs as batch processor (no exported API)
- **Depends on:** `lib/config`, `requests`, Anthropic API (Sonnet), Google Drive via `gws-auth` CLI, Gmail via `gws-auth` CLI, SQLite
- **Used by:** Cron (every 2 hours)
- **Cron schedule:** `0 */2 * * *`
- **Notes:**
  - Model: `claude-sonnet-4-5-20250929`
  - Transcript truncated to 20,000 chars
  - Good prompt injection defense in system prompt
  - Redundant `import shlex` at line 231

### Meeting Auto-Join
- **File:** `skills/meeting-bot/meeting-auto-join` (255-line Python script)
- **Purpose:** Auto-joins Google Meet meetings within 5-minute window. Checks calendar, extracts Meet URLs, launches browser join.
- **Exposes:** Runs as cron job (no exported API)
- **Depends on:** `lib/config`, Google Calendar via `gws-auth` CLI, `node camofox-join.js` or Playwright (on server: rewritten to use Playwright CDP)
- **Used by:** Cron (every 3 minutes)
- **Cron schedule:** `*/3 * * * *`
- **Notes:**
  - Uses `fcntl.flock` on `~/.bot-joined-meetings.json` for concurrency
  - 12-hour dedup window
  - On server: rewritten to use Playwright CDP to LinkedIn browser (port 18801) instead of camofox-join.js

### Camofox Join (Meeting Bot JS)
- **File:** `skills/meeting-bot/camofox-join.js` (909 lines)
- **Purpose:** Full-featured meeting join bot. Connects to LinkedIn browser via CDP, joins Google Meet, mutes mic/cam, enables Gemini notes, monitors attendance, sends WhatsApp/Twilio alerts for latecomers, processes Gemini meeting notes post-meeting.
- **Exposes:** Self-executing IIFE (no exports)
- **Depends on:** `playwright-core` (Chromium CDP), `camoufox-js`, `../../lib/config`, Google Meet web UI, Twilio API (phone calls), `gws-auth` CLI (Gmail), `openclaw` CLI (WhatsApp)
- **Used by:** `join-meeting` bash wrapper, `meeting-auto-join` (in repo version)
- **Notes:**
  - SSRF protection via domain allowlist
  - Shell injection protection via `shellEscape()`
  - Unused imports: `firefox` from playwright-core, `launchOptions` from camoufox-js
  - Sends late-joiner alerts via WhatsApp (+3 min) then Twilio phone call (+5 min)

### Google Workspace
- **File:** `skills/google-workspace/google-workspace` (52-line bash script)
- **Purpose:** Thin CLI wrapper around `gog` for calendar and Gmail operations.
- **Exposes:** Actions: `calendar-list`, `calendar-create`, `calendar-delete`, `gmail-send`, `gmail-read`, `calendar-availability`
- **Depends on:** `gws-auth` CLI
- **Used by:** OpenClaw skill trigger
- **Notes:**
  - Shebang has escaped `!` (`#\!/bin/bash`)
  - No `.env` loading
  - No argument validation

### Google Workspace - Calendar for User
- **File:** `skills/google-workspace/calendar-for-user` (49-line bash script)
- **Purpose:** Gets calendar events for a team member identified by phone number.
- **Depends on:** `lib/config` (via inline Python), `gws-auth` CLI
- **Notes:** Uses GNU `date -d` -- won't work on macOS

### Google Workspace - Create Calendar Event
- **File:** `skills/google-workspace/create-calendar-event` (110-line Python script)
- **Purpose:** Creates calendar events with attendee invitations.
- **Depends on:** `gws-auth` CLI
- **Notes:** Hardcoded timezone `+02:00` -- wrong during Israel DST (+03:00)

### Google Workspace - Download Google Doc
- **File:** `skills/google-workspace/download-google-doc` (36-line bash script)
- **Purpose:** Downloads a Google Doc as plain text.
- **Depends on:** `gws-auth` CLI
- **Notes:** Uses `grep -oP` (Perl regex) -- not available on macOS. Default account is placeholder.

### Google Workspace - Get My Calendar
- **File:** `skills/google-workspace/get-my-calendar` (48-line Python script)
- **Purpose:** Shows requesting user's calendar (resolves phone to email).
- **Depends on:** `gws-auth` CLI
- **Notes:** Uses deprecated `datetime.utcnow()`

### LinkedIn Browser
- **File:** `skills/linkedin/linkedin` (63-line bash script)
- **Purpose:** Browser automation wrapper for LinkedIn. Search, profile lookup, company lookup, messages, status.
- **Exposes:** Actions via `openclaw browser` commands with `linkedin` browser profile
- **Depends on:** `openclaw browser` CLI, LinkedIn browser service (port 18801)
- **Used by:** `founder-scout/scout.py`, `deal-analyzer/analyzer.py` (via DocSend), ad-hoc research
- **Notes:**
  - Shell injection fixed — `$QUERY` passed via `sys.argv[1]`

### Ping Teammate
- **File:** `skills/ping-teammate/ping-teammate` (153-line bash script with inline Python)
- **Purpose:** Calls a team member via Twilio when pinged on WhatsApp.
- **Depends on:** Twilio REST API, `lib/config` (via inline Python), `config.yaml`
- **Notes:**
  - Good TwiML injection protection via `html.escape()`
  - Self-ping prevention
  - Auto-generates `team-phones.json` from config
  - 60-second max poll (12 iterations x 5s)

### VC Automation - Deal Pass
- **File:** `skills/vc-automation/deal-pass-automation` (365-line Python script)
- **Purpose:** Moves HubSpot deals to Pass (closedlost) stage from email or direct ID. Sends confirmation email.
- **Depends on:** `requests`, HubSpot via Maton API, `gws-auth` CLI (Gmail)
- **Notes:**
  - Manual argument parsing -- fragile (no bounds checking on argv index)
  - Simplistic company name extraction from email subject

### VC Automation - Meeting Notes to CRM
- **File:** `skills/vc-automation/meeting-notes-to-crm` (388-line Python script)
- **Purpose:** Processes meeting notes via Claude AI, extracts structured data, updates HubSpot deals, creates calendar follow-up reminders.
- **Depends on:** `requests`, Anthropic API (Sonnet), HubSpot via Maton API, `create-calendar-event` script
- **Notes:**
  - Model: `claude-sonnet-4-20250514`
  - Good prompt injection defense

### VC Automation - Research Founder
- **File:** `skills/vc-automation/research-founder` (314-line Python script)
- **Purpose:** On-demand founder due diligence. Web research via Brave Search + Claude analysis.
- **Depends on:** `requests`, Anthropic API (Sonnet), Brave Search API
- **Notes:**
  - **Standalone** -- does NOT import `lib/config` or load `.env`
  - Saves reports to `/tmp/founder-research-*.md`
  - Gracefully degrades without Brave API key (but analysis will be speculative)

### Deal Logger
- **File:** `skills/deal-logger/deal-logger.sh` (80-line bash script)
- **Purpose:** Automated deal conversation tracking. Reads `~/deals.json`, queries OpenClaw logs, uses AI to match conversations to deals.
- **Depends on:** `openclaw` CLI (logs, agent)
- **Notes:**
  - Simpler than SKILL.md suggests (no CRM/Notion integration despite docs claiming it)
  - `head -1000` hard limit on conversation logs

### Content Writer Profiles
- **Files:** `skills/content-writer/profiles/<name>/{voice,brand,audience}.json`
- **Purpose:** Per-team-member voice, brand, and audience profiles for content generation.
- **Notes:** Example profile provided in `profiles/example/`. Real profiles in `.gitignore`.

---

## Scripts (Cron Jobs & Automation)

### Email-to-Deal Automation
- **File:** `scripts/email-to-deal-automation.py` (~1500 lines)
- **Purpose:** Main deal pipeline. Monitors team emails for incoming deals, extracts companies from subjects, fetches/analyzes pitch decks, creates HubSpot companies/deals, sends confirmations via email/WhatsApp. Includes portfolio update detection.
- **Depends on:** `lib/config`, `lib/gws`, `lib/safe_url`, `scripts/portfolio_monitor`, `requests`, Anthropic API (Haiku + Sonnet), HubSpot via Maton API, gws-auth CLI (Gmail), `openclaw` CLI (WhatsApp), Camofox browser (DocSend), `pdftotext`
- **Used by:** Cron
- **Cron schedule:** `*/10 * * * *`
- **Notes:**
  - Second largest file
  - Uses `fcntl.flock` to prevent concurrent cron runs
  - Portfolio email detection via `handle_portfolio_email()` before deal creation
  - Company name extraction with domain + Claude fallback chain
  - Also handles opt-in/opt-out requests and WhatsApp deal submissions

### Meeting Brief Opt-in Handler
- **File:** `scripts/meeting-brief-optin-handler.py` (337 lines)
- **Purpose:** Standalone handler for meeting-brief opt-in/opt-out requests via email (and WhatsApp placeholder).
- **Depends on:** `lib/config`, `gws-auth` CLI (Gmail), `openclaw` CLI (WhatsApp)
- **Notes:**
  - **Duplicate** of opt-in logic in email-to-deal-automation.py
  - Modifies Python source code at runtime via regex (`set_opt_in()`) -- fragile
  - WhatsApp checking is a stub (always returns empty)
  - `create_opt_in_instructions()` defined but never called -- dead code
  - `json` and `timedelta` imported but never used

### Health Check
- **File:** `scripts/health-check.sh` (~260 lines)
- **Purpose:** System health monitor with full escalation chain. Checks gateway, WhatsApp, agents, disk, memory, Camofox, log sizes. Auto-recovery with email alerts + Twilio phone call escalation.
- **Depends on:** `systemctl`, `openclaw` CLI, `gws-auth` CLI (email alerts), Twilio API (phone escalation), Camofox server (`localhost:9377/health`)
- **Cron schedule:** `*/15 * * * *`
- **Notes:**
  - State-file dedup for email alerts (one per incident)
  - Twilio phone call escalation with 1-hour cooldown
  - Standardized on `systemctl --user restart openclaw-gateway` for all restarts
  - Subsumes all functionality from former whatsapp-watchdog.sh (escalation) and whatsapp-healthcheck.sh (deleted)

### WhatsApp Watchdog [TO REMOVE]
- **File:** `scripts/whatsapp-watchdog.sh` (138 lines)
- **Purpose:** Active WhatsApp health monitor using real send test. Escalation logic merged into health-check.sh.
- **Status:** Can be removed — all unique functionality (Twilio escalation) has been merged into health-check.sh.

### Daily Maintenance
- **File:** `scripts/daily-maintenance.sh` (83 lines)
- **Purpose:** OpenClaw updates, apt-get system updates, auto-reboot if required.
- **Cron schedule:** `0 4 * * *` (4 AM UTC)
- **Notes:**
  - `apt-get upgrade -y` without human review
  - Auto-reboot without guarding against running processes
  - No notification before reboot

### Run Scheduled
- **File:** `scripts/run-scheduled.sh` (67 lines)
- **Purpose:** Wrapper for christina-scheduler Node.js service. Enforces business hours (9AM Israel - 6PM NY) and skips Shabbat.
- **Depends on:** Node.js, `.env`, `.profile`, christina-scheduler compiled JS
- **Cron schedule:** Called by cron on a regular schedule (designed to self-gate on time)
- **Notes:**
  - Shabbat logic simplified (skips all Saturday, but Shabbat ends at nightfall)

---

## Exports

### Standalone Deal Analyzer
- **File:** `exports/deal-analyzer/deal_analyzer.py` (1185 lines)
- **Purpose:** Portable, standalone version of the deal analyzer for external use. Single-file module with `DealAnalyzerConfig` dataclass and `DealAnalyzer` class.
- **Exposes:** `DealAnalyzerConfig`, `DealAnalyzer` (with `extract()`, `research()`, `analyze()`, `evaluate()`)
- **Depends on:** `requests` (declared in `requirements.txt`), optionally `openclaw browser` for DocSend
- **Notes:**
  - Claims "no external dependencies beyond requests" but DocSend path shells out to `openclaw`
  - Model IDs: `claude-haiku-4-5-20251001`, `claude-sonnet-4-20250514`
  - `max_deck_chars` default 25000 (vs 20000 in deck-analyzer SKILL.md)

### Example Usage
- **File:** `exports/deal-analyzer/example.py` (80 lines)
- **Purpose:** Demonstrates standalone DealAnalyzer usage.

---

## Systemd Services

### LinkedIn Browser
- **File:** `services/linkedin-browser.service` (13 lines)
- **Purpose:** Persistent headless Chromium for LinkedIn automation. Runs on port 18801.
- **Notes:**
  - Hardcoded Chromium path includes version `chromium-1208` -- breaks on Playwright updates
  - User data at `/root/.openclaw/browser-data/linkedin/`
  - Auto-restarts with 5s delay

---

## External API Integrations (Summary)

| API | Used By | Auth Method |
|-----|---------|-------------|
| Anthropic (Claude) | content-writer, deal-analyzer, deck-analyzer, founder-scout, keep-on-radar, meeting-bot, meeting-notes-to-crm, research-founder | `ANTHROPIC_API_KEY` header |
| Brave Search | content-writer, deal-analyzer, keep-on-radar, research-founder | `BRAVE_SEARCH_API_KEY` header |
| HubSpot (via Maton) | deal-analyzer, keep-on-radar, meeting-reminders, email-to-deal, deal-pass-automation, meeting-notes-to-crm | `MATON_API_KEY` Bearer token |
| Google Calendar | meeting-reminders, meeting-auto-join, create-calendar-event, get-my-calendar, calendar-for-user | `gws-auth` CLI (OAuth) |
| Gmail | content-writer, deal-analyzer, founder-scout, keep-on-radar, meeting-bot, email-to-deal, meeting-brief-optin-handler, deal-pass-automation, health-check, whatsapp-watchdog | `gws-auth` CLI (OAuth) |
| Google Drive | meeting-bot, deal-analyzer | `gws-auth` CLI + direct OAuth |
| Twilio | ping-teammate, whatsapp-watchdog, camofox-join.js | API Key SID + Secret |
| LinkedIn (browser) | founder-scout, linkedin skill | CDP to Chromium (port 18801) |
| OpenClaw/WhatsApp | All skills with WhatsApp delivery | `openclaw message send` CLI |
