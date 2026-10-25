# TransMark - Production AI Video Dubbing & Lip-Sync Platform

A production-grade AI platform for automated video translation, voice cloning, and neural lip-syncing (similar to Instagram Reels Auto-Translate).

---

## 🏗 Architecture Overview

```
backend/
├── app/
│   ├── api/                    # API Routing & WebSockets
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   └── projects.py     # POST /upload, GET /:id, GET /:id/artifacts/:type
│   │   ├── websockets.py       # WS /ws/progress/{job_id} endpoint
│   │   └── __init__.py
│   ├── core/                   # Core platform configuration
│   │   ├── config.py           # Pydantic Settings & storage directory setup
│   │   ├── logging.py          # Structured production logging
│   │   ├── ws_manager.py       # Real-time WebSocket connection manager
│   │   └── __init__.py
│   ├── models/                 # Strict Pydantic V2 validation schemas
│   │   ├── job.py              # JobStatus enum & JobProgressUpdate schema
│   │   ├── media.py            # VideoMetadata & MediaExtractionResult
│   │   ├── project.py          # Project request & response payloads
│   │   └── __init__.py
│   ├── services/               # Core media & AI engine services
│   │   ├── media_engine.py     # Lossless FFmpeg wrapper & Demucs separation
│   │   ├── orchestrator.py     # Asynchronous task pipeline coordinator
│   │   ├── asr.py              # Speech recognition interface (Mission 2)
│   │   ├── translation.py      # LLM Translation & Cadence Curation (Mission 2)
│   │   ├── tts.py              # Zero-shot voice cloning interface (Mission 3)
│   │   ├── lipsync.py          # Neural lip-sync synthesis interface (Mission 4)
│   │   └── __init__.py
│   └── storage/                # Local temp storage
│       ├── raw/                # Uploaded video storage
│       ├── audio_segments/     # Separated vocals and background stems
│       ├── video_frames/       # Frame sequences for neural models
│       └── outputs/            # Lossless silent videos & dubbed outputs
├── tests/
│   ├── verify_lossless_demux.py # Zero-frame-drop lossless demux verification
│   ├── test_media_engine.py    # Unit & pipeline tests
│   └── test_api.py             # FastAPI HTTP & WebSocket tests
├── main.py                     # Application entry point & Lifespan manager
└── requirements.txt            # Production dependencies
```

---

## 🚀 Key Pipeline Lifecycle States

Every job moves through strict lifecycle states streamed via WebSockets:

1. `UPLOADING` (0-10%): Video file received and storage allocated.
2. `SEPARATING_AUDIO` (10-45%):
   - **Lossless Stream Copy**: Extracts video stream without re-encoding (`-c:v copy -an`), preserving 100% of original bitrate, visual quality, and frame count.
   - **Demucs Stem Separation**: Isolates vocals and background accompaniment (`htdemucs`).
   - **Acoustic Fallback**: Intelligent high-pass/low-pass center-channel isolation if GPU/Demucs is uninitialized.
   - **Stem Normalization**:
     - `vocals_16k.wav` (16kHz mono `pcm_s16le` for Whisper ASR)
     - `vocals_44k.wav` (44.1kHz stereo `pcm_s16le` for voice cloning)
     - `background.wav` (44.1kHz stereo `pcm_s16le` for ambient remixing)
3. `TRANSCRIBING` (55%): ASR acoustic transcription (staged for Mission 2).
4. `CURATING_TRANSLATION` (65%): Syllable cadence & subtitle curation (Mission 2).
5. `CLONING_VOICE` (75%): Zero-shot timbre synthesis (Mission 3).
6. `LIP_SYNCING` (88%): Wav2Lip / MuseTalk mouth animation (Mission 4).
7. `REMUXING` (95%): Lossless remux of ambient background + dubbed audio with video.
8. `COMPLETED` (100%): Output ready for download.
9. `FAILED`: Unhandled error capture with stack trace and message broadcast.

---

## 🛠 Quickstart

