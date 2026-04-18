# VoiceAgent Platform

A fully customizable AI agent platform for customer engagement. Build voice agents for company recognition, customer support, sales, and AI-powered lead generation.

## Features

### Backend (FastAPI + SQLAlchemy)
- **Agent Management**: CRUD, duplication, status management
- **Persona Builder**: 8 personality traits (friendliness, formality, empathy...), communication style, emotional responses, automatic system prompt generation
- **Visual Workflow Engine**: 14 node types (AI Prompt, Question, Condition, Transfer, Webhook, API Call, Knowledge Lookup, Set Variable, Wait, Collect Input, Function Call, Play Audio, Start, End)
- **Workflow Execution Engine**: Conversation flow through workflows, variable interpolation, condition evaluation, retry logic
- **Conversation Tracking**: Message history, sentiment analysis, company profile extraction
- **Company Profiles**: Automatic company profile extraction from conversations
- **Knowledge Base**: Reference knowledge base for agents
- **WebSocket**: Real-time voice conversation infrastructure
- **Workflow Templates**: Ready-made templates (Company Recognition, Customer Support, Sales, Appointment, Survey)
- **AI Lead Finder**: AI-powered lead generation with web search, ICP generation, lead scoring, and outreach message drafting
- **LinkedIn Integration (Unipile)**: Search LinkedIn profiles, send connection requests, send messages via Unipile API
- **HappyRobot AI Calls**: Outbound AI phone calls to leads and high-intent customers, auto-triggered at intent score 90+
- **Auto-Call Offer**: When intent score hits 70+, AI offers customers a phone call across all channels
- **Meeting Calendar**: Scheduled meetings from AI outreach, with full AI-generated reports (summary, talking points, approach, risks, transcript)
- **Demo Data Seeder**: 5 English demo customers with conversations, CSAT ratings, and broadcast campaigns
- **Multi-Channel**: Instagram, Telegram, Messenger, WhatsApp, Live Chat widget

### Frontend (React + Vite + React Flow)
- **Dashboard**: Overview, statistics
- **Agent Editor**: Voice settings, LLM settings, behavior rules, persona assignment
- **Visual Workflow Builder**: Drag-and-drop node editor (React Flow), node configuration, edge management
- **Persona Editor**: Personality trait sliders, communication rules, emotional response management, automatic system prompt
- **Conversations**: Past conversations, analytics, message details
- **Customers**: Unified customer database across all channels
- **Lead Finder**: AI-powered lead generation with preset filters, editable search criteria, LinkedIn search via Unipile, auto-call top leads, LinkedIn fallback
- **Meetings**: Calendar view with AI-generated meeting reports — conversation summary, recommended approach, talking points, risk factors, call transcript
- **Analytics**: Performance overview, intent scoring, sales funnel
- **Settings**: Business hours, auto-reply, live chat widget, language selection (EN/TR)

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
ELEVENLABS_API_KEY=your_elevenlabs_key
INSTAGRAM_ACCESS_TOKEN=your_instagram_token
TELEGRAM_BOT_TOKEN=your_telegram_token
UNIPILE_API_KEY=your_unipile_access_token
UNIPILE_DSN=api1.unipile.com:13337
UNIPILE_ACCOUNT_ID=your_linkedin_account_id
HAPPYROBOT_API_KEY=your_happyrobot_key
HAPPYROBOT_USE_CASE_ID=your_use_case_id
HAPPYROBOT_NUMBER_ID=your_number_id
```

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy (async), SQLite/PostgreSQL
- **Frontend**: React 18, Vite, Tailwind CSS, Lucide Icons
- **Voice**: ElevenLabs API, OpenAI Whisper (STT), WebSocket
- **LLM**: OpenAI GPT-4.1 (chat, ICP generation, lead scoring, outreach)
- **Channels**: Instagram, Telegram, Messenger, WhatsApp, Live Chat
- **Lead Generation**: OpenAI Web Search (Responses API), Unipile LinkedIn API
- **AI Calling**: HappyRobot outbound AI phone calls
- **Integrations**: Apollo.io (optional), Fashn virtual try-on
