"""OpenAI Whisper API for speech-to-text."""

import os
import httpx


def _api_key() -> str:
    return os.environ.get("OPENAI_API_KEY", "")


async def transcribe_audio(audio_bytes: bytes, language: str = "en", filename: str = "audio.webm") -> str:
    """Transcribe audio using OpenAI Whisper."""
    # Determine MIME type from filename
    mime = "audio/webm"
    if filename.endswith(".mp3"):
        mime = "audio/mpeg"
    elif filename.endswith(".wav"):
        mime = "audio/wav"
    elif filename.endswith(".m4a"):
        mime = "audio/mp4"

    headers = {"Authorization": f"Bearer {_api_key()}"}

    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(
            "https://api.openai.com/v1/audio/transcriptions",
            headers=headers,
            files={"file": (filename, audio_bytes, mime)},
            data={"model": "whisper-1", "language": language},
        )
        resp.raise_for_status()
        return resp.json()["text"]
