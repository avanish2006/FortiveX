"""
HubSpot CRM integration.
Creates and updates contacts and deals.
Falls back gracefully when API key is not configured.
"""
from __future__ import annotations

import logging
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def upsert_contact(
    email: str,
    full_name: Optional[str] = None,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    job_title: Optional[str] = None,
    deal_stage: Optional[str] = None,
    notes: Optional[str] = None,
) -> dict:
    """Create or update a HubSpot contact. Returns contact id and status."""
    if not settings.hubspot_api_key:
        logger.warning("HubSpot not configured — returning mock response")
        return {"contact_id": "mock_001", "email": email, "mode": "mock"}

    try:
        import hubspot
        from hubspot.crm.contacts import SimplePublicObjectInput, ApiException

        client = hubspot.Client.create(access_token=settings.hubspot_api_key)

        props = {"email": email}
        if full_name:
            parts = full_name.split(" ", 1)
            props["firstname"] = parts[0]
            if len(parts) > 1:
                props["lastname"] = parts[1]
        if phone:
            props["phone"] = phone
        if company:
            props["company"] = company
        if job_title:
            props["jobtitle"] = job_title
        if notes:
            props["hs_lead_status"] = notes[:100]

        contact_input = SimplePublicObjectInput(properties=props)

        try:
            result = client.crm.contacts.basic_api.create(simple_public_object_input=contact_input)
            contact_id = result.id
            action = "created"
        except ApiException as e:
            if e.status == 409:
                existing = client.crm.contacts.basic_api.get_by_id(email, id_property="email")
                client.crm.contacts.basic_api.update(
                    existing.id, simple_public_object_input=contact_input
                )
                contact_id = existing.id
                action = "updated"
            else:
                raise

        return {"contact_id": contact_id, "email": email, "action": action}

    except Exception as e:
        logger.error("HubSpot error: %s", e)
        return {"contact_id": "error", "email": email, "error": str(e)}


async def get_contact(email: str) -> Optional[dict]:
    """Fetch a contact from HubSpot by email."""
    if not settings.hubspot_api_key:
        return None
    try:
        import hubspot
        client = hubspot.Client.create(access_token=settings.hubspot_api_key)
        result = client.crm.contacts.basic_api.get_by_id(email, id_property="email")
        return result.to_dict()
    except Exception as e:
        logger.error("HubSpot get_contact error: %s", e)
        return None
