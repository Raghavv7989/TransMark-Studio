# TransMark Studio

> **Instagram Reels-Inspired AI Auto-Translation, Context-Aware Vernacular Dubbing, and Zero-Damage Neural Lip-Sync Platform**

TransMark Studio is an industry-grade, end-to-end AI platform engineered for automated video localization, zero-shot voice cloning with speaker register matching, and high-fidelity zero-damage neural lip-syncing. Designed to match Meta's Instagram Reels Auto-Translate standard, TransMark translates fast-paced creator videos into authentic Indian vernacular and international languages (**Telugu**, **Hindi**, **Tamil**, **Spanish**, **French**, and **English**) while preserving the original video resolution, speaker timbre, and video quality without degrading upper facial expressions or 4K/1080p backgrounds.

---

## ⚡ Key Highlights & Capabilities

- **Zero-Damage Lower-Face Lip-Sync**: Modifies *strictly* the lower facial landmarks (mouth, lips, jawline) with CodeFormer/GFPGAN texture restoration and Gaussian feathered Poisson blending. Upper face, eyes, hair, clothes, and 1080p/4K background remain 100% bit-identical.
- **Resting-Lip Silence Suppression**: When dubbed dialogue has pauses, mouth aperture is smoothly compressed to neutral closed/resting lips ($0.82\text{x}$) with temporal exponential smoothing, eliminating ghost mouth flapping from the original video.
- **Authentic Code-Switched Indian Creator Localization ("Telugish" / "Hinglish")**: Technical terms (`SRM University`, `Machine Learning`, `XGBoost`, `RAG Pipeline`, `Dynamic Programming`) remain in clean Latin script, while conversational dialogue uses pure native Unicode script ending with complete natural spoken verbs. Archaic textbook conjunctions (e.g. stiff `"మరియు"`) are strictly eliminated.
- **Bilingual Indian Neural TTS & Pitch Profile Matching**: Routes Telugu (`te`), Hindi (`hi`), and Tamil (`ta`) to bilingual neural models (`te-IN-MohanNeural` / `te-IN-ShrutiNeural`, `hi-IN-MadhurNeural`, etc.) with fundamental frequency ($F_0$) pitch matching against the speaker's vocal register. Unvoiced consonants and soft word endings (`"చేస్తున్నాను"`, `"సిస్టమ్"`) are protected via $-55\,\text{dB}$ silence trimming and $120\,\text{ms}$ tail padding.
- **Dynamic Smart Ducking**: Dialogue timeline is mastered at $-1.0\,\text{dB}$ true-peak headroom with automated dynamic background ducking ($-14\,\text{dB}$ during speech, $60\%$ during natural pauses).

---

## 🏛 System Architecture Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                             TRANSMARK STUDIO                                │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
   1. LOSSLESS DEMUXING & NEURAL VOCAL SEPARATION
   ├── Video Demux: FFmpeg lossless stream copy (100% bit-identical frames)
   └── Stem Separation: PyTorch htdemucs (70/30 vocal-to-background isolation)
                                      │
   2. PRECISION ACOUSTIC ALIGNMENT & ASR
   ├── Multi-Tier Whisper: faster-whisper (MPS / CUDA / CPU) with VAD filter
   └── Phrasing Parser: Splits clauses by >300ms acoustic pause boundaries
                                      │
   3. FULL-DISCOURSE ISOCHRONIC TRANSLATION
   ├── Frontier LLM: Google Gemini 2.5/3 Flash / OpenAI GPT-4o-mini
   ├── Dual-Script Code-Switching: English technical terms + Native Unicode verbs
   └── Indic Akshara Counter: Orthographic syllable estimator (\u0C00-\u0C7F & \u0900-\u097F)
                                      │
   4. PROSODY-LOCKED NEURAL SYNTHESIS & VOICE CLONING
   ├── Voice Engine: Bilingual Microsoft Edge Neural TTS / ElevenLabs Multilingual v2
   ├── Speaker F0 Delta Profiling: Vocal fundamental frequency pitch shift (±30 Hz)
   ├── Dynamic Time-Stretch: Clamped atempo (0.90x–1.15x) + 120ms protective tail pad
   └── Broadcast Audio Mastering: -14 dB background ducking + -1.0 dB true-peak limiter
                                      │
   5. ZERO-DAMAGE LIP-SYNC & FACE RESTORATION
   ├── Viseme Modulator: Dynamic aperture expansion (1.05x–1.38x) matching audio RMS
   ├── Silence Suppression: Neutral closed-lip resting state during pauses (< 0.012 RMS)
   ├── Patch Restoration: CodeFormer / GFPGAN high-frequency unsharp skin filtering
   └── Boundary Blend: Gaussian elliptical feather mask + Poisson seamless cloning
                                      │
   6. HIGH-FIDELITY MASTER REMUXING
   └── Visually lossless H.264 encode (CRF 18 fast preset, 320k stereo AAC audio)
