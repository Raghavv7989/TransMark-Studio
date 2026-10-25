"""ASR (Automatic Speech Recognition) service interface for Whisper/faster-whisper."""
from pathlib import Path
from typing import Any, Dict, Optional
from pydantic import BaseModel
from app.core.logging import get_logger

logger = get_logger("asr_service")


class TranscriptionSegment(BaseModel):
    id: int
    start: float
    end: float
    text: str
    words: Optional[list] = None


class ASRResult(BaseModel):
    language: str
    text: str
    segments: list[TranscriptionSegment]
    duration: float


class ASRService:
    """ASR Service staging for Mission 2 (Whisper / Faster-Whisper with word-level timestamps)."""

    def __init__(self, model_size: str = "large-v3"):
        self.model_size = model_size
        logger.info(f"Initialized ASRService stub [Model: {self.model_size}]")

    async def transcribe(self, audio_path: Path, language: Optional[str] = None) -> ASRResult:
        """Transcribe 16kHz mono vocal audio stem."""
        logger.info(f"ASR transcribe called on {audio_path} (language={language})")
        # Staged for Mission 2
        return ASRResult(
            language=language or "auto",
            text="Transcription pipeline staged.",
            segments=[],
            duration=0.0,
        )


asr_service = ASRService()
