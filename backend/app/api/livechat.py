"""Live chat WebSocket endpoint + widget serving."""

import os
import json
import uuid
from datetime import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, FileResponse
from dotenv import load_dotenv
import httpx

load_dotenv()

router = APIRouter()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Active WebSocket connections: {session_id: websocket}
active_connections = {}

# In-memory session store: {session_id: {messages: [], persona_id: str, visitor_name: str}}
chat_sessions = {}


@router.get("/widget/chat.js")
async def serve_widget_js(request: Request):
    """Serve the embeddable chat widget JavaScript."""
    base_url = os.getenv("PUBLIC_BASE_URL", f"{request.url.scheme}://{request.url.netloc}")
    ws_url = base_url.replace("https://", "wss://").replace("http://", "ws://")

    js = f"""
(function() {{
  if (window.__livechat_loaded) return;
  window.__livechat_loaded = true;

  var personaId = document.currentScript ? document.currentScript.getAttribute('data-persona-id') || '' : '';
  var baseUrl = '{base_url}';
  var wsUrl = '{ws_url}';
  var sessionId = 'lc_' + Math.random().toString(36).substr(2, 12);
  var messages = [];
  var isOpen = false;
  var ws = null;
  var visitorName = '';

  // Styles
  var style = document.createElement('style');
  style.textContent = `
    #lc-bubble {{
      position: fixed; bottom: 24px; right: 24px; z-index: 99999;
      width: 60px; height: 60px; border-radius: 50%;
      background: #000; color: #fff; border: none; cursor: pointer;
      font-size: 24px; display: flex; align-items: center; justify-content: center;
      box-shadow: 0 4px 12px rgba(0,0,0,0.15); transition: transform 0.2s;
    }}
    #lc-bubble:hover {{ transform: scale(1.1); }}
    #lc-panel {{
      position: fixed; bottom: 100px; right: 24px; z-index: 99999;
      width: 380px; height: 520px; background: #fff;
      border-radius: 16px; box-shadow: 0 8px 30px rgba(0,0,0,0.12);
      display: none; flex-direction: column; overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      border: 1px solid #e5e7eb;
    }}
    #lc-panel.open {{ display: flex; }}
    #lc-header {{
      padding: 16px 20px; background: #000; color: #fff;
      display: flex; justify-content: space-between; align-items: center;
    }}
    #lc-header-title {{ font-weight: 600; font-size: 15px; }}
    #lc-header-sub {{ font-size: 12px; opacity: 0.7; }}
    #lc-close {{ background: none; border: none; color: #fff; font-size: 20px; cursor: pointer; padding: 0; }}
    #lc-messages {{
      flex: 1; overflow-y: auto; padding: 16px;
      display: flex; flex-direction: column; gap: 8px;
    }}
    .lc-msg {{
      max-width: 85%; padding: 10px 14px; border-radius: 12px;
      font-size: 14px; line-height: 1.4; word-wrap: break-word;
    }}
    .lc-msg.user {{
      align-self: flex-end; background: #000; color: #fff;
      border-bottom-right-radius: 4px;
    }}
    .lc-msg.ai {{
      align-self: flex-start; background: #f3f4f6; color: #111;
      border-bottom-left-radius: 4px;
    }}
    .lc-msg.system {{
      align-self: center; font-size: 12px; color: #9ca3af;
      background: none; padding: 4px;
    }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    .lc-typing {{
      align-self: flex-start; padding: 10px 14px;
      background: #f3f4f6; border-radius: 12px;
      font-size: 13px; color: #9ca3af;
    }}
    #lc-input-area {{
      padding: 12px 16px; border-top: 1px solid #e5e7eb;
      display: flex; gap: 8px;
    }}
    #lc-input {{
      flex: 1; padding: 10px 14px; border: 1px solid #e5e7eb;
      border-radius: 9999px; font-size: 14px; outline: none;
    }}
    #lc-input:focus {{ border-color: #000; }}
    #lc-send {{
      width: 40px; height: 40px; border-radius: 50%;
      background: #000; color: #fff; border: none; cursor: pointer;
      font-size: 16px; display: flex; align-items: center; justify-content: center;
    }}
    #lc-send:disabled {{ opacity: 0.3; cursor: default; }}
    #lc-name-form {{
      padding: 24px; display: flex; flex-direction: column;
      align-items: center; justify-content: center; flex: 1;
    }}
    #lc-name-form h3 {{
      font-size: 16px; font-weight: 600; margin-bottom: 4px;
    }}
    #lc-name-form p {{
      font-size: 13px; color: #6b7280; margin-bottom: 16px;
    }}
    #lc-name-input {{
      width: 100%; padding: 10px 14px; border: 1px solid #e5e7eb;
      border-radius: 9999px; font-size: 14px; outline: none;
      margin-bottom: 12px; text-align: center;
    }}
    #lc-name-btn {{
      padding: 10px 24px; background: #000; color: #fff;
      border: none; border-radius: 9999px; font-size: 14px;
      cursor: pointer;
    }}
  `;
  document.head.appendChild(style);

  // Create bubble
  var bubble = document.createElement('button');
  bubble.id = 'lc-bubble';
  bubble.innerHTML = '&#128172;';
  bubble.onclick = function() {{ togglePanel(); }};
  document.body.appendChild(bubble);

  // Create panel
  var panel = document.createElement('div');
  panel.id = 'lc-panel';
  panel.innerHTML = `
    <div id="lc-header">
      <div>
        <div id="lc-header-title">Chat with us</div>
        <div id="lc-header-sub">We typically reply instantly</div>
      </div>
      <button id="lc-close" onclick="document.getElementById('lc-panel').classList.remove('open')">&times;</button>
    </div>
    <div id="lc-name-form">
      <h3>Welcome!</h3>
      <p>Enter your name to start chatting</p>
      <input id="lc-name-input" type="text" placeholder="Your name..." />
      <button id="lc-name-btn" onclick="window.__lc_start_chat()">Start Chat</button>
    </div>
    <div id="lc-messages" style="display:none;"></div>
    <div id="lc-input-area" style="display:none;">
      <input id="lc-input" type="text" placeholder="Type a message..." />
      <button id="lc-send" onclick="window.__lc_send()">&#9654;</button>
    </div>
  `;
  document.body.appendChild(panel);

  // Enter key support
  setTimeout(function() {{
    var input = document.getElementById('lc-input');
    if (input) input.addEventListener('keydown', function(e) {{
      if (e.key === 'Enter') window.__lc_send();
    }});
    var nameInput = document.getElementById('lc-name-input');
    if (nameInput) nameInput.addEventListener('keydown', function(e) {{
      if (e.key === 'Enter') window.__lc_start_chat();
    }});
  }}, 100);

  function togglePanel() {{
    panel.classList.toggle('open');
  }}

  window.__lc_start_chat = function() {{
    visitorName = document.getElementById('lc-name-input').value.trim() || 'Visitor';
    document.getElementById('lc-name-form').style.display = 'none';
    document.getElementById('lc-messages').style.display = 'flex';
    document.getElementById('lc-input-area').style.display = 'flex';
    connectWs();
  }};

  function connectWs() {{
    ws = new WebSocket(wsUrl + '/ws/chat?session_id=' + sessionId + '&persona_id=' + personaId + '&visitor_name=' + encodeURIComponent(visitorName));

    ws.onopen = function() {{
      addMessage('system', 'Connected! How can we help you?');
    }};

    ws.onmessage = function(event) {{
      var data = JSON.parse(event.data);
      if (data.type === 'reply') {{
        removeTyping();
        addMessage('ai', data.text);
        if (data.images && data.images.length > 0) {{
          data.images.forEach(function(url) {{
            addImage('ai', url);
          }});
        }}
        if (data.calling) {{
          addMessage('system', '📞 Connecting your call now...');
          var loader = document.createElement('div');
          loader.className = 'lc-msg system';
          loader.id = 'lc-call-loader';
          loader.innerHTML = '<div style="display:flex;align-items:center;gap:8px;"><div style="width:12px;height:12px;border:2px solid #000;border-top-color:transparent;border-radius:50%;animation:spin 1s linear infinite;"></div> Calling you now...</div>';
          document.getElementById('lc-messages').appendChild(loader);
        }}
      }}
    }};

    ws.onclose = function() {{
      addMessage('system', 'Connection closed. Refresh to reconnect.');
    }};

    ws.onerror = function() {{
      addMessage('system', 'Connection error. Please try again.');
    }};
  }}

  window.__lc_send = function() {{
    var input = document.getElementById('lc-input');
    var text = input.value.trim();
    if (!text || !ws || ws.readyState !== WebSocket.OPEN) return;
    input.value = '';
    addMessage('user', text);
    addTyping();
    ws.send(JSON.stringify({{ type: 'message', text: text }}));
  }};

  function addMessage(role, text) {{
    var container = document.getElementById('lc-messages');
    var div = document.createElement('div');
    div.className = 'lc-msg ' + role;
    div.textContent = text;
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  }}

  function addImage(role, url) {{
    var container = document.getElementById('lc-messages');
    var div = document.createElement('div');
    div.className = 'lc-msg ' + role;
    div.innerHTML = '<img src="' + url + '" style="max-width:100%;border-radius:8px;" />';
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  }}

  function addTyping() {{
    var container = document.getElementById('lc-messages');
    var div = document.createElement('div');
    div.className = 'lc-typing';
    div.id = 'lc-typing-indicator';
    div.textContent = 'Typing...';
    container.appendChild(div);
    container.scrollTop = container.scrollHeight;
  }}

  function removeTyping() {{
    var el = document.getElementById('lc-typing-indicator');
    if (el) el.remove();
  }}
}})();
"""
    return HTMLResponse(content=js, media_type="application/javascript")


