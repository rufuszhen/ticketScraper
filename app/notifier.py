from __future__ import annotations

import smtplib
from email.message import EmailMessage

from .config import EmailConfig


def send_email(config: EmailConfig, subject: str, body: str) -> None:
    if not config.smtp_host or not config.smtp_to:
        return
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = config.smtp_from or config.smtp_user or config.smtp_to
    message["To"] = config.smtp_to
    message.set_content(body)

    with smtplib.SMTP(config.smtp_host, config.smtp_port, timeout=30) as server:
        if config.use_tls:
            server.starttls()
        if config.smtp_user:
            server.login(config.smtp_user, config.smtp_password)
        server.send_message(message)
