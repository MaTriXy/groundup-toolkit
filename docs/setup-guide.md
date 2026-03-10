# Setup Guide

Step-by-step guide to deploy the GroundUp Toolkit on a fresh server.

## Prerequisites

- **Server**: Ubuntu 22.04+ (ARM or x86), minimum 2GB RAM, 20GB disk
- **Domain knowledge**: Basic familiarity with cron, SSH, and CLI tools
- **Accounts needed**: Google Workspace, HubSpot (via Maton), Anthropic, WhatsApp Business

## Step 1: Server Setup

```bash
# SSH into your server
ssh root@your-server-ip

# Clone the toolkit
git clone https://github.com/navotvolkgroundup/groundup-toolkit.git
cd groundup-toolkit
```

## Step 2: Configuration

### config.yaml
```bash
cp config.example.yaml config.yaml
```

Edit `config.yaml` with your team's details:
- **assistant**: Your AI assistant's name and email
- **team.members**: Each person's name, email, phone (with country code), timezone, and HubSpot owner ID
- **hubspot**: Your Maton API gateway URL and pipeline settings
- **scheduling**: Work hours and Shabbat awareness
- **notifications**: Who gets alerts when things break

### .env
```bash
cp .env.example .env
```

Fill in API keys:
- `ANTHROPIC_API_KEY` - From [console.anthropic.com](https://console.anthropic.com)
- `MATON_API_KEY` - From [maton.ai](https://maton.ai) (HubSpot gateway)
- `GOG_KEYRING_PASSWORD` - Any string, used to encrypt Google OAuth tokens
- `BRAVE_SEARCH_API_KEY` - From [brave.com/search/api](https://brave.com/search/api)
- `TWILIO_*` - From [twilio.com](https://twilio.com) console

## Step 3: Install

```bash
sudo bash install.sh
```

This installs: Node.js 18+, Python 3 (with venv), OpenClaw, gws-auth CLI, js-yaml, and all dependencies.
Python packages are installed in `.venv/` — activate with `source .venv/bin/activate`.

## Step 4: Google OAuth

```bash
gws-auth auth login
```

Follow the browser-based OAuth flow. This grants access to:
- Google Calendar (read team calendars, create events)
- Gmail (send emails, read inbox)
- Google Drive (access meeting recordings)

## Step 5: WhatsApp

```bash
# Login to WhatsApp
openclaw channels login

# A QR code will appear - scan it with your WhatsApp phone
# Then start the gateway:
nohup openclaw gateway > /var/log/openclaw-gateway.log 2>&1 &

# Wait 8 seconds, then verify:
sleep 8
openclaw channels status
```

You should see: `WhatsApp: enabled, configured, linked, running, connected`

## Step 6: Cron Jobs

```bash
# Edit the crontab template with your toolkit path
nano cron/crontab.example
# Change TOOLKIT_DIR=/path/to/groundup-toolkit

# Install cron jobs
crontab cron/crontab.example
```

## Step 7: Verify

```bash
# Run health check
bash scripts/health-check.sh

# Test WhatsApp (sends a dot to the assistant's number)
openclaw message send --channel whatsapp --target "+YOUR_NUMBER" --message "test"

# Test meeting reminders (dry run)
source .venv/bin/activate
source .env
cd /path/to/groundup-toolkit
python3 skills/meeting-reminders/reminders.py
```

## Troubleshooting

### WhatsApp "No active listener"
The WhatsApp session expired. Re-scan QR:
```bash
openclaw channels logout
openclaw channels login
# Scan QR, then restart gateway:
pkill -f openclaw-gateway
nohup openclaw gateway > /var/log/openclaw-gateway.log 2>&1 &
```

### 401 Unauthorized from WhatsApp
Stale session. Full reset:
```bash
openclaw channels logout
# Wait 5 seconds
openclaw channels login
# Scan QR
pkill -f openclaw-gateway
nohup openclaw gateway > /var/log/openclaw-gateway.log 2>&1 &
```

### gws-auth commands failing
Check OAuth tokens:
```bash
gws-auth auth status
# If expired:
gws-auth auth login
```

### Meeting bot can't join meets
Check Camoufox browser:
```bash
curl http://localhost:9377/health
# If down:
cd /path/to/camofox-browser
PORT=9377 nohup node server.js > /var/log/camofox.log 2>&1 &
```

## Logs

All logs are in `/var/log/`:
- `meeting-reminders.log` - Reminder notifications
- `meeting-bot.log` - Recording processing
- `meeting-auto-join.log` - Meeting join attempts
- `toolkit-health.log` - Health check results
- `whatsapp-watchdog.log` - Connection monitoring
- `openclaw-gateway.log` - Gateway process
