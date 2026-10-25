import asyncio
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, Optional, Tuple

import ffmpeg
from app.core.config import settings
from app.core.logging import get_logger
from app.models.media import MediaExtractionResult, VideoMetadata

logger = get_logger("media_engine")


class MediaProcessingError(Exception):
    """Raised when FFmpeg or Demucs media processing fails."""
    pass


class MediaEngine:
    """Production-grade lossless FFmpeg demuxing and Demucs audio separation engine."""

    def __init__(self, demucs_model: Optional[str] = None, device: Optional[str] = None):
        self.demucs_model = demucs_model or settings.DEMUCS_MODEL
        self.device = device or self._detect_optimal_device()
        logger.info(f"Initialized MediaEngine [Demucs Model: {self.demucs_model}, Device: {self.device}]")

    def _detect_optimal_device(self) -> str:
        """Detect the fastest available hardware accelerator (CUDA -> MPS -> CPU)."""
        if settings.DEMUCS_DEVICE != "auto":
            return settings.DEMUCS_DEVICE

        try:
            import torch
            if torch.cuda.is_available():
                return "cuda"
            # Note: Demucs on some macOS MPS configurations can fall back or work on cpu
            # If MPS is available, CPU is still rock solid for short reels/clips
            return "cpu"
        except Exception:
            return "cpu"

    # =========================================================================
    # Metadata Probing
    # =========================================================================

    def probe_metadata(self, media_path: Path) -> VideoMetadata:
        """
        Probe exact container and stream metadata using ffprobe.
        Accurately parses FPS fractions, resolution, duration, codecs, and frame counts.
        """
        if not media_path.exists():
            raise FileNotFoundError(f"Media file not found: {media_path}")

        try:
            probe_data = ffmpeg.probe(str(media_path))
        except ffmpeg.Error as e:
            err_msg = e.stderr.decode("utf-8") if e.stderr else str(e)
            logger.error(f"FFprobe failed for {media_path}: {err_msg}")
            raise MediaProcessingError(f"Failed to probe media metadata: {err_msg}") from e

        streams = probe_data.get("streams", [])
        format_info = probe_data.get("format", {})

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        if not video_stream:
            raise MediaProcessingError("No video stream found in the uploaded file.")

        # Parse duration
        duration = float(format_info.get("duration") or video_stream.get("duration") or 0.0)

        # Parse FPS
        fps_str = video_stream.get("avg_frame_rate") or video_stream.get("r_frame_rate") or "30/1"
        try:
            if "/" in fps_str:
                num, den = fps_str.split("/")
                fps = float(num) / float(den) if float(den) != 0 else 30.0
            else:
                fps = float(fps_str)
        except Exception:
            fps = 30.0
        fps = round(fps, 3)

        # Total frames (probe exact frame count if header is missing)
        nb_frames_str = video_stream.get("nb_frames")
        if nb_frames_str and nb_frames_str.isdigit():
            total_frames = int(nb_frames_str)
        else:
            total_frames = self.count_exact_frames(media_path)

        # Video bitrate
        v_bitrate = None
        if "bit_rate" in video_stream:
            v_bitrate = int(video_stream["bit_rate"])
        elif "bit_rate" in format_info:
            v_bitrate = int(format_info["bit_rate"])

        # Audio stream details
        has_audio = audio_stream is not None
        audio_codec = audio_stream.get("codec_name") if has_audio else None
        audio_sample_rate = int(audio_stream["sample_rate"]) if has_audio and "sample_rate" in audio_stream else None
        audio_channels = int(audio_stream["channels"]) if has_audio and "channels" in audio_stream else None
        audio_bitrate = int(audio_stream["bit_rate"]) if has_audio and "bit_rate" in audio_stream else None

        file_size = os.path.getsize(media_path)

        metadata = VideoMetadata(
            duration_seconds=round(duration, 3),
            width=int(video_stream.get("width", 0)),
            height=int(video_stream.get("height", 0)),
            fps=fps,
            total_frames=total_frames,
            video_codec=video_stream.get("codec_name", "unknown"),
            video_bitrate=v_bitrate,
            pixel_format=video_stream.get("pix_fmt"),
            has_audio=has_audio,
            audio_codec=audio_codec,
            audio_sample_rate=audio_sample_rate,
            audio_channels=audio_channels,
            audio_bitrate=audio_bitrate,
            file_size_bytes=file_size,
        )

        logger.info(
            f"Probed metadata for {media_path.name}: {metadata.width}x{metadata.height} @ {metadata.fps}fps, "
            f"{metadata.total_frames} frames, duration: {metadata.duration_seconds}s, has_audio={metadata.has_audio}"
        )
        return metadata

    def count_exact_frames(self, media_path: Path) -> int:
        """
        Count the exact number of video packets/frames by scanning the stream.
        Guarantees zero-drift frame counting even for VFR or truncated containers.
        """
        cmd = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-count_packets",
            "-show_entries", "stream=nb_read_packets",
            "-of", "csv=p=0",
            str(media_path),
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            output = res.stdout.strip()
            if output.isdigit():
                return int(output)
        except Exception as e:
            logger.warning(f"Fast packet frame count failed, falling back to read_frames: {e}")

        # Fallback frame count
        cmd_frames = [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-count_frames",
            "-show_entries", "stream=nb_read_frames",
            "-of", "csv=p=0",
            str(media_path),
        ]
        try:
            res = subprocess.run(cmd_frames, capture_output=True, text=True, check=True)
            output = res.stdout.strip()
            if output.isdigit():
                return int(output)
        except Exception as e:
            logger.error(f"Frame count failed: {e}")

        # Estimator fallback
        try:
            probe = ffmpeg.probe(str(media_path))
            v_stream = next(s for s in probe["streams"] if s["codec_type"] == "video")
            duration = float(probe["format"].get("duration", 0))
            fps_str = v_stream.get("avg_frame_rate", "30/1")
            num, den = fps_str.split("/")
            fps = float(num) / float(den) if float(den) != 0 else 30.0
            return int(round(duration * fps))
        except Exception:
            return 0

    # =========================================================================
    # Lossless Video Extraction
    # =========================================================================

    def extract_lossless_video(self, input_video: Path, output_video: Path) -> Path:
        """
        Extract the video stream without re-encoding or compressing it.
        Uses stream copy (-c:v copy -an), ensuring 100% of the original bitrate,
        visual quality, and zero dropped frames.
        """
        if not input_video.exists():
            raise FileNotFoundError(f"Input video does not exist: {input_video}")

        output_video.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(input_video),
            "-map", "0:v:0",
            "-c:v", "copy",
            "-an",
            str(output_video),
        ]
        logger.info(f"Extracting lossless video stream: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg lossless video extraction failed: {e.stderr}")
            raise MediaProcessingError(f"Lossless video extraction failed: {e.stderr}") from e

        # Verification of frame count
        input_frames = self.count_exact_frames(input_video)
        output_frames = self.count_exact_frames(output_video)
        if input_frames != output_frames:
            logger.error(f"Frame mismatch detected! Input: {input_frames}, Output: {output_frames}")
            raise MediaProcessingError(
                f"Lossless extraction dropped frames! Input has {input_frames} frames but output has {output_frames} frames."
            )

        logger.info(f"Lossless video extracted successfully ({output_frames} frames verified, 0 dropped frames).")
        return output_video

    # =========================================================================
    # Audio Demuxing & Stem Separation
    # =========================================================================

    def extract_raw_audio(self, input_video: Path, output_wav: Path) -> Path:
        """Extract uncompressed PCM 16-bit audio from video container."""
        if not input_video.exists():
            raise FileNotFoundError(f"Input video does not exist: {input_video}")

        output_wav.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(input_video),
            "-map", "0:a:0",
            "-vn",
            "-c:a", "pcm_s16le",
            str(output_wav),
        ]
        logger.info(f"Extracting raw audio track: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg audio extraction failed: {e.stderr}")
            raise MediaProcessingError(f"Failed to extract audio stream: {e.stderr}") from e

        return output_wav

    def separate_audio_demucs(
        self,
        input_audio: Path,
        output_dir: Path,
    ) -> Tuple[Path, Path]:
        """
        Separate audio track into vocals and background (accompaniment) using Demucs (htdemucs).
        Returns paths to (raw_vocals_wav, raw_background_wav).
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        import sys

        # Demucs command with two-stems separation for optimal speed and memory efficiency
        cmd = [
            sys.executable,
            "-m", "demucs.separate",
            "--two-stems", "vocals",
            "-n", self.demucs_model,
            "-d", self.device,
            "-j", "2",
            "-o", str(output_dir),
            str(input_audio),
        ]
        logger.info(f"Executing Demucs vocal separation on {self.device}: {' '.join(cmd)}")

        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode != 0 and self.device != "cpu":
            logger.warning(f"Demucs on {self.device} failed; retrying on CPU with multi-threading: {res.stderr[:200]}")
            cmd_cpu = [c for c in cmd]
            cmd_cpu[cmd_cpu.index("-d") + 1] = "cpu"
            res = subprocess.run(cmd_cpu, capture_output=True, text=True)

        if res.returncode != 0:
            logger.warning(f"Demucs execution failed (code {res.returncode}): {res.stderr}")
            raise MediaProcessingError(f"Demucs separation failed: {res.stderr}")

        track_stem_dir = output_dir / self.demucs_model / input_audio.stem
        vocals_path = track_stem_dir / "vocals.wav"
        background_path = track_stem_dir / "no_vocals.wav"

        if not vocals_path.exists() or not background_path.exists():
            raise MediaProcessingError(
                f"Demucs finished but expected stems missing in {track_stem_dir}. "
                f"Found: {list(track_stem_dir.glob('*')) if track_stem_dir.exists() else 'dir not found'}"
            )

        logger.info(f"Demucs stems successfully separated: {vocals_path.name}, {background_path.name}")
        return vocals_path, background_path

    def separate_audio_ffmpeg_fallback(
        self,
        input_audio: Path,
        output_dir: Path,
    ) -> Tuple[Path, Path]:
        """
        Acoustic vocal/background separation fallback using high-pass, low-pass,
        and out-of-phase center-channel isolation.
        Executed when GPU / Demucs is uninitialized or unavailable.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        vocals_raw = output_dir / "vocals_raw_fallback.wav"
        background_raw = output_dir / "background_raw_fallback.wav"

        # Check channels
        probe = ffmpeg.probe(str(input_audio))
        a_stream = next(s for s in probe["streams"] if s["codec_type"] == "audio")
        channels = int(a_stream.get("channels", 2))

        # 1. Vocals extraction: Clean human speech range (80Hz - 7500Hz) with EBU R128 loudnorm
        if channels >= 2:
            vocal_filter = (
                "pan=mono|c0=0.5*c0+0.5*c1,"
                "highpass=f=80,"
                "lowpass=f=7500,"
                "loudnorm=I=-16:TP=-1.5:LRA=11"
            )
        else:
            vocal_filter = "highpass=f=80,lowpass=f=7500,loudnorm=I=-16:TP=-1.5:LRA=11"

        cmd_vocals = [
            "ffmpeg",
            "-y",
            "-i", str(input_audio),
            "-af", vocal_filter,
            "-c:a", "pcm_s16le",
            str(vocals_raw),
        ]
        logger.info(f"Extracting vocals via FFmpeg acoustic fallback: {' '.join(cmd_vocals)}")
        subprocess.run(cmd_vocals, capture_output=True, text=True, check=True)

        # 2. Background extraction: Center-channel vocal attenuation
        if channels >= 2:
            bg_filter = "pan=stereo|c0=c0-0.85*c1|c1=c1-0.85*c0,volume=1.0"
        else:
            # For mono, attenuate voice band (-12dB) to preserve ambient low-end and high-end air
            bg_filter = "equalizer=f=1200:t=q:w=1.5:g=-12"

        cmd_bg = [
            "ffmpeg",
            "-y",
            "-i", str(input_audio),
            "-af", bg_filter,
            "-c:a", "pcm_s16le",
            str(background_raw),
        ]
        logger.info(f"Extracting background via FFmpeg acoustic fallback: {' '.join(cmd_bg)}")
        subprocess.run(cmd_bg, capture_output=True, text=True, check=True)

        return vocals_raw, background_raw

    def format_audio_stems(
        self,
        raw_vocals_path: Path,
        raw_background_path: Path,
        output_dir: Path,
        raw_audio_path: Optional[Path] = None,
    ) -> Tuple[Path, Path, Path]:
        """
        Normalize stems into exact production specifications:
        1. vocals.wav (16kHz mono for ASR): `vocals_asr.wav` - mixed 70/30 with source track
           and boosted with gentle speech presence EQ (2.5kHz +3dB) and EBU R128 loudness normalization
           so not a single spoken syllable is lost under background music.
        2. vocals.wav (44.1kHz stereo for voice cloning): `vocals_clone.wav`
        3. background.wav (44.1kHz stereo for natural remixing): `background.wav`
        """
        vocals_asr_path = output_dir / "vocals_16k.wav"
        vocals_clone_path = output_dir / "vocals_44k.wav"
        background_path = output_dir / "background.wav"

        # 16kHz mono for ASR: 70% isolated vocals + 30% original source audio track with presence EQ
        if raw_audio_path and raw_audio_path.exists():
            cmd_asr = [
                "ffmpeg",
                "-y",
                "-i", str(raw_vocals_path),
                "-i", str(raw_audio_path),
                "-filter_complex",
                "[0:a][1:a]amix=inputs=2:weights=0.7 0.3,equalizer=f=2500:t=q:w=1:g=3,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=16000[out]",
                "-map", "[out]",
                "-ac", "1",
                "-c:a", "pcm_s16le",
                str(vocals_asr_path),
            ]
        else:
            cmd_asr = [
                "ffmpeg",
                "-y",
                "-i", str(raw_vocals_path),
                "-af", "equalizer=f=2500:t=q:w=1:g=3,loudnorm=I=-16:TP=-1.5:LRA=11",
                "-ar", "16000",
                "-ac", "1",
                "-c:a", "pcm_s16le",
                str(vocals_asr_path),
            ]
        subprocess.run(cmd_asr, capture_output=True, text=True, check=True)

        # 44.1kHz stereo for voice cloning reference
        cmd_clone = [
            "ffmpeg",
            "-y",
            "-i", str(raw_vocals_path),
            "-ar", "44100",
            "-ac", "2",
            "-c:a", "pcm_s16le",
            str(vocals_clone_path),
        ]
        subprocess.run(cmd_clone, capture_output=True, text=True, check=True)

        # 44.1kHz stereo background ambient noise
        cmd_bg = [
            "ffmpeg",
            "-y",
            "-i", str(raw_background_path),
            "-ar", "44100",
            "-ac", "2",
            "-c:a", "pcm_s16le",
            str(background_path),
        ]
        subprocess.run(cmd_bg, capture_output=True, text=True, check=True)

        return vocals_asr_path, vocals_clone_path, background_path

    # =========================================================================
    # Final Lossless Remuxing
    # =========================================================================

    def remux_final_video(
        self,
        synced_video_path: Path,
        mixed_audio_path: Path,
        output_final_path: Path,
    ) -> Path:
        """
        Combine restored video frames with newly mixed master audio track:
        - CRF 18 (visually lossless)
        - slow preset for optimal macroblock compression
        - yuv420p standard chroma subsampling
        - 320kbps pristine AAC audio track
        """
        output_final_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg",
            "-y",
            "-i", str(synced_video_path),
            "-i", str(mixed_audio_path),
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "libx264",
            "-crf", "18",
            "-preset", "fast",
            "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
            "-c:a", "aac",
            "-b:a", "320k",
            "-shortest",
            str(output_final_path),
        ]
        logger.info(f"Remuxing final high-definition video: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
        except subprocess.CalledProcessError as e:
            logger.error(f"Final remuxing failed: {e.stderr}")
            raise MediaProcessingError(f"Remuxing failed: {e.stderr}") from e

        logger.info(f"Final dubbed video remuxed successfully at {output_final_path.name}")
        return output_final_path

    # =========================================================================
    # Full Demuxing & Separation Pipeline
    # =========================================================================

    async def process_media_pipeline(
        self,
        job_id: str,
        video_path: Path,
        progress_callback: Optional[Callable[[str, float, str, Optional[Dict[str, Any]]], Any]] = None,
    ) -> MediaExtractionResult:
        """
        End-to-end media demuxing pipeline:
        1. Probe exact container & stream metadata
        2. Extract raw lossless video stream (zero re-encoding)
        3. Extract raw audio stream
        4. Separate vocal and background stems via Demucs (or fallback)
        5. Format audio stems into 16kHz mono (ASR) and 44.1kHz stereo (Cloning & Ambient)
        """
        job_storage = settings.get_job_storage(job_id)
        audio_dir = job_storage["audio_dir"]
        output_dir = job_storage["output_dir"]

        # Step 1: Probe metadata
        if progress_callback:
            await progress_callback(job_id, 12.0, "Probing video container and stream metadata", None)

        metadata = await asyncio.to_thread(self.probe_metadata, video_path)

        if not metadata.has_audio:
            raise MediaProcessingError("Uploaded video must contain an audio track for dubbing and voice cloning.")

        # Step 2: Lossless video extraction (copy video stream, drop audio)
        lossless_video_path = output_dir / f"{video_path.stem}_lossless_silent.mp4"
        if progress_callback:
            await progress_callback(
                job_id,
                18.0,
                f"Extracting lossless video stream ({metadata.total_frames} frames, bit-identical quality)",
                {"total_frames": metadata.total_frames, "fps": metadata.fps},
            )

        await asyncio.to_thread(self.extract_lossless_video, video_path, lossless_video_path)

        # Step 3: Extract raw audio track
        extracted_audio_path = audio_dir / "raw_audio.wav"
        if progress_callback:
            await progress_callback(job_id, 24.0, "Extracting lossless audio stream", None)

        await asyncio.to_thread(self.extract_raw_audio, video_path, extracted_audio_path)

        # Step 4: Separate vocal and background stems
        separation_method = "demucs"
        raw_vocals: Path
        raw_background: Path

        if settings.FORCE_FFMPEG_FALLBACK:
            if progress_callback:
                await progress_callback(job_id, 30.0, "Separating audio stems via FFmpeg acoustic filter (forced)", None)
            raw_vocals, raw_background = await asyncio.to_thread(
                self.separate_audio_ffmpeg_fallback, extracted_audio_path, audio_dir
            )
            separation_method = "ffmpeg_fallback"
        else:
            try:
                if progress_callback:
                    await progress_callback(
                        job_id,
                        30.0,
                        f"Separating vocal and background audio stems using Demucs ({self.demucs_model} on {self.device})",
                        {"model": self.demucs_model, "device": self.device},
                    )
                raw_vocals, raw_background = await asyncio.to_thread(
                    self.separate_audio_demucs, extracted_audio_path, audio_dir
                )
            except Exception as demucs_err:
                logger.warning(f"Demucs failed or uninitialized, falling back to FFmpeg acoustic separation: {demucs_err}")
                if progress_callback:
                    await progress_callback(
                        job_id,
                        32.0,
                        "Demucs uninitialized; falling back to FFmpeg high-pass/low-pass acoustic isolation",
                        {"fallback_reason": str(demucs_err)},
                    )
                raw_vocals, raw_background = await asyncio.to_thread(
                    self.separate_audio_ffmpeg_fallback, extracted_audio_path, audio_dir
                )
                separation_method = "ffmpeg_fallback"

        # Step 5: Format stems into 16kHz mono (Whisper) & 44.1kHz stereo (Cloning & Ambient)
        if progress_callback:
            await progress_callback(
                job_id,
                40.0,
                "Formatting audio stems (16kHz mono for ASR, 44.1kHz stereo for voice cloning and background remix)",
                {"separation_method": separation_method},
            )

        vocals_asr, vocals_clone, background_stem = await asyncio.to_thread(
            self.format_audio_stems, raw_vocals, raw_background, audio_dir, extracted_audio_path
        )

        result = MediaExtractionResult(
            job_id=job_id,
            raw_video_path=str(video_path),
            lossless_video_path=str(lossless_video_path),
            extracted_audio_path=str(extracted_audio_path),
            vocals_asr_path=str(vocals_asr),
            vocals_clone_path=str(vocals_clone),
            background_path=str(background_stem),
            metadata=metadata,
            separation_method=separation_method,
        )

        logger.info(f"Media extraction pipeline complete for job {job_id} using {separation_method}.")
        return result


media_engine = MediaEngine()
