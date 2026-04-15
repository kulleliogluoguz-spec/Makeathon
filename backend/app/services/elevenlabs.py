"""ElevenLabs API wrapper for voice listing and TTS."""

import os
import httpx

ELEVENLABS_BASE = "https://api.elevenlabs.io/v1"


def _api_key() -> str:
    return os.environ.get("ELEVENLABS_API_KEY", "")


async def list_voices(search: str = None, category: str = None, gender: str = None, language: str = None) -> list:
    """List voices from ElevenLabs, with optional filters."""
    headers = {"xi-api-key": _api_key()}

    # Use the search endpoint for filtering
    params = {}
    if search:
        params["search"] = search
    if category:
        params["category"] = category

    async with httpx.AsyncClient(timeout=15.0) as client:
        if search or category:
            resp = await client.get(f"{ELEVENLABS_BASE}/voices/search", headers=headers, params=params)
        else:
            resp = await client.get(f"{ELEVENLABS_BASE}/voices", headers=headers)
        resp.raise_for_status()
        data = resp.json()

    voices = []
    for v in data.get("voices", []):
        labels = v.get("labels", {})
        v_gender = labels.get("gender", "")
        v_language = labels.get("language", "")

        # Client-side filtering for gender/language if provided
        if gender and v_gender and v_gender.lower() != gender.lower():
            continue
        if language and v_language and v_language.lower() != language.lower():
            continue

        voices.append({
            "voice_id": v["voice_id"],
            "name": v["name"],
            "category": v.get("category", ""),
            "description": v.get("description", ""),
            "preview_url": v.get("preview_url", ""),
            "labels": labels,
            "language": v_language,
            "gender": v_gender,
            "age": labels.get("age", ""),
            "accent": labels.get("accent", ""),
            "use_case": labels.get("use_case", ""),
        })
    return voices


async def get_voice(voice_id: str) -> dict:
    """Get single voice details."""
    headers = {"xi-api-key": _api_key()}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(f"{ELEVENLABS_BASE}/voices/{voice_id}", headers=headers)
        resp.raise_for_status()
        return resp.json()


async def text_to_speech(
    text: str,
    voice_id: str,
    model_id: str = "eleven_turbo_v2",
    stability: float = 0.5,
    similarity_boost: float = 0.75,
    style: float = 0.0,
    speed: float = 1.0,
) -> bytes:
    """Generate speech audio (MP3 bytes) from text using ElevenLabs."""
    headers = {
        "xi-api-key": _api_key(),
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "model_id": model_id,
        "voice_settings": {
            "stability": stability,
            "similarity_boost": similarity_boost,
            "style": style,
            "use_speaker_boost": True,
        },
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            f"{ELEVENLABS_BASE}/text-to-speech/{voice_id}",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        return resp.content
