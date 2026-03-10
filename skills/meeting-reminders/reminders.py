#!/usr/bin/env python3
"""
Meeting Reminder Automation - GroundUp Toolkit
Enhanced with: AI briefs, email context, stage-aware tips, previous meeting context,
and post-meeting nudge (for deals only).
"""

import os
import sys
import json
import subprocess
import sqlite3
import fcntl
import time
import requests
import re
from datetime import datetime, timedelta
import pytz

# Shared config loader
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from lib.config import config
from lib.whatsapp import send_whatsapp
from lib.email import send_email
from lib.gws import gws_calendar_events, gws_gmail_send, gws_gmail_search, gws_gmail_thread_get
from lib.hubspot import (
    search_company as _search_company, get_deals_for_company,
    get_latest_note as _get_latest_note
)
from lib.claude import call_claude

# Enrichment library integration
try:
    from enrichment import EnrichmentService
    ENRICHMENT_AVAILABLE = True
except ImportError:
    print("Warning: Enrichment library not available")
    ENRICHMENT_AVAILABLE = False

WHATSAPP_ACCOUNT = config.whatsapp_account

# Persistent database path (survives reboots, unlike /tmp)
_TOOLKIT_ROOT = os.environ.get('TOOLKIT_ROOT', os.path.join(os.path.dirname(__file__), '..', '..'))
_DATA_DIR = os.path.join(_TOOLKIT_ROOT, 'data')
os.makedirs(_DATA_DIR, mode=0o700, exist_ok=True)
DB_PATH = os.path.join(_DATA_DIR, "meeting-reminders.db")
LOCK_PATH = os.path.join(_DATA_DIR, "meeting-reminders.lock")

# Team members with calendars and phone numbers (loaded from config)
TEAM_MEMBERS = {}
for m in config.team_members:
    TEAM_MEMBERS[m['email']] = {
        'name': m['name'].split()[0],  # First name only
        'phone': m['phone'],
        'timezone': m['timezone'],
        'enabled': m.get('reminders_enabled', True)
    }

# Notification window: 5-20 minutes before meeting
NOTIFICATION_WINDOW_START = 20  # minutes before meeting (far edge)
NOTIFICATION_WINDOW_END = 5     # minutes before meeting (near edge)

# Post-meeting nudge: 30-40 minutes after meeting ended
NUDGE_WINDOW_START = 30
NUDGE_WINDOW_END = 40

# VC pipeline stage map with talking point suggestions
# Loaded from config.yaml if available, with hardcoded fallback
_DEFAULT_STAGE_MAP = {
    'qualifiedtobuy': {
        'label': 'Sourcing',
        'tips': 'Initial screen — validate thesis fit, team background, and market size. Ask what made them start this company.',
    },
    'appointmentscheduled': {
        'label': 'Screening',
        'tips': 'Deeper dive — understand product differentiation, early traction signals, and competitive landscape.',
    },
    'presentationscheduled': {
        'label': 'First Meeting',
        'tips': 'Get specifics: unit economics, customer pipeline, go-to-market plan. Assess founder-market fit.',
    },
    'decisionmakerboughtin': {
        'label': 'IC Review',
        'tips': 'Prepare for IC — gather reference points, comparable deals, and key risks to present.',
    },
    'contractsent': {
        'label': 'Due Diligence',
        'tips': 'Deep DD — financials, cap table, legal, customer references. Verify claims made in earlier meetings.',
    },
    'closedwon': {
        'label': 'Term Sheet Offered',
        'tips': 'Negotiate terms — valuation, board seat, pro-rata rights, milestones. Keep momentum.',
    },
    '1112320899': {
        'label': 'Term Sheet Signed',
        'tips': 'Legal close — coordinate with lawyers, finalize docs, wire timeline.',
    },
    '1112320900': {
        'label': 'Investment Closed',
        'tips': 'Post-close — discuss board cadence, reporting expectations, how you can help.',
    },
    '1008223160': {
        'label': 'Portfolio Monitoring',
        'tips': 'Check-in — KPIs, runway, hiring progress, any blockers you can help unblock.',
    },
    '1138024523': {
        'label': 'Keep on Radar',
        'tips': 'Light touch — see what has changed since you last spoke, if timing is better now.',
    },
}
# Prefer config.yaml stages, fall back to hardcoded
STAGE_MAP = config.get_stage_map() or _DEFAULT_STAGE_MAP


