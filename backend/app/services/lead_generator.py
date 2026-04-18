"""AI-powered lead generation using web search + GPT analysis."""

import os
import json
import uuid
import httpx
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


async def generate_icp_from_persona(persona: dict) -> dict:
    """Use AI to analyze persona info and generate an Ideal Customer Profile."""
    persona_context = f"""
Company: {persona.get('company_name', '')}
Role: {persona.get('role_title', '')}
Description: {persona.get('description', '')}
Expertise: {', '.join(persona.get('expertise_areas', []))}
Background: {persona.get('background_story', '')}
"""

    prompt = f"""Analyze this business persona and generate an Ideal Customer Profile (ICP) for lead generation.

{persona_context}

Based on this information, determine:
1. What industry/sector does this business serve?
2. What products/services do they sell?
3. Who are their ideal customers? (B2B or B2C?)
4. What job titles should they target as decision-makers?
5. What company sizes are ideal?
6. What locations are most relevant?
7. What keywords describe their target market?

Return JSON only, no other text:
{{
    "target_industries": ["industry1", "industry2"],
    "target_job_titles": ["title1", "title2", "title3"],
    "target_seniorities": ["director", "vp", "c_suite", "manager"],
    "target_company_sizes": ["11,50", "51,200", "201,1000"],
    "target_locations": ["location1", "location2"],
    "target_keywords": "keyword phrase for search",
    "icp_description": "2-3 sentence description of the ideal customer",
    "outreach_angle": "What value proposition to lead with when reaching out"
}}"""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4.1-nano",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"},
                },
            )
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
    except Exception as e:
        print(f"ICP generation error: {e}")
        return {}


def build_linkedin_search_url(first_name: str, last_name: str, company_name: str) -> str:
    """Build a LinkedIn people search URL with name + company for best accuracy."""
    import urllib.parse
    parts = [first_name, last_name]
    if company_name:
        parts.append(company_name)
    query = " ".join(parts).strip()
    encoded = urllib.parse.quote(query, safe='')
    return f"https://www.linkedin.com/search/results/people/?keywords={encoded}&origin=GLOBAL_SEARCH_HEADER"


async def search_leads_with_ai(icp: dict, page: int = 1, per_page: int = 10) -> dict:
    """Use OpenAI web search to find real companies and decision-makers matching the ICP."""
    if not OPENAI_API_KEY:
        return {"error": "OPENAI_API_KEY not set", "people": []}

    industries = ", ".join(icp.get("target_industries", []))
    titles = ", ".join(icp.get("target_job_titles", []))
    locations = ", ".join(icp.get("target_locations", []))
    keywords = icp.get("target_keywords", "")
    icp_desc = icp.get("icp_description", "")
    sizes = ", ".join(icp.get("target_company_sizes", []))

    prompt = f"""Search the web and find {per_page} REAL companies and their decision-makers that match this Ideal Customer Profile.

ICP: {icp_desc}
Target Industries: {industries}
Target Job Titles: {titles}
Target Locations: {locations}
Company Size Ranges (employees): {sizes}
Keywords: {keywords}
Page: {page} (find different results than page {page - 1} if page > 1)

For each lead, find REAL people at REAL companies using web search. Look on LinkedIn, company websites, Crunchbase, etc.

Return ONLY a JSON object, no other text:
{{
  "total": <estimated total matching companies>,
  "people": [
    {{
      "first_name": "<real first name>",
      "last_name": "<real last name>",
      "title": "<their actual job title>",
      "city": "<city>",
      "state": "<state/region>",
      "country": "<country>",
      "company_name": "<real company name>",
      "company_industry": "<industry>",
      "company_size": "<estimated number of employees>",
      "company_revenue": "<estimated annual revenue if known>",
      "company_website": "<company website URL>",
      "company_city": "<company HQ city>",
      "company_country": "<company HQ country>"
    }}
  ]
}}

IMPORTANT: Return REAL companies and people you find via web search. Each result must be a real, verifiable company."""

    try:
        async with httpx.AsyncClient(timeout=90) as client:
            resp = await client.post(
                "https://api.openai.com/v1/responses",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4.1-mini",
                    "tools": [{"type": "web_search_preview"}],
                    "input": prompt,
                },
            )
            data = resp.json()

            # Extract text from Responses API output
            content = ""
            for item in data.get("output", []):
                if item.get("type") == "message":
                    for part in item.get("content", []):
                        if part.get("type") == "output_text":
                            content = part.get("text", "")
                            break

            if not content:
                print(f"AI search raw response: {json.dumps(data)[:500]}")
                return {"error": "No results from AI search", "people": []}

            # Extract JSON from response (may be wrapped in ```json blocks)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            parsed = json.loads(content.strip())
            people = parsed.get("people", [])

            # Clean up AI responses and ensure valid data
            cleaned = []
            for p in people:
                # Skip entries with N/A names
                fn = p.get("first_name", "")
                ln = p.get("last_name", "")
                if not fn or fn.upper() == "N/A" or not ln or ln.upper() == "N/A":
                    continue
                # Clean N/A values across all fields
                for key, val in p.items():
                    if isinstance(val, str) and val.upper() == "N/A":
                        p[key] = ""
                if not p.get("apollo_id"):
                    p["apollo_id"] = str(uuid.uuid4())
                # Always use LinkedIn search URL — profile URLs are unreliable
                p["linkedin_url"] = build_linkedin_search_url(fn, ln, p.get("company_name", ""))
                cleaned.append(p)
            people = cleaned

            return {
                "total": parsed.get("total", len(people)),
                "page": page,
                "per_page": per_page,
                "people": people,
            }
    except Exception as e:
        print(f"AI web search error: {e}")
        return {"error": str(e), "people": []}


