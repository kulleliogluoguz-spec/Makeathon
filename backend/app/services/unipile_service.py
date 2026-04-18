"""Unipile API integration — LinkedIn search, invite, message."""

import os
import httpx
from dotenv import load_dotenv

load_dotenv()

UNIPILE_API_KEY = os.getenv("UNIPILE_API_KEY", "")
UNIPILE_DSN = os.getenv("UNIPILE_DSN", "")
UNIPILE_ACCOUNT_ID = os.getenv("UNIPILE_ACCOUNT_ID", "")

def get_base_url():
    if not UNIPILE_DSN:
        return ""
    # DSN format: api1.unipile.com:13337
    if "://" not in UNIPILE_DSN:
        return f"https://{UNIPILE_DSN}"
    return UNIPILE_DSN

HEADERS = {
    "accept": "application/json",
    "X-API-KEY": UNIPILE_API_KEY,
}


async def search_linkedin_people(
    keywords: str = "",
    location: list = None,
    industry: list = None,
    limit: int = 10,
) -> dict:
    """Search LinkedIn for people using Unipile API."""
    base = get_base_url()
    if not base or not UNIPILE_API_KEY:
        return {"error": "Unipile not configured", "people": []}

    try:
        params = {
            "account_id": UNIPILE_ACCOUNT_ID,
            "limit": min(limit, 50),
        }

        body = {
            "api": "classic",
            "category": "people",
        }

        if keywords:
            body["keywords"] = keywords
        if location:
            body["location"] = location
        if industry:
            body["industry"] = industry

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{base}/api/v1/linkedin/search",
                headers=HEADERS,
                params=params,
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        items = data.get("items", [])
        people = []
        for item in items:
            people.append({
                "provider_id": item.get("provider_id", ""),
                "first_name": item.get("first_name", ""),
                "last_name": item.get("last_name", ""),
                "headline": item.get("headline", ""),
                "title": item.get("headline", ""),
                "linkedin_url": item.get("public_profile_url", "") or f"https://www.linkedin.com/in/{item.get('public_identifier', '')}",
                "profile_picture": item.get("profile_picture", ""),
                "location": item.get("location", ""),
                "company_name": item.get("current_company_name", "") or _extract_company(item.get("headline", "")),
                "network_distance": item.get("network_distance", ""),
            })

        cursor = data.get("cursor", "")
        return {
            "total": len(people),
            "cursor": cursor,
            "people": people,
        }

    except Exception as e:
        print(f"Unipile search error: {e}")
        return {"error": str(e), "people": []}


async def get_linkedin_profile(identifier: str) -> dict:
    """Get detailed LinkedIn profile by username or provider_id."""
    base = get_base_url()
    if not base:
        return {"error": "Unipile not configured"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{base}/api/v1/users/{identifier}",
                headers=HEADERS,
                params={"account_id": UNIPILE_ACCOUNT_ID},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        print(f"Unipile profile error: {e}")
        return {"error": str(e)}


async def send_linkedin_invite(provider_id: str, message: str = "") -> dict:
    """Send a LinkedIn connection request with optional note."""
    base = get_base_url()
    if not base:
        return {"success": False, "error": "Unipile not configured"}

    try:
        body = {
            "provider_id": provider_id,
            "account_id": UNIPILE_ACCOUNT_ID,
        }
        if message:
            body["message"] = message[:300]  # LinkedIn connection note max 300 chars

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{base}/api/v1/users/invite",
                headers={**HEADERS, "content-type": "application/json"},
                json=body,
            )
            resp.raise_for_status()
            return {"success": True, "data": resp.json()}
    except Exception as e:
        print(f"Unipile invite error: {e}")
        return {"success": False, "error": str(e)}


async def send_linkedin_message(provider_id: str, text: str) -> dict:
    """Send a LinkedIn message to an existing connection."""
    base = get_base_url()
    if not base:
        return {"success": False, "error": "Unipile not configured"}

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{base}/api/v1/chats",
                headers={**HEADERS, "content-type": "multipart/form-data"},
                data={
                    "account_id": UNIPILE_ACCOUNT_ID,
                    "text": text,
                    "attendees_ids": provider_id,
                },
            )
            resp.raise_for_status()
            return {"success": True, "data": resp.json()}
    except Exception as e:
        print(f"Unipile message error: {e}")
        return {"success": False, "error": str(e)}


def _extract_company(headline: str) -> str:
    """Try to extract company name from headline like 'CEO at TechCorp'."""
    if " at " in headline:
        return headline.split(" at ")[-1].strip()
    if " @ " in headline:
        return headline.split(" @ ")[-1].strip()
    if " | " in headline:
        return headline.split(" | ")[-1].strip()
    return ""
