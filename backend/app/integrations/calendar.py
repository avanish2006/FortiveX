"""
Google Calendar integration for appointment booking.
Falls back gracefully when credentials are not configured.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def create_calendar_event(
    title: str,
    description: str,
    start_str: str,
    attendee_email: str,
    duration_minutes: int = 30,
    timezone: str = "UTC",
) -> dict:
    """
    Create a Google Calendar event and return event details.
    start_str: 'YYYY-MM-DD HH:MM' format
    """
    if not settings.google_client_id or not settings.google_client_secret:
        logger.warning("Google Calendar not configured — returning mock event")
        return _mock_event(title, start_str, attendee_email, duration_minutes)

    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build

        creds = _load_credentials()
        if not creds:
            return _mock_event(title, start_str, attendee_email, duration_minutes)

        service = build("calendar", "v3", credentials=creds)
        start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=duration_minutes)

        event = {
            "summary": title,
            "description": description,
            "start": {"dateTime": start_dt.isoformat(), "timeZone": timezone},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": timezone},
            "attendees": [{"email": attendee_email}],
            "conferenceData": {
                "createRequest": {
                    "requestId": f"salespilot-{int(start_dt.timestamp())}",
                    "conferenceSolutionKey": {"type": "hangoutsMeet"},
                }
            },
        }

        result = (
            service.events()
            .insert(
                calendarId=settings.google_calendar_id,
                body=event,
                conferenceDataVersion=1,
                sendUpdates="all",
            )
            .execute()
        )

        meet_link = (
            result.get("conferenceData", {})
            .get("entryPoints", [{}])[0]
            .get("uri", "")
        )

        return {
            "event_id": result["id"],
            "meet_link": meet_link,
            "start": start_str,
            "end": end_dt.strftime("%Y-%m-%d %H:%M"),
            "html_link": result.get("htmlLink", ""),
        }

    except Exception as e:
        logger.error("Google Calendar error: %s", e)
        return _mock_event(title, start_str, attendee_email, duration_minutes)


def _load_credentials():
    """Load stored OAuth credentials. Stub — implement with token storage."""
    return None


def _mock_event(title: str, start_str: str, email: str, duration: int) -> dict:
    try:
        start_dt = datetime.strptime(start_str, "%Y-%m-%d %H:%M")
        end_dt = start_dt + timedelta(minutes=duration)
    except ValueError:
        start_dt = datetime.utcnow()
        end_dt = start_dt + timedelta(minutes=duration)

    return {
        "event_id": "mock_event_001",
        "meet_link": "https://meet.google.com/xxx-yyyy-zzz",
        "start": start_dt.strftime("%Y-%m-%d %H:%M"),
        "end": end_dt.strftime("%Y-%m-%d %H:%M"),
        "html_link": "",
        "note": "Mock event — configure Google Calendar credentials to enable real booking",
    }