```

---

## 🛠 Tech Stack

| Layer | Technologies |
| :--- | :--- |
| **Backend API** | FastAPI, Python 3.12, Uvicorn, Pydantic V2, WebSockets, `aiofiles`, `httpx` |
| **Audio & Media** | FFmpeg 9.0+, PyTorch `demucs` (`htdemucs`), `faster-whisper`, `librosa`, `soundfile`, `pydub` |
| **Speech & Translation** | Google Gemini 2.5/3 Flash, ElevenLabs Multilingual v2, Microsoft Edge Neural TTS, Indic Akshara Syllable Counter |
| **Vision & Lip-Sync** | OpenCV, NumPy, Haar Cascade Facial Geometry, CodeFormer / GFPGAN restoration, Sync Labs v2 API |
| **Frontend Studio UI** | React 18, TypeScript, Vite, Tailwind CSS, Framer Motion, Lucide Icons |
| **Mobile & Native Bridge** | Capacitor (iOS & Android native container configuration, PWA manifest) |

---

## ⚡ Quickstart

### 1. Prerequisites
- **macOS / Linux** with Python 3.12+ and Node.js 18+ installed.
- **FFmpeg**:
  ```bash
  # macOS (Homebrew)
  brew install ffmpeg

  # Ubuntu / Debian
  sudo apt-get install -y ffmpeg
  ```

### 2. Configure Environment Variables
Copy the example environment file to both root and `backend/.env`:
```bash
cp .env.example .env
cp .env.example backend/.env
```

Edit `backend/.env` with your API credentials (or run in offline heuristic mode):
```bash
# Frontier LLM for Isochronic Dubbing Translation
GEMINI_API_KEY=your_gemini_api_key_here
# Optional: ElevenLabs for Western voice cloning (en, es, fr)
ELEVENLABS_API_KEY=your_elevenlabs_api_key_here
# Optional: Sync Labs Cloud GPU for remote lip-sync
SYNCLABS_API_KEY=your_synclabs_api_key_here
```

### 3. Launch TransMark Studio (One Command)
Start both backend and frontend services with pre-flight dependency checks and automatic port management:
```bash
./start_studio.sh
```

- **Studio Web Interface:** [http://localhost:5173](http://localhost:5173)
- **FastAPI REST API:** [http://localhost:8000](http://localhost:8000)
- **Swagger Documentation:** [http://localhost:8000/docs](http://localhost:8000/docs)
- **System Health & AI Engine Telemetry:** [http://localhost:8000/api/v1/system/health](http://localhost:8000/api/v1/system/health)

Press `Ctrl+C` in the terminal to gracefully stop all services.

---

## 🧪 Testing & Verification

Run the automated test suite across all media processing, translation, and lip-sync modules:

```bash
# 1. Run all backend unit & integration tests
PYTHONPATH=backend backend/.venv/bin/pytest backend/tests/ -v

# 2. Verify lossless FFmpeg demuxing and frame preservation
PYTHONPATH=backend backend/.venv/bin/python backend/tests/verify_lossless_demux.py

# 3. Verify end-to-end voice synthesis and lip-sync pipeline
PYTHONPATH=backend backend/.venv/bin/python backend/test_production_verification.py

# 4. Verify frontend build
cd frontend && npm run build
```

---

## 📂 Project Structure

```
TransMark/
├── .env.example                # Documented production AI keys & fallback flags
├── .gitignore                  # Git rules preventing secrets and heavy binaries
├── README.md                   # Platform documentation & architecture guide
├── start_studio.sh             # One-command orchestration script (macOS/Linux)
│
├── backend/                    # Python 3.12 + FastAPI Backend
│   ├── app/
│   │   ├── api/v1/             # Projects, Curation, System Health & WebSockets
│   │   ├── core/               # Configuration, logging, WebSocket manager
│   │   ├── models/             # Pydantic V2 models (Jobs, Stems, Segments)
│   │   ├── services/           # MediaEngine, Transcription, Translator,
│   │   │                       # VoiceSynthesisEngine, ZeroDamageLipSyncEngine
│   │   └── storage/            # Local storage (raw, stems, frames, outputs)
│   ├── tests/                  # Automated pytest suite and verification scripts
│   ├── requirements.txt        # Python dependencies
│   └── main.py                 # FastAPI application entry point
│
└── frontend/                   # React 18 + TypeScript + Vite + Tailwind CSS
    ├── public/                 # PWA manifest.json and icons
    ├── capacitor.config.json   # iOS & Android native wrapper configuration
    ├── src/
    │   ├── components/         # Studio Header, VideoStage, CurationTimeline,
    │   │                       # ProcessingHUD, LanguageSelector, Dropzone
    │   ├── utils/              # Indic Akshara syllable counter, API & WS clients
    │   └── App.tsx             # Responsive split-screen editing workspace
    └── package.json
```

---

## 📱 Mobile App Generation (Capacitor)

The TransMark frontend is designed with responsive mobile layouts and supports vertical 9:16 Instagram Reels. To build native mobile applications:

```bash
cd frontend
npm run build
npx cap add ios
npx cap add android
npx cap copy
npx cap open ios      # Opens native Xcode project
npx cap open android  # Opens Android Studio project
```

---

## 📄 License

MIT License. Designed and engineered for high-craft creator workflows.