@router.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket, session_id: str = "", persona_id: str = "", visitor_name: str = "Visitor"):
    await websocket.accept()

    if not session_id:
        session_id = f"lc_{uuid.uuid4().hex[:12]}"

    active_connections[session_id] = websocket
    chat_sessions[session_id] = {
        "messages": [],
        "persona_id": persona_id,
        "visitor_name": visitor_name,
        "created_at": datetime.utcnow().isoformat(),
    }

    try:
        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)

            if data.get("type") == "message":
                user_text = data.get("text", "").strip()
                if not user_text:
                    continue

                # Check for negative signals and trigger learning
                negative_keywords = ["not interested", "no thanks", "too expensive", "stop", "unsubscribe", "terrible", "worst", "never again", "waste of time", "horrible service"]
                if any(kw in user_text.lower() for kw in negative_keywords):
                    try:
                        from app.services.ai_learning import trigger_learning_on_negative_signal
                        import asyncio
                        asyncio.create_task(trigger_learning_on_negative_signal(session_id, "negative_reaction", "livechat"))
                    except Exception:
                        pass

                # Save user message
                chat_sessions[session_id]["messages"].append({
                    "role": "user",
                    "content": user_text,
                })

                # Generate AI reply
                reply_text, product_images, recommend_ids, all_products, trigger_call, call_number = await generate_livechat_reply(
                    session_id=session_id,
                    persona_id=persona_id,
                    user_message=user_text,
                    history=chat_sessions[session_id]["messages"],
                    visitor_name=visitor_name,
                )

                # Save AI reply
                chat_sessions[session_id]["messages"].append({
                    "role": "assistant",
                    "content": reply_text,
                })

                # Save to database
                await save_livechat_to_db(session_id, persona_id, visitor_name, chat_sessions[session_id]["messages"])

                # Send reply
                response = {"type": "reply", "text": reply_text}
                if product_images:
                    response["images"] = product_images
                if trigger_call and call_number:
                    response["calling"] = True
                    response["call_number"] = call_number
                    import asyncio
                    asyncio.create_task(_handle_happyrobot_call_livechat(session_id, call_number, visitor_name))
                await websocket.send_text(json.dumps(response))

                # Auto-trigger try-on for first recommended product
                if recommend_ids and all_products:
                    first_product = next((p for p in all_products if p["id"] == recommend_ids[0]), None)
                    if first_product and first_product.get("image_url"):
                        import asyncio
                        asyncio.create_task(_handle_tryon_async_livechat(websocket, session_id, first_product))

    except WebSocketDisconnect:
        active_connections.pop(session_id, None)
    except Exception as e:
        print(f"LiveChat WS error: {e}")
        active_connections.pop(session_id, None)


