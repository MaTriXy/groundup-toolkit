# Duplicates Report

Every case of duplicated or redundant logic in the codebase.

---

## 1. `call_claude()` -- Duplicated 5 Times

**What:** Function to call the Anthropic Claude API with a prompt and system prompt.

**Where:**
| File | Lines | Retry Logic | Timeout |
|------|-------|------------|---------|
| `skills/content-writer/writer.py` | 748-802 | None | 90s |
| `skills/deal-analyzer/analyzer.py` | 47-88 | 5 attempts (429/529) | 120s |
| `skills/deck-analyzer/analyzer.py` | 64-118 | None | 60s |
| `skills/founder-scout/scout.py` | 331-365 | 3 attempts (429) | 60s |
| `skills/keep-on-radar/radar.py` | 158-184 | None | 60s |

**Impact:** 3 of 5 implementations have NO retry logic, meaning a single 429 rate-limit response causes permanent failure. The implementations also differ in model defaults, max_tokens, and error handling.

**Recommendation:** Extract to `lib/claude.py` with configurable retry logic, model, max_tokens, and timeout. All skills import from the shared module.

---

## 2. `brave_search()` -- Duplicated 3 Times

**What:** Function to query the Brave Search API.

**Where:**
| File | Lines | Count Default |
|------|-------|--------------|
| `skills/content-writer/writer.py` | 516-536 | 5 |
| `skills/deal-analyzer/analyzer.py` | 90-109 | 5 |
| `skills/keep-on-radar/radar.py` | 136-156 | 5 |

**Impact:** Identical implementation. Any bug fix or API change must be applied 3 times.

**Recommendation:** Extract to `lib/brave.py` with a `brave_search(query, count=5)` function.

---

## 3. `send_whatsapp()` -- Duplicated 5 Times

**What:** Function to send a WhatsApp message via `openclaw message send`.

**Where:**
| File | Lines | Uses `--account` |
|------|-------|-----------------|
| `skills/content-writer/writer.py` | 814-837 | No |
| `skills/deal-analyzer/analyzer.py` | 111-132 | No |
| `skills/founder-scout/scout.py` | 705-730 | No |
| `skills/keep-on-radar/radar.py` | 480-505 | No |
| `skills/meeting-reminders/reminders.py` | 181-224 | Yes |

**Impact:** All use the same `openclaw message send --channel whatsapp` subprocess pattern with 3 retries and 3-second delay, but meeting-reminders includes the `--account` flag while others don't. If the system has multiple WhatsApp accounts, the 4 without `--account` have ambiguous behavior.

**Recommendation:** Extract to `lib/whatsapp.py` with a `send_whatsapp(phone, message, account=None)` function.

---

## 4. `send_email()` via gog CLI -- Duplicated 4 Times

**What:** Function to send email by writing body to temp file and calling `gog gmail send --body-file`.

**Where:**
| File | Lines |
|------|-------|
| `skills/content-writer/writer.py` | 839-867 |
| `skills/deal-analyzer/analyzer.py` | 134-160 |
| `skills/founder-scout/scout.py` | 673-702 |
| `skills/keep-on-radar/radar.py` | 448-477 |

**Impact:** Identical pattern. Additionally, `scripts/email-to-deal-automation.py`, `scripts/meeting-brief-optin-handler.py`, `skills/meeting-reminders/reminders.py`, and `skills/vc-automation/deal-pass-automation` all have their own slightly different email-sending implementations.

**Recommendation:** This is already solved on the server side by `lib/gws.py` (`gws_gmail_send`). The repo version should add a `lib/email.py` or extend `lib/gws.py` with a unified `send_email(to, subject, body)`.

---

## 5. `TEAM_MEMBERS` Dict Construction -- Duplicated 2+ Times

**What:** Building a dict of team member info from `config.team_members`.

**Where:**
| File | Lines | Keys Used |
|------|-------|-----------|
| `skills/keep-on-radar/radar.py` | 57-67 | name, first_name, phone, hubspot_owner_id |
| `skills/meeting-reminders/reminders.py` | 48-55 | name, phone, timezone, enabled |

