# skills/ — OpenClaw Skills

Each subdirectory is an OpenClaw skill invoked via `openclaw skill run <name>`.

## Structure

Each skill folder contains:
- An executable entry point (bash wrapper or Python script) matching the folder name
- `SKILL.md` — Skill metadata (description, arguments, examples)
- Supporting Python/JS modules as needed

## Active Skills

| Skill | Purpose |
|-------|---------|
| content-writer | Generate blog posts with voice learning |
| deal-analyzer | Full VC deal evaluation (deck + research + HubSpot) |
| deal-automation | Automated deal stage transitions |
| deal-logger | Log deals to file |
| founder-scout | LinkedIn-based founder discovery |
| google-workspace | Google Calendar/Gmail/Drive operations |
| keep-on-radar | Monthly HubSpot deal review |
| linkedin | LinkedIn search and profile viewing |
| meeting-bot | Meeting recording/transcript processor + auto-join |
| meeting-reminders | WhatsApp meeting reminders with HubSpot context |
| ping-teammate | Send messages to team members |
| vc-automation | VC outreach and deal pass automation |

## Deprecated

| Skill | Reason | Replacement |
|-------|--------|-------------|
| deck-analyzer | Strict subset of deal-analyzer | Use deal-analyzer |

## What does NOT belong here

- Cron job scripts (goes in scripts/)
- Shared libraries (goes in lib/)
- Systemd service files (goes in services/)
