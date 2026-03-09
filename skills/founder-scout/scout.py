#!/usr/bin/env python3
"""
Founder Scout v2 — Proactive discovery of Israeli tech founders starting new companies.

Multi-source discovery: LinkedIn browser automation, Brave news scanning, GitHub repo monitoring, HubSpot cross-ref.
Two-pass AI filtering: Haiku fast triage → Sonnet deep analysis.
Profile diff detection, priority scoring (1-100), rich WhatsApp alerts, HubSpot auto-create.

Actions:
  scan              Run daily discovery (LinkedIn rotation + Brave news)
  briefing          Compile and send weekly email + WhatsApp summary
  watchlist-update  Re-scan tracked people for profile changes
  news-scan         Brave-only news scan for Israeli startup activity
  github-scan       Scan GitHub for new repos by Israeli founders
  status            Print tracked people and signal counts
  add <name> [url]  Manually add a person to track
  dismiss <id>      Mark a person as dismissed

Usage:
  python3 scout.py scan
  python3 scout.py briefing
  python3 scout.py watchlist-update
  python3 scout.py news-scan
  python3 scout.py github-scan
  python3 scout.py status
  python3 scout.py add "Yossi Cohen" "https://linkedin.com/in/yossicohen"
  python3 scout.py dismiss 42
"""

import sys
import os
import re
import json
import time
import fcntl
import hashlib
import sqlite3
import subprocess
import requests
from datetime import datetime, timedelta

# Load shared config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from lib.config import config
from lib.claude import call_claude
from lib.whatsapp import send_whatsapp
from lib.email import send_email
from lib.brave import brave_search
from lib.hubspot import search_company, add_note as hubspot_add_note

# --- Configuration ---
LINKEDIN_PROFILE = "linkedin"
LINKEDIN_NAV_DELAY = 5
LINKEDIN_RATE_LIMIT = 5
MAX_LINKEDIN_LOOKUPS_PER_SCAN = 20
MAX_PROFILES_PER_QUERY = 5

# AI budget per scan
MAX_HAIKU_CALLS = 30
MAX_SONNET_CALLS = 10

# Data directory
_TOOLKIT_ROOT = os.environ.get('TOOLKIT_ROOT', os.path.join(os.path.dirname(__file__), '..', '..'))
_DATA_DIR = os.path.join(_TOOLKIT_ROOT, 'data')
os.makedirs(_DATA_DIR, mode=0o700, exist_ok=True)
DB_PATH = os.path.join(_DATA_DIR, 'founder-scout.db')
LOCK_PATH = os.path.join(_DATA_DIR, 'founder-scout.lock')

WHATSAPP_ACCOUNT = config.whatsapp_account

# Email recipients
_SCOUT_EMAILS = set(config._data.get('founder_scout', {}).get('recipient_emails', []))
SCOUT_RECIPIENTS = []
for m in config.team_members:
    if m['email'] in _SCOUT_EMAILS:
        SCOUT_RECIPIENTS.append({
            'name': m['name'],
            'first_name': m['name'].split()[0],
            'email': m['email'],
            'phone': m['phone'],
        })

# GroundUp team names (for mutual connection detection)
TEAM_NAMES = [m['name'] for m in config.team_members]
TEAM_DOMAIN = config.team_domain

# --- Search Queries (expanded) ---

SEARCH_QUERIES = {
    # Core signals
    'stealth_israel': {
        'query': 'Israel founder stealth',
        'priority': 'high',
    },
    'building_new': {
        'query': 'Israel CTO building something new',
        'priority': 'high',
    },
    'exited_founder': {
        'query': 'Israel founder exited startup',
        'priority': 'high',
    },
    'next_chapter': {
        'query': 'Israel CEO next chapter',
        'priority': 'high',
    },

    # Sector-specific (GroundUp focus areas)
    'cyber_founder': {
        'query': 'Israel cybersecurity founder stealth',
        'priority': 'high',
    },
    'ai_founder': {
        'query': 'Israel AI founder stealth',
        'priority': 'high',
    },
    'fintech_founder': {
        'query': 'Israel fintech founder new company',
        'priority': 'medium',
    },
    'devtools_founder': {
        'query': 'Israel developer tools founder startup',
        'priority': 'medium',
    },
    'climate_founder': {
        'query': 'Israel climate tech founder startup',
        'priority': 'medium',
    },

    # Alumni networks
    '8200_founder': {
        'query': '8200 alumni founder startup Israel',
        'priority': 'medium',
    },
    'talpiot_founder': {
        'query': 'Talpiot founder startup Israel',
        'priority': 'medium',
    },
    'technion_cs': {
        'query': 'Technion computer science founder stealth Israel',
        'priority': 'low',
    },

    # Job change signals
    'vp_left': {
        'query': 'Israel VP Engineering left building',
        'priority': 'medium',
    },
    'cofounder_exploring': {
        'query': 'Israel co-founder exploring new',
        'priority': 'medium',
    },
    'ex_bigtech': {
        'query': 'ex-Google ex-Meta founder Israel startup',
        'priority': 'low',
    },

    # Early stage
    'pre_seed': {
        'query': 'Israel pre-seed founder startup',
        'priority': 'low',
    },
    'day_one': {
        'query': 'Israel startup day one founder building',
        'priority': 'low',
    },
}

# Brave news queries (rotated)
NEWS_QUERIES = [
    'Israel startup founded 2026',
    'Israeli founder stealth mode startup',
    'Israel seed round 2026 startup',
    'Israeli entrepreneur new company launch',
    'Israel tech startup pre-seed funding',
    'Tel Aviv startup founded cybersecurity AI',
    'Israel startup exit founder new venture',
    '8200 Talpiot alumni new startup 2026',
]

# GitHub discovery — queries are rotated across scans to stay within rate limits
# Each scan picks a subset; over a week all get covered

GITHUB_REPO_QUERIES = [
    # --- Cybersecurity ---
    {'q': 'cybersecurity created:>{date} language:Python language:Go', 'topic': 'cybersecurity', 'priority': 'high'},
    {'q': 'security scanning SAST DAST created:>{date}', 'topic': 'cybersecurity', 'priority': 'high'},
    {'q': 'vulnerability scanner created:>{date}', 'topic': 'cybersecurity', 'priority': 'medium'},
    {'q': 'threat detection SIEM created:>{date}', 'topic': 'cybersecurity', 'priority': 'medium'},
    {'q': 'zero trust identity access created:>{date}', 'topic': 'cybersecurity', 'priority': 'medium'},
    {'q': 'API security gateway created:>{date}', 'topic': 'cybersecurity', 'priority': 'low'},
    {'q': 'cloud security posture CSPM created:>{date}', 'topic': 'cybersecurity', 'priority': 'low'},
    {'q': 'supply chain security SBOM created:>{date}', 'topic': 'cybersecurity', 'priority': 'low'},

    # --- AI / ML ---
    {'q': 'AI agent framework created:>{date} language:Python', 'topic': 'ai', 'priority': 'high'},
    {'q': 'LLM inference created:>{date}', 'topic': 'ai', 'priority': 'high'},
    {'q': 'RAG retrieval augmented generation created:>{date}', 'topic': 'ai', 'priority': 'high'},
    {'q': 'AI coding assistant created:>{date}', 'topic': 'ai', 'priority': 'medium'},
    {'q': 'vector database embedding created:>{date}', 'topic': 'ai', 'priority': 'medium'},
    {'q': 'LLM evaluation benchmark created:>{date}', 'topic': 'ai', 'priority': 'medium'},
    {'q': 'AI guardrails safety created:>{date}', 'topic': 'ai', 'priority': 'medium'},
    {'q': 'model fine-tuning training pipeline created:>{date}', 'topic': 'ai', 'priority': 'low'},
    {'q': 'computer vision real-time created:>{date}', 'topic': 'ai', 'priority': 'low'},
    {'q': 'speech synthesis TTS created:>{date}', 'topic': 'ai', 'priority': 'low'},

    # --- Developer Tools ---
    {'q': 'developer tools CLI created:>{date} language:TypeScript language:Rust', 'topic': 'devtools', 'priority': 'high'},
    {'q': 'observability monitoring created:>{date}', 'topic': 'devtools', 'priority': 'high'},
    {'q': 'CI CD pipeline automation created:>{date}', 'topic': 'devtools', 'priority': 'medium'},
    {'q': 'infrastructure as code Terraform Pulumi created:>{date}', 'topic': 'devtools', 'priority': 'medium'},
    {'q': 'API platform gateway management created:>{date}', 'topic': 'devtools', 'priority': 'medium'},
    {'q': 'database management migration created:>{date}', 'topic': 'devtools', 'priority': 'low'},
    {'q': 'testing framework automation created:>{date}', 'topic': 'devtools', 'priority': 'low'},
    {'q': 'feature flag management created:>{date}', 'topic': 'devtools', 'priority': 'low'},
    {'q': 'developer portal internal created:>{date}', 'topic': 'devtools', 'priority': 'low'},

    # --- Fintech ---
    {'q': 'fintech payments created:>{date} language:Python language:TypeScript', 'topic': 'fintech', 'priority': 'medium'},
    {'q': 'blockchain DeFi protocol created:>{date}', 'topic': 'fintech', 'priority': 'medium'},
    {'q': 'compliance KYC AML created:>{date}', 'topic': 'fintech', 'priority': 'low'},
    {'q': 'trading algorithm exchange created:>{date}', 'topic': 'fintech', 'priority': 'low'},

    # --- Data / Analytics ---
    {'q': 'data pipeline ETL created:>{date} language:Python language:Rust', 'topic': 'data', 'priority': 'medium'},
    {'q': 'data catalog governance created:>{date}', 'topic': 'data', 'priority': 'low'},
    {'q': 'real-time analytics streaming created:>{date}', 'topic': 'data', 'priority': 'low'},

    # --- Climate / Deep Tech ---
    {'q': 'climate tech sustainability energy created:>{date}', 'topic': 'climate', 'priority': 'low'},
    {'q': 'robotics autonomous created:>{date}', 'topic': 'deeptech', 'priority': 'low'},
    {'q': 'quantum computing created:>{date}', 'topic': 'deeptech', 'priority': 'low'},

    # --- Health Tech ---
    {'q': 'health tech medical imaging created:>{date}', 'topic': 'healthtech', 'priority': 'low'},
    {'q': 'digital health wearable created:>{date}', 'topic': 'healthtech', 'priority': 'low'},

    # --- Infrastructure / Cloud ---
    {'q': 'kubernetes operator controller created:>{date}', 'topic': 'infra', 'priority': 'medium'},
    {'q': 'serverless edge computing created:>{date}', 'topic': 'infra', 'priority': 'low'},
    {'q': 'service mesh proxy created:>{date}', 'topic': 'infra', 'priority': 'low'},
]

