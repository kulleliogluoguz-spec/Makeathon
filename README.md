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
- **Multi-Channel**: Instagram, Telegram, Messenger, WhatsApp, Live Chat widget

### Frontend (React + Vite + React Flow)
- **Dashboard**: Overview, statistics
- **Agent Editor**: Voice settings, LLM settings, behavior rules, persona assignment
- **Visual Workflow Builder**: Drag-and-drop node editor (React Flow), node configuration, edge management
- **Persona Editor**: Personality trait sliders, communication rules, emotional response management, automatic system prompt
- **Conversations**: Past conversations, analytics, message details
- **Customers**: Unified customer database across all channels
- **Lead Finder**: AI-powered lead generation with preset filters, editable search criteria, LinkedIn outreach
- **Analytics**: Performance overview, intent scoring, sales funnel
- **Broadcast**: Bulk messaging campaigns
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

## Next Steps

1. **Voice Integration**: ElevenLabs/OpenAI TTS-STT integration
2. **LLM Integration**: Connect OpenAI/Anthropic/Ollama providers
3. **Phone Integration**: Twilio/Vonage phone connection
4. **Vector Search**: Embedding-based search for knowledge base
5. **Analytics Dashboard**: Detailed conversation analytics
6. **Multi-tenant**: Multi-user support
7. **A/B Testing**: Workflow variant testing

## Tech Stack

- **Backend**: Python 3.11+, FastAPI, SQLAlchemy (async), SQLite/PostgreSQL
- **Frontend**: React 18, Vite, Tailwind CSS, React Flow, Lucide Icons
- **Voice**: ElevenLabs API, OpenAI Whisper (STT), WebSocket
- **LLM**: OpenAI, Anthropic, Ollama (local)
- **Channels**: Instagram, Telegram, Messenger, WhatsApp, Live Chat
