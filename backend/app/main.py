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

# Create media directory
Path("media").mkdir(exist_ok=True)
Path("media/products").mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
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
