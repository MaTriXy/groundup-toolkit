---
name: meeting-reminders
description: Automated WhatsApp notifications for upcoming calendar meetings + on-demand next meeting queries. Sends reminders 10 minutes before meetings and provides rich attendee context on request.
version: 2.0.0
author: GroundUp VC
actions:
  - check-and-notify
  - next-meeting
  - configure
---

# Meeting Reminders Skill

Automatically sends WhatsApp notifications 10 minutes before calendar meetings start, with optional HubSpot context for external attendees. Also provides on-demand next meeting queries with rich attendee enrichment.

## When to Use This Skill

**Automatic reminders:** Runs via cron schedule (every 5 minutes) to check for upcoming meetings and send timely reminders.

**On-demand queries:** Ask via WhatsApp for your next meeting details.

Natural language triggers:
- "what's my next meeting?"
- "when is my next meeting?"
- "show my next meeting"
- "next meeting"
- "upcoming meeting"
- "what do I have next?"

## Features

### Automatic Reminders
- ⏰ **10-minute advance notifications** - Reminders sent 10-15 minutes before meetings
- 📱 **WhatsApp delivery** - Notifications via OpenClaw WhatsApp integration
- 🏢 **HubSpot context** - Includes company info, deals, and latest notes for external attendees
- 👥 **Per-team-member configuration** - Enable/disable for each person
- 🌍 **Timezone-aware** - Displays times in each team member's timezone
- 🔄 **Duplicate prevention** - SQLite database tracks sent notifications
- 🗓️ **Google Calendar integration** - Uses gws-auth CLI for calendar access

### Next Meeting Query (NEW)
- 🔍 **On-demand lookup** - Query your next upcoming meeting anytime
- ⏱️ **Countdown timer** - Shows "in 2 hours" / "in 30 minutes"
- 👤 **Rich attendee enrichment** - Automatic context for external attendees:
  - **LinkedIn:** Profile, title, company, experience, education
  - **Crunchbase:** Funding stage, total raised, investors, company size
  - **GitHub:** Repos, stars, languages (for technical contacts)
  - **Recent News:** Company announcements, funding news
- 💼 **HubSpot integration** - Deal stage, owner, recent activity
- 🔗 **Meeting links** - Google Meet links and locations
- 💾 **Smart caching** - 7-day cache to avoid rate limits

## Actions

### check-and-notify

Check for upcoming meetings and send WhatsApp reminders.

**Usage:**
```bash
meeting-reminders check-and-notify
```

This is the main action that:
1. Checks each enabled team member's calendar
2. Finds meetings starting in 10-15 minutes
3. Sends WhatsApp notifications with meeting details
4. Includes HubSpot context for external attendees
5. Tracks sent notifications to prevent duplicates

