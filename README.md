# Clerque

An AI-powered customer engagement platform that automates lead generation, outreach, phone calls, and meeting scheduling — all from a single dashboard.

## Features

### AI Lead Generation & Outreach
- **AI Lead Finder**: Search the web for potential customers using OpenAI, generate Ideal Customer Profiles (ICP) from persona data, AI-score leads 0-100
- **Preset Filters**: One-click search presets (German Startups, DACH E-Commerce, Digital Agencies, Restaurants)
- **LinkedIn Integration (Unipile)**: Search real LinkedIn profiles, send connection requests with personalized notes, send direct messages
- **Auto-Call Top Leads**: Batch-call high-scoring leads via HappyRobot AI — if no phone, falls back to LinkedIn invite
- **AI Outreach Messages**: Generate personalized outreach for LinkedIn, Email, WhatsApp with landing page URL included
- **Auto Landing Page**: After every lead search, Claude AI auto-generates a custom landing page for the top lead, auto-deploys to Netlify with live URL

### AI Phone Calls (HappyRobot)
- **Outbound AI Calls**: Full call script with persona context, email offer, meeting scheduling with available time slots
- **Auto-Call Offer**: When customer intent score hits 70+ in any channel, AI naturally offers a phone call
- **Auto-Trigger at 90+**: Automatically calls customers with very high buying intent
- **Webhook Integration**: Call transcripts auto-saved to conversations, meetings auto-created, follow-up emails auto-sent
- **Call Context**: AI introduces company, pitches services, offers email, schedules meeting — all in under 3 minutes

### Meeting Calendar & Reports
- **Calendar View**: All scheduled meetings from AI outreach calls
- **AI Meeting Reports**: Conversation summary, recommended approach, key talking points, risk factors, estimated deal value
- **Call Transcripts**: Full AI call transcripts attached to each meeting
- **Status Management**: scheduled, completed, cancelled, no_show

### AI Self-Learning + Cognee Knowledge Graph
- **Learns from Mistakes**: After negative customer reactions (low CSAT, complaints, lost customers), AI analyzes what went wrong
- **Lesson Database**: Stores mistakes with categories, better alternatives, and importance weights (SQLite)
- **Cognee Knowledge Graph**: All lessons, conversations, and customer interactions stored in Cognee's persistent knowledge graph via `cognee.remember()`
- **Graph-Based Recall**: Before every AI response, relevant lessons recalled from Cognee via `cognee.recall()` — structured, graph-connected memory
- **Auto-Improves**: Lessons from both SQLite and Cognee injected into AI prompts — the AI gets better with every conversation
- **Customer Memory**: Every interaction stored in Cognee — AI remembers past conversations with returning customers
- **Triggers**: Low CSAT (1-2), negative keywords, customer archived, complaint detected

### Customer Engagement (Multi-Channel)
- **Persona Builder**: 8 personality traits, communication style, emotional responses, auto-generated system prompts
- **Omnichannel AI**: Instagram, Telegram, Messenger, WhatsApp, Live Chat — all with AI auto-responses
- **Intent Scoring**: Real-time customer intent scoring (0-100) with stage tracking
- **Customer CRM**: Unified customer database across all channels with tags, notes, categories
- **Conversations Dashboard**: Live view of all customer conversations with customer names, intent scores, categories
- **CSAT Surveys**: Automatic customer satisfaction tracking
- **Quick Replies**: Predefined Q&A templates for common questions

### Landing Page Creator
- **AI Generation**: Claude API generates full production-ready HTML landing pages
- **Style Options**: Modern, Minimal, Bold, Corporate, Creative, Startup
- **Live Preview**: Desktop, tablet, mobile preview with iframe
- **Refine with AI**: Chat-based refinement — "make the hero bigger", "change colors to blue"
- **Netlify Deploy**: One-click deploy to Netlify with live URL
- **Download HTML**: Export as standalone HTML file

### Frontend (React + Vite)
- **Personas**: Create and manage AI agent personas with personality sliders
- **Conversations**: Live customer conversations with names, intent scores, channel icons (📷 Instagram, 📞 Phone, ✈️ Telegram, 💬 Messenger)
- **Customers**: Unified CRM with filters, categories, search
- **Lead Finder**: Search, score, call, draft outreach, auto-generate landing pages
- **Meetings**: Calendar with full AI-generated meeting reports
- **Settings**: Business hours, auto-reply, meeting availability, live chat widget

## Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Dashboard: http://localhost:5173
API: http://localhost:8000
API Docs: http://localhost:8000/docs

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/agents/` | GET, POST | List/create agents |
| `/api/v1/agents/{id}` | GET, PATCH, DELETE | Agent details/update/delete |
| `/api/v1/agents/{id}/duplicate` | POST | Duplicate agent |
| `/api/v1/personas/` | GET, POST | List/create personas |
| `/api/v1/personas/{id}/generate-system-prompt` | POST | Auto-generate system prompt |
| `/api/v1/workflows/` | GET, POST | List/create workflows |
| `/api/v1/workflows/{id}` | GET, PATCH, DELETE | Update workflow (node/edge sync) |
| `/api/v1/workflows/{id}/activate` | POST | Activate workflow |
| `/api/v1/workflows/{id}/nodes` | POST | Add node |
| `/api/v1/workflows/{id}/edges` | POST | Add edge |
| `/api/v1/workflows/templates/list` | GET | Ready-made templates |
| `/api/v1/conversations/` | GET, POST | List/start conversations |
| `/api/v1/conversations/ws/{id}` | WebSocket | Real-time voice conversation |
| `/api/v1/conversations/analytics/summary` | GET | Statistics |
| `/api/v1/companies/` | GET, POST | List/create companies |
| `/api/v1/knowledge/` | GET, POST | Knowledge base CRUD |
| `/api/v1/knowledge/search` | POST | Knowledge base search |
| `/api/v1/leads/generate-icp` | POST | Generate Ideal Customer Profile from persona |
| `/api/v1/leads/search` | POST | Search for leads via AI web search |
| `/api/v1/leads/save` | POST | Save a lead |
| `/api/v1/leads/saved` | GET | List saved leads |
| `/api/v1/leads/saved/{id}` | PATCH, DELETE | Update/delete saved lead |
| `/api/v1/leads/outreach-message` | POST | Generate outreach message |
| `/api/v1/leads/auto-call` | POST | Trigger AI outbound call for a lead |
| `/api/v1/linkedin/search` | POST | Search LinkedIn profiles via Unipile |
| `/api/v1/linkedin/profile/{id}` | GET | Get LinkedIn profile details |
| `/api/v1/linkedin/invite` | POST | Send LinkedIn connection request |
| `/api/v1/linkedin/message` | POST | Send LinkedIn message |
| `/api/v1/happyrobot/call` | POST | Trigger HappyRobot outbound AI call |
| `/api/v1/happyrobot/call/{id}` | GET | Get call status and transcript |
| `/api/v1/meetings/` | GET, POST | List/create meetings |
| `/api/v1/meetings/{id}` | GET, PATCH, DELETE | Meeting details/update/delete |
| `/api/v1/availability/` | GET, PUT | Get/set admin availability |
| `/api/v1/happyrobot/webhook` | POST | Receive call completion webhook |
| `/api/v1/landing-pages/generate` | POST | Generate landing page with AI |
| `/api/v1/landing-pages/` | GET | List saved landing pages |
| `/api/v1/landing-pages/{id}` | GET, PATCH, DELETE | Landing page CRUD |
| `/api/v1/landing-pages/{id}/preview` | GET | Serve landing page HTML |
| `/api/v1/landing-pages/{id}/refine` | POST | Refine landing page with AI |
| `/api/v1/landing-pages/{id}/deploy` | POST | Deploy to Netlify |
| `/api/v1/landing-pages/auto-generate-for-lead` | POST | Auto-generate for top lead |

## Workflow Node Types

| Node | Description |
|------|-------------|
| `start` | Flow start |
| `end` | Flow end |
| `ai_prompt` | Send prompt to LLM, get response |
| `question` | Ask user a question (text/number/yes_no/choice) |
| `condition` | Branch based on variable |
| `transfer` | Transfer to human agent |
| `webhook` | Send HTTP webhook |
| `knowledge_lookup` | Search knowledge base |
| `set_variable` | Assign variable |
| `wait` | Wait + show message |
| `collect_input` | Collect validated input (phone, email, date) |
| `api_call` | Call external API |
| `function_call` | Call function |

## Environment Variables

```
OPENAI_API_KEY=your_openai_key
ANTHROPIC_API_KEY=your_anthropic_key
ELEVENLABS_API_KEY=your_elevenlabs_key
INSTAGRAM_ACCESS_TOKEN=your_instagram_token
TELEGRAM_BOT_TOKEN=your_telegram_token
UNIPILE_API_KEY=your_unipile_access_token
UNIPILE_DSN=api1.unipile.com:13337
UNIPILE_ACCOUNT_ID=your_linkedin_account_id
HAPPYROBOT_API_KEY=your_happyrobot_key
HAPPYROBOT_USE_CASE_ID=your_use_case_id
HAPPYROBOT_NUMBER_ID=your_number_id
HAPPYROBOT_WEBHOOK_URL=your_happyrobot_webhook_url
NETLIFY_ACCESS_TOKEN=your_netlify_token
LLM_API_KEY=your_openai_key  # Used by Cognee (same as OPENAI_API_KEY)
```

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy (async), SQLite/PostgreSQL
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide Icons
- **LLM**: OpenAI GPT-4.1 (chat, ICP generation, lead scoring, outreach, self-learning)
- **Landing Pages**: Anthropic Claude (claude-sonnet-4) for HTML generation
- **AI Memory**: Cognee knowledge graph for persistent, graph-structured AI memory
- **Lead Search**: OpenAI Responses API with web_search_preview
- **LinkedIn**: Unipile API (search, invite, message)
- **AI Calling**: HappyRobot outbound AI phone calls with webhook
- **Deployment**: Netlify API for landing page auto-deploy
- **Channels**: Instagram, Telegram, Messenger, WhatsApp, Live Chat
- **Voice**: ElevenLabs API, OpenAI Whisper (STT), WebSocket
