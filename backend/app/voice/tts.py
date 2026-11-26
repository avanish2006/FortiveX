"""
Text-to-Speech module.
Supports:
  - openai      : OpenAI TTS API (tts-1 / tts-1-hd)
  - elevenlabs  : ElevenLabs streaming TTS
  - gtts        : Google Text-to-Speech (free multilingual fallback, no API key needed)
"""
from __future__ import annotations

import asyncio
import io
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


async def synthesize_speech(text: str, language: str = "en") -> bytes:
    """
    Convert text to audio bytes (MP3).
    Returns raw audio bytes that can be streamed to the client.
    """
    if not text.strip():
        return b""

    provider = settings.tts_provider

    if provider == "elevenlabs" and settings.elevenlabs_api_key:
        return await _tts_elevenlabs(text, language)
    if provider == "openai" and settings.openai_api_key:
        return await _tts_openai(text)
    return await _tts_gtts(text, language)


async def _tts_gtts(text: str, language: str = "en") -> bytes:
    from gtts import gTTS

    lang_code = language[:2].lower() if language else "en"

    def _call() -> bytes:
        buf = io.BytesIO()
        tts = gTTS(text=text, lang=lang_code)
        tts.write_to_fp(buf)
        return buf.getvalue()

    try:
        audio_bytes = await asyncio.to_thread(_call)
        logger.debug("TTS (gTTS): %d bytes for %d chars", len(audio_bytes), len(text))
        return audio_bytes
    except Exception as e:
        logger.error("TTS gTTS error: %s", e)
        return b""


async def _tts_openai(text: str) -> bytes:
    from openai import AsyncOpenAI

    client = AsyncOpenAI(api_key=settings.openai_api_key)
    try:
        response = await client.audio.speech.create(
            model="tts-1",
            voice="nova",
            input=text,
            response_format="mp3",
        )
        audio_bytes = b""
        async for chunk in response.iter_bytes(chunk_size=4096):
            audio_bytes += chunk
        logger.debug("TTS (OpenAI): %d bytes for %d chars", len(audio_bytes), len(text))
        return audio_bytes
    except Exception as e:
        logger.error("TTS OpenAI error: %s", e)
        return await _tts_gtts(text)


async def _tts_elevenlabs(text: str, language: str = "en") -> bytes:
    try:
        from elevenlabs import AsyncElevenLabs

        client = AsyncElevenLabs(api_key=settings.elevenlabs_api_key)
        audio_generator = await client.generate(
            text=text,
            voice=settings.elevenlabs_voice_id,
            model="eleven_multilingual_v2",
        )
        audio_bytes = b""
        async for chunk in audio_generator:
            audio_bytes += chunk
        return audio_bytes
    except Exception as e:
        logger.error("TTS ElevenLabs error: %s", e)
        if settings.openai_api_key:
            return await _tts_openai(text)
        return await _tts_gtts(text, language)
