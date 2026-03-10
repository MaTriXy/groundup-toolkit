---
name: Google Workspace
description: Access Google Calendar, Gmail, and Google Docs/Drive using gws-auth CLI. Download Google Docs, manage calendar events, and send emails.
---

# Google Workspace Integration

Use the `gws-auth` CLI to interact with Google Calendar, Gmail, and Google Drive/Docs.

## Google Docs Operations

### Downloading Google Docs

To download a Google Doc as text:

```bash
~/.openclaw/skills/google-workspace/download-google-doc "DOCUMENT_URL_OR_ID"
```

**Examples:**
```bash
# Full URL
~/.openclaw/skills/google-workspace/download-google-doc "https://docs.google.com/document/d/1aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789_example/edit"

# Just the document ID
~/.openclaw/skills/google-workspace/download-google-doc "1aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789_example"
```

**When to use:**
- User shares a Google Docs link and asks you to process it
- User asks you to download or read a Google Doc
- User wants meeting notes from a Google Doc processed

**Important:** You CAN access Google Docs. Do NOT say you cannot access them.

Phone-to-email mappings are loaded from `config.yaml`. See `config.example.yaml` for format.

### Creating Calendar Events

**IMPORTANT:** The assistant has READ-ONLY access to team calendars. When creating events, create them on the assistant's calendar and invite the requesting user.

**Syntax for creating events:**

```bash
gws-auth calendar +insert \
  --summary "Event Title" \
  --start "YYYY-MM-DDTHH:MM:SS+02:00" \
  --end "YYYY-MM-DDTHH:MM:SS+02:00" \
  --attendee user@yourcompany.com
```

**Example: Create "Pick up kids from school" event:**

```bash
gws-auth calendar +insert \
  --summary "Pick up kids from school" \
  --start "2026-02-08T12:45:00+02:00" \
  --end "2026-02-08T13:15:00+02:00" \
  --attendee user@yourcompany.com \
  --description "Reminder to pick up kids"
```

**Time Format Guidelines:**
- Use RFC3339 format: `YYYY-MM-DDTHH:MM:SS+02:00`
- Israel timezone: `+02:00` (or `+03:00` during DST)
- For "today at 12:45", construct: `2026-02-08T12:45:00+02:00`
- Default duration: 30 minutes if not specified

**Optional Flags:**
- `--description "text"` - Add event description
- `--location "address"` - Add location

### Important Notes:

1. **Always add the requesting user as --attendee**
2. **Use primary as the default calendar** (assistant's calendar)
3. **Calculate proper timezone offset** (Israel is +02:00 or +03:00)
4. **If time is ambiguous**, ask the user for clarification

## Gmail Operations

### Send email:

```bash
gws-auth gmail +send --to user@example.com --subject "Subject" --body "Message body"
```

### Search threads:

```bash
gws-auth gmail users threads list --params '{"userId":"me","q":"from:user@example.com","maxResults":5}'
```

## Authentication

All commands use the assistant account credentials configured via `gws-auth auth login`.
Credentials are stored in `~/.config/gws/`.
