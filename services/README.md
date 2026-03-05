# services/ — Systemd Service Files

Service definitions for long-running processes managed by systemd.

## Contents

| Service | Purpose |
|---------|---------|
| linkedin-browser.service | Headless Chromium browser for LinkedIn automation (port 18801) |

## What belongs here

- `.service` files for systemd
- Service-related configuration

## What does NOT belong here

- Cron jobs (goes in cron/)
- Application code (goes in skills/ or scripts/)
