"""Sends transactional email over SMTP - currently just the passwordless
login code (see auth.py's /auth/passwordless/request).

Security note: this exists because handing that code back in the API
response (which is what this app used to do) let anyone who knew a
username log in as them with zero credentials - the whole point of
"passwordless" is that only the account's real inbox ever sees the code.
Nothing in this module should change that; if you're tempted to return the
token from the request endpoint for convenience, don't.

Configured entirely via environment variables (see .env.example). The
default docker-compose setup points this at Mailpit, a fake SMTP server
with a web UI (http://localhost:8025) and HTTP API - local dev/test never
needs a real mail provider or real credentials. Point SMTP_HOST/PORT/
USERNAME/PASSWORD at a real provider (Gmail, Postmark, SES, your own mail
server - anything that speaks SMTP) for actual delivery.
"""

import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger("expense_tracker.email")

SMTP_HOST = os.environ.get("SMTP_HOST", "localhost")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "25"))
SMTP_USERNAME = os.environ.get("SMTP_USERNAME") or None
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD") or None
SMTP_USE_TLS = os.environ.get("SMTP_USE_TLS", "false").lower() == "true"
FROM_ADDRESS = os.environ.get("SMTP_FROM_ADDRESS", "no-reply@expense-tracker.local")
SEND_TIMEOUT_SECONDS = 10.0


def send_email(to_address: str, subject: str, body: str) -> bool:
    """Best-effort - returns whether it sent, never raises. A broken mail
    server must never turn into a 500 for the caller, and for the
    passwordless-login flow specifically, must never turn into a different
    response depending on whether the account exists - see auth.py's
    request_passwordless_login, which calls this and then always returns
    the same shape regardless of what happens here."""
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = FROM_ADDRESS
    message["To"] = to_address
    message.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=SEND_TIMEOUT_SECONDS) as client:
            if SMTP_USE_TLS:
                client.starttls()
            if SMTP_USERNAME and SMTP_PASSWORD:
                client.login(SMTP_USERNAME, SMTP_PASSWORD)
            client.send_message(message)
        return True
    except (smtplib.SMTPException, OSError):
        logger.exception("failed to send email to %s", to_address)
        return False


def send_passwordless_login_code(to_address: str, token: str, ttl_seconds: int) -> bool:
    minutes = max(1, ttl_seconds // 60)
    body = (
        "Here's your one-time login code for Expense Tracker:\n\n"
        f"    {token}\n\n"
        f"It expires in {minutes} minute{'s' if minutes != 1 else ''} and can only be used once.\n\n"
        "If you didn't request this, you can safely ignore this email - "
        "your account is still secure."
    )
    return send_email(to_address, "Your Expense Tracker login code", body)