async def generate_livechat_reply(session_id: str, persona_id: str, user_message: str, history: list, visitor_name: str):
    """Generate AI reply using persona + catalog. Returns (reply_text, product_image_urls)."""
    product_images = []

    # Load persona
    system_prompt = "You are a helpful assistant on a live chat widget. Be concise and friendly. Keep responses to 2-3 sentences."
    try:
        from app.core.database import async_session
        from app.models.models import Persona
        from sqlalchemy import select

        async with async_session() as session:
            if persona_id:
                result = await session.execute(select(Persona).where(Persona.id == persona_id))
            else:
                result = await session.execute(select(Persona).order_by(Persona.updated_at.desc()).limit(1))
            persona = result.scalar_one_or_none()
            if persona and persona.system_prompt:
                system_prompt = persona.system_prompt
            persona_db_id = persona.id if persona else None
    except Exception as e:
        print(f"Persona load error: {e}")
        persona_db_id = None

    # Load products
    products_text = ""
    products = []
    try:
        from app.models.catalog_models import Catalog, Product
        from sqlalchemy import select as sel, and_
        async with async_session() as session:
            result = await session.execute(
                sel(Product).join(Catalog).where(
                    and_(Catalog.persona_id == persona_db_id, Catalog.enabled == "true")
                )
            )
            products = [
                {"id": p.id, "name": p.name, "description": p.description,
                 "price": p.price, "tags": p.tags or [], "image_url": p.image_url}
                for p in result.scalars().all()
            ]
    except Exception as e:
        print(f"Product load error: {e}")

    if products:
        products_text = "\n\n## PRODUCT CATALOG\nYou have a product catalog. When you put product IDs in recommend_product_ids, the system will AUTOMATICALLY send the product images to the customer.\n\nAvailable products:\n\n"
        for p in products:
            products_text += f"ID: {p['id']}\nName: {p['name']}\nPrice: {p['price']}\nDescription: {p['description']}\nTags: {', '.join(p['tags'])}\n\n"
        products_text += '\nYou MUST respond in this JSON format: {"message": "your reply text", "recommend_product_ids": ["id1", "id2"]}\nRULES:\n- If the customer asks about ANY product, category, or shows interest, you MUST include 1-3 matching product IDs in recommend_product_ids.\n- NEVER say you cannot send images. The system sends them automatically when you include IDs.\n- Only use an empty recommend_product_ids [] for pure greetings with zero product context.'

    # Intent scoring context
    scoring_context = ""
    try:
        from app.services.intent_scorer import score_conversation
        scoring = await score_conversation(history)
        scoring_context = f"\n\n## CUSTOMER STATE\nIntent Score: {scoring['intent_score']}/100\nStage: {scoring['stage']}\nRecommended tone: {scoring['recommended_tone']}\nNext action: {scoring['next_action']}"
    except Exception as e:
        print(f"Scoring error: {e}")

    # Load quick reply templates
    quick_replies_text = ""
    try:
        from app.models.quick_reply import QuickReply
        from sqlalchemy import select as sel3
        async with async_session() as session:
            qr_result = await session.execute(sel3(QuickReply))
            qr_list = qr_result.scalars().all()
            if qr_list:
                quick_replies_text = "\n\n## PREDEFINED Q&A\nBelow are predefined question-answer pairs. When the customer asks about any of these topics, use the provided answer as your source of truth. IMPORTANT: The answers below may be written in a different language than the customer is using. You MUST translate the answer into the customer's language while keeping the exact same meaning and information. Do NOT change the facts — only translate.\n\n"
                for qr in qr_list:
                    quick_replies_text += f"QUESTION: {qr.title}\nANSWER: {qr.content}\n\n"
    except Exception as e:
        print(f"Quick replies load error: {e}")

    # Add phone call offer instruction for high intent
    call_offer_text = ""
    if scoring_context:
        try:
            score = scoring.get("intent_score", 0)
            if score >= 70:
                call_offer_text = """

## PHONE CALL OFFER
The customer's intent score is high (70+). They are very interested in buying. You should naturally offer them a phone call to help complete their purchase. Here's how:

1. FIRST, naturally mention: "If you'd like, we can call you right now to help you with your purchase — it'll only take a minute!"
2. If they say yes, ask: "Would you like us to call you, or would you prefer our number so you can call us?"
3. If they want YOU to call THEM, say: "Great! Just share your phone number and we'll call you right away! 📞"
4. When the customer provides a phone number, respond with EXACTLY this JSON format:
   {"message": "Perfect! We're calling you right now! 📞", "recommend_product_ids": [], "trigger_call": true, "call_number": "+XXXXXXXXXXX"}
   Replace +XXXXXXXXXXX with the actual phone number they provided. Make sure to include country code.
5. IMPORTANT: Only set trigger_call to true when the customer has EXPLICITLY provided their phone number.
6. Do NOT offer to call if you already offered in this conversation.
"""
        except Exception:
            pass

    # Self-learning: inject lessons from past conversations
    try:
        from app.services.ai_learning import get_lessons_for_prompt
        lessons_text = await get_lessons_for_prompt()
    except Exception:
        lessons_text = ""

    full_prompt = system_prompt + products_text + scoring_context + call_offer_text + quick_replies_text + lessons_text

    # Call LLM
    try:
        last_user_text = ""
        for m in reversed(history):
            if m.get("role") == "user":
                last_user_text = m.get("content", "")
                break
        language_override = {"role": "system", "content": f"OVERRIDE: The customer wrote: '{last_user_text}'. You MUST reply in the same language as this text. If this is English, your entire reply must be in English. If Turkish, reply in Turkish. NO EXCEPTIONS."}
        messages = [{"role": "system", "content": full_prompt}, language_override] + [
            {"role": m["role"], "content": m["content"]} for m in history[-20:]
        ]

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"},
                json={"model": "gpt-4.1-nano", "messages": messages, "temperature": 0.7, "max_tokens": 300},
            )
            resp.raise_for_status()
            reply_raw = resp.json()["choices"][0]["message"]["content"]

        # Parse product recommendations
        reply_text = reply_raw
        recommend_ids = []
        if products:
            try:
                parsed = json.loads(reply_raw)
                reply_text = parsed.get("message", reply_raw)
                recommend_ids = parsed.get("recommend_product_ids", [])
            except (json.JSONDecodeError, TypeError):
                reply_text = reply_raw

        # Detect phone call trigger
        trigger_call = False
        call_number = ""
        if products:
            try:
                if isinstance(parsed, dict):
                    trigger_call = parsed.get("trigger_call", False)
                    call_number = parsed.get("call_number", "")
            except Exception:
                pass

        # Get image URLs for recommended products
        for pid in recommend_ids[:3]:
            prod = next((p for p in products if p["id"] == pid), None)
            if prod and prod.get("image_url"):
                product_images.append(prod["image_url"])

        return reply_text, product_images, recommend_ids, products, trigger_call, call_number

    except Exception as e:
        print(f"LLM error: {e}")
        return "Sorry, I'm having a technical issue. Please try again!", [], [], [], False, ""


