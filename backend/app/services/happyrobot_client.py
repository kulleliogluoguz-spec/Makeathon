"""HappyRobot integration client.

Fires the Lead Outreach Pipeline workflow in HappyRobot whenever a new
qualified lead is saved. The workflow generates a personalized German
outreach email (and can be extended to send via LinkedIn, WhatsApp, voice).

Workflow lives at:
  https://platform.eu.happyrobot.ai/tumai/workflow/csflc5r0sxjl/editor/vxmp9v47md9l

Configure the trigger URL via the HAPPYROBOT_WEBHOOK_URL environment variable.
Grab the URL from the Webhook Trigger node in the editor above.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Trigger URL for the "Lead Outreach Pipeline" workflow.
# Format: https://platform.eu.happyrobot.ai/webhook/<workflow_slug>/<trigger_id>
HAPPYROBOT_WEBHOOK_URL: Optional[str] = os.getenv("HAPPYROBOT_WEBHOOK_URL")

# How long to wait before giving up on the trigger call. We keep this short
# because lead creation should not block on an external service.
HAPPYROBOT_TIMEOUT_SECONDS: float = float(os.getenv("HAPPYROBOT_TIMEOUT_SECONDS", "10"))


def _build_payload(lead) -> dict:
    """Map a SavedLead ORM object to the JSON payload expected by the
    HappyRobot Predefined Webhook trigger.

    Field names here must match the `params` array configured on the trigger
    node in HappyRobot. If you add fields here, also add them to the trigger.
    """
    return {
        "lead_id": str(getattr(lead, "id", "")),
        "first_name": getattr(lead, "first_name", "") or "",
        "last_name": getattr(lead, "last_name", "") or "",
        "company_name": getattr(lead, "company_name", "") or "",
        "title": getattr(lead, "title", "") or "",
        "linkedin_url": getattr(lead, "linkedin_url", "") or "",
        # The Lead model does not currently have email/phone fields;
        # we send empty strings so the workflow sees the keys consistently.
        "email": getattr(lead, "email", "") or "",
        "phone_number": getattr(lead, "phone_number", "") or "",
    }


async def trigger_lead_outreach(lead) -> dict:
    """Fire the HappyRobot Lead Outreach Pipeline workflow for a saved lead.

    Returns a dict describing what happened. Never raises — failures are
    logged but do not break the lead-save flow.
    """
    if not HAPPYROBOT_WEBHOOK_URL:
        logger.warning(
            "HAPPYROBOT_WEBHOOK_URL is not set; skipping HappyRobot trigger "
            "for lead_id=%s",
            getattr(lead, "id", "?"),
        )
        return {"triggered": False, "reason": "webhook_url_not_configured"}

    payload = _build_payload(lead)

    try:
        async with httpx.AsyncClient(timeout=HAPPYROBOT_TIMEOUT_SECONDS) as client:
            resp = await client.post(HAPPYROBOT_WEBHOOK_URL, json=payload)
            resp.raise_for_status()
            logger.info(
                "HappyRobot workflow triggered for lead_id=%s status=%s",
                payload["lead_id"],
                resp.status_code,
            )
            return {
                "triggered": True,
                "status_code": resp.status_code,
                "lead_id": payload["lead_id"],
            }
    except httpx.HTTPError as exc:
        logger.exception(
            "HappyRobot trigger failed for lead_id=%s: %s",
            payload["lead_id"],
            exc,
        )
        return {"triggered": False, "reason": "http_error", "error": str(exc)}