**Impact:** Each skill builds its own team member lookup dict with different fields. If the config structure changes, each must be updated.

**Recommendation:** Add lookup methods to `lib/config.py` (e.g., `config.team_members_by_email`) or return full member dicts so callers pick what they need.

---

## 6. `extract_deck_links()` -- Duplicated 2 Times

**What:** Regex extraction of deck URLs (DocSend, Google Drive, Dropbox, etc.) from text.

**Where:**
| File | Lines | Patterns |
|------|-------|----------|
| `skills/deck-analyzer/analyzer.py` | 20-35 | DocSend, Google Drive, Dropbox |
| `skills/deal-analyzer/analyzer.py` | 553-565 | DocSend, Google Drive, Dropbox, Papermark, Pitch |

**Impact:** The deal-analyzer version is strictly more comprehensive (includes Papermark and Pitch). The deck-analyzer version is a subset that could miss valid deck links.

**Recommendation:** Delete deck-analyzer's version. If deck-analyzer is retained, have it import from deal-analyzer or a shared `lib/deck_utils.py`.

---

## 7. Opt-In/Opt-Out Email Processing -- Duplicated 2 Times

**What:** Logic to detect "opt in"/"opt out" requests in emails and toggle a member's meeting-brief subscription.

**Where:**
| File | Lines | Write Method |
|------|-------|-------------|
| `scripts/email-to-deal-automation.py` | 524-648 | Direct `open('w')` -- non-atomic |
| `scripts/meeting-brief-optin-handler.py` | 70-88 (set_opt_in), 150-250 (main logic) | `tempfile` + `os.replace()` -- atomic |

**Impact:** Two independent implementations of the same feature with different safety characteristics. Both modify `meeting-brief-automation.py` source code via regex at runtime.

**Recommendation:** Remove the opt-in logic from `email-to-deal-automation.py`. Keep only the standalone handler. Better: replace source-code modification with a JSON/YAML config file.

---

## 8. HubSpot Company Search -- Duplicated 2 Times

**What:** Searching HubSpot for a company by name or domain.

**Where:**
| File | Lines | Search Strategy |
|------|-------|----------------|
| `skills/deal-analyzer/analyzer.py` | 488-516 | `CONTAINS_TOKEN` on `name` |
| `skills/meeting-reminders/reminders.py` | 310-346 | `EQ` on `domain` |

**Impact:** Different search strategies for the same API. Neither handles pagination.

**Recommendation:** Extract to `lib/hubspot.py` with `search_company(name=None, domain=None)`.

---

## 9. WhatsApp Health Monitoring -- 3 Overlapping Scripts

**What:** Checking WhatsApp connection status and attempting recovery.

**Where:**
| File | Approach | Alerting | Gateway Restart |
|------|----------|----------|----------------|
| `scripts/health-check.sh` | Status probe | Email | `systemctl restart` |
| `scripts/whatsapp-watchdog.sh` | Real send test | Email + Twilio call | `pkill` + `nohup` |
| `scripts/whatsapp-healthcheck.sh` | Status check | None | `openclaw gateway restart` |

**Impact:** Three scripts with overlapping scope using three different restart mechanisms. Could fight each other (one restarts via systemd while another uses pkill). The healthcheck has no alerting, making it strictly weaker than the other two.

**Recommendation:** Consolidate into one script. Use `health-check.sh` for overall health + WhatsApp (status probe + optional send test). Remove `whatsapp-healthcheck.sh` entirely. Merge Twilio escalation from watchdog into health-check.

---

## 10. `.env` Loading -- Duplicated 5+ Times

**What:** Loading environment variables from `.env` file using `while IFS='=' read` loop.

**Where:**
- `scripts/health-check.sh` (lines 15-19)
- `scripts/whatsapp-watchdog.sh` (lines 19-23)
- `scripts/run-scheduled.sh` (lines 60-64)
- `install.sh` (lines 123-130)
- Most bash skill wrappers (content-writer, deal-analyzer, founder-scout, keep-on-radar, meeting-reminders)

