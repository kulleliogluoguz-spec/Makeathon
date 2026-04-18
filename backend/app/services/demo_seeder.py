"""Seeds demo data — English customers, conversations, broadcasts."""

from datetime import datetime, timedelta
from sqlalchemy import select
from app.core.database import async_session
from app.models.customer import Customer
from app.models.conversation_state import ConversationState
from app.models.csat import CSATResponse
from app.models.broadcast import BroadcastCampaign


DEMO_CUSTOMERS = [
    {
        "display_name": "Emma Johnson",
        "email": "emma.johnson@gmail.com",
        "phone": "+1 415 829 1033",
        "source": "instagram",
        "handle": "@emmajohnson.style",
        "tags": ["vip", "returning"],
        "is_archived": False,
        "intent_score": 92,
        "stage": "purchase",
        "categories": ["high_sales_potential"],
        "response_mode": "ai_auto",
        "csat_rating": 5,
        "messages": [
            {"role": "user", "content": "Hey! Do you have any new arrivals this season?", "ts": -180},
            {"role": "assistant", "content": "Hi Emma! 😊 Yes, we just dropped some amazing new pieces! Our oversized tees and crop tops are flying off the shelves. What style are you into?", "ts": -179},
            {"role": "user", "content": "I'd love to check out the oversized tees. What's the price range?", "ts": -175},
            {"role": "assistant", "content": "Our oversized tees range from $29 to $45. The bestseller is the black premium cotton one at $35. Want me to check your size?", "ts": -174},
            {"role": "user", "content": "Size M in the black one — is it in stock?", "ts": -170},
            {"role": "assistant", "content": "Yes, size M is available! 🎉 Would you like to order? We have free shipping today!", "ts": -169},
            {"role": "user", "content": "Perfect, I'll take it!", "ts": -165},
            {"role": "assistant", "content": "Awesome! Sending you the order link now. It'll ship within 2 business days. Thanks Emma! 🛍️", "ts": -164},
            {"role": "user", "content": "Package arrived, absolutely love it! The quality is incredible 😍", "ts": -96},
            {"role": "assistant", "content": "So glad you love it! It's going to look amazing on you. Thanks for choosing us! 💛", "ts": -95},
            {"role": "user", "content": "5", "ts": -94},
            {"role": "assistant", "content": "Thank you for your wonderful feedback! 🙏", "ts": -93},
        ],
    },
    {
        "display_name": "James Mitchell",
        "email": "j.mitchell@techventures.io",
        "phone": "+44 20 7946 0958",
        "source": "telegram",
        "handle": "@jamesmitchell",
        "tags": ["business", "bulk"],
        "is_archived": False,
        "intent_score": 68,
        "stage": "consideration",
        "categories": ["sales_potential"],
        "response_mode": "ai_suggest",
        "csat_rating": 4,
        "messages": [
            {"role": "user", "content": "Hi, I'm looking for bulk orders for my company. Do you offer corporate pricing?", "ts": -120},
            {"role": "assistant", "content": "Hello James! Yes, we offer corporate pricing for bulk orders. Could you tell me more about what you need — quantity and product types?", "ts": -119},
            {"role": "user", "content": "We need about 50 branded t-shirts for our team event, with our company logo printed", "ts": -115},
            {"role": "assistant", "content": "That's great! We can do custom branded t-shirts. For 50 units, we offer a 25% discount from retail. Logo printing is included. Shall I send you a detailed quote?", "ts": -114},
            {"role": "user", "content": "Yes please, but I need to check with my business partner first. Can you email the quote?", "ts": -110},
            {"role": "assistant", "content": "Of course! I'll prepare a detailed quote with pricing, fabric options, and delivery timeline. I'll email it shortly. Take your time!", "ts": -109},
            {"role": "user", "content": "Got the quote, looks good. We're comparing with 2 other suppliers. Will get back to you this week.", "ts": -72},
            {"role": "assistant", "content": "Thank you for considering us, James! We're confident in our quality and pricing. Don't hesitate to reach out if you have questions!", "ts": -71},
            {"role": "user", "content": "4", "ts": -70},
            {"role": "assistant", "content": "Thank you for your feedback! 🙏", "ts": -69},
        ],
    },
    {
        "display_name": "Sarah Williams",
        "email": "sarah.w@outlook.com",
        "phone": "",
        "source": "messenger",
        "handle": "sarah.williams.88",
        "tags": [],
        "is_archived": False,
        "intent_score": 35,
        "stage": "awareness",
        "categories": ["no_sales_potential"],
        "response_mode": "ai_auto",
        "csat_rating": 2,
        "messages": [
            {"role": "user", "content": "Where are your products made?", "ts": -200},
            {"role": "assistant", "content": "Hi! Our products are made in our workshop in Portland, Oregon. We use 100% organic cotton. Any other questions?", "ts": -199},
            {"role": "user", "content": "Your prices are too high for me", "ts": -195},
            {"role": "assistant", "content": "Our prices reflect premium quality materials and craftsmanship. We do have budget-friendly options in our basics collection starting at $19. Want me to show you?", "ts": -194},
            {"role": "user", "content": "No thanks, I found something cheaper elsewhere", "ts": -190},
            {"role": "assistant", "content": "I understand! You're always welcome back. Have a great day! 😊", "ts": -189},
            {"role": "user", "content": "2", "ts": -188},
            {"role": "assistant", "content": "Thank you for your feedback. We'll work to improve! 🙏", "ts": -187},
        ],
    },
    {
        "display_name": "Laura Chen",
        "email": "laura.chen@designstudio.co",
        "phone": "+1 628 555 7721",
        "source": "livechat",
        "handle": "",
        "tags": ["newsletter", "international"],
        "is_archived": False,
        "intent_score": 78,
        "stage": "decision",
        "categories": ["high_sales_potential"],
        "response_mode": "ai_auto",
        "csat_rating": 5,
        "messages": [
            {"role": "user", "content": "Hello! I found you through Instagram. Do you ship internationally?", "ts": -48},
            {"role": "assistant", "content": "Hi Laura! Yes, we ship worldwide! Standard international delivery takes 5-7 business days. Free shipping on orders over $60. What are you looking for?", "ts": -47},
            {"role": "user", "content": "I love the green oversized hoodie! Is it available in size S?", "ts": -46},
            {"role": "assistant", "content": "Great taste! The green oversized hoodie is one of our bestsellers. Size S is in stock! It's $49.90 — you're close to free shipping, maybe add something small?", "ts": -45},
            {"role": "user", "content": "Smart! What would you recommend to go with it?", "ts": -44},
            {"role": "assistant", "content": "I'd pair it with our matching beanie ($12.90) or the canvas tote bag ($14.90). Both are super popular combos! Total would be around $63-65 with free shipping.", "ts": -43},
            {"role": "user", "content": "Love it, I'll take the hoodie + beanie combo! How do I order?", "ts": -42},
            {"role": "assistant", "content": "Awesome choice! 🎉 Sending you the order link now. Total: $62.80 with free international shipping. You'll get a tracking number once it ships!", "ts": -41},
            {"role": "user", "content": "Everything arrived perfectly! The quality is amazing, you've got a loyal customer now!", "ts": -10},
            {"role": "assistant", "content": "That means so much to us, Laura! We're so glad you love it. Welcome to the family! 💚", "ts": -9},
            {"role": "user", "content": "5", "ts": -8},
            {"role": "assistant", "content": "Thank you for your wonderful feedback! 🙏", "ts": -7},
        ],
    },
    {
        "display_name": "Ryan Cooper",
        "email": "ryan.cooper@hotmail.com",
        "phone": "+1 312 555 9876",
        "source": "whatsapp",
        "handle": "",
        "tags": ["complaint"],
        "is_archived": True,
        "intent_score": 15,
        "stage": "objection",
        "categories": ["no_sales_potential"],
        "response_mode": "human_only",
        "csat_rating": 1,
        "messages": [
            {"role": "user", "content": "I ordered a week ago and still haven't received my package", "ts": -168},
            {"role": "assistant", "content": "Hi Ryan, I'm sorry about the delay. Could you share your order number? I'll check the shipping status right away.", "ts": -167},
            {"role": "user", "content": "ORD-29481", "ts": -166},
            {"role": "assistant", "content": "I've checked — your package was shipped yesterday and is currently in transit. It should arrive tomorrow. Tracking number: US84729104. Sorry again for the delay!", "ts": -165},
            {"role": "user", "content": "It arrived but you sent the wrong size. I ordered L and got M.", "ts": -144},
            {"role": "assistant", "content": "I'm really sorry! That's our mistake. I'm starting the exchange process immediately. I'll send you a free return label, and we'll ship the correct size ASAP.", "ts": -143},
            {"role": "user", "content": "It's been 3 weeks and I still haven't received the replacement. This is terrible service. Never shopping here again.", "ts": -72},
            {"role": "assistant", "content": "Ryan, this is unacceptable and I sincerely apologize. I'm escalating this to a manager right now to get this resolved immediately.", "ts": -71},
            {"role": "user", "content": "1", "ts": -70},
            {"role": "assistant", "content": "Thank you for your feedback. We'll work to improve! 🙏", "ts": -69},
        ],
    },
]