class ReminderDatabase:
    """Track which meetings have been notified and nudged"""

    def __init__(self, db_path):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Check if table exists with old schema (event_id-only PK).
        cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='notified_meetings'")
        row = cursor.fetchone()
        if row and 'PRIMARY KEY (event_id, email)' not in row[0]:
            cursor.execute('DROP TABLE notified_meetings')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notified_meetings (
                event_id TEXT NOT NULL,
                email TEXT NOT NULL,
                notified_at TEXT NOT NULL,
                meeting_start TEXT NOT NULL,
                PRIMARY KEY (event_id, email)
            )
        ''')

        # Post-meeting nudge tracking
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nudged_meetings (
                event_id TEXT NOT NULL,
                email TEXT NOT NULL,
                nudged_at TEXT NOT NULL,
                PRIMARY KEY (event_id, email)
            )
        ''')

        # Clean up old records (older than 48 hours)
        cutoff = (datetime.now(pytz.UTC).replace(tzinfo=None) - timedelta(hours=48)).isoformat()
        cursor.execute('DELETE FROM notified_meetings WHERE notified_at < ?', (cutoff,))
        cursor.execute('DELETE FROM nudged_meetings WHERE nudged_at < ?', (cutoff,))
        conn.commit()
        conn.close()

    def is_notified(self, event_id, email):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM notified_meetings WHERE event_id = ? AND email = ?', (event_id, email))
        result = cursor.fetchone() is not None
        conn.close()
        return result

    def mark_notified(self, event_id, email, meeting_start):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO notified_meetings (event_id, email, notified_at, meeting_start) VALUES (?, ?, ?, ?)',
            (event_id, email, datetime.now(pytz.UTC).replace(tzinfo=None).isoformat(), meeting_start)
        )
        conn.commit()
        conn.close()

    def is_nudged(self, event_id, email):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT 1 FROM nudged_meetings WHERE event_id = ? AND email = ?', (event_id, email))
        result = cursor.fetchone() is not None
        conn.close()
        return result

    def mark_nudged(self, event_id, email):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT OR REPLACE INTO nudged_meetings (event_id, email, nudged_at) VALUES (?, ?, ?)',
            (event_id, email, datetime.now(pytz.UTC).replace(tzinfo=None).isoformat())
        )
        conn.commit()
        conn.close()

    def get_notified_meetings_ending_between(self, start, end):
        """Get meetings that were notified and ended in the given window."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            'SELECT event_id, email, meeting_start FROM notified_meetings WHERE meeting_start BETWEEN ? AND ?',
            (start.isoformat(), end.isoformat())
        )
        results = cursor.fetchall()
        conn.close()
        return results


def get_upcoming_events(email, start_time, end_time):
    """Get calendar events in time range via gws-auth."""
    time_min = start_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    time_max = end_time.strftime('%Y-%m-%dT%H:%M:%SZ')
    return gws_calendar_events(email, time_min, time_max, max_results=50)


def format_meeting_time(start_time_str, timezone_str):
    """Format meeting time in user's timezone"""
    start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
    user_tz = pytz.timezone(timezone_str)
    local_time = start_time.astimezone(user_tz)
    return local_time.strftime('%I:%M %p').lstrip('0')


def send_whatsapp_message(phone, message, max_retries=3, retry_delay=3):
    """Send WhatsApp message via OpenClaw with retry logic."""
    return send_whatsapp(phone, message, account=WHATSAPP_ACCOUNT,
                         max_retries=max_retries, retry_delay=retry_delay)


