"""
Email sending abstraction for APPROVED LeadOutreach drafts only.

Default provider is "mock" -- never sends a real email, safe for demos and tests
with zero configuration. Real sending (SMTPProvider, stdlib smtplib, no new heavy
dependency) requires explicitly setting EMAIL_PROVIDER=smtp plus SMTP_HOST/PORT/
USERNAME/PASSWORD/EMAIL_FROM in backend/.env.

This module has no opinion about HITL -- it only knows how to move bytes. The
caller (app.api.v1.leads' send-outreach endpoint) is solely responsible for
gating a send on LeadOutreach.status == "approved" before ever calling this.
"""
import asyncio
import logging
import smtplib
import uuid
from abc import ABC, abstractmethod
from email.mime.text import MIMEText
from typing import Dict

from app.config import settings

logger = logging.getLogger("ja_assure.email")


class EmailSendError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class EmailProvider(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    async def send(self, to: str, subject: str, body: str) -> Dict[str, str]:
        """Returns {"status": "sent", "provider": ..., "message_id": ...}.
        Raises EmailSendError on failure -- never returns a fake success."""
        ...


class MockEmailProvider(EmailProvider):
    """Default provider. Never sends a real email -- logs what WOULD be sent and
    returns a clearly-labeled mock result. Safe with zero configuration; this is
    what keeps the system from sending real email merely because a lead exists."""

    @property
    def name(self) -> str:
        return "mock"

    async def send(self, to: str, subject: str, body: str) -> Dict[str, str]:
        logger.info(f"[MOCK EMAIL] To: {to} | Subject: {subject} | (not actually sent -- EMAIL_PROVIDER=mock)")
        return {"status": "sent", "provider": "mock", "message_id": f"mock-{uuid.uuid4().hex[:12]}"}


class SMTPProvider(EmailProvider):
    """Real email via any standard SMTP server (Gmail, SendGrid's SMTP relay,
    Resend's SMTP endpoint, a self-hosted relay, etc.) using stdlib smtplib --
    deliberately no new third-party dependency for something this standard."""

    @property
    def name(self) -> str:
        return "smtp"

    @property
    def is_configured(self) -> bool:
        return bool(settings.SMTP_HOST and settings.EMAIL_FROM)

    async def send(self, to: str, subject: str, body: str) -> Dict[str, str]:
        if not self.is_configured:
            raise EmailSendError(
                "SMTP_HOST and EMAIL_FROM must both be configured to send real email "
                "(see backend/.env). Set EMAIL_PROVIDER=mock to keep sending disabled."
            )
        try:
            await asyncio.to_thread(self._send_sync, to, subject, body)
        except EmailSendError:
            raise
        except Exception as e:
            raise EmailSendError(f"SMTP send failed: {e}")

        return {"status": "sent", "provider": "smtp", "message_id": f"smtp-{uuid.uuid4().hex[:12]}"}

    def _send_sync(self, to: str, subject: str, body: str) -> None:
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = settings.EMAIL_FROM
        msg["To"] = to

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=15) as server:
            server.starttls()
            if settings.SMTP_USERNAME and settings.SMTP_PASSWORD:
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.sendmail(settings.EMAIL_FROM, [to], msg.as_string())


def get_email_provider() -> EmailProvider:
    choice = (settings.EMAIL_PROVIDER or "mock").strip().lower()
    if choice == "smtp":
        return SMTPProvider()
    return MockEmailProvider()
