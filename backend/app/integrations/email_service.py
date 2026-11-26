"""
Email notification service using aiosmtplib.
Sends appointment confirmations and call summaries.
"""
from __future__ import annotations

import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import aiosmtplib

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def send_email(to: str, subject: str, html_body: str, text_body: str = "") -> bool:
    """Send an email. Returns True on success."""
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning("Email not configured — skipping send to %s", to)
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg["Subject"] = subject

    if text_body:
        msg.attach(MIMEText(text_body, "plain"))
    msg.attach(MIMEText(html_body, "html"))

    try:
        await aiosmtplib.send(
            msg,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        logger.info("Email sent to %s: %s", to, subject)
        return True
    except Exception as e:
        logger.error("Email send error: %s", e)
        return False


async def send_appointment_confirmation(
    to_email: str,
    lead_name: str,
    start_time: str,
    meet_link: str,
    sales_rep_name: str = "SalesPilot AI",
) -> bool:
    subject = f"Your Appointment is Confirmed — {start_time}"
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <h2 style="color: #2563eb;">Appointment Confirmed</h2>
      <p>Hi {lead_name},</p>
      <p>Your appointment has been confirmed. Here are the details:</p>
      <table style="border-collapse: collapse; width: 100%;">
        <tr><td style="padding: 8px; font-weight: bold;">Date &amp; Time:</td>
            <td style="padding: 8px;">{start_time}</td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">Meeting Link:</td>
            <td style="padding: 8px;"><a href="{meet_link}">{meet_link}</a></td></tr>
        <tr><td style="padding: 8px; font-weight: bold;">Host:</td>
            <td style="padding: 8px;">{sales_rep_name}</td></tr>
      </table>
      <p>We look forward to speaking with you!</p>
      <p style="color: #6b7280; font-size: 0.875rem;">SalesPilot AI — Powered by Generative AI</p>
    </div>
    """
    return await send_email(to_email, subject, html_body)


async def send_call_summary(
    to_email: str,
    lead_name: str,
    summary: dict,
) -> bool:
    subject = f"Call Summary — {lead_name}"
    next_steps = "".join(f"<li>{s}</li>" for s in summary.get("recommended_next_steps", []))
    html_body = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
      <h2 style="color: #2563eb;">Call Summary</h2>
      <p><strong>Lead:</strong> {lead_name}</p>
      <p><strong>BANT Score:</strong> {summary.get('bant_score', 'N/A')}</p>
      <p><strong>Qualification Level:</strong> {summary.get('qualification_level', 'N/A')}</p>
      <p><strong>Sentiment:</strong> {summary.get('overall_sentiment', 'N/A')}</p>
      <h3>Recommended Next Steps</h3>
      <ul>{next_steps}</ul>
    </div>
    """
    return await send_email(to_email, subject, html_body)
