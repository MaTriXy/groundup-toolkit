# lib/ — Shared Libraries

Reusable modules imported by skills and scripts. Every shared function lives here.

## What belongs here

- **config.py** — Config singleton (reads config.yaml + .env)
- **config.js** — JS config (should read config.yaml via js-yaml)
- **safe_url.py** — SSRF protection (URL validation, safe HTTP requests)
- **claude.py** — Shared Claude API client with retry logic
- **brave.py** — Brave Search API client
- **whatsapp.py** — WhatsApp message sender via openclaw CLI
- **email.py** — Email sender via gog/gws-auth CLI
- **hubspot.py** — HubSpot CRM operations via Maton API gateway

## What does NOT belong here

- Skill-specific business logic (goes in skills/)
- CLI scripts or cron jobs (goes in scripts/)
- One-off utilities that aren't shared across 2+ consumers
