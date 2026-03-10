# External Services Setup

## Required Services

### OpenClaw
WhatsApp gateway and AI agent framework.

1. Install: `npm install -g openclaw`
2. Login: `openclaw channels login` (scan QR with WhatsApp phone)
3. Start gateway: `nohup openclaw gateway &`

**Docs**: [openclaw.ai](https://openclaw.ai)

### Google Workspace (via gws-auth CLI)
Calendar, Gmail, and Drive access.

1. Install: `npm install -g gws-auth`
2. Set up OAuth: `gws-auth auth login`
3. Grant access to: Calendar, Gmail, Drive

The assistant's Google account needs:
- Its own Google Calendar
- Gmail access
- Team members must share their calendars with the assistant (read-only)

### Anthropic (Claude AI)
Used for meeting analysis, deck extraction, note processing, and founder research.

1. Sign up at [console.anthropic.com](https://console.anthropic.com)
2. Create an API key
3. Add to `.env`: `ANTHROPIC_API_KEY=sk-ant-...`

## Optional Services

### HubSpot (via Maton)
CRM integration for deal management.

1. Sign up at [maton.ai](https://maton.ai)
2. Connect your HubSpot account
3. Get API key, add to `.env`: `MATON_API_KEY=...`
4. Note your HubSpot owner IDs (Settings > Users & Teams) for each team member

### Twilio
Phone call alerts and teammate pinging.

1. Sign up at [twilio.com](https://twilio.com)
2. Get a phone number
3. Create API keys
4. Add to `.env`:
   ```
   TWILIO_ACCOUNT_SID=...
   TWILIO_API_KEY_SID=...
   TWILIO_API_KEY_SECRET=...
   TWILIO_FROM_NUMBER=+1...
   ```

### Brave Search
Web search for founder research and attendee enrichment.

1. Sign up at [brave.com/search/api](https://brave.com/search/api)
2. Get API key
3. Add to `.env`: `BRAVE_SEARCH_API_KEY=...`

### LinkedIn
Profile research requires a LinkedIn session cookie.

1. Log into LinkedIn in a browser
2. Extract the `li_at` cookie
3. Save to `~/.linkedin-mcp/session.json`

Note: LinkedIn scraping is against their ToS. Use at your own risk for internal research only.

## Service Health

Run `scripts/health-check.sh` to verify all services are connected and healthy.