def send_email_fallback(to_email, name, message):
    """Fallback: send meeting reminder via email when WhatsApp is down"""
    try:
        subject = "Meeting Reminder"
        first_line = message.split('\n')[0] if message else ''
        if first_line:
            subject = f"Meeting Reminder: {first_line.strip()}"
            if len(subject) > 120:
                subject = subject[:117] + '...'
        body = f"Hi {name},\n\n{message}\n\n-- {config.assistant_name} (sent via email because WhatsApp was unavailable)"
        if gws_gmail_send(to_email, subject, body):
            print(f"  ✓ Email fallback sent to {to_email}")
            return True
        else:
            print(f"  ✗ Email fallback failed for {to_email}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"  ✗ Email fallback exception for {to_email}: {e}", file=sys.stderr)
        return False


def format_attendees(attendees, owner_email):
    """Format attendee list (excluding owner)"""
    if not attendees:
        return "No other attendees"
    filtered = [a for a in attendees if a != owner_email and '@' in a]
    if not filtered:
        return "No other attendees"
    names = [a.split('@')[0].replace('.', ' ').title() for a in filtered[:3]]
    if len(filtered) > 3:
        return f"{', '.join(names)} and {len(filtered) - 3} others"
    return ', '.join(names)


def get_external_attendees(attendees, owner_email):
    """Get list of external (non-team-domain) attendee emails"""
    if not attendees:
        return []
    external = []
    for attendee in attendees:
        email = attendee.get('email', '') if isinstance(attendee, dict) else attendee
        if email and '@' in email and email != owner_email:
            if not email.endswith('@' + config.team_domain):
                external.append(email)
    return external


def is_internal_meeting(attendees, owner_email):
    """Check if all attendees are internal — no external guests"""
    return len(get_external_attendees(attendees, owner_email)) == 0


def search_hubspot_company(email_domain):
    """Search HubSpot for company by domain."""
    return _search_company(domain=email_domain)


def get_company_deals(company_id):
    """Get active deals for a company."""
    return get_deals_for_company(company_id, limit=3)


def get_latest_note(company_id):
    """Get the latest note for a company."""
    return _get_latest_note(company_id)


def get_hubspot_context(attendees, owner_email):
    """Get HubSpot context for external attendees"""
    external_emails = get_external_attendees(attendees, owner_email)
    if not external_emails:
        return None

    first_email = external_emails[0] if isinstance(external_emails[0], str) else external_emails[0].get('email', '')
    domain = first_email.split('@')[-1]
    print(f"    Looking up HubSpot data for {domain}...")

    company = search_hubspot_company(domain)
    if not company:
        print(f"    No HubSpot company found")
        return None

    company_id = company.get('id')
    company_name = company.get("properties", {}).get("name") or domain
    company_industry = company.get('properties', {}).get('industry', '')
    print(f"    Found company: {company_name}")

    deals = get_company_deals(company_id)
    latest_note = get_latest_note(company_id)

    return {
        'company_id': company_id,
        'company_name': company_name,
        'industry': company_industry,
        'deals': deals,
        'latest_note': latest_note
    }


def get_deal_stage_info(deals):
    """Extract deal stage info for stage-aware suggestions"""
    if not deals:
        return None, None
    deal = deals[0]
    stage_id = deal.get('properties', {}).get('dealstage', '')
    stage_info = STAGE_MAP.get(stage_id)
    return stage_id, stage_info


# ============================================================
# NEW: Recent email context
# ============================================================

def get_recent_email_context(external_emails, attendee_names=None, max_threads=3):
    """Search Gmail for recent email threads with external attendees.

    Searches by exact email AND by name (for forwarded emails where from: doesn't match).
    Returns a short summary of recent email exchanges.
    """
    if not external_emails and not attendee_names:
        return None

    # Build search query — combine email addresses AND names
    query_parts = []

    # Search by exact email
    for email in (external_emails or []):
        e = email if isinstance(email, str) else email.get('email', '')
        if '@' in e:
            query_parts.append(f"from:{e} OR to:{e}")

    # Also search by name (catches forwarded emails and form submissions)
    if attendee_names:
        for name in attendee_names[:3]:
            name = name.strip()
            if name and len(name) > 2:
                query_parts.append(f'"{name}"')

    if not query_parts:
        return None

    query = f"({' OR '.join(query_parts)}) newer_than:30d"

    try:
        threads = gws_gmail_search(query, max_results=max_threads)
        if not threads:
            return None

        snippets = []
        for thread in threads[:max_threads]:
            thread_id = thread.get('id')
            if not thread_id:
                continue
            thread_data = gws_gmail_thread_get(thread_id, fmt="metadata")
            if not thread_data:
                continue

            messages = thread_data.get('messages', [])
            if not messages:
                continue

            # Get subject from first message headers
            headers = messages[0].get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'].lower() == 'subject'), 'No subject')
            # Clean subject
            subject = re.sub(r'^(re|fwd|fw):\s*', '', subject, flags=re.IGNORECASE).strip()

            snippet = thread.get('snippet', '')[:120]
            date_ms = int(messages[-1].get('internalDate', 0))
            date_str = datetime.fromtimestamp(date_ms / 1000).strftime('%b %d') if date_ms else ''

            snippets.append(f"• {subject} ({date_str}): {snippet}")

        return '\n'.join(snippets) if snippets else None

    except Exception as e:
        print(f"    Email context error: {e}", file=sys.stderr)
        return None


# ============================================================
# NEW: Previous meeting context
# ============================================================

def get_previous_meeting_context(email, external_domains, current_event_id,
                                  external_emails=None):
    """Find previous calendar meetings with the same external attendees.

    Uses exact email matching when available. Falls back to domain matching
    only for company-specific domains (skips generic providers like gmail.com).
    """
    # Generic email providers — domain matching is useless for these
    GENERIC_DOMAINS = {
        'gmail.com', 'outlook.com', 'hotmail.com', 'yahoo.com', 'icloud.com',
        'live.com', 'aol.com', 'protonmail.com', 'me.com', 'mail.com',
        'googlemail.com', 'msn.com', 'ymail.com',
    }

    # Build match sets
    exact_emails = set()
    if external_emails:
        for e in external_emails:
            addr = e if isinstance(e, str) else e.get('email', '')
            if '@' in addr:
                exact_emails.add(addr.lower())

    # Only use domain matching for company domains, not generic ones
    match_domains = set()
    if external_domains:
        for d in external_domains:
            if d and d not in GENERIC_DOMAINS and d != config.team_domain:
                match_domains.add(d)

    if not exact_emails and not match_domains:
        return None

    now = datetime.now(pytz.UTC).replace(tzinfo=None)
    lookback_start = now - timedelta(days=90)

    try:
        events = get_upcoming_events(email, lookback_start, now)
        if not events:
            return None

        past_meetings = []
        for event in events:
            eid = event.get('id')
            if eid == current_event_id:
                continue

            attendees = event.get('attendees', [])
            attendee_emails_list = [a.get('email', '').lower() for a in attendees]

            # Check for exact email match first (always reliable)
            has_match = bool(exact_emails & set(attendee_emails_list))

            # Fall back to domain matching only for company domains
            if not has_match and match_domains:
                for ae in attendee_emails_list:
                    if '@' in ae:
                        domain = ae.split('@')[-1]
                        if domain in match_domains:
                            has_match = True
                            break

            if has_match:
                start = event.get('start', {}).get('dateTime', '')
                summary = event.get('summary', 'Untitled')
                if start:
                    try:
                        dt = datetime.fromisoformat(start.replace('Z', '+00:00')).astimezone(pytz.UTC).replace(tzinfo=None)
                        days_ago = (now - dt).days
                        past_meetings.append({
                            'summary': summary,
                            'days_ago': days_ago,
                            'date': dt.strftime('%b %d'),
                        })
                    except Exception:
                        pass

        if not past_meetings:
            return None

        past_meetings.sort(key=lambda m: m['days_ago'])
        lines = []
        for m in past_meetings[:3]:
            lines.append(f"• {m['summary']} ({m['date']}, {m['days_ago']}d ago)")

        return '\n'.join(lines)

    except Exception as e:
        print(f"    Previous meeting lookup error: {e}", file=sys.stderr)
        return None


# ============================================================
# NEW: AI-generated meeting brief
# ============================================================

def generate_ai_brief(summary, member_name, attendee_names, hubspot_context,
                      email_context, previous_meetings, stage_info):
    """Use Claude to generate a concise, actionable meeting prep brief."""

    context_parts = []
    context_parts.append(f"Meeting: {summary}")
    context_parts.append(f"Team member: {member_name}")
    context_parts.append(f"External attendees: {attendee_names}")

    if hubspot_context:
        context_parts.append(f"\nHubSpot company: {hubspot_context.get('company_name', 'Unknown')}")
        if hubspot_context.get('industry'):
            context_parts.append(f"Industry: {hubspot_context['industry']}")
        if hubspot_context.get('deals'):
            deal = hubspot_context['deals'][0]
            props = deal.get('properties', {})
            deal_name = props.get('dealname', 'Unknown')
            stage_id = props.get('dealstage', '')
            stage_label = STAGE_MAP.get(stage_id, {}).get('label', stage_id)
            context_parts.append(f"Deal: {deal_name} (Stage: {stage_label})")
        if hubspot_context.get('latest_note'):
            context_parts.append(f"Latest CRM note: {hubspot_context['latest_note']}")

    if email_context:
        context_parts.append(f"\nRecent email threads with this person/company:\n{email_context}")
        context_parts.append("NOTE: Some emails above may be about OTHER companies or people — only reference emails that clearly involve the meeting attendee.")

    if previous_meetings:
        context_parts.append(f"\nPrevious meetings with this contact:\n{previous_meetings}")

    if stage_info:
        context_parts.append(f"\nStage guidance: {stage_info.get('tips', '')}")

    context_text = '\n'.join(context_parts)

    system = (
        f"You are {config.assistant_name}, a VC firm assistant at GroundUp Ventures. "
        "Write a meeting prep note for a team member. "
        "Format for WhatsApp readability: use short lines with line breaks between each point. "
        "\n\n"
        "Structure: "
        "Line 1: One sentence — who you are meeting and the context (e.g. their role, company, relationship). "
        "Then a blank line. "
        "Then 2-3 bullet points (use the bullet character) with specific, actionable talking points. "
        "Then a blank line. "
        "Final line: one concrete goal or decision to aim for in this meeting. "
        "\n\n"
        "CRITICAL RULES:\n"
        "- NEVER fabricate or infer information not explicitly in the data. If you don't have data, say so.\n"
        "- NEVER invent narratives about past interactions (e.g. 'last connected at a gathering').\n"
        "- Only reference emails/meetings that clearly involve the meeting attendee — ignore unrelated emails about other companies.\n"
        "- Do not mention deck reviews, pitches, or analyses unless they are specifically about this attendee's company.\n"
        "- Be specific, not generic. No filler like 'catch up on momentum' or 'explore synergies'.\n"
        "- If previous meetings exist, state them factually (date, topic) — don't embellish.\n"
        "- If no meaningful data exists, write: 'No prior context found — first real interaction.' and suggest discovery questions.\n"
        "- No markdown formatting (no ** or #). Plain text only.\n"
        "- Total length: 5-8 short lines max."
    )

    try:
        brief = call_claude(
            context_text,
            system_prompt=system,
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            timeout=30,
        )
        return brief
    except Exception as e:
        print(f"    AI brief generation error: {e}", file=sys.stderr)
        return None


# ============================================================
# NEW: Post-meeting nudge
# ============================================================

def process_post_meeting_nudges(db):
    """Send follow-up nudges after meetings that have a HubSpot deal."""
    now = datetime.now(pytz.UTC).replace(tzinfo=None)

    # Look for meetings that ended 30-40 minutes ago
    nudge_start = now - timedelta(minutes=NUDGE_WINDOW_END)
    nudge_end = now - timedelta(minutes=NUDGE_WINDOW_START)

    print(f"\n  Checking for post-meeting nudges (meetings ended {NUDGE_WINDOW_START}-{NUDGE_WINDOW_END}m ago)...")

    nudge_count = 0

    for email, member in TEAM_MEMBERS.items():
        if not member['enabled']:
            continue

        # Get events that ended in the nudge window
        # We fetch events that started up to 2 hours before the nudge window end
        fetch_start = nudge_start - timedelta(hours=2)
        events = get_upcoming_events(email, fetch_start, nudge_end)

        if not events:
            continue

        for event in events:
            event_id = event.get('id')
            if not event_id:
                continue

            # Calculate event end time
            end_time_str = event.get('end', {}).get('dateTime')
            if not end_time_str:
                continue

            try:
                event_end = datetime.fromisoformat(end_time_str.replace('Z', '+00:00')).astimezone(pytz.UTC).replace(tzinfo=None)
            except Exception:
                continue

            # Check if the meeting ended in our nudge window
            if not (nudge_start <= event_end <= nudge_end):
                continue

            # Skip if already nudged
            if db.is_nudged(event_id, email):
                continue

            # Skip solo meetings
            attendees = event.get('attendees', [])
            other_attendees = [a for a in attendees if a.get('email', '') != email]
            if not other_attendees:
                continue

            # Skip internal meetings
            if is_internal_meeting(attendees, email):
                continue

            # Only nudge if there's a HubSpot deal
            external_emails = get_external_attendees(attendees, email)
            if not external_emails:
                continue

            first_email = external_emails[0]
            domain = first_email.split('@')[-1]
            company = search_hubspot_company(domain)

            if not company:
                print(f"    ⏭  No HubSpot company for {domain}, skipping nudge")
                continue

            company_id = company.get('id')
            company_name = company.get("properties", {}).get("name") or domain
            deals = get_company_deals(company_id)

            if not deals:
                print(f"    ⏭  No deals for {company_name}, skipping nudge")
                continue

            # We have a deal — send the nudge
            summary = event.get('summary', 'your meeting')
            deal_name = deals[0].get('properties', {}).get('dealname', company_name)
            stage_id = deals[0].get('properties', {}).get('dealstage', '')
            stage_label = STAGE_MAP.get(stage_id, {}).get('label', stage_id)

            nudge_msg = (
                f"👋 How did \"{summary}\" go?\n"
                f"\n"
                f"📋 Deal: {deal_name} ({stage_label})\n"
                f"\n"
                f"Quick options:\n"
                f"• Reply with a note and I'll log it to HubSpot\n"
                f"• \"move to [stage]\" to update the deal stage\n"
                f"• \"pass\" if we're not moving forward"
            )

            print(f"    📤 Sending post-meeting nudge: {summary} → {member['name']}")
            sent = send_whatsapp_message(member['phone'], nudge_msg)
            if sent:
                db.mark_nudged(event_id, email)
                nudge_count += 1

    print(f"  📬 Sent {nudge_count} post-meeting nudge(s)")


# ============================================================
# Enrichment (existing)
# ============================================================

def enrich_external_attendees(attendees, owner_email):
    """Enrich external attendees with LinkedIn, Crunchbase, GitHub, News"""
    if not ENRICHMENT_AVAILABLE:
        return []

    team_emails = set(TEAM_MEMBERS.keys())
    enriched_results = []
    service = EnrichmentService()

    for attendee in attendees:
        email = attendee.get('email', '').lower()
        name = attendee.get('displayName', email)

        if email in team_emails or email == owner_email.lower():
            continue
        if not email or '@' not in email:
            continue
        if any(x in email for x in ['noreply', 'no-reply', 'calendar', 'bot', 'notification']):
            continue

        try:
            enrichment = service.enrich_attendee(email, name, use_cache=True)
            has_data = (
                enrichment.get('linkedin') or enrichment.get('crunchbase') or
                enrichment.get('github') or enrichment.get('recent_news')
            )
            if has_data:
                formatted = service.format_enrichment(enrichment)
                enriched_results.append(formatted)
        except Exception as e:
            print(f"    Warning: Could not enrich {name} ({email}): {e}")
            continue

    return enriched_results


# ============================================================
# Main reminder processing
# ============================================================

def process_meeting_reminders():
    """Main processing function"""
    lock_file = open(LOCK_PATH, 'w')
    try:
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        print(f"[{datetime.now(pytz.UTC).replace(tzinfo=None).isoformat()}] Another instance is running, skipping.")
        return

    try:
        _do_process_meeting_reminders()
    finally:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()


def _do_process_meeting_reminders():
    """Inner processing function (called under lock)"""
    print(f"[{datetime.now(pytz.UTC).replace(tzinfo=None).isoformat()}] Starting meeting reminder check...")

    db = ReminderDatabase(DB_PATH)
    now = datetime.now(pytz.UTC).replace(tzinfo=None)

    # Check window: 5-20 minutes from now
    window_start = now + timedelta(minutes=NOTIFICATION_WINDOW_END)
    window_end = now + timedelta(minutes=NOTIFICATION_WINDOW_START)

    print(f"  Checking for meetings between {window_start.strftime('%H:%M')} and {window_end.strftime('%H:%M')} UTC")

    total_notifications = 0

    for email, member in TEAM_MEMBERS.items():
        if not member['enabled']:
            continue

        print(f"\n  Checking {member['name']}'s calendar...")

        events = get_upcoming_events(email, window_start, window_end)

        if not events:
            print(f"    No upcoming meetings")
            continue

        print(f"    Found {len(events)} meeting(s) in notification window")

        for event in events:
            event_id = event.get('id')
            summary = event.get('summary', 'Untitled Meeting')
            start_time = event.get('start', {}).get('dateTime')
            location = event.get('location', '')
            conference = event.get('conferenceData', {})
            attendees = event.get('attendees', [])

            if not event_id or not start_time:
                continue

            # Validate meeting time
            try:
                meeting_start = datetime.fromisoformat(start_time.replace('Z', '+00:00')).astimezone(pytz.UTC).replace(tzinfo=None)
                if meeting_start < now:
                    print(f"    ⏭  Already started: {summary}")
                    continue
                if meeting_start > window_end:
                    minutes_away = (meeting_start - now).total_seconds() / 60
                    print(f"    ⏭  Too far in future: {summary} ({minutes_away:.1f} min away)")
                    continue
                minutes_away = (meeting_start - now).total_seconds() / 60
                print(f"    ✓ In window: {summary} ({minutes_away:.1f} min away)")
            except Exception as e:
                print(f"    Warning: Could not parse time for {summary}: {e}")
                continue

            # Skip solo meetings (blocked time)
            other_attendees = [a for a in attendees if a.get('email', '') != email]
            if not other_attendees:
                print(f"    ⏭  Solo meeting (blocked time): {summary}")
                continue

            # Check if already notified
            if db.is_notified(event_id, email):
                print(f"    ⏭  Already notified: {summary}")
                continue

            # Format meeting details
            meeting_time = format_meeting_time(start_time, member['timezone'])
            internal = is_internal_meeting(attendees, email)

            mins_away = int(round(minutes_away))
            message_lines = [
                f"🔔 Meeting in ~{mins_away} minutes:",
                f"",
                f"📅 {summary}",
                f"⏰ {meeting_time}",
            ]

            # Attendees for external meetings
            if not internal:
                attendee_list = format_attendees([a.get('email') for a in attendees], email)
                message_lines.append(f"👥 {attendee_list}")

            # Meeting link / location
            meet_link = None
            if conference and 'entryPoints' in conference:
                for entry in conference['entryPoints']:
                    if entry.get('entryPointType') == 'video':
                        meet_link = entry.get('uri')
                        break

            if meet_link:
                message_lines.append(f"🔗 {meet_link}")
            elif location:
                message_lines.append(f"📍 {location}")

            # --- Enhanced context for external meetings ---
            hubspot_context = None
            email_context = None
            previous_meetings = None
            stage_info = None
            ai_brief = None

            if not internal:
                external_emails = get_external_attendees(attendees, email)
                external_domains = set()
                for ext_email in external_emails:
                    if '@' in ext_email:
                        external_domains.add(ext_email.split('@')[-1])

                # HubSpot context
                hubspot_context = get_hubspot_context(attendees, email)

                # Stage-aware suggestions
                if hubspot_context and hubspot_context.get('deals'):
                    _, stage_info = get_deal_stage_info(hubspot_context['deals'])

                # Extract external attendee names for name-based search
                ext_attendee_names = []
                for a in (attendees or []):
                    if isinstance(a, dict):
                        ae = a.get('email', '')
                        if ae in external_emails and a.get('displayName'):
                            ext_attendee_names.append(a['displayName'])

                # Recent email threads
                print(f"    📧 Searching recent emails...")
                email_context = get_recent_email_context(external_emails, attendee_names=ext_attendee_names)

                # Previous meetings with this contact
                print(f"    📅 Checking previous meetings...")
                previous_meetings = get_previous_meeting_context(email, external_domains, event_id, external_emails=external_emails)

                # Enrichment
                if ENRICHMENT_AVAILABLE and attendees:
                    enriched_attendees = enrich_external_attendees(attendees, email)
                    if enriched_attendees:
                        message_lines.append("")
                        message_lines.append("👥 ATTENDEE CONTEXT:")
                        for enriched in enriched_attendees:
                            message_lines.append(enriched)

                # HubSpot details (company, deal, note)
                if hubspot_context:
                    message_lines.append("")
                    message_lines.append(f"🏢 {hubspot_context['company_name']}")
                    if hubspot_context.get('industry'):
                        message_lines.append(f"🏭 {hubspot_context['industry']}")
                    if hubspot_context.get('deals'):
                        deal = hubspot_context['deals'][0]
                        deal_name = deal.get('properties', {}).get('dealname', 'Unnamed Deal')
                        deal_stage = deal.get('properties', {}).get('dealstage', '')
                        stage_label = STAGE_MAP.get(deal_stage, {}).get('label', deal_stage)
                        message_lines.append(f"💼 Deal: {deal_name}")
                        if stage_label:
                            message_lines.append(f"📊 Stage: {stage_label}")
                    if hubspot_context.get('latest_note'):
                        message_lines.append("")
                        message_lines.append("📝 Last Note:")
                        message_lines.append(hubspot_context['latest_note'])

                # Previous meetings
                if previous_meetings:
                    message_lines.append("")
                    message_lines.append("🕐 Previous meetings:")
                    message_lines.append(previous_meetings)

                # Email thread context
                if email_context:
                    message_lines.append("")
                    message_lines.append("📧 Recent emails:")
                    message_lines.append(email_context)

                # AI Brief — the star of the show
                attendee_names = format_attendees([a.get('email') for a in attendees], email)
                print(f"    🤖 Generating AI brief...")
                ai_brief = generate_ai_brief(
                    summary, member['name'], attendee_names,
                    hubspot_context, email_context, previous_meetings, stage_info
                )

                if ai_brief:
                    message_lines.append("")
                    message_lines.append("💡 PREP BRIEF:")
                    message_lines.append(ai_brief)
                elif stage_info:
                    # Fallback: just show stage tips if AI brief failed
                    message_lines.append("")
                    message_lines.append(f"💡 {stage_info['tips']}")

            message = '\n'.join(message_lines)

            # Send
            print(f"    📤 Sending reminder: {summary}")
            sent = send_whatsapp_message(member['phone'], message)
            if not sent:
                print(f"    📧 WhatsApp failed, falling back to email...")
                sent = send_email_fallback(email, member['name'], message)
            if sent:
                db.mark_notified(event_id, email, start_time)
                total_notifications += 1

    print(f"\n✅ Sent {total_notifications} reminder(s)")

    # Post-meeting nudges
    process_post_meeting_nudges(db)


# ============================================================
# Query mode (unchanged)
# ============================================================

def get_next_meeting(email):
    """Get the next upcoming meeting for a user"""
    now = datetime.now(pytz.UTC).replace(tzinfo=None)
    end_time = now + timedelta(days=7)
    events = get_upcoming_events(email, now, end_time)

    if not events:
        return None

    future_events = []
    for event in events:
        start_time = event.get('start', {}).get('dateTime')
        if not start_time:
            continue
        try:
            meeting_start = datetime.fromisoformat(start_time.replace('Z', '+00:00')).astimezone(pytz.UTC).replace(tzinfo=None)
            if meeting_start > now:
                event['_parsed_start'] = meeting_start
                future_events.append(event)
        except Exception:
            continue

    if not future_events:
        return None

    future_events.sort(key=lambda e: e['_parsed_start'])
    return future_events[0]


def format_next_meeting_message(event, member_info):
    """Format a rich message about the next meeting with attendee enrichment"""
    if not event:
        return f"📅 No upcoming meetings found for {member_info['name']}"

    summary = event.get('summary', 'Untitled Meeting')
    start_time = event.get('start', {}).get('dateTime')
    location = event.get('location', '')
    conference = event.get('conferenceData', {})
    attendees = event.get('attendees', [])

    meeting_start = datetime.fromisoformat(start_time.replace('Z', '+00:00')).astimezone(pytz.UTC).replace(tzinfo=None)
    now = datetime.now(pytz.UTC).replace(tzinfo=None)
    time_until = meeting_start - now

    if time_until.days > 0:
        time_until_str = f"in {time_until.days} day(s)"
    elif time_until.seconds >= 3600:
        hours = time_until.seconds // 3600
        time_until_str = f"in {hours} hour(s)"
    else:
        minutes = time_until.seconds // 60
        time_until_str = f"in {minutes} minute(s)"

    meeting_time = format_meeting_time(start_time, member_info['timezone'])
    internal = is_internal_meeting(attendees, member_info.get('email', ''))

    message_lines = [
        f"📅 Your next meeting {time_until_str}:",
        f"",
        f"📝 {summary}",
        f"⏰ {meeting_time}",
    ]

    if not internal:
        attendee_list = format_attendees([a.get('email') for a in attendees], member_info.get('email', ''))
        message_lines.append(f"👥 {attendee_list}")

    meet_link = None
    if conference and 'entryPoints' in conference:
        for entry in conference['entryPoints']:
            if entry.get('entryPointType') == 'video':
                meet_link = entry.get('uri')
                break

    if meet_link:
        message_lines.append(f"🔗 {meet_link}")
    elif location:
        message_lines.append(f"📍 {location}")

    if not internal:
        if ENRICHMENT_AVAILABLE and attendees:
            enriched_attendees = enrich_external_attendees(attendees, member_info.get('email', ''))
            if enriched_attendees:
                message_lines.append("")
                message_lines.append("👥 ATTENDEE CONTEXT:")
                for enriched in enriched_attendees:
                    message_lines.append(enriched)

        hubspot_context = get_hubspot_context(attendees, member_info.get('email', ''))
        if hubspot_context:
            message_lines.append("")
            message_lines.append(f"🏢 {hubspot_context['company_name']}")
            if hubspot_context.get('industry'):
                message_lines.append(f"🏭 {hubspot_context['industry']}")
            if hubspot_context.get('deals'):
                deal = hubspot_context['deals'][0]
                deal_name = deal.get('properties', {}).get('dealname', 'Unnamed Deal')
                deal_stage = deal.get('properties', {}).get('dealstage', '')
                stage_label = STAGE_MAP.get(deal_stage, {}).get('label', deal_stage)
                message_lines.append(f"💼 Deal: {deal_name}")
                if stage_label:
                    message_lines.append(f"📊 Stage: {stage_label}")
            if hubspot_context.get('latest_note'):
                message_lines.append("")
                message_lines.append("📝 Last Note:")
                message_lines.append(hubspot_context['latest_note'])

    return '\n'.join(message_lines)


def query_next_meeting(identifier):
    """Query next meeting by email or phone number"""
    member = None
    member_email = None

    for email_addr, info in TEAM_MEMBERS.items():
        if identifier.lower() == email_addr.lower() or identifier == info['phone']:
            member = info
            member_email = email_addr
            member['email'] = email_addr
            break

    if not member:
        return f"❌ User not found: {identifier}"

    print(f"🔍 Looking up next meeting for {member['name']} ({member_email})...")

    next_meeting = get_next_meeting(member_email)
    message = format_next_meeting_message(next_meeting, member)
    return message


def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == 'query':
        identifier = sys.argv[2] if len(sys.argv) > 2 else None
        if identifier:
            message = query_next_meeting(identifier)
            print(message)
        else:
            print("Usage: reminders.py query <email|phone>")
            sys.exit(1)
    else:
        try:
            process_meeting_reminders()
        except KeyboardInterrupt:
            print("\n\nInterrupted by user")
            sys.exit(0)
        except Exception as e:
            print(f"\n❌ Fatal error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    main()