async def seed_demo_data():
    """Insert demo customers, conversations, CSAT and broadcasts if not already present."""
    async with async_session() as session:
        # Check if demo data already exists
        result = await session.execute(
            select(Customer).where(Customer.display_name == "Emma Johnson")
        )
        if result.scalar_one_or_none():
            return  # Already seeded

        now = datetime.utcnow()

        for i, cust_data in enumerate(DEMO_CUSTOMERS):
            sender_id = f"demo_sender_{i+1}"

            # Create customer
            customer = Customer(
                display_name=cust_data["display_name"],
                email=cust_data["email"],
                phone=cust_data["phone"],
                source=cust_data["source"],
                handle=cust_data["handle"],
                tags=cust_data["tags"],
                is_archived=cust_data["is_archived"],
                instagram_sender_id=sender_id if cust_data["source"] == "instagram" else "",
                last_contact_at=now + timedelta(minutes=cust_data["messages"][-1]["ts"]),
                total_messages=str(len(cust_data["messages"])),
                created_at=now + timedelta(minutes=cust_data["messages"][0]["ts"]),
            )
            session.add(customer)

            # Build message list with timestamps
            messages = []
            for msg in cust_data["messages"]:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"],
                    "timestamp": (now + timedelta(minutes=msg["ts"])).isoformat(),
                })

            # Create conversation state
            conv_state = ConversationState(
                sender_id=sender_id,
                channel=cust_data["source"],
                intent_score=cust_data["intent_score"],
                stage=cust_data["stage"],
                categories=cust_data["categories"],
                response_mode=cust_data["response_mode"],
                messages=messages,
                message_count=len(messages),
                last_message_at=now + timedelta(minutes=cust_data["messages"][-1]["ts"]),
                created_at=now + timedelta(minutes=cust_data["messages"][0]["ts"]),
            )
            session.add(conv_state)

            # Create CSAT response
            if cust_data.get("csat_rating"):
                csat = CSATResponse(
                    conversation_id=sender_id,
                    sender_id=sender_id,
                    channel=cust_data["source"],
                    rating=cust_data["csat_rating"],
                    created_at=now + timedelta(minutes=cust_data["messages"][-2]["ts"]),
                )
                session.add(csat)

        # Create demo broadcast campaigns
        campaign1 = BroadcastCampaign(
            name="Spring Collection Launch",
            subject="🌸 Our Spring Collection Just Dropped!",
            message="Hey! Our new spring collection is here — fresh styles, lightweight fabrics, and colors you'll love. Check it out and enjoy 15% off with code SPRING15. Shop now before your favorites sell out!",
            channels=["email", "telegram"],
            recipient_filter={},
            recipient_count=4,
            sent_count=3,
            failed_count=1,
            status="sent",
            results=[
                {"customer_id": "demo1", "channel": "email", "status": "sent"},
                {"customer_id": "demo2", "channel": "email", "status": "sent"},
                {"customer_id": "demo3", "channel": "email", "status": "failed", "error": "No email address"},
                {"customer_id": "demo4", "channel": "email", "status": "sent"},
            ],
            sent_at=now - timedelta(days=5),
            created_at=now - timedelta(days=5),
        )
        session.add(campaign1)

        campaign2 = BroadcastCampaign(
            name="Customer Feedback Survey",
            subject="📝 We'd love your feedback!",
            message="Hi! We're always looking to improve. Could you take 30 seconds to tell us about your recent experience? Your feedback helps us serve you better. Reply with a rating from 1-5!",
            channels=["email"],
            recipient_filter={"category": "high_sales_potential"},
            recipient_count=2,
            sent_count=2,
            failed_count=0,
            status="sent",
            results=[
                {"customer_id": "demo1", "channel": "email", "status": "sent"},
                {"customer_id": "demo4", "channel": "email", "status": "sent"},
            ],
            sent_at=now - timedelta(days=2),
            created_at=now - timedelta(days=2),
        )
        session.add(campaign2)

        campaign3 = BroadcastCampaign(
            name="Summer Sale Preview",
            subject="☀️ Summer Sale starts tomorrow!",
            message="Get ready! Our biggest summer sale starts tomorrow. Up to 40% off selected items. VIP customers get early access — that's you! Click the link to browse early.",
            channels=["email", "telegram"],
            recipient_filter={},
            status="draft",
            created_at=now - timedelta(hours=3),
        )
        session.add(campaign3)

        await session.commit()
        print("Demo data seeded successfully!")