# Direct user search queries — find Israeli developers by profile
GITHUB_USER_QUERIES = [
    {'q': 'location:Israel followers:>50 repos:>5 created:>{date}', 'label': 'active Israeli devs'},
    {'q': 'location:"Tel Aviv" followers:>20 repos:>3', 'label': 'Tel Aviv devs'},
    {'q': 'location:Israel bio:founder', 'label': 'Israeli founders'},
    {'q': 'location:Israel bio:CEO', 'label': 'Israeli CEOs'},
    {'q': 'location:Israel bio:CTO', 'label': 'Israeli CTOs'},
    {'q': 'location:Israel bio:stealth', 'label': 'stealth mode'},
    {'q': 'location:Israel bio:"building"', 'label': 'building something'},
    {'q': 'location:Israel bio:"co-founder"', 'label': 'co-founders'},
    {'q': 'location:"Herzliya" bio:founder', 'label': 'Herzliya founders'},
    {'q': 'location:Haifa bio:founder', 'label': 'Haifa founders'},
]

# Max queries per scan (rotated to spread across runs)
GITHUB_REPO_QUERIES_PER_SCAN = 8
GITHUB_USER_QUERIES_PER_SCAN = 4

# GitHub rate limit: 10 search requests/min unauthenticated, 30/min with token
GITHUB_API_DELAY = 6  # seconds between requests (safe for unauthenticated)
GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN', '')  # optional, increases rate limit

PRIORITY_INTERVALS = {
    'high': 1,
    'medium': 2,
    'low': 4,
}

MAX_QUERIES_PER_SCAN = 6


# --- Database ---

