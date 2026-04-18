"""Generate customized landing pages using Anthropic Claude API."""

import os
import json
import httpx
from dotenv import load_dotenv

load_dotenv()

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


async def generate_landing_page(
    customer_name: str = "",
    customer_company: str = "",
    customer_industry: str = "",
    customer_description: str = "",
    persona_company: str = "",
    persona_description: str = "",
    persona_services: list = None,
    style: str = "modern",
    color_scheme: str = "auto",
    language: str = "en",
    additional_instructions: str = "",
) -> dict:
    """Generate a complete HTML landing page using Claude."""
    if not ANTHROPIC_API_KEY:
        return {"success": False, "html": "", "error": "ANTHROPIC_API_KEY not set"}

    services_text = ", ".join(persona_services or [])

    prompt = f"""Create a complete, production-ready HTML landing page. Return ONLY the HTML code, nothing else. No markdown backticks, no explanations.

## CLIENT INFORMATION
- Company Name: {customer_company or 'TechStartup'}
- Contact Person: {customer_name}
- Industry: {customer_industry or 'Technology'}
- About the company: {customer_description or 'A growing startup'}

## BUILT BY
- Agency/Builder: {persona_company}
- Services offered: {services_text}

## DESIGN REQUIREMENTS
- Style: {style} (options: modern, minimal, bold, corporate, creative, startup)
- Color scheme: {color_scheme} (options: auto, dark, light, blue, green, purple, red, orange)
- Language: {language}
- Must be fully responsive (mobile + tablet + desktop)
- Must look professional and premium

## MANDATORY SECTIONS (in this order)
1. **Navigation bar** — Company logo (text-based), menu links (smooth scroll), CTA button
2. **Hero section** — Large headline, subheadline, CTA button, background gradient or pattern
3. **About/What We Do** — 2-3 sentences about the company, with an icon or illustration placeholder
4. **Services/Features** — 3-4 service cards with icons (use emoji or SVG), title, description
5. **Why Choose Us** — 3 key differentiators with stats or highlights
6. **Testimonials** — 2-3 fake but realistic customer testimonials with names and roles
7. **Call to Action** — Big CTA section with email signup or contact form
8. **Footer** — Company info, social links (placeholder), copyright

## TECHNICAL REQUIREMENTS
- Single HTML file with all CSS inline in <style> tags
- Use modern CSS: flexbox, grid, CSS variables, smooth animations
- Add subtle hover effects and transitions
- Use Google Fonts (Inter or Poppins)
- Include smooth scroll behavior
- Add a simple fade-in animation for sections on load
- Form inputs should have proper styling
- All text should be realistic and specific to the client's business
- NO placeholder "Lorem ipsum" text — write real, compelling copy
- Include meta viewport tag for mobile

## ADDITIONAL INSTRUCTIONS
{additional_instructions or 'Make it look stunning and professional.'}

Return ONLY the complete HTML code starting with <!DOCTYPE html> and ending with </html>. No other text."""

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 8000,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            data = resp.json()

            html = data["content"][0]["text"]

            # Clean up — remove markdown backticks if present
            if html.startswith("```html"):
                html = html[7:]
            if html.startswith("```"):
                html = html[3:]
            if html.endswith("```"):
                html = html[:-3]
            html = html.strip()

            return {"success": True, "html": html, "error": ""}

    except Exception as e:
        print(f"Landing page generation error: {e}")
        return {"success": False, "html": "", "error": str(e)}


async def refine_landing_page(current_html: str, instruction: str) -> dict:
    """Refine an existing landing page based on user feedback."""
    if not ANTHROPIC_API_KEY:
        return {"success": False, "html": "", "error": "ANTHROPIC_API_KEY not set"}

    prompt = f"""Here is an existing HTML landing page. Modify it based on the user's instruction. Return ONLY the complete modified HTML code. No markdown backticks, no explanations.

## CURRENT HTML
{current_html}

## USER'S INSTRUCTION
{instruction}

Return ONLY the complete modified HTML starting with <!DOCTYPE html> and ending with </html>."""

    try:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-sonnet-4-20250514",
                    "max_tokens": 8000,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
            data = resp.json()
            html = data["content"][0]["text"]

            if html.startswith("```html"):
                html = html[7:]
            if html.startswith("```"):
                html = html[3:]
            if html.endswith("```"):
                html = html[:-3]
            html = html.strip()

            return {"success": True, "html": html, "error": ""}
    except Exception as e:
        print(f"Landing page refine error: {e}")
        return {"success": False, "html": "", "error": str(e)}
