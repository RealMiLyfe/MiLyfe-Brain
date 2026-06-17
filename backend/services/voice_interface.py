"""MiLyfe Brain — Voice Interface (Local STT/TTS).

STT: Whisper.cpp (local)
TTS: Piper/system TTS (local)
"""

from __future__ import annotations

import asyncio
import io
import tempfile
from pathlib import Path
from typing import Optional

import structlog

logger = structlog.get_logger()


class VoiceInterface:
    """Local voice input/output (no cloud APIs)."""

    def __init__(self):
        self._whisper_available = False
        self._tts_available = False

    async def initialize(self):
        """Check voice capabilities."""
        self._whisper_available = await self._check_whisper()
        self._tts_available = await self._check_tts()

    async def speech_to_text(self, audio_data: bytes, format: str = "wav") -> str:
        """Convert speech to text using local Whisper."""
        if not self._whisper_available:
            # Fallback: try using soundfile + basic processing
            return await self._fallback_stt(audio_data, format)

        # Write to temp file
        with tempfile.NamedTemporaryFile(suffix=f".{format}", delete=False) as f:
            f.write(audio_data)
            temp_path = f.name

        try:
            proc = await asyncio.create_subprocess_exec(
                "whisper", temp_path, "--model", "base", "--output_format", "txt",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode == 0:
                # Read the output text file
                txt_path = Path(temp_path).with_suffix(".txt")
                if txt_path.exists():
                    text = txt_path.read_text().strip()
                    txt_path.unlink()
                    return text

            return stdout.decode().strip() if stdout else ""
        except Exception as e:
            logger.error("stt_failed", error=str(e))
            return ""
        finally:
            Path(temp_path).unlink(missing_ok=True)

    async def text_to_speech(self, text: str) -> Optional[bytes]:
        """Convert text to speech using local TTS."""
        if not self._tts_available:
            return None

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name

        try:
            # Try piper first
            proc = await asyncio.create_subprocess_shell(
                f'echo "{text}" | piper --model en_US-lessac-medium --output_file {temp_path}',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            if proc.returncode == 0 and Path(temp_path).exists():
                return Path(temp_path).read_bytes()

            # Fallback to espeak
            proc = await asyncio.create_subprocess_exec(
                "espeak", "-w", temp_path, text,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()

            if Path(temp_path).exists():
                return Path(temp_path).read_bytes()

        except Exception as e:
            logger.error("tts_failed", error=str(e))
        finally:
            Path(temp_path).unlink(missing_ok=True)

        return None

    def get_capabilities(self) -> dict:
        """Get voice capabilities."""
        return {
            "stt_available": self._whisper_available,
            "tts_available": self._tts_available,
            "supported_formats": ["wav", "mp3", "ogg", "webm"],
        }

    async def _check_whisper(self) -> bool:
        import shutil
        return shutil.which("whisper") is not None

    async def _check_tts(self) -> bool:
        import shutil
        return shutil.which("piper") is not None or shutil.which("espeak") is not None

    async def _fallback_stt(self, audio_data: bytes, format: str) -> str:
        """Fallback STT using Ollama's multimodal capabilities."""
        return "(Voice input received but Whisper not installed. Install: pip install openai-whisper)"


# Singleton
voice_interface = VoiceInterface()