### 1. Installation
```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Run Zero-Frame-Drop Verification
```bash
python tests/verify_lossless_demux.py
```

### 3. Run Mission 2 Live E2E (ASR, Isochronic Translation & Curation API)
```bash
python tests/verify_e2e_ws.py
```

### 4. Run Mission 3 Live E2E (Voice Cloning, Time-Alignment, Zero-Damage Lip-Sync & Remuxing)
```bash
python tests/verify_mission3_e2e.py
```

### 5. Run Full Test Suite (26 Automated Tests)
```bash
pytest tests/ -v
```

### 6. Start Backend Server
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
Interactive API docs available at `http://localhost:8000/docs`.

---

## 🎭 Mission 3: Voice Cloning, Time-Alignment & Zero-Damage Lip-Sync

### 1. Segmented Voice Cloning (`app/services/voice_synthesis.py`)
- Modular zero-shot voice cloning supporting **ElevenLabs Multilingual v2** and localized timbre matching using the isolated vocal reference stem (`vocals_44k.wav`).
- **Dynamic Audio Time-Alignment**: Measures synthesized audio length against the segment's duration budget ($\text{end\_ms} - \text{start\_ms}$). Applies pitch-invariant phase vocoder time-stretching/compression ($\pm 50\%$) and guarantees exact sample-accurate duration matching.
- **Master Timeline & Ambient Remixing**: Stitches aligned segments onto a master dialogue track and blends it with the original `background.wav` ambient stem at calibrated volume levels ($0.70$ / $-3\text{dB}$) to retain natural room acoustics.

### 2. Zero-Damage Lip-Sync Engine (`app/services/lipsync_engine.py`)
- **Zero-Damage Spatial Constraint**: Uses facial geometry to detect strictly the lower facial bounding box (mouth and jaw). Upper face, eyes, forehead, hair, and video background are **100% bit-identical and untouched**.
- **Acoustic Phoneme Kinematics**: Modulates mouth aperture and phoneme kinematics synchronized to the aligned audio track.
- **CodeFormer / GFPGAN Restoration Pass**: High-frequency restoration applied strictly to the mouth bounding box to eliminate blurriness and match the texture and grain of 4K/1080p source video.
- **Seamless Blending**: Gaussian-feathered elliptical alpha masking and Poisson seamless cloning eliminate harsh seams and color banding.

### 3. Visually Lossless FFmpeg Remuxing
- Combines restored frames with the mixed master audio using `-c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p -c:a aac -b:a 320k`.
- Triggered asynchronously via `POST /api/v1/projects/{job_id}/synthesize`, streaming live progress over WebSockets.

---

## 🎙 Mission 2: Transcription & Isochronic Translation Engine

### 1. Precision ASR (`app/services/transcription.py`)
- Integrated `faster-whisper` extracting word-level alignment timestamps (`start_ms`, `end_ms`, `confidence`).
- Intelligently groups tokens into natural phrasing segments wherever pauses exceed **300ms** or upon sentence boundary punctuation.

### 2. Multi-Lingual Syllable Pacing (`app/services/syllables.py`)
- Custom syllable estimator supporting Brahmic abugidas (Telugu, Hindi, Tamil, Kannada, Malayalam, Bengali) by computing aksharas (independent vowels and consonants minus viramas/halants).
- Latin phonology accounting for vowel clusters, hiatus pairs (`vid-e-o`, `ra-di-o`), and silent word-final vowels.
- Computes `pacing_ratio` and enforces a strict **±10% duration tolerance margin** (`FITS`, `TOO_LONG`, `TOO_SHORT`).

### 3. Isochronic LLM Translation (`app/services/translator.py`)
- Replaces literal translations with duration-budgeted vernacular adaptations for Telugu (`te`), Hindi (`hi`), Tamil (`ta`), Spanish (`es`), French (`fr`), and English (`en`).
- Supplies LLM with `duration_seconds` (`(end_ms - start_ms) / 1000.0`), `original_syllable_count`, and target language script specifications.
- Produces **native script** (e.g., Telugu, Devanagari) alongside **conversational Romanized phonetic script** (e.g., Teluglish, Hinglish) for voice cloning and neural lip-sync.

### 4. Human-in-the-Loop Curation API (`app/api/curation.py`)
- `GET /api/v1/projects/{job_id}/segments`: Returns time-coded segment arrays with source/target texts, phonetic pronunciations, syllable counts, and pacing budgets.
- `PUT /api/v1/projects/{job_id}/segments`: Allows frontends to edit words, automatically recalculating target syllable counts, pacing ratios, and duration budget fit status.
