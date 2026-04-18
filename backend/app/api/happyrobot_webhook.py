"""HappyRobot webhook — receives call results, transcripts, and scheduled meetings."""

import os
import json
from datetime import datetime, timedelta
from fastapi import APIRouter, Request
from sqlalchemy import select

from app.core.database import async_session
from app.models.conversation_state import ConversationState
from app.models.customer import Customer
from app.models.meeting import Meeting

router = APIRouter()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


@router.post("/happyrobot/webhook")
async def happyrobot_webhook(request: Request):
    """Receive call completion data from HappyRobot."""
    data = await request.json()
    print(f"HappyRobot webhook received: {json.dumps(data, indent=2)[:500]}")

    call_id = data.get("id", data.get("call_id", ""))
    status = data.get("status", "")
    transcript = data.get("transcript", "")
    metadata = data.get("metadata", {})
    duration = data.get("duration", data.get("call_duration", ""))

    customer_name = metadata.get("customer_name", "")
    customer_company = metadata.get("customer_company", "")
    customer_email = metadata.get("customer_email", "")
    lead_reason = metadata.get("lead_reason", "")

    # Extract structured data from transcript using AI
    call_analysis = await analyze_call_transcript(transcript, customer_name, customer_company)

    # Save to ConversationState
    await save_call_to_conversations(
        call_id=call_id,
        customer_name=customer_name,
        customer_company=customer_company,
        transcript=transcript,
        duration=str(duration),
        analysis=call_analysis,
    )

    # If meeting was scheduled, create Meeting entry
    if call_analysis.get("meeting_scheduled"):
        await create_meeting_from_call(
            call_id=call_id,
            customer_name=customer_name,
            customer_company=customer_company,
            customer_email=customer_email or call_analysis.get("email_captured", ""),
            transcript=transcript,
            analysis=call_analysis,
            duration=str(duration),
            metadata=metadata,
        )

    # If email was accepted, send it
    if call_analysis.get("email_accepted"):
        email_address = call_analysis.get("email_captured", customer_email)
        if email_address:
            await send_followup_email(
                to_email=email_address,
                customer_name=customer_name,
                customer_company=customer_company,
                metadata=metadata,
            )

    return {"status": "ok"}


async def analyze_call_transcript(transcript: str, customer_name: str, company: str) -> dict:
    """Use AI to extract structured data from the call transcript."""
    if not transcript or not OPENAI_API_KEY:
        return {}

    import httpx
    prompt = f"""Analyze this phone call transcript and extract the following information.

Transcript:
{transcript}

Return JSON only:
{{
    "call_summary": "2-3 sentence summary of the call",
    "customer_interest_level": 1-10 scale,
    "email_accepted": true/false (did customer agree to receive an email?),
    "email_captured": "email@example.com" or "" (if customer provided their email),
    "meeting_scheduled": true/false (did customer agree to a meeting?),
    "meeting_date": "2026-04-22T14:00:00" or "" (if a specific date was agreed),
    "meeting_duration": "15" or "30" (minutes),
    "objections": ["list of concerns or objections raised"],
    "customer_needs": ["list of needs or pain points mentioned"],
    "next_steps": "what was agreed at the end of the call",
    "overall_outcome": "positive" or "neutral" or "negative",
    "key_quotes": ["1-2 important things the customer said verbatim"]
}}"""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "gpt-4.1-nano",
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0.2,
                    "response_format": {"type": "json_object"},
                },
            )
            data = resp.json()
            return json.loads(data["choices"][0]["message"]["content"])
    except Exception as e:
        print(f"Call analysis error: {e}")
        return {}


async def save_call_to_conversations(call_id, customer_name, customer_company, transcript, duration, analysis):
    """Save HappyRobot call as a conversation in ConversationState."""
    try:
        async with async_session() as session:
            sender_id = f"call_{call_id}"

            # Parse transcript into messages
            messages = []
            now = datetime.utcnow()
            if transcript:
                lines = transcript.strip().split("\n")
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    if line.startswith("AI Agent:") or line.startswith("Agent:"):
                        messages.append({
                            "role": "assistant",
                            "content": line.split(":", 1)[-1].strip(),
                            "timestamp": now.isoformat(),
                        })
                    elif ":" in line:
                        messages.append({
                            "role": "user",
                            "content": line.split(":", 1)[-1].strip(),
                            "timestamp": now.isoformat(),
                        })

            conv = ConversationState(
                sender_id=sender_id,
                channel="phone",
                messages=messages,
                message_count=len(messages),
                intent_score=min((analysis.get("customer_interest_level", 5) * 10), 100),
                stage="consideration" if analysis.get("meeting_scheduled") else "interest",
                categories=["high_sales_potential"] if analysis.get("customer_interest_level", 0) >= 7 else ["sales_potential"],
                response_mode="human_only",
                signals=analysis.get("customer_needs", []),
                next_action=analysis.get("next_steps", ""),
                score_breakdown=analysis.get("call_summary", ""),
                last_message_at=now,
                created_at=now,
            )
            session.add(conv)

            # Create/update customer
            result = await session.execute(
                select(Customer).where(Customer.display_name == customer_name)
            )
            customer = result.scalar_one_or_none()
            if not customer:
                customer = Customer(
                    display_name=customer_name,
                    source="phone",
                    instagram_sender_id=sender_id,
                    last_contact_at=now,
                    total_messages=str(len(messages)),
                )
                session.add(customer)
            else:
                customer.last_contact_at = now

            await session.commit()
            print(f"Call saved to conversations: {sender_id}")
    except Exception as e:
        print(f"Save call error: {e}")


