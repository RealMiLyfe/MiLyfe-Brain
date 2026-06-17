"""
MiLyfe Brain - Voice Interface Service

Provides speech-to-text and text-to-speech capabilities.
Stub implementation — integrates with system TTS/STT when available.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


async def speech_to_text(
    audio_data: bytes,
    format: str = "wav",
    language: str = "en",
) -> Dict[str, Any]:
    """
    Convert speech audio to text.

    Args:
        audio_data: Raw audio bytes.
        format: Audio format ('wav', 'mp3', 'ogg').
        language: Language code.

    Returns:
        Dict with 'text', 'confidence', 'language'.
    """
    logger.info("Speech-to-text requested (format=%s, language=%s, bytes=%d)", format, language, len(audio_data))

    # Stub: would integrate with Whisper or system STT
    return {
        "text": "",
        "confidence": 0.0,
        "language": language,
        "error": "Speech-to-text not yet implemented. Install whisper for local STT.",
    }


async def text_to_speech(
    text: str,
    voice: str = "default",
    speed: float = 1.0,
) -> Optional[bytes]:
    """
    Convert text to speech audio.

    Args:
        text: Text to synthesize.
        voice: Voice identifier.
        speed: Playback speed multiplier.

    Returns:
        Audio bytes (WAV format), or None if not available.
    """
    logger.info("Text-to-speech requested (voice=%s, speed=%.1f, chars=%d)", voice, speed, len(text))

    # Stub: would integrate with piper-tts or system TTS
    return None


async def get_capabilities() -> Dict[str, Any]:
    """
    Get available voice capabilities.

    Returns:
        Dict with 'stt_available', 'tts_available', 'voices', 'languages'.
    """
    stt_available = False
    tts_available = False

    # Check for whisper
    try:
        import whisper  # noqa: F401
        stt_available = True
    except ImportError:
        pass

    # Check for piper or system TTS
    try:
        import subprocess
        result = subprocess.run(
            ["which", "piper"], capture_output=True, timeout=2,
        )
        tts_available = result.returncode == 0
    except Exception:
        pass

    return {
        "stt_available": stt_available,
        "tts_available": tts_available,
        "voices": ["default"] if tts_available else [],
        "languages": ["en"],
        "supported_formats": ["wav", "mp3", "ogg"],
    }
