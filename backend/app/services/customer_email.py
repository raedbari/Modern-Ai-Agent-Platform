"""Customer email delivery for Athka Chatbots."""

from __future__ import annotations

import asyncio
import logging
import os
import smtplib
from email.message import EmailMessage
from urllib.parse import quote

LOGGER = logging.getLogger(__name__)


def build_verification_url(raw_token: str) -> str:
    app_url = os.getenv(
        "ATHKA_PUBLIC_APP_URL",
        "http://localhost:3000",
    ).rstrip("/")
    return f"{app_url}/verify-email?token={quote(raw_token, safe='')}"


def _smtp_send(*, recipient: str, verification_url: str) -> None:
    host = os.getenv("ATHKA_SMTP_HOST", "").strip()
    port = int(os.getenv("ATHKA_SMTP_PORT", "587"))
    username = os.getenv("ATHKA_SMTP_USERNAME", "").strip()
    password = os.getenv("ATHKA_SMTP_PASSWORD", "")
    sender = os.getenv(
        "ATHKA_EMAIL_FROM",
        "no-reply@athkachatbots.com",
    ).strip()

    if not host:
        raise RuntimeError(
            "ATHKA_SMTP_HOST is required when ATHKA_EMAIL_MODE=smtp."
        )

    message = EmailMessage()
    message["Subject"] = "Verify your Athka Chatbots account"
    message["From"] = sender
    message["To"] = recipient
    message.set_content(
        "Welcome to Athka Chatbots.\n\n"
        "Verify your email address using this link:\n"
        f"{verification_url}\n\n"
        "If you did not create this account, ignore this message."
    )

    use_starttls = os.getenv(
        "ATHKA_SMTP_STARTTLS",
        "true",
    ).strip().lower() not in {"0", "false", "no"}

    with smtplib.SMTP(host, port, timeout=15) as client:
        client.ehlo()
        if use_starttls:
            client.starttls()
            client.ehlo()
        if username:
            client.login(username, password)
        client.send_message(message)


async def send_verification_email(
    *,
    recipient: str,
    raw_token: str,
) -> str:
    verification_url = build_verification_url(raw_token)
    mode = os.getenv("ATHKA_EMAIL_MODE", "log").strip().lower()

    if mode == "log":
        LOGGER.info(
            "Athka verification email recipient=%s url=%s",
            recipient,
            verification_url,
        )
        return verification_url

    if mode != "smtp":
        raise RuntimeError("ATHKA_EMAIL_MODE must be 'log' or 'smtp'.")

    await asyncio.to_thread(
        _smtp_send,
        recipient=recipient,
        verification_url=verification_url,
    )
    return verification_url
