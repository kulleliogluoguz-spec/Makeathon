"""
VoiceAgent Platform - Main Application
A comprehensive voice agent system for company recognition and customer interaction.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from pathlib import Path

from app.core.config import settings
from app.core.database import engine, Base
from app.api import agents, workflows, conversations, personas, companies, knowledge_base
from app.api.voices import router as voices_router
from app.api.voice_builder import router as voice_builder_router
from app.api.catalogs import router as catalogs_router
from app.api.conversations_api import router as conversations_api_router
from app.api.customers import router as customers_router
from app.api.categories import router as categories_router
from app.services.category_seeder import seed_builtin_categories
from app.api.settings import router as settings_router
from app.api.persona_templates import router as templates_router
from app.api.conversation_export import router as export_router
from app.api.livechat import router as livechat_router
from app.api.messenger import router as messenger_router
from app.api.analytics import router as analytics_router
from app.api.csat import router as csat_router
from app.api.quick_replies import router as quick_replies_router
from app.api.auth import router as auth_router
from app.api.assignment import router as assignment_router
from app.api.teams import router as teams_router
from app.api.agent_performance import router as perf_router
from app.api.broadcast import router as broadcast_router
from app.api.telegram import router as telegram_router
from app.api.tryon import router as tryon_router

# Create media directory
Path("media").mkdir(exist_ok=True)
Path("media/products").mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await seed_builtin_categories()
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="VoiceAgent Platform",
    description="AI-powered voice agent system with customizable personas and visual workflow builder",
    version="1.0.0",
    lifespan=lifespan,
)

app.mount("/media", StaticFiles(directory="media"), name="media")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Routes
app.include_router(agents.router, prefix="/api/v1/agents", tags=["Agents"])
app.include_router(workflows.router, prefix="/api/v1/workflows", tags=["Workflows"])
app.include_router(conversations.router, prefix="/api/v1/conversations", tags=["Conversations"])
app.include_router(personas.router, prefix="/api/v1/personas", tags=["Personas"])
app.include_router(companies.router, prefix="/api/v1/companies", tags=["Companies"])
app.include_router(knowledge_base.router, prefix="/api/v1/knowledge", tags=["Knowledge Base"])
app.include_router(voices_router, prefix="/api/v1", tags=["Voices"])
app.include_router(voice_builder_router, prefix="/api/v1/voice-builder", tags=["Voice Builder"])
app.include_router(catalogs_router, prefix="/api/v1", tags=["Catalogs"])
app.include_router(conversations_api_router, prefix="/api/v1/dashboard", tags=["Dashboard Conversations"])
app.include_router(customers_router, prefix="/api/v1", tags=["Customers"])
app.include_router(categories_router, prefix="/api/v1", tags=["Categories"])
app.include_router(settings_router, prefix="/api/v1", tags=["Settings"])
app.include_router(templates_router, prefix="/api/v1", tags=["Templates"])
app.include_router(export_router, prefix="/api/v1/dashboard", tags=["Export"])
app.include_router(livechat_router, tags=["LiveChat"])
app.include_router(messenger_router, prefix="/api/v1", tags=["Messenger"])
app.include_router(analytics_router, prefix="/api/v1", tags=["Analytics"])
app.include_router(csat_router, prefix="/api/v1", tags=["CSAT"])
app.include_router(quick_replies_router, prefix="/api/v1", tags=["Quick Replies"])
app.include_router(auth_router, prefix="/api/v1", tags=["Auth"])
app.include_router(assignment_router, prefix="/api/v1", tags=["Assignment"])
app.include_router(teams_router, prefix="/api/v1", tags=["Teams"])
app.include_router(perf_router, prefix="/api/v1", tags=["Performance"])
app.include_router(broadcast_router, prefix="/api/v1", tags=["Broadcast"])
app.include_router(telegram_router, prefix="/api/v1", tags=["Telegram"])
app.include_router(tryon_router, prefix="/api/v1", tags=["TryOn"])


@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "1.0.0"}

@app.get("/privacy")
async def privacy():
    return HTMLResponse("<h1>Privacy Policy</h1><p>We collect messages for automated responses only.</p>")

@app.get("/terms")
async def terms():
    return HTMLResponse("<h1>Terms of Service</h1><p>Standard terms apply.</p>")

@app.get("/data-deletion")
async def data_deletion():
    return HTMLResponse("<h1>Data Deletion</h1><p>Email okullelioglu@gmail.com</p>")
from app.api.instagram import router as instagram_router
app.include_router(instagram_router, prefix="/api/v1", tags=["Instagram"])
