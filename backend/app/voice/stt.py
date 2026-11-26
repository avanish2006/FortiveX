"""
Speech-to-Text module.
Supports:
  - gemini         : Gemini multimodal audio transcription (works with GEMINI_API_KEY)
  - openai_whisper : OpenAI Whisper API (audio file upload)
"""
from __future__ import annotations

import asyncio
import io
import logging
from typing import Optional

from openai import AsyncOpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_openai_client: Optional[AsyncOpenAI] = None


def _get_openai() -> AsyncOpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _openai_client


async def transcribe_audio(audio_bytes: bytes, language: str = "en") -> str:
    """
    Transcribe raw audio bytes to text.
    audio_bytes: raw PCM/WAV/WebM/OGG bytes
    language: BCP-47 language code (e.g. 'en', 'es', 'fr')
    Returns the transcript string.
    """
    provider = settings.stt_provider

    if provider == "gemini" or (not settings.openai_api_key and settings.gemini_api_key):
        return await _transcribe_gemini(audio_bytes, language)
    if provider == "openai_whisper" and settings.openai_api_key:
        return await _transcribe_openai(audio_bytes, language)

    logger.warning("No STT API key configured (neither OPENAI_API_KEY nor GEMINI_API_KEY)")
    return ""


async def _transcribe_gemini(audio_bytes: bytes, language: str) -> str:
    import google.generativeai as genai

    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel(settings.llm_model or "gemini-3.1-flash-lite")

    prompt = (
        f"Transcribe the following speech audio accurately in language '{language}'. "
        "Return ONLY the transcribed text, with no extra commentary."
    )

    def _call():
        response = model.generate_content(
            [
                prompt,
                {"mime_type": "audio/webm", "data": audio_bytes},
            ]
        )
        return (response.text or "").strip()

    try:
        transcript = await asyncio.to_thread(_call)
        logger.debug("Gemini STT transcript: %s", transcript[:80])
        return transcript
    except Exception as e:
        logger.error("Gemini STT error: %s", e)
        return ""


async def _transcribe_openai(audio_bytes: bytes, language: str) -> str:
    client = _get_openai()
    audio_file = io.BytesIO(audio_bytes)
    audio_file.name = "audio.webm"

    try:
        response = await client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language=language if len(language) == 2 else language[:2],
            response_format="text",
        )
        transcript = response.strip() if isinstance(response, str) else response.text.strip()
        logger.debug("OpenAI STT transcript: %s", transcript[:80])
        return transcript
    except Exception as e:
        logger.error("OpenAI STT error: %s", e)
        return ""
