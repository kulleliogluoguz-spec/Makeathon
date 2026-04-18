"""Seed 2 demo meetings with full reports."""

from datetime import datetime, timedelta
from sqlalchemy import select
from app.core.database import async_session
from app.models.meeting import Meeting


async def seed_demo_meetings():
    async with async_session() as session:
        result = await session.execute(select(Meeting).limit(1))
        if result.scalar_one_or_none():
            return

        now = datetime.utcnow()

        meeting1 = Meeting(
            customer_name="Thomas Berger",
            customer_company="NovaTech Solutions GmbH",
            customer_title="Co-Founder & CEO",
            customer_phone="+49 151 2283 9471",
            customer_email="t.berger@novatech-solutions.de",
            customer_linkedin="https://www.linkedin.com/in/thomasberger",
            scheduled_date=now + timedelta(days=2, hours=3),
            duration_minutes="15",
            meeting_type="call",
            status="scheduled",
            source_channel="linkedin",
            initial_contact_method="ai_call",
            conversation_summary="Thomas was contacted through our AI outbound call system after being identified as a high-potential lead via LinkedIn search. He is the Co-Founder of NovaTech Solutions, a 6-person startup in Munich building SaaS tools for logistics companies. During the AI call, he expressed interest in our customer engagement platform, specifically the omnichannel messaging capabilities and AI-powered response system. He mentioned they currently handle customer inquiries manually via email and are losing potential clients due to slow response times. He agreed to a follow-up call with our sales manager to discuss pricing and implementation timeline.",
            customer_interests="Omnichannel messaging (WhatsApp + Instagram), AI auto-responses, lead scoring, CRM integration",
            recommended_approach="""1. Start by acknowledging their pain point: slow manual email responses losing clients
2. Demo the Instagram/WhatsApp AI auto-reply — show how it responds in seconds vs hours
3. Highlight the intent scoring feature — they can prioritize high-value leads automatically
4. Show the analytics dashboard — data-driven decisions
5. Pricing: Start with the startup tier, emphasize ROI (time saved = money saved)
6. Close with a trial offer: "Try it free for 14 days on your Instagram, see the difference"
7. AVOID: Don't push enterprise features yet, they're a small team. Keep it simple.""",
            talking_points=[
                "Their current pain: manual email responses taking 4-6 hours",
                "They lost 3 potential B2B clients last month due to slow responses",
                "They're already on Instagram and WhatsApp but not using them for business",
                "Budget: mentioned they have budget for tools under \u20ac200/month",
                "Decision maker: Thomas makes final call but will consult co-founder Lisa",
                "Timeline: wants to implement within 2 weeks if it's a good fit",
            ],
            risk_factors="Small team, limited budget. Co-founder Lisa not yet involved \u2014 may need a second call. They mentioned evaluating 2 other solutions (Zendesk and Freshdesk).",
            estimated_deal_value="\u20ac150/month (Startup plan)",
            call_transcript="""AI Agent: Hi, is this Thomas Berger?
Thomas: Yes, speaking.
AI Agent: Hi Thomas, I'm calling from [Company]. We noticed NovaTech Solutions is building some really interesting logistics tools, and I wanted to reach out because we help companies like yours automate customer communication across channels like WhatsApp and Instagram.
Thomas: Oh interesting, how did you find us?
AI Agent: We came across your LinkedIn profile and company page. I noticed you're a small but growing team, and from what I've seen, many startups at your stage struggle with keeping up with customer inquiries manually.
Thomas: That's actually spot on. We're drowning in emails right now. Takes us hours to respond sometimes.
AI Agent: That's exactly what we solve. Our platform uses AI to respond to customers instantly on WhatsApp, Instagram, and other channels. Would you be open to a quick 15-minute call with our sales manager to see if it could work for you?
Thomas: Sure, I'd be interested. When would that be?
AI Agent: How about day after tomorrow, around 2 PM Berlin time?
Thomas: That works for me.
AI Agent: Perfect! Our sales manager will reach out to confirm. Thanks for your time, Thomas!
Thomas: Thanks, looking forward to it.""",
            call_duration_seconds="127",
            call_id="hr_call_demo_001",
            assigned_to="",
            notes="",
        )
        session.add(meeting1)

        meeting2 = Meeting(
            customer_name="Sarah Kim",
            customer_company="UrbanBite Food Delivery",
            customer_title="Head of Operations",
            customer_phone="+49 176 8827 3344",
            customer_email="sarah.kim@urbanbite.de",
            customer_linkedin="https://www.linkedin.com/in/sarahkim-urbanbite",
            scheduled_date=now + timedelta(days=4, hours=5),
            duration_minutes="30",
            meeting_type="video",
            status="scheduled",
            source_channel="instagram",
            initial_contact_method="dm_conversation",
            conversation_summary="Sarah initially reached out via Instagram DM asking about our platform's capabilities for food delivery businesses. The AI assistant engaged with her for 12 messages, during which her intent score climbed to 85. She was particularly interested in automated order confirmations, WhatsApp integration for delivery updates, and the ability to handle customer complaints via AI before escalating to humans. When the AI offered a phone call at intent score 78, she accepted and provided her number. During the HappyRobot call, she was impressed by the AI's natural conversation and agreed to a 30-minute video demo with the sales manager.",
            customer_interests="Order confirmation automation, WhatsApp delivery updates, complaint handling AI, multi-language support (German + English + Turkish)",
            recommended_approach="""1. This is a warm lead \u2014 she already used the product (chatted with AI on Instagram) and was impressed
2. Start the demo by showing HER OWN conversation with the AI \u2014 she'll love seeing it from the admin side
3. Focus on the restaurant-specific use case: order confirmations, delivery tracking, complaint management
4. Show the multi-language feature \u2014 they serve diverse communities in Berlin
5. Demo the CSAT survey \u2014 she mentioned wanting to track customer satisfaction
6. Show analytics: "Imagine seeing this data for your 200+ daily orders"
7. Pricing: She's Head of Operations, so focus on time/cost savings. Calculate: "If each customer inquiry takes 3 minutes manually, and you get 50 inquiries/day, that's 2.5 hours saved daily"
8. Push for the Professional plan \u2014 they need multi-channel + team features
9. She has authority to sign but needs CFO approval above \u20ac300/month""",
            talking_points=[
                "She used the AI chatbot herself on Instagram and was impressed",
                "UrbanBite does 200+ deliveries/day across 3 Berlin locations",
                "Current pain: 3 staff members spend 30% of their time on customer messages",
                "They use WhatsApp Business manually \u2014 wants to automate it",
                "Handles complaints in German, English, and Turkish \u2014 needs multilingual AI",
                "Competitor analysis: they tried Zendesk but found it too complex and expensive",
                "Budget range: \u20ac200-400/month, needs CFO approval above \u20ac300",
                "Decision timeline: wants to start pilot within 1 month",
            ],
            risk_factors="Needs CFO approval for budget above \u20ac300/month. Has 3 locations \u2014 may want location-specific setups which adds complexity. Previous bad experience with Zendesk \u2014 sensitive about complex onboarding.",
            estimated_deal_value="\u20ac350/month (Professional plan)",
            call_transcript="""AI Agent: Hi Sarah, this is the AI assistant from [Company]. We've been chatting on Instagram and you mentioned you'd be interested in a call.
Sarah: Yes! I have to say, your AI on Instagram was really impressive. I almost forgot I wasn't talking to a real person.
AI Agent: Thank you! That's exactly what we aim for. So you're running UrbanBite Food Delivery, right? Tell me more about how you currently handle customer communication.
Sarah: We have 3 locations in Berlin, about 200 deliveries a day. Right now we have 3 people just answering WhatsApp and Instagram messages. It's getting unsustainable.
AI Agent: That sounds like a lot of manual work. Our platform could automate most of those conversations. Would you be interested in a video demo with our sales manager? They can show you exactly how it would work for a food delivery business.
Sarah: Definitely. Can we do a 30-minute session? I want to see the full capabilities.
AI Agent: Absolutely. How about Thursday at 3 PM?
Sarah: Perfect, make it a video call. I'll have some questions about pricing and multi-location setup.
AI Agent: Noted! Our sales manager will send you a calendar invite. Thanks Sarah!
Sarah: Thank you, excited to see more!""",
            call_duration_seconds="98",
            call_id="hr_call_demo_002",
            assigned_to="",
            notes="",
        )
        session.add(meeting2)

        await session.commit()
        print("Demo meetings seeded: 2 meetings with full reports")