async def _handle_happyrobot_call_livechat(session_id: str, phone_number: str, visitor_name: str):
    """Background task: trigger HappyRobot outbound call for LiveChat."""
    try:
        from app.services.happyrobot_service import trigger_outbound_call
        import asyncio
        await asyncio.sleep(2)

        recent_msgs = chat_sessions.get(session_id, {}).get("messages", [])[-5:]
        context = " | ".join([f"{m['role']}: {m['content'][:50]}" for m in recent_msgs])

        result = await trigger_outbound_call(
            phone_number=phone_number,
            customer_name=visitor_name,
            context=f"Customer was chatting on LiveChat and showed high buying intent. Recent conversation: {context}",
        )

        if result.get("success"):
            print(f"HappyRobot call initiated for livechat {session_id}: {result.get('call_id')}")
        else:
            print(f"HappyRobot call failed for livechat {session_id}: {result.get('error')}")

    except Exception as e:
        print(f"HappyRobot livechat call error: {e}")


async def _handle_tryon_async_livechat(websocket: WebSocket, session_id: str, product: dict):
    """Background task: generate try-on image + video and send via WebSocket."""
    try:
        from app.services.fashn_service import product_to_model, image_to_video

        model_result = await product_to_model(product["image_url"])
        if model_result["success"]:
            await websocket.send_text(json.dumps({
                "type": "reply",
                "text": "",
                "images": [model_result["image_url"]],
            }))

            video_result = await image_to_video(model_result["image_url"])
            if video_result["success"]:
                await websocket.send_text(json.dumps({
                    "type": "reply",
                    "text": "",
                    "video": video_result["video_url"],
                }))
            else:
                print(f"Video generation failed: {video_result['error']}")
        else:
            print(f"Try-on failed: {model_result['error']}")
    except Exception as e:
        print(f"Try-on async error: {e}")


