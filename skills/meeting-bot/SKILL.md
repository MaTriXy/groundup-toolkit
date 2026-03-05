# Meeting Bot

Auto-joins meetings the assistant is invited to, records them, and extracts action items.

## Current Version: V1.5

**V1.5 Features:**
- Auto-joins meetings the assistant is invited to
- **Now uses Camoufox** for better fingerprinting resistance
- Records with Google Meet native recording
- Extracts to-dos and meeting summary
- Emails summary to configured alert recipient after meeting

**V2 (Planned):**
- Email each team member their individual action items

## Usage

### Automatic (via cron)
The bot runs automatically via cron every 5 minutes:
```bash
$TOOLKIT_DIR/skills/meeting-bot/meeting-bot
```

### Manual Join
Join a specific meeting immediately using Camofox:
```bash
join-meeting <meeting-url>
```

**Examples:**
```bash
join-meeting https://meet.google.com/abc-defg-hij
join-meeting meet.google.com/abc-defg-hij
```

**From anywhere:**
```bash
$TOOLKIT_DIR/skills/meeting-bot/join-meeting <url>
```

## Requirements

- **Camofox browser** running on port 9377 (via OpenClaw)
- **Node.js** + puppeteer-core (for browser automation)
- **Anthropic API key** (for extracting action items)
- **Google Meet recording** enabled for the assistant's Google account (configured in config.yaml)

## How It Works

1. **Check Calendar** (every 5 min): Looks for meetings starting in next 10 minutes
2. **Join Meeting**: If the assistant is invited, joins using Camofox browser
   - Connects to Camofox on localhost:9377
   - Loads authentication cookies
   - Mutes camera and microphone
   - Clicks "Join" button
3. **Record**: Uses Google Meet's native recording
4. **Wait**: Stays in meeting up to 2 hours
5. **Process**: After meeting ends:
   - Finds recording in Google Drive
   - Downloads Google's automatic transcript
   - Extracts summary, decisions, and action items with Claude
   - Emails summary to the configured alert recipient

## Email Format

```
Subject: Meeting Summary: [Meeting Title]

## Meeting Summary
[Overview of discussion]

## Key Decisions
- Decision 1
- Decision 2

## Action Items
- [ ] Task - Owner: Name - Due: date
- [ ] Task - Owner: Name

## Important Notes
- Context and follow-ups
```

## Configuration

Environment variables in ~/.env:
```bash
ANTHROPIC_API_KEY=sk-ant-...
GOG_KEYRING_PASSWORD=your-keyring-password
```

## Browser Integration

The meeting bot now uses **Camofox** (the default OpenClaw browser) instead of launching separate Chrome/Chromium instances. Benefits:

- ✅ **Better stealth**: Camofox has advanced fingerprinting resistance
- ✅ **Consistent auth**: Uses same browser session as other OpenClaw tools
- ✅ **Resource efficient**: Reuses existing browser instance
- ✅ **More human-like**: Better mimics real user behavior

The bot connects to Camofox via `puppeteer-core` at `http://localhost:9377`.

## Files

- `meeting-bot` - Main Python script (processes recordings)
- `camofox-join.js` - Node.js script to join meetings via Camofox
- `join-meeting` - Bash wrapper for easy meeting joining
- `google-cookies.json` - Stored authentication cookies

## Cron Schedule

```bash
*/5 * * * * source ~/.env && $TOOLKIT_DIR/skills/meeting-bot/meeting-bot >> /var/log/meeting-bot.log 2>&1
```

## Troubleshooting

**Meeting won't join:**
- Check if Camofox is running: `curl http://localhost:9377/health`
- Check cookies are valid: `ls -lh $TOOLKIT_DIR/skills/meeting-bot/google-cookies.json`
- View screenshots: `ls -lh /tmp/camofox-meet-*.png`

**Authentication issues:**
- Re-export cookies from authenticated browser session
- Ensure the assistant's Google account has access to the meeting

**Camofox not running:**
```bash
# Check OpenClaw browser status
openclaw doctor

# Restart Camofox if needed
cd $TOOLKIT_DIR/workspace/camofox-browser && npm start
```
