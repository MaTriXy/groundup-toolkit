"""
Shared email sender via gog CLI.

Usage:
    from lib.email import send_email

    send_email("user@example.com", "Subject", "Body text")
"""

import os
import sys
import tempfile
import subprocess

from lib.config import config

GOG_ACCOUNT = config.assistant_email


def send_email(to_email, subject, body, account=None):
    """Send email using gog CLI with body file.

    Args:
        to_email: Recipient email address.
        subject: Email subject.
        body: Email body text.
        account: Google account to send from (default: assistant email from config).

    Returns:
        True on success, False on failure.
    """
    account = account or GOG_ACCOUNT
    try:
        fd, body_file = tempfile.mkstemp(suffix='.txt', prefix='toolkit-email-')
        with os.fdopen(fd, 'w') as f:
            f.write(body)

        cmd = [
            'gog', 'gmail', 'send',
            '--to', to_email,
            '--subject', subject,
            '--body-file', body_file,
            '--account', account,
            '--force', '--no-input'
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        try:
            os.unlink(body_file)
        except OSError:
            pass

        if result.returncode == 0:
            print(f"  Email sent to {to_email}")
            return True
        else:
            print(f"  Email failed for {to_email}: {result.stderr.strip()[:200]}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"  Email exception for {to_email}: {e}", file=sys.stderr)
        return False
