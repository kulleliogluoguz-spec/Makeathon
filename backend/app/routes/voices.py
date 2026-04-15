from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import Response
from pydantic import BaseModel

from app.services.elevenlabs import list_voices, get_voice, text_to_speech
from app.services.openai_stt import transcribe_audio

router = APIRouter(tags=["voices"])


# --- Voice listing ---

@router.get("/voices/")
async def api_list_voices(
    search: str = None,
    category: str = None,
    gender: str = None,
    language: str = None,
):
    try:
        voices = await list_voices(search=search, category=category, gender=gender, language=language)
        return voices
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ElevenLabs API error: {str(e)}")


@router.get("/voices/{voice_id}")
async def api_get_voice(voice_id: str):
    try:
        voice = await get_voice(voice_id)
        return voice
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ElevenLabs API error: {str(e)}")


# --- TTS ---

class TTSRequest(BaseModel):
    text: str
    voice_id: str
    model_id: str = "eleven_turbo_v2"
    stability: float = 0.5
    similarity_boost: float = 0.75
    style: float = 0.0
    speed: float = 1.0


@router.post("/tts/generate")
async def api_tts_generate(data: TTSRequest):
    try:
        audio_bytes = await text_to_speech(
            text=data.text,
            voice_id=data.voice_id,
            model_id=data.model_id,
            stability=data.stability,
            similarity_boost=data.similarity_boost,
            style=data.style,
            speed=data.speed,
        )
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"ElevenLabs TTS error: {str(e)}")


# --- STT ---

@router.post("/stt/transcribe")
async def api_stt_transcribe(
    file: UploadFile = File(...),
    language: str = Form("en"),
):
    try:
        audio_bytes = await file.read()
        text = await transcribe_audio(audio_bytes, language=language, filename=file.filename or "audio.webm")
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Whisper STT error: {str(e)}")
