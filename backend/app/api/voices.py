"""Voice endpoints — ElevenLabs voice listing and TTS generation."""

import os
from typing import Optional
from dotenv import load_dotenv
from fastapi import APIRouter, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import Response
from pydantic import BaseModel
import httpx

load_dotenv()

router = APIRouter()

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")


@router.get("/voices/")
async def list_voices(
    search: Optional[str] = Query(None),
    gender: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
):
    if not ELEVENLABS_API_KEY:
        raise HTTPException(status_code=500, detail="ELEVENLABS_API_KEY not configured")

    params = {}
    if search:
        params["search"] = search
    if gender:
        params["gender"] = gender
    if category:
        params["category"] = category

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(
            "https://api.elevenlabs.io/v1/voices",
            headers={"xi-api-key": ELEVENLABS_API_KEY},
            params=params,
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="ElevenLabs API error")
    data = resp.json()
    voices = data.get("voices", data) if isinstance(data, dict) else data
    return [
        {
            "voice_id": v.get("voice_id"),
            "name": v.get("name"),
            "preview_url": v.get("preview_url"),
            "category": v.get("category", ""),
            "gender": (v.get("labels") or {}).get("gender", ""),
            "age": (v.get("labels") or {}).get("age", ""),
            "accent": (v.get("labels") or {}).get("accent", ""),
        }
        for v in voices
    ]


class TTSRequest(BaseModel):
    text: str
    voice_id: str
    model_id: Optional[str] = "eleven_turbo_v2"
    stability: Optional[float] = 0.5
    similarity_boost: Optional[float] = 0.75
    style: Optional[float] = 0.0
    speed: Optional[float] = 1.0


@router.post("/tts/generate")
async def generate_tts(req: TTSRequest):
    if not ELEVENLABS_API_KEY:
        raise HTTPException(status_code=500, detail="ELEVENLABS_API_KEY not configured")
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"https://api.elevenlabs.io/v1/text-to-speech/{req.voice_id}",
            headers={"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"},
            json={
                "text": req.text,
                "model_id": req.model_id,
                "voice_settings": {
                    "stability": req.stability,
                    "similarity_boost": req.similarity_boost,
                    "style": req.style,
                    "speed": req.speed,
                },
            },
        )
    if resp.status_code != 200:
        raise HTTPException(status_code=resp.status_code, detail="TTS generation failed")
    return Response(content=resp.content, media_type="audio/mpeg")


@router.post("/stt/transcribe")
async def transcribe_audio(
    file: UploadFile = File(...),
    language: str = Form("en"),
):
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY not configured")
    audio_bytes = await file.read()
    if len(audio_bytes) < 100:
        raise HTTPException(status_code=400, detail="Audio file too small")
    from openai import OpenAI
    import io
    client = OpenAI(api_key=OPENAI_API_KEY)
    try:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=(file.filename or "audio.webm", io.BytesIO(audio_bytes)),
            language=language,
        )
        return {"text": transcript.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")
