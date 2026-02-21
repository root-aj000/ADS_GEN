"""
Notification system — Slack/Discord webhooks + email.
"""

from __future__ import annotations

import json
import smtplib
import threading
from email.mime.text import MIMEText
from typing import Optional

import requests

from config.settings import NotificationConfig
from utils.log_config import get_logger

log = get_logger(__name__)


class Notifier:
    """
    Fire-and-forget notifications.
    All sends happen in background threads.
    """

    def __init__(self, cfg: NotificationConfig) -> None:
        self.cfg = cfg

    def _send_async(self, func, *args) -> None:
        if not self.cfg.enabled:
            return
        t = threading.Thread(target=func, args=args, daemon=True)
        t.start()

    # ── webhook (Slack / Discord) ───────────────────────────
    def _send_webhook(self, title: str, message: str) -> None:
        if not self.cfg.webhook_url:
            return
        try:
            payload = {
                "text": f"*{title}*\n{message}",           # Slack
                "content": f"**{title}**\n{message}",       # Discord
            }
            requests.post(
                self.cfg.webhook_url,
                json=payload,
                timeout=10,
            )
        except Exception as exc:
            log.debug("Webhook failed: %s", exc)

    # ── email ───────────────────────────────────────────────
    def _send_email(self, subject: str, body: str) -> None:
        c = self.cfg
        if not c.email_to or not c.smtp_host:
            return
        try:
            msg = MIMEText(body)
            msg["Subject"] = f"[AdGen] {subject}"
            msg["From"] = c.smtp_user
            msg["To"] = c.email_to

            with smtplib.SMTP(c.smtp_host, c.smtp_port) as smtp:
                smtp.starttls()
                smtp.login(c.smtp_user, c.smtp_pass)
                smtp.send_message(msg)
        except Exception as exc:
            log.debug("Email failed: %s", exc)

    # ── public API ──────────────────────────────────────────
    def notify(self, title: str, message: str) -> None:
        self._send_async(self._send_webhook, title, message)
        self._send_async(self._send_email, title, message)

    def on_completion(self, total: int, success: int, elapsed: float) -> None:
        if "completion" not in self.cfg.notify_on:
            return
        msg = (
            f"Total: {total}\n"
            f"Success: {success}\n"
            f"Failed: {total - success}\n"
            f"Time: {elapsed:.1f}s"
        )
        self.notify("✅ Pipeline Complete", msg)

    def on_failure(self, idx: int, error: str) -> None:
        if "failure" not in self.cfg.notify_on:
            return
        self.notify("❌ Row Failed", f"Index: {idx}\nError: {error[:200]}")

    def on_milestone(self, count: int) -> None:
        if "milestone" not in self.cfg.notify_on:
            return
        if count % self.cfg.milestone_every == 0:
            self.notify("🎯 Milestone", f"{count} ads generated successfully!")