async def create_meeting_from_call(call_id, customer_name, customer_company, customer_email, transcript, analysis, duration, metadata):
    """Create a Meeting entry from a scheduled call."""
    try:
        # Generate meeting report using AI
        report = await generate_meeting_report(transcript, customer_name, customer_company, analysis, metadata)

        meeting_date_str = analysis.get("meeting_date", "")
        if meeting_date_str:
            try:
                meeting_date = datetime.fromisoformat(meeting_date_str)
            except Exception:
                meeting_date = datetime.utcnow() + timedelta(days=2)
        else:
            meeting_date = datetime.utcnow() + timedelta(days=2)

        async with async_session() as session:
            meeting = Meeting(
                customer_name=customer_name,
                customer_company=customer_company,
                customer_title=metadata.get("customer_title", ""),
                customer_phone=metadata.get("phone_number", ""),
                customer_email=customer_email,
                customer_linkedin=metadata.get("customer_linkedin", ""),
                scheduled_date=meeting_date,
                duration_minutes=analysis.get("meeting_duration", "15"),
                meeting_type="call",
                status="scheduled",
                source_channel=metadata.get("source_channel", "phone"),
                initial_contact_method="ai_call",
                conversation_summary=analysis.get("call_summary", ""),
                customer_interests=", ".join(analysis.get("customer_needs", [])) if isinstance(analysis.get("customer_needs"), list) else str(analysis.get("customer_interests", "")),
                recommended_approach="\n".join(report.get("recommended_approach")) if isinstance(report.get("recommended_approach"), list) else str(report.get("recommended_approach", "")),
                talking_points=report.get("talking_points", []) if isinstance(report.get("talking_points"), list) else [],
                risk_factors="\n".join(report.get("risk_factors")) if isinstance(report.get("risk_factors"), list) else str(report.get("risk_factors", "")),
                estimated_deal_value=str(report.get("estimated_deal_value", "")),
                call_transcript=transcript,
                call_duration_seconds=duration,
                call_id=call_id,
            )
            session.add(meeting)
            await session.commit()
            print(f"Meeting created from call {call_id}")
    except Exception as e:
        print(f"Create meeting error: {e}")


async def generate_meeting_report(transcript, customer_name, customer_company, analysis, metadata):
    """AI generates a detailed meeting prep report."""
    import httpx

    prompt = f"""Based on this AI sales call, generate a meeting preparation report for the sales manager.

Call transcript:
{transcript}

Customer: {customer_name} at {customer_company}
Call analysis: {json.dumps(analysis)}
How they were found: {metadata.get('lead_reason', 'outbound prospecting')}

Generate a detailed report in JSON:
{{
    "recommended_approach": "Step-by-step approach for the meeting (numbered list, 5-7 steps)",
    "talking_points": ["point 1", "point 2", ...] (6-8 key points),
    "risk_factors": "What could go wrong and how to handle it",
    "estimated_deal_value": "Estimated monthly/annual value based on their company size and needs"
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
            return json.loads(data["choices"][0]["message"]["content"])
    except Exception as e:
        print(f"Report generation error: {e}")
        return {}


async def send_followup_email(to_email, customer_name, customer_company, metadata):
    """Send a personalized follow-up email after the call."""
    import httpx

    persona_desc = metadata.get("company_desc", "")
    company_name = metadata.get("company_name", "our company")

    # Generate email content with AI
    prompt = f"""Write a professional follow-up email after a sales call.

From: {company_name}
To: {customer_name} at {customer_company}
Context: We just had a brief phone call where we introduced {company_name} and they agreed to receive more information.
About us: {persona_desc}

Write a short, professional email (max 150 words):
- Thank them for the call
- Briefly recap what {company_name} offers
- Include 3 key benefits
- End with a soft CTA
- Include a subject line on the first line

Return ONLY the email text, nothing else. Subject line on first line."""

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
            email_text = data["choices"][0]["message"]["content"]
    except Exception:
        email_text = f"Subject: Following up on our call\n\nHi {customer_name},\n\nThank you for taking the time to speak with us today. We'd love to help {customer_company} grow. Looking forward to connecting again soon.\n\nBest regards"

    # Send via Resend
    try:
        from app.services.email_sender import send_email
        lines = email_text.strip().split("\n")
        subject = lines[0].replace("Subject:", "").strip()
        body = "\n".join(lines[1:]).strip()
        await send_email(to_email, subject, body)
        print(f"Follow-up email sent to {to_email}")
    except Exception as e:
        print(f"Email send error: {e}")
