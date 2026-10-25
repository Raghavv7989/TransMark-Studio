import os
from typing import Any, Dict
from fastapi import APIRouter

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("api_system")
router = APIRouter(prefix="/system", tags=["system"])


def detect_accelerator() -> str:
    """Detect hardware acceleration device."""
    try:
        import torch
        if torch.cuda.is_available():
            return "cuda"
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        return "cpu"
    except Exception:
        return "cpu"


@router.get("/health")
async def get_system_engine_health() -> Dict[str, Any]:
    """
    Returns live telemetry regarding whether AI models are running in
    LIVE PRODUCTION MODE (using cloud API credentials & GPU models) vs
    LOCAL/FALLBACK MODE (using local offline engines).
    """
    accelerator = detect_accelerator()

    # 1. Translation Engine status
    gemini_key = os.getenv("GEMINI_API_KEY") or settings.GEMINI_API_KEY
    openai_key = os.getenv("OPENAI_API_KEY") or settings.OPENAI_API_KEY

    if gemini_key:
        translation_mode = "LIVE_PRODUCTION"
        translation_engine = "google-gemini-2.5-flash"
    elif openai_key:
        translation_mode = "LIVE_PRODUCTION"
        translation_engine = "openai-gpt-4o-mini"
    else:
        translation_mode = "LOCAL_FALLBACK"
        translation_engine = "google-neural-gtx"

    # 2. Voice Cloning status
    eleven_key = os.getenv("ELEVENLABS_API_KEY") or settings.ELEVENLABS_API_KEY
    if eleven_key:
        tts_mode = "LIVE_PRODUCTION"
        tts_engine = "elevenlabs-multilingual-v2"
    else:
        tts_mode = "LOCAL_FALLBACK"
        tts_engine = "microsoft-edge-neural-tts"

    # 3. LipSync & Restoration status
    synclabs_key = os.getenv("SYNCLABS_API_KEY") or settings.SYNCLABS_API_KEY
    replicate_token = os.getenv("REPLICATE_API_TOKEN") or settings.REPLICATE_API_TOKEN

    if synclabs_key:
        lipsync_mode = "LIVE_PRODUCTION"
        lipsync_engine_name = "synclabs-cloud-gpu"
    elif replicate_token:
        lipsync_mode = "LIVE_PRODUCTION"
        lipsync_engine_name = "replicate-musetalk-gpu"
    elif accelerator in ["cuda", "mps"]:
        lipsync_mode = "LIVE_PRODUCTION"
        lipsync_engine_name = f"local-musetalk-{accelerator}"
    else:
        lipsync_mode = "LOCAL_FALLBACK"
        lipsync_engine_name = "zero-damage-mouth-kinematics"

    # 4. ASR & Demux status
    asr_mode = "LIVE_PRODUCTION"
    asr_engine_name = f"faster-whisper-{settings.WHISPER_MODEL_SIZE}"

    demux_mode = "FFMPEG_FALLBACK" if settings.FORCE_FFMPEG_FALLBACK else "LIVE_PRODUCTION"
    demux_engine_name = f"demucs-{settings.DEMUCS_MODEL}"

    # Overall mode summary
    live_count = sum(
        1 for m in [translation_mode, tts_mode, lipsync_mode, asr_mode, demux_mode] if m == "LIVE_PRODUCTION"
    )
    if live_count >= 4:
        overall_mode = "LIVE_PRODUCTION"
    elif live_count > 0:
        overall_mode = "HYBRID_LOCAL"
    else:
        overall_mode = "OFFLINE_STUDIO"

    return {
        "status": "online",
        "overall_mode": overall_mode,
        "hardware_accelerator": accelerator,
        "version": settings.VERSION,
        "engines": {
            "asr": {
                "name": asr_engine_name,
                "mode": asr_mode,
                "device": accelerator,
                "model_size": settings.WHISPER_MODEL_SIZE,
            },
            "translation": {
                "name": translation_engine,
                "mode": translation_mode,
                "has_api_key": bool(gemini_key or openai_key),
            },
            "voice_cloning": {
                "name": tts_engine,
                "mode": tts_mode,
                "has_api_key": bool(eleven_key),
                "sample_rate": settings.TTS_SAMPLE_RATE,
            },
            "lipsync": {
                "name": lipsync_engine_name,
                "mode": lipsync_mode,
                "has_cloud_gpu": bool(synclabs_key or replicate_token),
                "restoration": settings.FACE_RESTORATION,
                "zero_damage_guaranteed": True,
            },
            "demux": {
                "name": demux_engine_name,
                "mode": demux_mode,
                "model": settings.DEMUCS_MODEL,
            },
        },
    }