async def ai_score_leads(leads: list, persona: dict, icp: dict) -> list:
    """AI scores each lead 0-100 with reasoning."""
    if not leads:
        return []

    leads_text = ""
    for i, lead in enumerate(leads):
        leads_text += f"""
Lead {i+1}:
  Name: {lead['first_name']} {lead['last_name']}
  Title: {lead['title']}
  Company: {lead['company_name']}
  Industry: {lead.get('company_industry', '')}
  Size: {lead.get('company_size', '')} employees
  Revenue: {lead.get('company_revenue', '')}
  Location: {lead.get('city', '')}, {lead.get('country', '')}
"""

    prompt = f"""You are a B2B sales analyst. Score these leads for a business with this profile:

Business: {persona.get('company_name', '')} - {persona.get('description', '')}
Ideal Customer: {icp.get('icp_description', '')}
Value Proposition: {icp.get('outreach_angle', '')}

{leads_text}

For each lead, provide:
- Score (0-100): How likely this lead is to buy from this business
- Reason: 1 sentence explaining why this score
- Approach: 1 sentence on how to approach this person

Return JSON array only:
[
  {{"lead_index": 0, "score": 85, "reason": "Decision maker at a mid-size company in the target industry", "approach": "Mention their recent expansion and how your product can help"}},
  ...
]"""

    try:
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4.1-nano",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.3,
                    "response_format": {"type": "json_object"},
                    "max_tokens": 2000,
                },
            )
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)

            # Handle if AI wraps in object
            if isinstance(parsed, dict):
                scored = parsed.get("leads", parsed.get("results", []))
            else:
                scored = parsed

            # Merge scores into leads
            for item in scored:
                idx = item.get("lead_index", 0)
                if 0 <= idx < len(leads):
                    leads[idx]["ai_score"] = item.get("score", 50)
                    leads[idx]["ai_reason"] = item.get("reason", "")
                    leads[idx]["ai_approach"] = item.get("approach", "")

            # Sort by score descending
            leads.sort(key=lambda x: x.get("ai_score", 0), reverse=True)
            return leads

    except Exception as e:
        print(f"AI scoring error: {e}")
        return leads


async def generate_outreach_message(lead: dict, persona: dict, icp: dict, channel: str = "email", landing_page_url: str = "") -> str:
    """Generate a personalized outreach message for a specific lead."""
    if channel == "linkedin_connection":
        channel_rules = "This is a LinkedIn CONNECTION REQUEST note. Max 300 characters. Be very short and personal. No selling. Just express genuine interest in connecting."
    elif channel == "linkedin":
        channel_rules = "This is a LinkedIn direct message. Keep it under 5 sentences. Professional but warm. Reference something specific about their company or role."
    elif channel == "email":
        channel_rules = "This is a cold email. Include a subject line on the first line. Keep the body under 6 sentences. Professional, clear value proposition."
    elif channel == "whatsapp":
        channel_rules = "This is a WhatsApp message. Very casual and brief. 2-3 sentences max. Friendly tone, like texting a colleague."
    else:
        channel_rules = "Keep it brief and professional."

    prompt = f"""Write a short, personalized {channel} outreach message.

From: {persona.get('display_name', '')} at {persona.get('company_name', '')}
To: {lead.get('first_name', '')} {lead.get('last_name', '')}, {lead.get('title', '')} at {lead.get('company_name', '')}

Business: {persona.get('description', '')}
Value Proposition: {icp.get('outreach_angle', '')}
Why this person: {lead.get('ai_reason', '')}
Approach: {lead.get('ai_approach', '')}

{"" if not landing_page_url else f'''
IMPORTANT: We have created a custom landing page specifically for their company. Include this URL in your message and reference it naturally.
Landing Page URL: {landing_page_url}
Mention something like: "We actually built a custom landing page for {lead.get("company_name", "your company")} — take a look: {landing_page_url}. If you like what you see, I would love to set up a quick meeting to discuss how we can help."
'''}
Rules:
- Be specific to their company/role
- No generic "I hope this finds you well"
- End with a clear, low-pressure CTA
- {channel_rules}

Return ONLY the message text, nothing else."""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4.1-nano",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.7,
                    "max_tokens": 300,
                },
            )
            data = resp.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"Outreach message error: {e}")
        return ""