**Notification includes:**
- Meeting title
- Start time (in user's timezone)
- Attendee list
- Google Meet link or location
- Company info (if external attendee from HubSpot)
- Active deals and stage
- Latest CRM note

### next-meeting

Query the next upcoming meeting for a team member with rich attendee context.

**Usage:**
```bash
meeting-reminders next-meeting <email|phone>
```

**Arguments:**
- `email|phone` - Team member's email address or phone number

**Examples:**
```bash
meeting-reminders next-meeting user@yourcompany.com
meeting-reminders next-meeting +15551234567
meeting-reminders next-meeting teammate@yourcompany.com
```

**Response includes:**
- Meeting title
- Time until meeting (countdown)
- Start time (in user's timezone)
- Attendee list
- Google Meet link or location
- **Enriched attendee context** (for external attendees):
  - LinkedIn profile data
  - Crunchbase company information
  - GitHub profile (if technical)
  - Recent company news
- HubSpot deal context (stage, owner, notes)

**Example output:**
```
📅 Your next meeting in 2 hour(s):

📝 StarCloud Series A Discussion
⏰ Today at 3:00 PM EST
👥 You, Sarah Chen
🔗 https://meet.google.com/xyz-abcd

👥 ATTENDEE CONTEXT:

   👤 Sarah Chen
      📧 sarah@starcloud.com
      💼 CEO & Co-Founder at StarCloud
      📊 Series A - $12M raised (25-50 employees)
      📈 SaaS, Cloud Infrastructure
      🎓 Stanford University
      📰 Recent: StarCloud announces AWS partnership
      🔗 https://linkedin.com/in/example-profile

💼 DEAL CONTEXT:
📊 StarCloud - Series A
   Stage: Due Diligence
   Deal owner: Team Member
```

**WhatsApp Integration:**
When invoked via WhatsApp natural language (e.g., "what's my next meeting?"), the assistant will:
1. Detect the intent
2. Identify the caller by phone number
3. Call this action automatically
4. Return formatted results via WhatsApp

### configure

Display current configuration and team member status.

**Usage:**
```bash
meeting-reminders configure
```

Shows:
- Which team members have reminders enabled
- Phone numbers and timezones
- Database location
- Notification window settings

## Team Member Configuration

Edit the Python script to enable/disable reminders for team members:

Team members are configured in `config.yaml`. Each member can have `reminders_enabled: true/false`.

**To enable/disable:**
```bash
nano ~/.openclaw/skills/meeting-reminders/reminders.py
# Change 'enabled': True/False for each team member
```

## Attendee Enrichment System

**Added:** February 10, 2026

When you query your next meeting, external attendees are automatically enriched with data from:

### Phase 1: LinkedIn
- Current title and company
- Years of experience
- Previous notable roles
- Education background
- LinkedIn profile URL

### Phase 2: Crunchbase
- Funding stage (Seed, Series A, etc.)
- Total funding raised
- Last funding round details
- Company size (employee count)
- Industry/category
- Key investors

### Phase 3: GitHub
- Repository count
- Stars received
- Top programming languages
- Follower count
- GitHub profile URL

### Phase 4: Recent News
- Latest company announcements
- Recent funding news
- Product launches
- Strategic partnerships

**Technical details:**
- Uses web scraping (no API keys required)
- Smart 7-day caching to avoid rate limits
- Cache location: `$TOOLKIT_DIR/data/attendee_cache.db`
- Shared enrichment library: `$TOOLKIT_DIR/lib/enrichment.py`
- Automatically skips team members
- Only enriches external attendees
- Graceful degradation if data unavailable

**Note:** Not all attendees will have enrichment data. The system shows enrichment only when meaningful public profiles are found.

## Database

**Reminders tracking:** `/tmp/meeting-reminders.db`
- Tracks which meetings have been notified
- Auto-cleanup: Removes entries older than 24 hours
- Prevents duplicate notifications

**Enrichment cache:** `$TOOLKIT_DIR/data/attendee_cache.db`
- Caches attendee enrichment data for 7 days
- Speeds up repeat queries
- Respects rate limits

## Environment Requirements

**Required environment variables:**
- `MATON_API_KEY` - For HubSpot integration (optional)
- `WHATSAPP_ACCOUNT` - OpenClaw WhatsApp account (default: "main")

**Optional (enrichment works without these via web scraping):**
- `LINKEDIN_API_KEY` - If using LinkedIn API instead of scraping
- `CRUNCHBASE_API_KEY` - If using Crunchbase API instead of scraping

## Cron Schedule

Recommended: Run every 5 minutes for reliable 10-minute advance notifications

```cron
*/5 * * * * ~/.openclaw/skills/meeting-reminders/meeting-reminders check-and-notify
```

## Technical Details

- **Language:** Python 3
- **Dependencies:** pytz, requests, sqlite3
- **Calendar API:** gws-auth (Google Workspace CLI)
- **Messaging:** OpenClaw WhatsApp channel
- **CRM:** Maton API (HubSpot proxy)
- **Enrichment:** Web scraping via openclaw web search/fetch

## Monitoring

**Check recent notifications:**
```bash
tail -50 /var/log/meeting-reminders.log
```

**Test automatic reminders:**
```bash
meeting-reminders check-and-notify
```

**Test next meeting query:**
```bash
meeting-reminders next-meeting user@yourcompany.com
```

**View reminders database:**
```bash
sqlite3 /tmp/meeting-reminders.db "SELECT * FROM notified_meetings ORDER BY notified_at DESC LIMIT 10"
```

**View enrichment cache:**
```bash
sqlite3 $TOOLKIT_DIR/data/attendee_cache.db "SELECT email, last_updated FROM attendee_cache"
```

**Clear enrichment cache (force fresh data):**
```bash
rm $TOOLKIT_DIR/data/attendee_cache.db
```

## Troubleshooting

**No notifications received:**
1. Check if enabled in configuration
2. Verify WhatsApp account is working
3. Check gog authentication
4. Review logs for errors

**Wrong timezone:**
Edit team member timezone in configuration

**Duplicate notifications:**
Database should prevent this automatically. If it happens, clear the database:
```bash
rm /tmp/meeting-reminders.db
```

**Enrichment not showing:**
- Some attendees may not have public profiles
- Check if enrichment library is installed: `ls $TOOLKIT_DIR/lib/enrichment.py`
- Test enrichment directly: `python3 $TOOLKIT_DIR/lib/enrichment.py test@example.com "Test User"`
- Enrichment only shows for external attendees (not team members)

**Enrichment taking too long:**
- First query: 10-15 seconds (scraping all sources)
- Cached queries: <1 second
- Check cache: `ls -lh $TOOLKIT_DIR/data/attendee_cache.db`

## Privacy & Security

- Only accesses calendar event metadata (no descriptions)
- Only sends to opted-in team members
- No cross-calendar access
- Auto-cleanup of tracking data after 24 hours
- Enrichment uses only publicly available data
- Enrichment cache retained for 7 days only
- Only enriches external attendees (team members skipped)
