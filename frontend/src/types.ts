export type JobStatus =
  | "UPLOADING"
  | "SEPARATING_AUDIO"
  | "TRANSCRIBING"
  | "CURATING_TRANSLATION"
  | "CLONING_VOICE"
  | "LIP_SYNCING"
  | "REMUXING"
  | "COMPLETED"
  | "FAILED";

export interface WordTimestamp {
  word: string;
  start_ms: number;
  end_ms: number;
  start_time: number;
  end_time: number;
  confidence: number;
}

export interface IsochronicSegment {
  segment_id: number;
  start_time: number;
  end_time: number;
  start_ms: number;
  end_ms: number;
  duration_budget: number;
  source_text: string;
  target_text: string;
  phonetic_text: string;
  original_syllables: number;
  target_syllables: number;
  pacing_ratio: number;
  fit_status: "FITS" | "TOO_LONG" | "TOO_SHORT" | "PENDING";
  tolerance_pct: number;
  speaker_id?: string;
  words?: WordTimestamp[];
  is_curated?: boolean;
}

export interface VideoMetadata {
  duration_seconds: number;
  width: number;
  height: number;
  fps: number;
  total_frames: number;
  video_codec: string;
  has_audio: boolean;
  audio_sample_rate?: number;
  audio_codec?: string;
  file_size_bytes?: number;
}

export interface JobProgressUpdate {
  job_id: string;
  status: JobStatus;
  progress: number;
  subtask: string;
  timestamp: string;
  details?: Record<string, any>;
  error?: string | null;
}

export interface ProjectUploadResponse {
  job_id: string;
  filename: string;
  status: JobStatus;
  ws_url: string;
  message: string;
}

export interface LanguageOption {
  code: string;
  name: string;
  script: string;
  nativeBadge: string;
  samplePhonetic: string;
}

export const SUPPORTED_LANGUAGES: LanguageOption[] = [
  {
    code: "te",
    name: "Telugu",
    script: "తెలుగు",
    nativeBadge: "తెలుగు",
    samplePhonetic: "Teluglish",
  },
  {
    code: "hi",
    name: "Hindi",
    script: "हिन्दी",
    nativeBadge: "हिन्दी",
    samplePhonetic: "Hinglish",
  },
  {
    code: "ta",
    name: "Tamil",
    script: "தமிழ்",
    nativeBadge: "தமிழ்",
    samplePhonetic: "Tanglish",
  },
  {
    code: "es",
    name: "Spanish",
    script: "Español",
    nativeBadge: "Español",
    samplePhonetic: "Castilian",
  },
  {
    code: "fr",
    name: "French",
    script: "Français",
    nativeBadge: "Français",
    samplePhonetic: "Standard",
  },
  {
    code: "en",
    name: "English",
    script: "English",
    nativeBadge: "English",
    samplePhonetic: "US",
  },
];
