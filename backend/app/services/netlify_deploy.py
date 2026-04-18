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
        async with httpx.AsyncClient(timeout=60) as client:
            # Step 1: Create a new site
            create_resp = await client.post(
                f"{NETLIFY_API}/sites",
                headers={**headers, "Content-Type": "application/json"},
                json={"name": clean_name},
            )

            # If name taken, try with random suffix
            if create_resp.status_code == 422:
                import random
                clean_name = f"{clean_name}-{random.randint(1000, 9999)}"
                create_resp = await client.post(
                    f"{NETLIFY_API}/sites",
                    headers={**headers, "Content-Type": "application/json"},
                    json={"name": clean_name},
                )

            create_resp.raise_for_status()
            site_data = create_resp.json()
            site_id = site_data.get("id", "")

            # Step 2: Create ZIP with index.html
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("index.html", html_content)
            zip_bytes = zip_buffer.getvalue()

            # Step 3: Deploy ZIP file
            deploy_resp = await client.post(
                f"{NETLIFY_API}/sites/{site_id}/deploys",
                headers={
                    "Authorization": f"Bearer {NETLIFY_ACCESS_TOKEN}",
                    "Content-Type": "application/zip",
                },
                content=zip_bytes,
            )
            deploy_resp.raise_for_status()
            deploy_data = deploy_resp.json()

            # Step 4: Wait for deploy to be ready
            deploy_id = deploy_data.get("id", "")
            site_url = f"https://{clean_name}.netlify.app"

            # Poll until ready (max 30 seconds)
            import asyncio
            for _ in range(15):
                check_resp = await client.get(
                    f"{NETLIFY_API}/deploys/{deploy_id}",
                    headers=headers,
                )
                if check_resp.status_code == 200:
                    check_data = check_resp.json()
                    state = check_data.get("state", "")
                    if state == "ready":
                        site_url = check_data.get("ssl_url", "") or check_data.get("url", "") or site_url
                        break
                await asyncio.sleep(2)

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