class ScoutDatabase:
    """Track scouted founders, signals, and profile diffs."""

    def __init__(self, db_path):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS tracked_people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            linkedin_url TEXT UNIQUE,
            headline TEXT,
            source TEXT,
            signal_tier TEXT,
            priority_score INTEGER DEFAULT 0,
            last_signal TEXT,
            last_scanned TEXT,
            profile_hash TEXT,
            profile_snapshot TEXT,
            added_at TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            hubspot_contact_id TEXT,
            notes TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS signal_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            person_id INTEGER REFERENCES tracked_people(id),
            signal_type TEXT NOT NULL,
            signal_tier TEXT NOT NULL,
            description TEXT,
            source_url TEXT,
            detected_at TEXT NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS scan_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scan_type TEXT NOT NULL,
            started_at TEXT NOT NULL,
            completed_at TEXT,
            queries_run INTEGER DEFAULT 0,
            people_found INTEGER DEFAULT 0,
            signals_detected INTEGER DEFAULT 0,
            details TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS search_rotation (
            query_key TEXT PRIMARY KEY,
            last_run TEXT,
            run_count INTEGER DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS sent_profiles (
            linkedin_url TEXT PRIMARY KEY,
            name TEXT,
            sent_at TEXT NOT NULL
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS news_cache (
            url TEXT PRIMARY KEY,
            title TEXT,
            description TEXT,
            source_query TEXT,
            found_at TEXT NOT NULL,
            processed INTEGER DEFAULT 0
        )''')
        # Migrate: add columns if missing (for upgrades from v1)
        existing = {row[1] for row in c.execute("PRAGMA table_info(tracked_people)").fetchall()}
        if 'priority_score' not in existing:
            c.execute('ALTER TABLE tracked_people ADD COLUMN priority_score INTEGER DEFAULT 0')
        if 'profile_hash' not in existing:
            c.execute('ALTER TABLE tracked_people ADD COLUMN profile_hash TEXT')
        if 'profile_snapshot' not in existing:
            c.execute('ALTER TABLE tracked_people ADD COLUMN profile_snapshot TEXT')
        if 'hubspot_contact_id' not in existing:
            c.execute('ALTER TABLE tracked_people ADD COLUMN hubspot_contact_id TEXT')
        if 'headline' not in existing:
            c.execute('ALTER TABLE tracked_people ADD COLUMN headline TEXT')
        if 'github_url' not in existing:
            c.execute('ALTER TABLE tracked_people ADD COLUMN github_url TEXT')
        # Migrate scan_log
        scan_cols = {row[1] for row in c.execute("PRAGMA table_info(scan_log)").fetchall()}
        if 'details' not in scan_cols:
            c.execute('ALTER TABLE scan_log ADD COLUMN details TEXT')
        conn.commit()
        conn.close()

    # --- Profile tracking ---

    def is_profile_sent(self, linkedin_url):
        conn = sqlite3.connect(self.db_path)
        result = conn.execute(
            'SELECT 1 FROM sent_profiles WHERE linkedin_url = ?', (linkedin_url,)
        ).fetchone()
        conn.close()
        return result is not None

    def mark_profiles_sent(self, profiles):
        conn = sqlite3.connect(self.db_path)
        now = datetime.now().isoformat()
        for p in profiles:
            conn.execute(
                'INSERT OR IGNORE INTO sent_profiles (linkedin_url, name, sent_at) VALUES (?, ?, ?)',
                (p.get('linkedin_url', ''), p.get('name', ''), now)
            )
        conn.commit()
        conn.close()

    def add_person(self, name, linkedin_url=None, headline=None, source='linkedin_search',
                   priority_score=0, profile_hash=None, profile_snapshot=None):
        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                '''INSERT OR IGNORE INTO tracked_people
                   (name, linkedin_url, headline, source, priority_score, profile_hash,
                    profile_snapshot, added_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (name, linkedin_url, headline, source, priority_score, profile_hash,
                 profile_snapshot, datetime.now().isoformat())
            )
            conn.commit()
            row = conn.execute(
                'SELECT id FROM tracked_people WHERE name = ? AND (linkedin_url = ? OR (linkedin_url IS NULL AND ? IS NULL))',
                (name, linkedin_url, linkedin_url)
            ).fetchone()
            return row[0] if row else None
        finally:
            conn.close()

    def get_person_by_linkedin(self, url):
        conn = sqlite3.connect(self.db_path)
        row = conn.execute(
            'SELECT id, name, profile_hash, profile_snapshot, priority_score FROM tracked_people WHERE linkedin_url = ?',
            (url,)
        ).fetchone()
        conn.close()
        if row:
            return {'id': row[0], 'name': row[1], 'profile_hash': row[2],
                    'profile_snapshot': row[3], 'priority_score': row[4]}
        return None

    def update_person(self, person_id, **kwargs):
        conn = sqlite3.connect(self.db_path)
        sets = []
        vals = []
        for k, v in kwargs.items():
            sets.append(f"{k} = ?")
            vals.append(v)
        vals.append(person_id)
        conn.execute(f"UPDATE tracked_people SET {', '.join(sets)} WHERE id = ?", vals)
        conn.commit()
        conn.close()

    def get_active_people(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        results = conn.execute(
            '''SELECT * FROM tracked_people WHERE status = ?
               ORDER BY priority_score DESC, added_at DESC''',
            ('active',)
        ).fetchall()
        conn.close()
        return [dict(r) for r in results]

    def record_signal(self, person_id, signal_type, tier, description, source_url=None):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            '''INSERT INTO signal_history
               (person_id, signal_type, signal_tier, description, source_url, detected_at)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (person_id, signal_type, tier, description, source_url, datetime.now().isoformat())
        )
        conn.execute(
            'UPDATE tracked_people SET signal_tier = ?, last_signal = ?, last_scanned = ? WHERE id = ?',
            (tier, description, datetime.now().isoformat(), person_id)
        )
        conn.commit()
        conn.close()

    def get_signals_since(self, since_date):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        results = conn.execute(
            '''SELECT sh.*, tp.name, tp.linkedin_url, tp.priority_score, tp.headline
               FROM signal_history sh
               JOIN tracked_people tp ON sh.person_id = tp.id
               WHERE sh.detected_at >= ?
               ORDER BY tp.priority_score DESC, sh.detected_at DESC''',
            (since_date,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in results]

    def get_rotation_queue(self, max_queries):
        now = datetime.now()
        conn = sqlite3.connect(self.db_path)
        queue = []
        for key, info in SEARCH_QUERIES.items():
            row = conn.execute(
                'SELECT last_run FROM search_rotation WHERE query_key = ?', (key,)
            ).fetchone()
            interval_days = PRIORITY_INTERVALS[info['priority']]
            if row and row[0]:
                last_run = datetime.fromisoformat(row[0])
                if (now - last_run).total_seconds() < interval_days * 86400:
                    continue
            queue.append((key, info['priority']))
        conn.close()
        order = {'high': 0, 'medium': 1, 'low': 2}
        queue.sort(key=lambda x: order[x[1]])
        return [key for key, _ in queue[:max_queries]]

    def update_rotation(self, query_key):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            '''INSERT OR REPLACE INTO search_rotation (query_key, last_run, run_count)
               VALUES (?, ?, COALESCE((SELECT run_count FROM search_rotation WHERE query_key = ?), 0) + 1)''',
            (query_key, datetime.now().isoformat(), query_key)
        )
        conn.commit()
        conn.close()

    def log_scan(self, scan_type, queries_run=0, people_found=0, signals_detected=0, details=None):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            '''INSERT INTO scan_log
               (scan_type, started_at, completed_at, queries_run, people_found, signals_detected, details)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (scan_type, datetime.now().isoformat(), datetime.now().isoformat(),
             queries_run, people_found, signals_detected, details)
        )
        conn.commit()
        conn.close()

    def dismiss_person(self, person_id):
        conn = sqlite3.connect(self.db_path)
        conn.execute('UPDATE tracked_people SET status = ? WHERE id = ?', ('dismissed', person_id))
        conn.commit()
        conn.close()

    # --- News cache ---

    def is_news_seen(self, url):
        conn = sqlite3.connect(self.db_path)
        result = conn.execute('SELECT 1 FROM news_cache WHERE url = ?', (url,)).fetchone()
        conn.close()
        return result is not None

    def add_news(self, url, title, description, source_query):
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            'INSERT OR IGNORE INTO news_cache (url, title, description, source_query, found_at) VALUES (?, ?, ?, ?, ?)',
            (url, title, description, source_query, datetime.now().isoformat())
        )
        conn.commit()
        conn.close()

    def get_stats(self):
        conn = sqlite3.connect(self.db_path)
        active = conn.execute('SELECT COUNT(*) FROM tracked_people WHERE status = ?', ('active',)).fetchone()[0]
        high = conn.execute('SELECT COUNT(*) FROM tracked_people WHERE status = ? AND signal_tier = ?', ('active', 'high')).fetchone()[0]
        medium = conn.execute('SELECT COUNT(*) FROM tracked_people WHERE status = ? AND signal_tier = ?', ('active', 'medium')).fetchone()[0]
        low = conn.execute('SELECT COUNT(*) FROM tracked_people WHERE status = ? AND signal_tier = ?', ('active', 'low')).fetchone()[0]
        total_signals = conn.execute('SELECT COUNT(*) FROM signal_history').fetchone()[0]
        total_scans = conn.execute('SELECT COUNT(*) FROM scan_log').fetchone()[0]
        avg_score = conn.execute('SELECT AVG(priority_score) FROM tracked_people WHERE status = ?', ('active',)).fetchone()[0] or 0
        conn.close()
        return {
            'active': active, 'high': high, 'medium': medium, 'low': low,
            'total_signals': total_signals, 'total_scans': total_scans,
            'avg_score': round(avg_score),
        }


# --- LinkedIn Browser (evaluate-based) ---

def _run_browser(cmd, timeout=30):
    """Run an openclaw browser command and return stdout."""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            return None
        out = result.stdout.strip()
        # Strip doctor warnings banner before JSON
        if out and '--json' in cmd:
            idx = out.find('{')
            if idx > 0:
                out = out[idx:]
        return out
    except Exception as e:
        print(f"    Browser error: {e}", file=sys.stderr)
        return None


def _linkedin_search_urls(encoded_query):
    """Navigate to LinkedIn search and extract profile URLs."""
    url = f"https://www.linkedin.com/search/results/people/?keywords={encoded_query}"
    _run_browser([
        'openclaw', 'browser', 'navigate',
        '--browser-profile', LINKEDIN_PROFILE, url
    ], timeout=30)
    time.sleep(6)

    # Extract profile URLs
    js_urls = 'Array.from(document.querySelectorAll("a")).filter(a=>a.href.includes("/in/")).slice(0,15).map(a=>a.href)'
    result = _run_browser([
        'openclaw', 'browser', 'evaluate',
        '--browser-profile', LINKEDIN_PROFILE,
        '--fn', js_urls, '--json'
    ], timeout=30)

    if not result:
        return []
    try:
        data = json.loads(result)
        urls = data.get('result', [])
        # Deduplicate and clean
        seen = set()
        clean = []
        for u in urls:
            base = re.sub(r'\?.*', '', u)
            if base not in seen and '/in/' in base:
                seen.add(base)
                clean.append(base)
        return clean
    except Exception:
        return []


def _parse_search_text_with_urls(text, urls):
    """Parse LinkedIn search results text + URLs into structured profiles.

    LinkedIn search text follows this pattern per result:
        Name
        View Name's profile
        ...degree connection
        Headline
        Location
    """
    profiles = []
    if not text or not urls:
        return profiles

    lines = [l.strip() for l in text.split('\n') if l.strip()]
    url_idx = 0

    i = 0
    while i < len(lines):
        line = lines[i]
        # Detect "View X's profile" which comes right after a name
        if line.startswith('View ') and ('s profile' in line[-12:]):
            # Name is the previous non-empty line
            name = lines[i - 1] if i > 0 else ''
            # Skip known nav/junk names
            if name in ('', 'People', 'Search', 'LinkedIn') or len(name) > 60:
                i += 1
                continue

            # Look ahead for headline (skip degree connection lines, mutual lines)
            headline = ''
            for j in range(i + 1, min(i + 8, len(lines))):
                candidate = lines[j]
                # Skip navigation/structural lines
                if any(skip in candidate for skip in [
                    'degree connection', 'Connect', 'Follow', 'Message',
                    'mutual connection', 'followers', 'View ', 'Provides '
                ]):
                    continue
                # Skip if it's the next person's name (followed by "View X's profile")
                if j + 1 < len(lines) and lines[j + 1].startswith('View ') and lines[j + 1].endswith("'s profile"):
                    break
                # This is likely the headline
                if len(candidate) > 5 and candidate[0].isupper():
                    headline = candidate
                    break

            # Assign URL
            url = urls[url_idx] if url_idx < len(urls) else ''
            url_idx += 1

            if name and url:
                profiles.append({'name': name, 'headline': headline, 'url': url})

        i += 1

    return profiles


def linkedin_search(query):
    """Search LinkedIn and return list of {name, headline, url} dicts."""
    import urllib.parse
    encoded = urllib.parse.quote(query)

    url = f"https://www.linkedin.com/search/results/people/?keywords={encoded}"
    _run_browser([
        'openclaw', 'browser', 'navigate',
        '--browser-profile', LINKEDIN_PROFILE, url
    ], timeout=30)
    time.sleep(6)

    # Get both URLs and page text in parallel
    js_urls = 'Array.from(document.querySelectorAll("a")).filter(a=>a.href.includes("/in/")).slice(0,15).map(a=>a.href)'
    url_result = _run_browser([
        'openclaw', 'browser', 'evaluate',
        '--browser-profile', LINKEDIN_PROFILE,
        '--fn', js_urls, '--json'
    ], timeout=30)

    urls = []
    if url_result:
        try:
            data = json.loads(url_result)
            raw_urls = data.get('result', [])
            seen = set()
            for u in raw_urls:
                base = re.sub(r'\?.*', '', u)
                # Skip encoded profile IDs (ACo...) — keep only human-readable slugs
                slug = base.split('/in/')[-1] if '/in/' in base else ''
                if slug.startswith('ACo'):
                    continue
                if base not in seen and '/in/' in base:
                    seen.add(base)
                    urls.append(base)
        except Exception:
            pass

    if not urls:
        return []

    # Get page text for name/headline extraction
    js_text = '(document.querySelector("main")?.innerText || "").substring(0,3000)'
    text_result = _run_browser([
        'openclaw', 'browser', 'evaluate',
        '--browser-profile', LINKEDIN_PROFILE,
        '--fn', js_text, '--json'
    ], timeout=30)

    page_text = ''
    if text_result:
        try:
            data = json.loads(text_result)
            page_text = data.get('result', '')
        except Exception:
            pass

    if page_text:
        profiles = _parse_search_text_with_urls(page_text, urls)
        if profiles:
            return profiles

    # Fallback: URLs only
    return [{'name': '', 'headline': '', 'url': u} for u in urls]


def linkedin_profile_text(url):
    """Navigate to a LinkedIn profile and extract rich text content."""
    _run_browser([
        'openclaw', 'browser', 'navigate',
        '--browser-profile', LINKEDIN_PROFILE, url
    ], timeout=30)
    time.sleep(4)

    js_fn = '(document.querySelector("main")?.innerText || document.querySelector(".pv-top-card")?.innerText || "").substring(0,4000)'
    result = _run_browser([
        'openclaw', 'browser', 'evaluate',
        '--browser-profile', LINKEDIN_PROFILE,
        '--fn', js_fn, '--json'
    ], timeout=30)

    if not result:
        return None
    try:
        data = json.loads(result)
        text = data.get('result', '')
        return text if text and len(text) > 50 else None
    except Exception:
        return None


def linkedin_browser_available():
    """Check if the LinkedIn browser session is available."""
    try:
        result = subprocess.run(
            ['openclaw', 'browser', 'evaluate',
             '--browser-profile', LINKEDIN_PROFILE,
             '--fn', 'document.title', '--json'],
            capture_output=True, text=True, timeout=15
        )
        return result.returncode == 0
    except Exception:
        return False


# --- Priority Scoring ---

def compute_priority_score(profile_text, headline, analysis_data=None):
    """Compute a 1-100 priority score based on weighted signals."""
    score = 0
    text = ((profile_text or '') + ' ' + (headline or '')).lower()

    # Role signals (+25-30)
    if any(w in text for w in ['stealth', 'stealth mode']):
        score += 30
    if any(w in text for w in ['building something', 'building the future', 'building a new']):
        score += 25
    if any(w in text for w in ['next chapter', "what's next", 'exploring next']):
        score += 20
    if any(w in text for w in ['co-founder', 'cofounder', 'co founder']):
        score += 15
    if any(w in text for w in ['founder', 'ceo', 'cto']):
        score += 10

    # Exit/experience signals (+15-20)
    if any(w in text for w in ['exited', 'acquired', 'ipo', 'exit']):
        score += 20
    if any(w in text for w in ['serial entrepreneur', 'second-time founder', '2x founder']):
        score += 15
    if any(w in text for w in ['formerly', 'ex-', 'former ']):
        score += 10

    # Elite background (+10)
    if any(w in text for w in ['8200', 'talpiot', 'unit 81']):
        score += 10
    if any(w in text for w in ['technion', 'weizmann', 'hebrew university', 'tel aviv university']):
        score += 5

    # Sector relevance — GroundUp focus areas (+10)
    if any(w in text for w in ['cybersecurity', 'cyber security', 'infosec', 'appsec']):
        score += 10
    if any(w in text for w in ['artificial intelligence', ' ai ', 'machine learning', 'deep learning', 'genai', 'llm']):
        score += 10
    if any(w in text for w in ['fintech', 'financial technology', 'payments', 'banking']):
        score += 8
    if any(w in text for w in ['devtools', 'developer tools', 'devops', 'platform engineering']):
        score += 8
    if any(w in text for w in ['climate', 'cleantech', 'sustainability']):
        score += 5

    # Freshness signals (+10)
    if any(w in text for w in ['2026', '2025', 'just started', 'day one', 'day 1', 'pre-seed', 'preseed']):
        score += 10

    # Mutual GroundUp connection (+10)
    for tn in TEAM_NAMES:
        if tn.lower() in text:
            score += 10
            break

    # GitHub activity signal (+10)
    if any(w in text for w in ['github.com', 'open source', 'new repo', 'github']):
        score += 10

    # AI analysis boost
    if analysis_data and analysis_data.get('relevant'):
        score += 15

    return min(score, 100)


# --- AI Analysis (Two-Pass) ---

def haiku_triage(profiles):
    """Pass 1: Fast Claude Haiku triage on headlines. Returns list of likely-relevant profiles."""
    if not profiles:
        return []

    # Batch up to 15 profiles per call for efficiency
    batches = [profiles[i:i+15] for i in range(0, len(profiles), 15)]
    relevant = []

    for batch in batches:
        entries = []
        for i, p in enumerate(batch):
            name = p.get('name', 'Unknown')
            headline = p.get('headline', 'No headline')
            entries.append(f"{i+1}. {name} — {headline}")

        prompt = f"""You are a VC scout for a first-check Israeli fund.
Review these LinkedIn profiles. For each, answer YES or NO: is this person likely starting a NEW company?

{chr(10).join(entries)}

YES means: stealth startup, building something new, recently left a role to start something, pre-seed stage, day one.
NO means: established company founder, investor/VC, advisor, consultant, corporate employee, academic.

Return ONLY a JSON array of the numbers that are YES. Example: [1, 3, 7]
If none are relevant, return: []"""

        try:
            response = call_claude(prompt, max_tokens=200, model="claude-haiku-4-5-20251001")
            if response:
                match = re.search(r'\[[\d,\s]*\]', response)
                if match:
                    indices = json.loads(match.group())
                    for idx in indices:
                        if 1 <= idx <= len(batch):
                            relevant.append(batch[idx - 1])
        except Exception as e:
            print(f"    Haiku triage error: {e}", file=sys.stderr)

    return relevant


def sonnet_deep_analysis(name, profile_text, linkedin_url):
    """Pass 2: Deep Claude Sonnet analysis on full profile.

    Returns dict with: relevant (bool), summary, current_title, sector, signals.
    """
    system = (
        "You are a VC scout for GroundUp Ventures, a first-check Israeli fund. "
        "Determine if this person is CURRENTLY starting a new company (last 6 months) "
        "or clearly about to. Be strict: only mark as relevant if there are concrete signals."
    )

    prompt = f"""Analyze this LinkedIn profile for new-startup signals.

NAME: {name}
URL: {linkedin_url}

PROFILE:
{profile_text[:4000]}

Return ONLY valid JSON:
{{
  "relevant": true/false,
  "confidence": "high" | "medium" | "low",
  "summary": "1-2 sentence explanation",
  "current_title": "their current role",
  "company": "current company name or null",
  "sector": "cybersecurity|AI|fintech|devtools|health|climate|other",
  "signals": ["stealth_mode", "role_change", "building_new", etc],
  "red_flags": ["any concerns"],
  "recommended_action": "reach_out|monitor|skip"
}}

RELEVANT (true): founded/co-founded something new in last ~6 months, stealth startup, building something unnamed, explicitly starting something new.
NOT RELEVANT (false): established company (>1yr), investor, VC, advisor, consultant, corporate employee, serial entrepreneur just promoting past exits."""

    try:
        response = call_claude(prompt, system_prompt=system, max_tokens=500, model="claude-sonnet-4-20250514")
        if response:
            match = re.search(r'\{.*\}', response, re.DOTALL)
            if match:
                return json.loads(match.group())
    except Exception as e:
        print(f"    Sonnet analysis error: {e}", file=sys.stderr)
    return None


# --- Brave News Scanner ---

def scan_news():
    """Scan Brave Search for recent Israeli startup news. Returns list of news items."""
    # Rotate through queries (pick 3 per scan)
    now = datetime.now()
    rotation_idx = now.timetuple().tm_yday % len(NEWS_QUERIES)
    queries = []
    for i in range(3):
        idx = (rotation_idx + i) % len(NEWS_QUERIES)
        queries.append(NEWS_QUERIES[idx])

    all_results = []
    for q in queries:
        results = brave_search(q, count=8)
        for r in results:
            r['source_query'] = q
        all_results.extend(results)
        time.sleep(1)

    # Deduplicate
    seen = set()
    unique = []
    for r in all_results:
        if r['url'] not in seen:
            seen.add(r['url'])
            unique.append(r)

    return unique


def extract_founders_from_news(news_items, db):
    """Use Haiku to extract founder names and companies from news articles."""
    new_items = [n for n in news_items if not db.is_news_seen(n['url'])]
    if not new_items:
        return []

    # Cache all news items
    for n in new_items:
        db.add_news(n['url'], n.get('title', ''), n.get('description', ''), n.get('source_query', ''))

    # Batch news for Claude extraction
    entries = []
    for i, n in enumerate(new_items[:20]):
        entries.append(f"{i+1}. {n.get('title', '')} — {n.get('description', '')[:150]}")

    prompt = f"""Extract founder/CEO names and their companies from these startup news items.
Only include people who are FOUNDING or LEADING a NEW startup (not investors, not established companies).

{chr(10).join(entries)}

Return ONLY a JSON array:
[{{"name": "Full Name", "company": "Company Name", "context": "brief context"}}]
If no founders found, return: []"""

    try:
        response = call_claude(prompt, max_tokens=500, model="claude-haiku-4-5-20251001")
        if response:
            match = re.search(r'\[.*\]', response, re.DOTALL)
            if match:
                return json.loads(match.group())
    except Exception as e:
        print(f"    News extraction error: {e}", file=sys.stderr)
    return []


# --- GitHub Discovery ---

def _github_api(endpoint, params=None):
    """Call GitHub API with rate limit awareness. Returns parsed JSON or None."""
    headers = {'Accept': 'application/vnd.github+json'}
    if GITHUB_TOKEN:
        headers['Authorization'] = f'Bearer {GITHUB_TOKEN}'
    try:
        resp = requests.get(
            f'https://api.github.com{endpoint}',
            headers=headers, params=params, timeout=15
        )
        # Respect rate limits proactively
        remaining = int(resp.headers.get('X-RateLimit-Remaining', 99))
        if remaining <= 2:
            reset_at = int(resp.headers.get('X-RateLimit-Reset', 0))
            wait = max(reset_at - int(time.time()), 10)
            print(f"    GitHub rate limit low ({remaining}), waiting {wait}s...", flush=True)
            time.sleep(min(wait, 120))
        if resp.status_code == 200:
            return resp.json()
        if resp.status_code in (403, 429):
            reset_at = int(resp.headers.get('X-RateLimit-Reset', 0))
            wait = max(reset_at - int(time.time()), 60)
            print(f"    GitHub rate limited, waiting {wait}s...", flush=True)
            time.sleep(min(wait, 120))
        return None
    except Exception as e:
        print(f"    GitHub API error: {e}", file=sys.stderr)
        return None


def github_search_repos(query, sort='stars', per_page=20):
    """Search GitHub repositories. Returns list of repo dicts."""
    data = _github_api('/search/repositories', {
        'q': query, 'sort': sort, 'order': 'desc', 'per_page': per_page
    })
    if data and 'items' in data:
        return data['items']
    return []


def github_search_users(query, sort='joined', per_page=20):
    """Search GitHub users. Returns list of user dicts."""
    data = _github_api('/search/users', {
        'q': query, 'sort': sort, 'order': 'desc', 'per_page': per_page
    })
    if data and 'items' in data:
        return data['items']
    return []


def github_user_profile(username):
    """Get GitHub user profile. Returns dict with name, bio, location, company, etc."""
    return _github_api(f'/users/{username}')


def github_user_repos(username, sort='created', per_page=10):
    """Get recent repos for a user."""
    data = _github_api(f'/users/{username}/repos', {
        'sort': sort, 'direction': 'desc', 'per_page': per_page, 'type': 'owner'
    })
    return data if isinstance(data, list) else []


def github_org_repos(org, sort='created', per_page=10):
    """Get recent repos for an org."""
    data = _github_api(f'/orgs/{org}/repos', {
        'sort': sort, 'direction': 'desc', 'per_page': per_page, 'type': 'sources'
    })
    return data if isinstance(data, list) else []


def _is_israeli_github_user(profile):
    """Check if a GitHub user profile indicates Israeli location."""
    if not profile:
        return False
    location = (profile.get('location') or '').lower()
    bio = (profile.get('bio') or '').lower()
    company = (profile.get('company') or '').lower()
    text = f"{location} {bio} {company}"
    return any(w in text for w in ['israel', 'tel aviv', 'tel-aviv', 'jerusalem',
                                    'haifa', 'herzliya', 'raanana', 'ra\'anana',
                                    'beer sheva', 'beersheva', 'netanya', 'rehovot',
                                    'petah tikva', 'rishon lezion', 'kfar saba'])


MAX_GITHUB_USER_CHECKS = 30  # Max user profiles to check per scan

def _extract_github_founders(repos, db):
    """From a list of repos, find Israeli founders creating new projects.
    Returns list of dicts: {name, github_url, github_username, repo_url, repo_name, description, stars, topic}"""
    candidates = []
    checked_users = set()
    checks = 0

    # Sort by stars descending to prioritize popular repos
    repos = sorted(repos, key=lambda r: r.get('stargazers_count', 0), reverse=True)

    for repo in repos:
        if checks >= MAX_GITHUB_USER_CHECKS:
            break

        owner = repo.get('owner', {})
        username = owner.get('login', '')
        if not username or username in checked_users:
            continue
        checked_users.add(username)

        # Skip orgs early (from search result metadata, no API call needed)
        if owner.get('type') == 'Organization':
            continue

        checks += 1
        time.sleep(4)  # stay within unauthenticated rate limit (60 req/hr for core API)
        profile = github_user_profile(username)
        if not profile:
            continue

        # Must be Israeli
        if not _is_israeli_github_user(profile):
            continue

        name = profile.get('name') or username
        bio = profile.get('bio') or ''
        github_url = profile.get('html_url', f'https://github.com/{username}')

        candidates.append({
            'name': name,
            'github_url': github_url,
            'github_username': username,
            'repo_url': repo.get('html_url', ''),
            'repo_name': repo.get('full_name', ''),
            'description': repo.get('description') or '',
            'stars': repo.get('stargazers_count', 0),
            'bio': bio,
            'topic': repo.get('_scout_topic', ''),
        })
        print(f"    Israeli founder: {name} — {repo.get('full_name', '')} ({repo.get('stargazers_count', 0)}★)", flush=True)

    return candidates


def _github_triage_and_add(candidates, db):
    """AI triage candidates and add confirmed founders to DB. Returns (added, signals) counts."""
    if not candidates:
        return 0, 0

    added = 0
    signals = 0

    # Process in batches of 20 (Haiku context)
    for batch_start in range(0, len(candidates), 20):
        batch = candidates[batch_start:batch_start + 20]
        entries = []
        for i, c in enumerate(batch):
            recent_repos = c.get('recent_repos', '')
            entries.append(
                f"{i+1}. {c['name']} ({c.get('github_username', '?')}) — Bio: {c.get('bio', '')[:100]} — "
                f"Repo: {c.get('repo_name', '')} ({c.get('stars', 0)}★) — {c.get('description', '')[:80]}"
                f"{f' — Also: {recent_repos}' if recent_repos else ''}"
            )

        prompt = f"""These are GitHub users from Israel who recently created new repositories.
Identify which ones are likely FOUNDERS building a new STARTUP product (not students, not open-source hobbyists, not employees at big companies contributing to work repos).

Signs of a founder:
- Bio mentions founder/CEO/CTO/building/stealth/ex-{'{company}'}
- Repo looks like a product (not a tutorial, homework, or fork)
- New org + new repo + relevant domain (cybersecurity, AI, devtools, fintech, etc.)
- Multiple recent repos in same domain = building a company

{chr(10).join(entries)}

Return ONLY a JSON array of the numbers that are likely founders:
[1, 3, 7]
If none are founders, return: []"""

        try:
            response = call_claude(prompt, max_tokens=200, model="claude-haiku-4-5-20251001")
            if response:
                match = re.search(r'\[[\d\s,]*\]', response)
                if match:
                    selected = json.loads(match.group())
                    for idx in selected:
                        if 1 <= idx <= len(batch):
                            c = batch[idx - 1]
                            person_id = db.add_person(
                                c['name'],
                                source=f"github:{c.get('topic', 'discovery')}",
                                headline=c.get('bio', '')[:200] or f"Building {c.get('repo_name', '')}",
                            )
                            if person_id:
                                db.update_person(person_id, github_url=c['github_url'])
                                desc = f"New GitHub repo: {c.get('repo_name', '')} ({c.get('stars', 0)}★) — {c.get('description', '')[:120]}"
                                db.record_signal(person_id, 'new_github_repo', 'medium', desc, c.get('repo_url', ''))
                                signals += 1
                                added += 1
                                score_text = f"{c.get('bio', '')} {c.get('description', '')} {c.get('topic', '')}"
                                score = compute_priority_score(score_text, c.get('bio', ''))
                                score += 10  # GitHub activity bonus
                                db.update_person(person_id, priority_score=min(score, 100))
                                print(f"    Added: {c['name']} — {c.get('repo_name', '')} ({c.get('stars', 0)}★) [score={min(score, 100)}]", flush=True)
        except Exception as e:
            print(f"    GitHub triage error: {e}", file=sys.stderr)

    return added, signals


def _get_github_rotation_queue(db, query_list, key_prefix, max_queries):
    """Pick next queries to run based on rotation (least recently run first)."""
    conn = sqlite3.connect(db.db_path)
    queue = []
    for i, gq in enumerate(query_list):
        key = f"{key_prefix}_{i}"
        row = conn.execute('SELECT last_run FROM search_rotation WHERE query_key = ?', (key,)).fetchone()
        priority = gq.get('priority', 'medium')
        interval = PRIORITY_INTERVALS.get(priority, 2)
        if row and row[0]:
            last_run = datetime.fromisoformat(row[0])
            if (datetime.now() - last_run).total_seconds() < interval * 86400:
                continue
        order = {'high': 0, 'medium': 1, 'low': 2}
        queue.append((i, order.get(priority, 1)))
    conn.close()
    queue.sort(key=lambda x: x[1])
    return [idx for idx, _ in queue[:max_queries]]


def run_github_scan():
    """Scan GitHub for new repos and Israeli founders across multiple discovery methods."""
    print(f"[{datetime.now()}] Starting Founder Scout GitHub scan...", flush=True)

    db = ScoutDatabase(DB_PATH)
    cutoff_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
    all_candidates = []
    queries_run = 0

    # ========== Part 1: Repo search (sector-specific) ==========
    repo_indices = _get_github_rotation_queue(db, GITHUB_REPO_QUERIES, 'gh_repo', GITHUB_REPO_QUERIES_PER_SCAN)
    print(f"  [Repos] Running {len(repo_indices)}/{len(GITHUB_REPO_QUERIES)} repo queries...", flush=True)

    all_repos = []
    for idx in repo_indices:
        gq = GITHUB_REPO_QUERIES[idx]
        query = gq['q'].replace('{date}', cutoff_date)
        print(f"    Searching: {query[:65]}...", flush=True)
        repos = github_search_repos(query, sort='stars', per_page=15)
        for r in repos:
            r['_scout_topic'] = gq['topic']
        all_repos.extend(repos)
        queries_run += 1
        db.update_rotation(f'gh_repo_{idx}')
        time.sleep(8)

    # Deduplicate
    seen_ids = set()
    unique_repos = []
    for r in all_repos:
        rid = r.get('id')
        if rid and rid not in seen_ids:
            seen_ids.add(rid)
            unique_repos.append(r)

    print(f"    Found {len(unique_repos)} unique repos", flush=True)
    repo_candidates = _extract_github_founders(unique_repos, db)
    all_candidates.extend(repo_candidates)
    print(f"    → {len(repo_candidates)} Israeli candidates from repos", flush=True)

    # ========== Part 2: Direct user search (find Israeli founders by profile) ==========
    user_indices = _get_github_rotation_queue(db, GITHUB_USER_QUERIES, 'gh_user', GITHUB_USER_QUERIES_PER_SCAN)
    print(f"  [Users] Running {len(user_indices)}/{len(GITHUB_USER_QUERIES)} user queries...", flush=True)

    user_candidates_raw = []
    seen_usernames = {c['github_username'] for c in all_candidates}

    for idx in user_indices:
        uq = GITHUB_USER_QUERIES[idx]
        query = uq['q'].replace('{date}', cutoff_date)
        print(f"    Searching users: {uq['label']}...", flush=True)
        users = github_search_users(query, per_page=15)
        queries_run += 1
        db.update_rotation(f'gh_user_{idx}')
        time.sleep(8)

        for user in users:
            username = user.get('login', '')
            if not username or username in seen_usernames:
                continue
            seen_usernames.add(username)
            if user.get('type') == 'Organization':
                continue
            user_candidates_raw.append(user)

    print(f"    Found {len(user_candidates_raw)} unique users to check", flush=True)

    # Enrich user candidates — get profile + recent repos
    for user in user_candidates_raw[:MAX_GITHUB_USER_CHECKS]:
        username = user.get('login', '')
        time.sleep(4)
        profile = github_user_profile(username)
        if not profile:
            continue

        # Already confirmed Israeli from search query, but verify
        if not _is_israeli_github_user(profile):
            continue

        # Get their recent repos to find what they're building
        time.sleep(3)
        repos = github_user_repos(username, sort='created', per_page=5)
        recent_non_fork = [r for r in repos if not r.get('fork') and r.get('created_at', '') >= cutoff_date]

        if not recent_non_fork:
            continue  # No new repos = not interesting right now

        best_repo = max(recent_non_fork, key=lambda r: r.get('stargazers_count', 0))
        other_repos = ', '.join(r.get('name', '') for r in recent_non_fork if r != best_repo)

        name = profile.get('name') or username
        bio = profile.get('bio') or ''
        github_url = profile.get('html_url', f'https://github.com/{username}')

        all_candidates.append({
            'name': name,
            'github_url': github_url,
            'github_username': username,
            'repo_url': best_repo.get('html_url', ''),
            'repo_name': best_repo.get('full_name', ''),
            'description': best_repo.get('description') or '',
            'stars': best_repo.get('stargazers_count', 0),
            'bio': bio,
            'topic': 'user_search',
            'recent_repos': other_repos,
        })
        print(f"    Israeli dev: {name} — {best_repo.get('full_name', '')} ({best_repo.get('stargazers_count', 0)}★)", flush=True)

    print(f"  Total candidates from all sources: {len(all_candidates)}", flush=True)

    # ========== Part 3: AI triage all candidates ==========
    added, signals = _github_triage_and_add(all_candidates, db)

    # ========== Part 4: Monitor tracked founders for new repos ==========
    people = db.get_active_people()
    github_people = [p for p in people if p.get('github_url')]
    print(f"  [Monitor] Checking {len(github_people)} tracked founders for new repos...", flush=True)

    for person in github_people:
        github_url = person['github_url']
        username = github_url.rstrip('/').split('/')[-1]
        if not username:
            continue

        time.sleep(GITHUB_API_DELAY)
        repos = github_user_repos(username, sort='created', per_page=5)

        for repo in repos:
            created = repo.get('created_at', '')
            if created < cutoff_date:
                continue
            if repo.get('fork'):
                continue

            desc = f"New repo: {repo.get('full_name', '')} — {repo.get('description', '')[:120]}"
            db.record_signal(person['id'], 'new_github_repo', 'medium', desc, repo.get('html_url', ''))
            signals += 1
            new_score = min((person.get('priority_score', 0) or 0) + 5, 100)
            db.update_person(person['id'], priority_score=new_score)
            print(f"    {person['name']}: new repo {repo.get('name', '')} (+5 score -> {new_score})", flush=True)

    db.log_scan('github_scan', queries_run=queries_run, people_found=added, signals_detected=signals)
    print(f"  GitHub scan complete: {queries_run} queries, {len(all_candidates)} candidates, "
          f"{added} new founders, {signals} signals", flush=True)


# --- Profile Diff Detection ---

def detect_profile_changes(person, new_profile_text):
    """Compare current profile against stored snapshot.

    Returns list of detected changes, or empty list.
    """
    if not new_profile_text:
        return []

    new_hash = hashlib.md5(new_profile_text.encode()).hexdigest()
    old_hash = person.get('profile_hash')

    if old_hash == new_hash:
        return []

    if not person.get('profile_snapshot'):
        return [{'type': 'first_scan', 'detail': 'Initial profile capture'}]

    # Compare key fields
    old_text = person['profile_snapshot']
    changes = []

    # Check headline change
    old_first_line = old_text.split('\n')[0].strip() if old_text else ''
    new_first_line = new_profile_text.split('\n')[0].strip()
    if old_first_line and new_first_line and old_first_line != new_first_line:
        changes.append({
            'type': 'headline_change',
            'detail': f"Changed from '{old_first_line[:60]}' to '{new_first_line[:60]}'"
        })

    # Check for "stealth" or "building" appearing in new but not old
    stealth_words = ['stealth', 'building something', 'co-founder', 'founded', 'launching']
    for word in stealth_words:
        if word in new_profile_text.lower() and word not in old_text.lower():
            changes.append({
                'type': 'new_signal_word',
                'detail': f"New keyword detected: '{word}'"
            })

    # Check company change
    old_companies = set(re.findall(r'(?:at|@)\s+([A-Z][a-zA-Z\s]+?)(?:\n|,|\.)', old_text))
    new_companies = set(re.findall(r'(?:at|@)\s+([A-Z][a-zA-Z\s]+?)(?:\n|,|\.)', new_profile_text))
    added = new_companies - old_companies
    if added:
        changes.append({
            'type': 'company_change',
            'detail': f"New company/role: {', '.join(list(added)[:3])}"
        })

    if not changes and old_hash != new_hash:
        changes.append({'type': 'minor_update', 'detail': 'Profile text updated'})

    return changes


# --- HubSpot Integration ---

def hubspot_create_contact(name, linkedin_url, summary, sector, score):
    """Create a HubSpot contact for a high-signal founder."""
    parts = name.split()
    if len(parts) < 2:
        return None

    try:
        desc = f"Founder Scout lead (score: {score})\n{summary}\nSector: {sector}\nLinkedIn: {linkedin_url}"

        response = requests.post(
            f"{config.hubspot_api_gateway}/crm/v3/objects/contacts",
            headers={
                "Authorization": f"Bearer {config.maton_api_key}",
                "Content-Type": "application/json",
            },
            json={
                "properties": {
                    "firstname": parts[0],
                    "lastname": ' '.join(parts[1:]),
                    "jobtitle": summary[:100] if summary else "Founder (Scout Lead)",
                    "hs_lead_status": "NEW",
                    "lifecyclestage": "lead",
                }
            },
            timeout=10,
        )
        if response.status_code in [200, 201]:
            contact_id = response.json().get('id')
            print(f"    Created HubSpot contact: {name} (ID: {contact_id})")
            hubspot_add_note(contact_id, desc, object_type="contacts")
            return contact_id
        elif response.status_code == 409:
            print(f"    HubSpot contact already exists: {name}")
            return None
        else:
            print(f"    HubSpot create failed ({response.status_code})", file=sys.stderr)
            return None
    except Exception as e:
        print(f"    HubSpot error: {e}", file=sys.stderr)
        return None


# --- Rich Alerts ---

def format_rich_whatsapp_alert(profiles):
    """Format rich WhatsApp alert for new high-signal founders."""
    if not profiles:
        return None

    lines = [f"🔍 FOUNDER SCOUT — {len(profiles)} new lead{'s' if len(profiles) != 1 else ''}", ""]

    for i, p in enumerate(profiles, 1):
        score = p.get('priority_score', 0)
        score_bar = '🟢' if score >= 70 else '🟡' if score >= 40 else '🔴'

        lines.append(f"{i}. {p['name']} {score_bar} {score}/100")
        if p.get('current_title'):
            lines.append(f"   {p['current_title']}")
        elif p.get('headline'):
            lines.append(f"   {p['headline']}")
        if p.get('summary'):
            lines.append(f"   {p['summary']}")
        if p.get('sector') and p['sector'] != 'other':
            lines.append(f"   Sector: {p['sector']}")
        if p.get('recommended_action') == 'reach_out':
            lines.append(f"   -> Recommended: Reach out")
        if p.get('linkedin_url'):
            lines.append(f"   {p['linkedin_url']}")
        if p.get('mutual_connections'):
            lines.append(f"   Mutual: {', '.join(p['mutual_connections'])}")
        lines.append("")

    if any(p.get('recommended_action') == 'reach_out' for p in profiles):
        lines.append("Action items flagged above")

    return '\n'.join(lines)


def format_rich_email(recipient_name, profiles, stats):
    """Format rich email with full scout results."""
    date_str = datetime.now().strftime('%b %d, %Y')

    lines = [
        f"Hi {recipient_name},",
        "",
        f"Founder Scout results for {date_str}:",
        f"({stats.get('active', 0)} people tracked, avg score: {stats.get('avg_score', 0)})",
        "",
    ]

    if profiles:
        lines.append(f"{len(profiles)} relevant profiles found:")
        lines.append("=" * 50)

        for i, p in enumerate(profiles, 1):
            score = p.get('priority_score', 0)
            lines.append(f"\n{i}. {p['name']} (Score: {score}/100)")
            if p.get('current_title'):
                lines.append(f"   Role: {p['current_title']}")
            if p.get('headline'):
                lines.append(f"   Headline: {p['headline']}")
            if p.get('summary'):
                lines.append(f"   Why: {p['summary']}")
            if p.get('sector') and p['sector'] != 'other':
                lines.append(f"   Sector: {p['sector']}")
            if p.get('signals'):
                lines.append(f"   Signals: {', '.join(p['signals'])}")
            if p.get('red_flags'):
                lines.append(f"   Watch: {', '.join(p['red_flags'])}")
            if p.get('linkedin_url'):
                lines.append(f"   LinkedIn: {p['linkedin_url']}")
            if p.get('recommended_action'):
                action_label = {'reach_out': 'REACH OUT', 'monitor': 'Monitor', 'skip': 'Skip'}
                lines.append(f"   Action: {action_label.get(p['recommended_action'], p['recommended_action'])}")
    else:
        lines.append("No relevant profiles found today.")

    lines.extend(["", f"-- {config.assistant_name}"])
    return '\n'.join(lines)


def format_briefing_email(recipient_name, high_signals, medium_signals, new_people, stats):
    """Format weekly briefing email."""
    now = datetime.now()
    week_start = (now - timedelta(days=7)).strftime('%b %d')
    week_end = now.strftime('%b %d, %Y')

    lines = [
        f"Hi {recipient_name},",
        "",
        f"Founder Scout weekly summary ({week_start} - {week_end}).",
        "",
        f"Watchlist: {stats['active']} people | Avg score: {stats['avg_score']}",
        f"High: {stats['high']} | Medium: {stats['medium']} | Low: {stats['low']}",
        "",
    ]

    if new_people:
        lines.append(f"NEW THIS WEEK ({len(new_people)} people)")
        lines.append("-" * 40)
        for p in new_people[:10]:
            score = p.get('priority_score', 0)
            lines.append(f"  [{score}] {p['name']}")
            if p.get('headline'):
                lines.append(f"       {p['headline'][:70]}")
            if p.get('linkedin_url'):
                lines.append(f"       {p['linkedin_url']}")
        lines.append("")

    if high_signals:
        lines.append("HIGH-PRIORITY SIGNALS")
        lines.append("-" * 40)
        for s in high_signals:
            lines.append(f"  {s['name']} [{s.get('priority_score', '?')}]")
            lines.append(f"    {s.get('description', 'N/A')}")
            if s.get('linkedin_url'):
                lines.append(f"    {s['linkedin_url']}")
        lines.append("")

    if medium_signals:
        lines.append("MEDIUM SIGNALS")
        lines.append("-" * 40)
        for s in medium_signals:
            lines.append(f"  {s['name']}: {s.get('description', 'N/A')}")
        lines.append("")

    if not high_signals and not medium_signals and not new_people:
        lines.append("Quiet week — no new signals on the watchlist.")
        lines.append("")

    lines.extend([f"-- {config.assistant_name}"])
    return '\n'.join(lines)


def format_briefing_whatsapp(high_signals, new_people, stats):
    """Format weekly briefing for WhatsApp."""
    lines = [
        "FOUNDER SCOUT WEEKLY",
        f"Tracking {stats['active']} people | Avg score: {stats['avg_score']}",
        "",
    ]

    if new_people:
        lines.append(f"New this week: {len(new_people)}")
        for p in new_people[:5]:
            score = p.get('priority_score', 0)
            name = p.get('name', '?')
            headline = p.get('headline', '')[:50]
            lines.append(f"  [{score}] {name} — {headline}")
        lines.append("")

    if high_signals:
        lines.append(f"High signals: {len(high_signals)}")
        for s in high_signals[:3]:
            lines.append(f"  {s['name']}: {s.get('description', '')[:60]}")
        lines.append("")

    if not new_people and not high_signals:
        lines.append("Quiet week — nothing new.")

    lines.append("Full report sent to email.")
    return '\n'.join(lines)


# --- Main Actions ---

def run_daily_scan():
    """Run daily discovery: LinkedIn rotation + Brave news."""
    print(f"[{datetime.now()}] Starting Founder Scout v2 daily scan...")

    db = ScoutDatabase(DB_PATH)

    # Check LinkedIn browser
    li_available = linkedin_browser_available()
    if li_available:
        print("  LinkedIn browser: available")
    else:
        print("  LinkedIn browser: UNAVAILABLE — LinkedIn search will be skipped")

    # Phase 0: Get search queue
    queue = db.get_rotation_queue(MAX_QUERIES_PER_SCAN)
    print(f"  Search queue: {len(queue)} queries due")

    all_profiles = []
    seen_urls = set()
    linkedin_lookups = 0

    # Phase 1: LinkedIn search rotation
    if li_available and queue:
        print(f"\n  === LINKEDIN SEARCH ({len(queue)} queries) ===")
        for query_key in queue:
            info = SEARCH_QUERIES[query_key]
            query = info['query']
            print(f"    [{query_key}] {query}...")

            results = linkedin_search(query)
            db.update_rotation(query_key)
            time.sleep(LINKEDIN_NAV_DELAY)

            if not results:
                print(f"      No results")
                continue

            new = []
            for p in results:
                url = p.get('url', '')
                if not url or url in seen_urls:
                    continue
                if db.is_profile_sent(url):
                    continue
                seen_urls.add(url)
                p['source'] = f"linkedin:{query_key}"
                new.append(p)

            skipped = len(results) - len(new)
            print(f"      {len(new)} new profiles" + (f" ({skipped} already seen)" if skipped else ""))
            all_profiles.extend(new)
    elif not queue:
        print("  No LinkedIn queries due today")

    # Phase 2: Brave news scan
    print(f"\n  === BRAVE NEWS SCAN ===")
    news_items = scan_news()
    print(f"    Found {len(news_items)} news items")

    if news_items:
        founders_from_news = extract_founders_from_news(news_items, db)
        print(f"    Extracted {len(founders_from_news)} founder mentions from news")

        # Try to find these founders on LinkedIn
        if li_available and founders_from_news:
            for f in founders_from_news[:5]:
                name = f.get('name', '')
                if not name:
                    continue
                if linkedin_lookups >= MAX_LINKEDIN_LOOKUPS_PER_SCAN:
                    break

                print(f"    Searching LinkedIn for news mention: {name}...")
                import urllib.parse
                encoded = urllib.parse.quote(name)
                urls = _linkedin_search_urls(encoded)
                linkedin_lookups += 1
                time.sleep(LINKEDIN_RATE_LIMIT)

                if urls:
                    url = urls[0]
                    if url not in seen_urls and not db.is_profile_sent(url):
                        seen_urls.add(url)
                        all_profiles.append({
                            'name': name,
                            'headline': f.get('context', ''),
                            'url': url,
                            'source': 'brave_news',
                        })

    if not all_profiles:
        print(f"\n  No new profiles found. Done.")
        db.log_scan('daily_scan', queries_run=len(queue))
        return

    # Mark all as sent (so they don't reappear)
    db.mark_profiles_sent([{'linkedin_url': p.get('url', ''), 'name': p.get('name', '')} for p in all_profiles])

    # Phase 3: Haiku fast triage
    print(f"\n  === HAIKU TRIAGE ({len(all_profiles)} profiles) ===")
    triage_passed = haiku_triage(all_profiles)
    print(f"    {len(triage_passed)} passed Haiku triage")

    if not triage_passed:
        print(f"\n  No relevant profiles after triage. Done.")
        db.log_scan('daily_scan', queries_run=len(queue), people_found=0)
        return

    # Phase 4: Sonnet deep analysis (visit profiles)
    print(f"\n  === SONNET DEEP ANALYSIS ({len(triage_passed)} profiles) ===")
    confirmed = []
    sonnet_calls = 0

    for i, p in enumerate(triage_passed):
        if sonnet_calls >= MAX_SONNET_CALLS:
            print(f"    Sonnet budget exhausted")
            break
        if linkedin_lookups >= MAX_LINKEDIN_LOOKUPS_PER_SCAN:
            print(f"    LinkedIn lookup budget exhausted")
            break

        name = p.get('name', 'Unknown')
        url = p.get('url', '')
        print(f"    [{i+1}/{len(triage_passed)}] {name}...")

        # Get full profile
        profile_text = None
        if li_available and url:
            profile_text = linkedin_profile_text(url)
            linkedin_lookups += 1
            time.sleep(LINKEDIN_NAV_DELAY)

        if not profile_text:
            print(f"      Could not load profile, using headline only")
            profile_text = f"Name: {name}\nHeadline: {p.get('headline', 'N/A')}"

        analysis = sonnet_deep_analysis(name, profile_text, url)
        sonnet_calls += 1

        if not analysis:
            print(f"      Analysis failed")
            continue

        if analysis.get('relevant'):
            # Compute priority score
            score = compute_priority_score(profile_text, p.get('headline'), analysis)

            # Check for mutual connections
            mutual = []
            for tn in TEAM_NAMES:
                if tn.lower() in profile_text.lower():
                    mutual.append(tn)

            entry = {
                'name': name,
                'linkedin_url': url,
                'headline': p.get('headline', ''),
                'current_title': analysis.get('current_title', ''),
                'summary': analysis.get('summary', ''),
                'sector': analysis.get('sector', 'other'),
                'signals': analysis.get('signals', []),
                'red_flags': analysis.get('red_flags', []),
                'recommended_action': analysis.get('recommended_action', 'monitor'),
                'priority_score': score,
                'mutual_connections': mutual,
                'source': p.get('source', ''),
            }

            # Store profile hash for diff detection
            profile_hash = hashlib.md5(profile_text.encode()).hexdigest() if profile_text else None

            # Add to DB
            person_id = db.add_person(
                name, url, p.get('headline'), p.get('source', 'scan'),
                priority_score=score, profile_hash=profile_hash,
                profile_snapshot=profile_text[:4000] if profile_text else None
            )
            if person_id:
                db.record_signal(
                    person_id, 'initial_detection',
                    analysis.get('confidence', 'medium'),
                    analysis.get('summary', ''),
                    url
                )

                # HubSpot auto-create for high-score founders
                if score >= 70:
                    print(f"      Creating HubSpot contact (score {score})...")
                    contact_id = hubspot_create_contact(
                        name, url, analysis.get('summary', ''),
                        analysis.get('sector', 'other'), score
                    )
                    if contact_id:
                        db.update_person(person_id, hubspot_contact_id=contact_id)

            confirmed.append(entry)
            print(f"      RELEVANT (score: {score}) — {analysis.get('summary', '')[:60]}")
        else:
            print(f"      Not relevant: {analysis.get('summary', '')[:60]}")

    # Phase 5: Send results
    print(f"\n  === RESULTS: {len(confirmed)} confirmed leads ===")

    if confirmed:
        # Sort by score
        confirmed.sort(key=lambda x: x.get('priority_score', 0), reverse=True)

        stats = db.get_stats()
        date_str = datetime.now().strftime('%b %d, %Y')
        subject = f"Founder Scout — {date_str} ({len(confirmed)} leads)"

        for recipient in SCOUT_RECIPIENTS:
            # Rich email
            email_body = format_rich_email(recipient['first_name'], confirmed, stats)
            send_email(recipient['email'], subject, email_body)

            # Rich WhatsApp
            wa_msg = format_rich_whatsapp_alert(confirmed)
            if wa_msg:
                send_whatsapp(recipient['phone'], wa_msg, account=WHATSAPP_ACCOUNT)

        print(f"  Sent to {len(SCOUT_RECIPIENTS)} recipients")

    db.log_scan('daily_scan', queries_run=len(queue), people_found=len(confirmed),
                signals_detected=len(confirmed),
                details=json.dumps({'sources': {'linkedin': len(queue), 'news': len(news_items)}}))
    print(f"\n  Scan complete: {len(queue)} LinkedIn queries, {len(news_items)} news items, "
          f"{len(confirmed)} confirmed leads")


def run_news_scan():
    """Brave-only news scan (runs more frequently than full scan)."""
    print(f"[{datetime.now()}] Starting Founder Scout news scan...")

    db = ScoutDatabase(DB_PATH)
    news_items = scan_news()
    print(f"  Found {len(news_items)} news items")

    if not news_items:
        db.log_scan('news_scan')
        return

    founders = extract_founders_from_news(news_items, db)
    print(f"  Extracted {len(founders)} founder mentions")

    if not founders:
        db.log_scan('news_scan', queries_run=3)
        return

    # Add to watchlist with basic info (LinkedIn lookup happens in daily scan)
    added = 0
    for f in founders:
        name = f.get('name', '')
        if not name or len(name) < 3:
            continue
        person_id = db.add_person(name, source='brave_news')
        if person_id:
            db.record_signal(
                person_id, 'news_mention', 'medium',
                f.get('context', f"Mentioned in startup news: {f.get('company', '')}")
            )
            added += 1
            print(f"    Added: {name} — {f.get('context', '')[:60]}")

    db.log_scan('news_scan', queries_run=3, people_found=added)
    print(f"  News scan complete: {added} new people added")


def run_watchlist_update():
    """Re-scan tracked people for profile changes via LinkedIn."""
    print(f"[{datetime.now()}] Starting Founder Scout watchlist update...")

    db = ScoutDatabase(DB_PATH)
    people = db.get_active_people()

    if not people:
        print("  No active people in watchlist.")
        db.log_scan('watchlist_update')
        return

    if not linkedin_browser_available():
        print("  LinkedIn browser unavailable. Skipping.")
        db.log_scan('watchlist_update')
        return

    print(f"  Re-scanning {len(people)} active people...")

    lookups = 0
    changes_detected = 0
    sonnet_calls = 0

    for person in people:
        if lookups >= MAX_LINKEDIN_LOOKUPS_PER_SCAN:
            break

        name = person['name']
        url = person.get('linkedin_url')
        person_id = person['id']

        if not url:
            # Try to find on LinkedIn
            print(f"    {name}: no LinkedIn URL, searching...")
            import urllib.parse
            results = _linkedin_search_urls(urllib.parse.quote(name))
            lookups += 1
            time.sleep(LINKEDIN_NAV_DELAY)

            if results:
                url = results[0]
                db.update_person(person_id, linkedin_url=url)
                print(f"      Found: {url}")
            else:
                db.update_person(person_id, last_scanned=datetime.now().isoformat())
                continue

        print(f"    {name}: checking profile...")
        profile_text = linkedin_profile_text(url)
        lookups += 1
        time.sleep(LINKEDIN_NAV_DELAY)

        if not profile_text:
            db.update_person(person_id, last_scanned=datetime.now().isoformat())
            continue

        # Detect changes
        changes = detect_profile_changes(person, profile_text)
        new_hash = hashlib.md5(profile_text.encode()).hexdigest()

        # Update stored profile
        db.update_person(
            person_id,
            profile_hash=new_hash,
            profile_snapshot=profile_text[:4000],
            last_scanned=datetime.now().isoformat()
        )

        significant_changes = [c for c in changes if c['type'] not in ('minor_update', 'first_scan')]
        if not significant_changes:
            print(f"      No significant changes")
            continue

        changes_detected += 1
        change_desc = '; '.join(c['detail'] for c in significant_changes)
        print(f"      CHANGE: {change_desc[:80]}")

        # Deep analysis on changed profiles
        if sonnet_calls < MAX_SONNET_CALLS:
            analysis = sonnet_deep_analysis(name, profile_text, url)
            sonnet_calls += 1

            if analysis:
                new_score = compute_priority_score(profile_text, person.get('headline'), analysis)
                tier = analysis.get('confidence', 'medium')

                db.record_signal(person_id, 'profile_change', tier, change_desc, url)
                db.update_person(person_id, priority_score=new_score, signal_tier=tier)

                if new_score > (person.get('priority_score', 0) or 0) + 15:
                    # Score jumped significantly — alert team
                    print(f"      Score jumped: {person.get('priority_score', 0)} -> {new_score}")
                    for recipient in SCOUT_RECIPIENTS:
                        msg = (
                            f"SCOUT ALERT — Profile Change\n\n"
                            f"{name} [{new_score}/100]\n"
                            f"{change_desc}\n"
                            f"{analysis.get('summary', '')}\n"
                            f"{url}"
                        )
                        send_whatsapp(recipient['phone'], msg, account=WHATSAPP_ACCOUNT)

    db.log_scan('watchlist_update', queries_run=len(people),
                people_found=changes_detected, signals_detected=changes_detected)
    print(f"  Watchlist update complete: {len(people)} checked, {changes_detected} changes, "
          f"{sonnet_calls} deep analyses")


def run_weekly_briefing():
    """Send weekly watchlist update — signals, new people, stats."""
    print(f"[{datetime.now()}] Sending Founder Scout weekly briefing...")

    db = ScoutDatabase(DB_PATH)
    since = (datetime.now() - timedelta(days=7)).isoformat()
    recent_signals = db.get_signals_since(since)

    high_signals = [s for s in recent_signals if s['signal_tier'] == 'high']
    medium_signals = [s for s in recent_signals if s['signal_tier'] == 'medium']

    # New people added this week
    all_people = db.get_active_people()
    week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    new_people = [p for p in all_people if p.get('added_at', '') >= week_ago]

    stats = db.get_stats()

    date_str = datetime.now().strftime('%b %d, %Y')
    subject = f"Founder Scout Weekly — {date_str}"

    for recipient in SCOUT_RECIPIENTS:
        email_body = format_briefing_email(
            recipient['first_name'], high_signals, medium_signals, new_people, stats
        )
        send_email(recipient['email'], subject, email_body)

        wa_msg = format_briefing_whatsapp(high_signals, new_people, stats)
        send_whatsapp(recipient['phone'], wa_msg, account=WHATSAPP_ACCOUNT)

    db.log_scan('weekly_briefing', signals_detected=len(recent_signals))
    print(f"  Briefing sent: {len(high_signals)} high, {len(medium_signals)} medium, "
          f"{len(new_people)} new people")


def run_status():
    """Print current tracked people and signal counts."""
    db = ScoutDatabase(DB_PATH)
    stats = db.get_stats()
    people = db.get_active_people()

    print(f"Founder Scout v2 — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    print(f"  Active: {stats['active']} | High: {stats['high']} | Med: {stats['medium']} | Low: {stats['low']}")
    print(f"  Avg score: {stats['avg_score']} | Signals: {stats['total_signals']} | Scans: {stats['total_scans']}")

    if people:
        print(f"\n  Watchlist (top 20 by score):")
        for p in people[:20]:
            score = p.get('priority_score', 0)
            tier = (p.get('signal_tier') or '---').upper()
            headline = (p.get('headline') or p.get('last_signal') or '')[:50]
            li = f"  {p['linkedin_url']}" if p.get('linkedin_url') else ""
            gh = f"  {p['github_url']}" if p.get('github_url') else ""
            hs = " [HubSpot]" if p.get('hubspot_contact_id') else ""
            print(f"    [{score:3d}] [{tier:6s}] {p['name']}{hs}")
            if headline:
                print(f"           {headline}")
            if li:
                print(f"          {li}")
            if gh:
                print(f"          {gh}")
    else:
        print("\n  No people tracked yet. Run 'scout.py scan' to start.")


def run_add(name, linkedin_url=None):
    """Manually add a person to track."""
    db = ScoutDatabase(DB_PATH)
    person_id = db.add_person(name, linkedin_url or None, source='manual')
    if person_id:
        print(f"Added {name} to watchlist (id={person_id})")
        if linkedin_url:
            print(f"  LinkedIn: {linkedin_url}")
    else:
        print(f"Could not add {name} (may already exist)")


def run_dismiss(person_id):
    """Mark a person as dismissed."""
    db = ScoutDatabase(DB_PATH)
    db.dismiss_person(int(person_id))
    print(f"Dismissed person id={person_id}")


# --- Entry Point ---

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    action = sys.argv[1]

    if action in ('scan', 'news-scan', 'watchlist-update', 'github-scan'):
        lock_file = open(LOCK_PATH, 'w')
        try:
            fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Another instance running, skipping.")
            return
        try:
            if action == 'scan':
                run_daily_scan()
            elif action == 'news-scan':
                run_news_scan()
            elif action == 'watchlist-update':
                run_watchlist_update()
            elif action == 'github-scan':
                run_github_scan()
        finally:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()

    elif action == 'briefing':
        run_weekly_briefing()

    elif action == 'status':
        run_status()

    elif action == 'add':
        if len(sys.argv) < 3:
            print("Usage: scout.py add <name> [linkedin_url]")
            sys.exit(1)
        name = sys.argv[2]
        linkedin_url = sys.argv[3] if len(sys.argv) > 3 else None
        run_add(name, linkedin_url)

    elif action == 'dismiss':
        if len(sys.argv) < 3:
            print("Usage: scout.py dismiss <id>")
            sys.exit(1)
        run_dismiss(sys.argv[2])

    else:
        print(f"Unknown action: {action}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()