async def save_livechat_to_db(session_id: str, persona_id: str, visitor_name: str, messages: list):
    """Save livechat conversation to ConversationState + Customer tables."""
    try:
        from app.core.database import async_session
        from app.models.conversation_state import ConversationState
        from app.models.customer import Customer
        from sqlalchemy import select
        from datetime import datetime

        async with async_session() as session:
            # Upsert ConversationState
            result = await session.execute(
                select(ConversationState).where(ConversationState.sender_id == session_id)
            )
            state = result.scalar_one_or_none()

            if not state:
                state = ConversationState(
                    sender_id=session_id,
                    persona_id=persona_id,
                    channel="livechat",
                    messages=[],
                    score_history=[],
                    signals=[],
                    products_mentioned=[],
                    categories=[],
                )
                session.add(state)

            # Update messages
            state.messages = [
                {"role": m["role"], "content": m["content"], "timestamp": datetime.utcnow().isoformat()}
                for m in messages[-100:]
            ]
            state.message_count = len(messages)
            state.last_message_at = datetime.utcnow()
            state.updated_at = datetime.utcnow()

            # Score and tag
            try:
                from app.services.intent_scorer import score_conversation
                from app.services.category_tagger import auto_tag_conversation

                scoring = await score_conversation(messages[-20:])
                state.intent_score = scoring.get("intent_score", 0)
                state.stage = scoring.get("stage", "awareness")
                state.signals = scoring.get("signals", [])
                state.next_action = scoring.get("next_action", "")
                state.score_breakdown = scoring.get("score_breakdown", "")

                tags = await auto_tag_conversation(messages[-10:])
                if tags:
                    state.categories = tags
            except Exception as e:
                print(f"Scoring/tagging error: {e}")

            await session.commit()

            # Upsert Customer
            cust_result = await session.execute(
                select(Customer).where(Customer.instagram_sender_id == session_id)
            )
            customer = cust_result.scalar_one_or_none()

            if not customer:
                customer = Customer(
                    display_name=visitor_name,
                    handle="",
                    source="livechat",
                    instagram_sender_id=session_id,
                    last_contact_at=datetime.utcnow(),
                    total_messages=str(len(messages)),
                )
                session.add(customer)
            else:
                customer.last_contact_at = datetime.utcnow()
                customer.total_messages = str(len(messages))
                if customer.is_archived:
                    customer.is_archived = False

            await session.commit()

    except Exception as e:
        print(f"DB save error: {e}")