**Impact:** Each has slightly different bugs. None strip quotes from values correctly. `load-env.sh` exists to solve this but is not used by most scripts.

**Recommendation:** Make all scripts source `load-env.sh` or a simpler shared `source-env.sh` that handles quote-stripping properly.

---

## 11. `get_google_access_token()` -- Duplicated 2 Times

**What:** Refreshing Google OAuth2 access token from gog's stored refresh token.

**Where:**
| File | Lines |
|------|-------|
| `skills/deal-analyzer/analyzer.py` | 168-208 |
| Server: `lib/gws.py` | 373-421 |

**Impact:** The deal-analyzer has its own token refresh implementation for Google Drive API access (creating Google Docs). The server's `gws.py` module has the same logic.

**Recommendation:** Once gws-auth migration is complete in the repo (not just server), this can use the shared `gws.py` module.

---

## 12. Dead/Prototype Meeting Bot JS Files -- 10 Redundant Files

**What:** Various prototypes and test scripts for meeting joining, all superseded by `camofox-join.js`.

**Where:**
- `skills/meeting-bot/force-click-join.js` (38 lines)
- `skills/meeting-bot/force-join.js` (51 lines)
- `skills/meeting-bot/headed-join.js` (145 lines)
- `skills/meeting-bot/join-authenticated.js` (95 lines)
- `skills/meeting-bot/join-current-meeting.js` (122 lines) -- **near-duplicate** of `stealth-join.js`
- `skills/meeting-bot/join-now.js` (93 lines)
- `skills/meeting-bot/setup-auth.js` (104 lines) -- overlaps with `authenticate-bot.js`
- `skills/meeting-bot/stealth-join.js` (122 lines) -- **near-duplicate** of `join-current-meeting.js`
- `skills/meeting-bot/test-join-fixed.js` (82 lines) -- **near-duplicate** of `test-join.js`
- `skills/meeting-bot/test-join.js` (98 lines) -- **near-duplicate** of `test-join-fixed.js`

**Impact:** 10 dead files totaling ~950 lines. All lack SSRF protection. The `package.json` declares dependencies only needed by these dead files (`puppeteer`, `puppeteer-extra`).

**Recommendation:** Delete all 10 files. Remove `puppeteer`/`puppeteer-extra` from `package.json`. Keep only `camofox-join.js` and `authenticate-bot.js` (if manual cookie auth is still needed as backup).

---

## 13. Deck Analyzer vs Deal Analyzer -- Overlapping Skills

**What:** Both extract and analyze pitch deck content.

**Where:**
| Feature | `deck-analyzer/analyzer.py` (201 lines) | `deal-analyzer/analyzer.py` (2077 lines) |
|---------|-----------|-----------|
| Deck extraction | 8 fields, Haiku | Full extraction, Haiku |
| Link patterns | 3 platforms | 5 platforms |
| Research | None | 15 Brave queries |
| Analysis | Single Claude call | 12 parallel sections |
| SSRF protection | `safe_url` (basic) | `safe_url` + `safe_request` |
| Retry logic | None | 5 attempts |
| HubSpot | None | Full integration |

**Impact:** Deck-analyzer is a strict subset of deal-analyzer. Maintaining both means bugs could exist in one but not the other.

**Recommendation:** Mark deck-analyzer as deprecated. For callers needing simple extraction only, add an `extract-only` mode to deal-analyzer.

---

## 14. JS Config vs Python Config -- Parallel Implementations

**What:** Team member data, credentials, and toolkit paths.

**Where:**
| File | Lines | Dynamic | Has PII in Git |
|------|-------|---------|---------------|
| `lib/config.py` | 268 | Yes (reads YAML) | No |
| `lib/config.js` | 36 | No (hardcoded) | **Yes** |

**Impact:** When team members change, `config.yaml` must be updated AND `lib/config.js` must be manually edited. The JS config has real PII committed to git.

**Recommendation:** Rewrite `lib/config.js` to read from `config.yaml` (using `js-yaml` which is already a project dependency). Remove hardcoded PII.
