# scripts/ — Cron Jobs and System Scripts

Scripts that run on a schedule (cron) or are invoked for system maintenance.

## Active Scripts

| Script | Schedule | Purpose |
|--------|----------|---------|
| email-to-deal-automation.py | */10 * * * * | Scan Gmail for deals, extract decks, create HubSpot entries |
| health-check.sh | */15 * * * * | System health monitoring with email alerts |
| daily-maintenance.sh | 0 4 * * * | System updates, OpenClaw updates |
| load-env.sh | (sourced) | Shared .env loader for bash scripts |
| run-scheduled.sh | 0 */2 * * * | Christina scheduler wrapper with business hours |
| meeting-brief-optin-handler.py | (unclear) | Meeting brief opt-in/opt-out processing |

## Removed/Consolidated

| Script | Status | Reason |
|--------|--------|--------|
| whatsapp-healthcheck.sh | TO REMOVE | Redundant — covered by health-check.sh |
| whatsapp-watchdog.sh | TO MERGE | Escalation logic to merge into health-check.sh |

## What does NOT belong here

- Skill entry points (goes in skills/)
- Shared libraries (goes in lib/)
- One-off migration scripts
