# Cron Jobs Map

Every scheduled job and background worker in the system.

---

## Active Cron Jobs

### Meeting Reminders
- **File:** `skills/meeting-reminders/reminders.py`
- **Schedule:** `*/5 * * * *` (every 5 minutes)
- **What it does:** Checks all enabled team members' Google Calendars for meetings starting in 5-20 minutes. Sends WhatsApp reminders with meeting details and HubSpot context (company, deals, last note). Falls back to email if WhatsApp fails.
- **Dependencies:** Google Calendar (gog CLI), HubSpot (Maton API), WhatsApp (openclaw), Gmail (gog CLI, fallback), SQLite (dedup)
- **Error handling:** Yes -- try/except with stderr logging. File lock prevents concurrent runs. WhatsApp retry (3 attempts) with email fallback. SQLite dedup prevents duplicate notifications.
- **Recommended improvements:**
  - Add structured logging (currently uses print to stderr)
  - Replace hardcoded HubSpot stage names with config-driven values

### Meeting Bot (Recording Processor)
- **File:** `skills/meeting-bot/meeting-bot`
- **Schedule:** `0 */2 * * *` (every 2 hours)
- **What it does:** Searches Google Drive for new meeting recordings, downloads associated transcripts, uses Claude to extract action items and summaries, emails results to relevant team members.
- **Dependencies:** Google Drive (gog CLI), Gmail (gog CLI), Anthropic API (Sonnet)
- **Error handling:** Yes -- try/except with stderr logging. Uses tempfile + os.replace for atomic writes. Tracks processed recordings.
- **Recommended improvements:**
  - Increase transcript limit (currently 20,000 chars -- may miss content in long meetings)
  - Add file lock for cron safety

### Meeting Auto-Join
- **File:** `skills/meeting-bot/meeting-auto-join`
- **Schedule:** `*/3 * * * *` (every 3 minutes)
- **What it does:** Checks Christina's calendar for meetings starting within -2 to +5 minutes. Extracts Google Meet URLs. Joins meetings via browser automation (Playwright CDP to LinkedIn browser on server, or camofox-join.js in repo).
- **Dependencies:** Google Calendar (gog CLI), Playwright/Camofox (browser), LinkedIn browser service (port 18801 on server)
- **Error handling:** Yes -- file lock on `~/.bot-joined-meetings.json` via `fcntl.flock`. 12-hour dedup. Meeting metadata written to state directory.
- **Recommended improvements:**
  - Consider 5-minute interval (still catches meetings with the time window)
  - Add health check for LinkedIn browser service availability before attempting join

### Email-to-Deal Automation
- **File:** `scripts/email-to-deal-automation.py`
- **Schedule:** `*/10 * * * *` (every 10 minutes)
- **What it does:** Scans team members' Gmail for deal-related emails. Extracts company names, fetches pitch decks (DocSend, Google Drive, PDF attachments), analyzes with Claude, creates HubSpot companies and deals, sends confirmation messages. Also handles opt-in/opt-out and WhatsApp deal submissions.
- **Dependencies:** Gmail (gog CLI), Anthropic API (Haiku + Sonnet), HubSpot (Maton API), Camofox browser (DocSend), WhatsApp (openclaw), pdftotext
- **Error handling:** Partial -- try/except blocks but NO file lock for concurrent run protection. Bare `except:` clauses in some places.
- **Recommended improvements:**
  - **Add file lock** (critical -- 10-min cron with multi-minute execution could overlap)
  - Replace bare `except:` with `except Exception:`
  - Extract opt-in logic to standalone handler
  - Split into smaller focused modules

### Health Check
- **File:** `scripts/health-check.sh`
- **Schedule:** `*/15 * * * *` (every 15 minutes)
- **What it does:** Checks gateway process, RPC health, WhatsApp connection, agent heartbeat, disk/memory usage, Camofox health, and log file sizes. Auto-recovers (restart gateway, start Camofox). Sends email alerts with state-file dedup for incident tracking.
- **Dependencies:** systemctl, openclaw CLI, gog CLI (email alerts), Camofox (localhost:9377)
- **Error handling:** Yes -- `set +e` (continues on error). Alert dedup via `/tmp/alert-state-*` files. Recovery notifications on issue resolution.
- **Recommended improvements:**
  - Refresh timestamp between long operations (currently set once at script start)
  - Use consistent gateway restart method (systemd)
  - Consolidate with whatsapp-watchdog functionality

### WhatsApp Watchdog
- **File:** `scripts/whatsapp-watchdog.sh`
- **Schedule:** `*/5 * * * *` (every 5 minutes)
- **What it does:** Sends a real "." message to the assistant's WhatsApp as a live connectivity test. On failure: restarts gateway, retries. If still failing: sends Twilio phone call + email alert.
- **Dependencies:** openclaw CLI, gog CLI (email), Twilio API (phone calls), python3 (URL encoding)
- **Error handling:** Yes -- retry logic with escalation. 1-hour cooldown on Twilio calls (but NOT on email alerts).
- **Recommended improvements:**
  - **Add cooldown to email alerts** (currently sends every 5 min on failure)
  - Use systemd for gateway restart instead of pkill+nohup
  - Consider using status check instead of sending real messages

### Run Scheduled (Christina Scheduler)
- **File:** `scripts/run-scheduled.sh`
- **Schedule:** `0 */2 * * *` (every 2 hours)
- **What it does:** Wrapper for christina-scheduler Node.js service. Enforces business hours (9AM Israel - 6PM NY) and Shabbat skip. Then runs the scheduler.
- **Dependencies:** Node.js, christina-scheduler compiled JS, .env, .profile
- **Error handling:** `set -e` (fails fast). Business hours and Shabbat checking prevent out-of-hours execution.
- **Recommended improvements:**
  - Shabbat logic should handle motzei Shabbat (Saturday night after sunset)

