import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Always load .env with override=True so live keys are active immediately
_curr_file = Path(__file__).resolve()
_env_backend = _curr_file.parent.parent.parent / ".env"
_env_root = _curr_file.parent.parent.parent.parent / ".env"

if _env_backend.exists():
    load_dotenv(_env_backend, override=True)
elif _env_root.exists():
    load_dotenv(_env_root, override=True)
else:
    load_dotenv(override=True)


class Settings(BaseSettings):
    """Application configuration settings."""

    # Project metadata
    PROJECT_NAME: str = "TransMark AI Dubbing Platform"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    DEBUG: bool = False

    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["*"]

    # Storage paths
    BASE_DIR: Path = Path(__file__).resolve().parent.parent
    STORAGE_ROOT: Path = BASE_DIR / "storage"
    RAW_STORAGE: Path = STORAGE_ROOT / "raw"
    AUDIO_SEGMENTS_STORAGE: Path = STORAGE_ROOT / "audio_segments"
    VIDEO_FRAMES_STORAGE: Path = STORAGE_ROOT / "video_frames"
    OUTPUTS_STORAGE: Path = STORAGE_ROOT / "outputs"

    # Audio separation & ML settings
    DEMUCS_MODEL: str = "htdemucs"
    DEMUCS_DEVICE: str = "auto"  # auto, cuda, mps, cpu
    FORCE_FFMPEG_FALLBACK: bool = False

    # ASR & Whisper settings
    WHISPER_MODEL_SIZE: str = "small"  # tiny, base, small, medium, large-v3
    WHISPER_DEVICE: str = "auto"  # auto, cpu, cuda
    WHISPER_COMPUTE_TYPE: str = "int8"
    PAUSE_THRESHOLD_MS: int = 300  # Pause boundary threshold in milliseconds
    GROQ_API_KEY: Optional[str] = None

    # LLM & Isochronic Translation settings
    DEFAULT_TARGET_LANGUAGE: str = "te"  # te (Telugu), hi (Hindi), ta (Tamil), es (Spanish), fr, en
    SYLLABLE_TOLERANCE_MARGIN: float = 0.10  # +/- 10%
    GEMINI_API_KEY: Optional[str] = None
    OPENAI_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "auto"  # auto, gemini, openai, groq, heuristic

    # Voice Cloning & Synthesis settings (Mission 3)
    ELEVENLABS_API_KEY: Optional[str] = None
    ELEVENLABS_VOICE_ID: Optional[str] = None
    SARVAM_API_KEY: Optional[str] = None
    TTS_BACKEND: str = "auto"  # auto, elevenlabs, xtts, synthetic
    TTS_SAMPLE_RATE: int = 44100
    BACKGROUND_MIX_VOLUME: float = 0.70  # Ambient background stem level

    # Zero-Damage Lip-Sync & Restoration settings (Mission 3)
    LIPSYNC_ENGINE: str = "musetalk"  # musetalk, synclabs, replicate, local
    SYNCLABS_API_KEY: Optional[str] = None
    REPLICATE_API_TOKEN: Optional[str] = None
    FACE_RESTORATION: str = "codeformer"  # codeformer, gfpgan, none
    MOUTH_FEATHER_RADIUS: int = 15
    POISSON_BLENDING: bool = True

    # Upload constraints
    MAX_UPLOAD_SIZE_MB: int = 500
    ALLOWED_EXTENSIONS: List[str] = [".mp4", ".mov", ".mkv", ".avi", ".webm"]

    model_config = SettingsConfigDict(
        env_file=str(_env_backend) if _env_backend.exists() else ".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    def init_storage(self) -> None:
        """Ensure all required local storage directories exist."""
        for path in [
            self.STORAGE_ROOT,
            self.RAW_STORAGE,
            self.AUDIO_SEGMENTS_STORAGE,
            self.VIDEO_FRAMES_STORAGE,
            self.OUTPUTS_STORAGE,
        ]:
            path.mkdir(parents=True, exist_ok=True)

    def get_job_storage(self, job_id: str) -> dict[str, Path]:
        """Generate structured paths for a specific job."""
        job_audio_dir = self.AUDIO_SEGMENTS_STORAGE / job_id
        job_frames_dir = self.VIDEO_FRAMES_STORAGE / job_id
        job_output_dir = self.OUTPUTS_STORAGE / job_id

        job_audio_dir.mkdir(parents=True, exist_ok=True)
        job_frames_dir.mkdir(parents=True, exist_ok=True)
        job_output_dir.mkdir(parents=True, exist_ok=True)

        return {
            "raw_dir": self.RAW_STORAGE,
            "audio_dir": job_audio_dir,
            "frames_dir": job_frames_dir,
            "output_dir": job_output_dir,
        }


settings = Settings()
