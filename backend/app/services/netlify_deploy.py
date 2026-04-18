"""Deploy HTML landing pages to Netlify via API."""

import os
import io
import zipfile
import httpx
from dotenv import load_dotenv

load_dotenv()

NETLIFY_ACCESS_TOKEN = os.getenv("NETLIFY_ACCESS_TOKEN", "")
NETLIFY_API = "https://api.netlify.com/api/v1"


async def deploy_landing_page(html_content: str, site_name: str = "") -> dict:
    """Deploy a single HTML file to Netlify. Returns the live URL."""
    if not NETLIFY_ACCESS_TOKEN:
        return {"success": False, "url": "", "error": "NETLIFY_ACCESS_TOKEN not set"}

    # Clean site name for subdomain
    clean_name = site_name.lower().strip()
    clean_name = "".join(c if c.isalnum() or c == "-" else "-" for c in clean_name)
    clean_name = clean_name.strip("-")[:50]
    if not clean_name:
        clean_name = "landing-page"

    headers = {
        "Authorization": f"Bearer {NETLIFY_ACCESS_TOKEN}",
    }

    try:
        # Step 1: Create a new site
        async with httpx.AsyncClient(timeout=30) as client:
            create_resp = await client.post(
                f"{NETLIFY_API}/sites",
                headers={**headers, "Content-Type": "application/json"},
                json={"name": clean_name},
            )

            # If name taken, try with random suffix
            if create_resp.status_code == 422:
                import random
                clean_name = f"{clean_name}-{random.randint(100,999)}"
                create_resp = await client.post(
                    f"{NETLIFY_API}/sites",
                    headers={**headers, "Content-Type": "application/json"},
                    json={"name": clean_name},
                )

            create_resp.raise_for_status()
            site_data = create_resp.json()
            site_id = site_data.get("id", "")

        # Step 2: Create a ZIP file with index.html
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("index.html", html_content)
        zip_buffer.seek(0)

        # Step 3: Deploy the ZIP to the site
        async with httpx.AsyncClient(timeout=60) as client:
            deploy_resp = await client.post(
                f"{NETLIFY_API}/sites/{site_id}/deploys",
                headers={
                    "Authorization": f"Bearer {NETLIFY_ACCESS_TOKEN}",
                    "Content-Type": "application/zip",
                },
                content=zip_buffer.read(),
            )
            deploy_resp.raise_for_status()
            deploy_data = deploy_resp.json()

        site_url = deploy_data.get("ssl_url", "") or deploy_data.get("url", "") or f"https://{clean_name}.netlify.app"

        print(f"Netlify deploy success: {site_url}")
        return {
            "success": True,
            "url": site_url,
            "site_id": site_id,
            "site_name": clean_name,
        }

    except Exception as e:
        print(f"Netlify deploy error: {e}")
        return {"success": False, "url": "", "error": str(e)}