### Founder Scout - Daily Scan
- **File:** `skills/founder-scout/scout.py` (action: `scan`)
- **Schedule:** `0 7 * * *` (7 AM UTC daily)
- **What it does:** Rotates through LinkedIn search queries targeting Israeli tech founders. Extracts profiles from search results, analyzes with Claude for startup signals, categorizes by tier (High/Medium/Low), sends alerts for high-tier signals.
- **Dependencies:** LinkedIn browser (openclaw browser), Anthropic API (Sonnet), gog CLI (email), openclaw CLI (WhatsApp), SQLite
- **Error handling:** Yes -- file lock prevents concurrent scans. Claude retry (3 attempts for 429). Dedup via sent_profiles table.
- **Recommended improvements:** None critical -- well-implemented.

### Founder Scout - Weekly Briefing
- **File:** `skills/founder-scout/scout.py` (action: `briefing`)
- **Schedule:** `0 8 * * 0` (8 AM UTC, Sundays)
- **What it does:** Compiles weekly summary of all discovered signals, sends email digest + WhatsApp summary to configured recipients.
- **Dependencies:** SQLite (reads signal_history), gog CLI (email), openclaw CLI (WhatsApp)
- **Error handling:** Yes -- file lock, try/except.
- **Recommended improvements:** None critical.

### Founder Scout - Watchlist Update
- **File:** `skills/founder-scout/scout.py` (action: `watchlist-update`)
- **Schedule:** `0 14 * * 3,6` (2 PM UTC, Wed/Sat)
- **What it does:** Re-scans all tracked people on LinkedIn for new activity/signals.
- **Dependencies:** LinkedIn browser (openclaw browser), Anthropic API (Sonnet), SQLite
- **Error handling:** Yes -- file lock, try/except.
- **Recommended improvements:** None critical.

### Daily Maintenance
- **File:** `scripts/daily-maintenance.sh`
- **Schedule:** `0 4 * * *` (4 AM UTC daily)
- **What it does:** Checks for OpenClaw updates, runs apt-get system updates, auto-reboots if required.
- **Dependencies:** apt-get, openclaw CLI, systemd
- **Error handling:** Minimal -- checks return codes but no alerting on update failures.
- **Recommended improvements:**
  - **Add notification before reboot** (team should know server is rebooting)
  - Guard against rebooting while long-running jobs are active
  - Use `unattended-upgrades` for security-only updates instead of `apt-get upgrade -y`

---

## Potentially Redundant Cron Jobs

### WhatsApp Healthcheck
- **File:** `scripts/whatsapp-healthcheck.sh`
- **Schedule:** `0 * * * *` (hourly)
- **What it does:** Simpler WhatsApp status check with 2 restart attempts. No alerting.
- **Status:** **Likely redundant** -- overlaps with both health-check.sh (WhatsApp probe) and whatsapp-watchdog.sh (send test + alerting). Provides no capability the other two don't cover.
- **Recommendation:** Remove entirely.

---

## Cron Jobs Referenced but Not in Crontab Example

### Meeting Brief Opt-in Handler
- **File:** `scripts/meeting-brief-optin-handler.py`
- **Schedule:** Not in `cron/crontab.example`
- **Status:** Unclear if it runs as a separate cron or is called from email-to-deal-automation.py (which has its own copy of the logic).
- **Recommendation:** Clarify: either add to crontab or remove if fully handled by email-to-deal.

### Keep on Radar - Review
- **File:** `skills/keep-on-radar/radar.py` (action: `review`)
- **Schedule:** Monthly on 15th (per SKILL.md) -- not in `cron/crontab.example`
- **Recommendation:** Add to crontab example.

### Keep on Radar - Check Replies
- **File:** `skills/keep-on-radar/radar.py` (action: `check-replies`)
- **Schedule:** Every 2 hours (per SKILL.md) -- not in `cron/crontab.example`
- **Recommendation:** Add to crontab example.

---

## Summary Table

| Job | Schedule | File | Lock | Alerting | Status |
|-----|----------|------|------|----------|--------|
| Meeting Reminders | */5 * * * * | reminders.py | Yes | WhatsApp + email fallback | Active |
| Meeting Bot | 0 */2 * * * | meeting-bot | No | Email (results) | Active |
| Meeting Auto-Join | */3 * * * * | meeting-auto-join | Yes | None | Active |
| Email-to-Deal | */10 * * * * | email-to-deal-automation.py | **No** | WhatsApp + email | Active |
| Health Check | */15 * * * * | health-check.sh | No (stateful) | Email | Active |
| WhatsApp Watchdog | */5 * * * * | whatsapp-watchdog.sh | No (stateful) | Email + Twilio | Active |
| Christina Scheduler | 0 */2 * * * | run-scheduled.sh | No | None | Active |
| Founder Scout Scan | 0 7 * * * | scout.py | Yes | WhatsApp + email | Active |
| Founder Scout Briefing | 0 8 * * 0 | scout.py | Yes | WhatsApp + email | Active |
| Founder Scout Watchlist | 0 14 * * 3,6 | scout.py | Yes | None | Active |
| Daily Maintenance | 0 4 * * * | daily-maintenance.sh | No | None | Active |
| WhatsApp Healthcheck | 0 * * * * | whatsapp-healthcheck.sh | No | None | **Redundant** |
| Keep on Radar Review | 0 9 15 * * | radar.py | Yes | Email | Missing from crontab |
| Keep on Radar Replies | 0 */2 * * * | radar.py | Yes | None | Missing from crontab |
| Opt-in Handler | ? | meeting-brief-optin-handler.py | No | Email | Unclear |
