from contextlib import asynccontextmanager

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routes import personas, agents, voice_builder, voices


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="VoiceAgent Persona & Rules Builder", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5176", "http://127.0.0.1:5176"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(personas.router, prefix="/api/v1")
app.include_router(agents.router, prefix="/api/v1")
app.include_router(voice_builder.router, prefix="/api/v1")
app.include_router(voices.router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "healthy"}
