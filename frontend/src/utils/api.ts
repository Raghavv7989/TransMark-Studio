import {
  IsochronicSegment,
  JobProgressUpdate,
  JobStatus,
  ProjectUploadResponse,
} from "../types";

// Base API configuration
const getApiBase = () => {
  return "/api/v1";
};

export const API_BASE = getApiBase();

const VALID_STATUSES: JobStatus[] = [
  "UPLOADING",
  "SEPARATING_AUDIO",
  "TRANSCRIBING",
  "CURATING_TRANSLATION",
  "CLONING_VOICE",
  "LIP_SYNCING",
  "REMUXING",
  "COMPLETED",
  "FAILED",
];

/**
 * Normalizes raw payload from either WebSocket messages or HTTP polling responses
 * into a strictly typed JobProgressUpdate.
 */
export function normalizeProgressUpdate(
  raw: any,
  fallbackJobId?: string
): JobProgressUpdate | null {
  if (!raw || typeof raw !== "object") return null;

  // Filter out internal WebSocket heartbeat frames
  if (raw.type === "pong" || raw.type === "ping") {
    return null;
  }

  const rawProgress = raw.progress ?? raw.percentage ?? raw.percent;
  const safeProgress = Number.isFinite(Number(rawProgress))
    ? Math.min(100, Math.max(0, Number(rawProgress)))
    : 0;

  const rawStatus = String(raw.status || raw.state || raw.stage || "UPLOADING").toUpperCase();
  const safeStatus: JobStatus = VALID_STATUSES.includes(rawStatus as JobStatus)
    ? (rawStatus as JobStatus)
    : "UPLOADING";

  const subtask =
    raw.subtask ||
    raw.message ||
    raw.detail ||
    raw.details?.subtask ||
    "Executing pipeline stage...";

  const jobId = raw.job_id || raw.jobId || fallbackJobId || "";

  return {
    job_id: jobId,
    status: safeStatus,
    progress: safeProgress,
    subtask: subtask,
    timestamp: raw.timestamp || new Date().toISOString(),
    details: raw.details,
    error: raw.error || null,
  };
}

export async function uploadVideo(
  file: File,
  targetLanguage: string = "te"
): Promise<ProjectUploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("target_language", targetLanguage);

  const res = await fetch(`${API_BASE}/projects/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || `Upload failed with status ${res.status}`);
  }

  return res.json();
}

export async function getProjectStatus(jobId: string) {
  const res = await fetch(`${API_BASE}/projects/${jobId}`);
  if (!res.ok) {
    throw new Error(`Failed to fetch project status for ${jobId}`);
  }
  return res.json();
}

export async function pollJobStatus(jobId: string): Promise<JobProgressUpdate | null> {
  try {
    const res = await fetch(`${API_BASE}/projects/${jobId}/status`);
    if (!res.ok) return null;
    const data = await res.json();
    return normalizeProgressUpdate(data, jobId);
  } catch (err) {
    return null;
  }
}

export async function getSegments(jobId: string): Promise<IsochronicSegment[]> {
  const res = await fetch(`${API_BASE}/projects/${jobId}/segments`);
  if (!res.ok) {
    if (res.status === 425) {
      return []; // Still processing
    }
    throw new Error(`Failed to fetch segments for ${jobId}`);
  }
  const data = await res.json();
  return data.segments || [];
}

export async function updateSegments(
  jobId: string,
  segments: { segment_id: number; target_text?: string; phonetic_text?: string }[]
): Promise<IsochronicSegment[]> {
  const res = await fetch(`${API_BASE}/projects/${jobId}/segments`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ segments }),
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to update segment curation");
  }

  const data = await res.json();
  return data.segments || [];
}

export async function triggerSynthesize(jobId: string) {
  const res = await fetch(`${API_BASE}/projects/${jobId}/synthesize`, {
    method: "POST",
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || "Failed to trigger synthesis");
  }

  return res.json();
}

export function getArtifactUrl(jobId: string, artifactType: string, cacheBust: boolean = true): string {
  const base = `${API_BASE}/projects/${jobId}/artifacts/${artifactType}`;
  return cacheBust ? `${base}?v=${Date.now()}` : base;
}

/**
 * Dual-Mode Progress Listener:
 * 1. Establishes primary WebSocket connection to /ws/progress/{job_id}.
 * 2. Concurrently runs 1000ms HTTP polling fallback to /api/v1/projects/{job_id}/status.
 * 3. Normalizes payloads & ignores heartbeats, preventing NaN% or blank UI.
 */
export function connectProgressWebSocket(
  jobId: string,
  onUpdate: (update: JobProgressUpdate) => void,
  onError?: (err: Event) => void
): () => void {
  let isCleanedUp = false;
  let socket: WebSocket | null = null;
  let heartbeatTimer: any = null;
  let pollTimer: any = null;

  const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
  const host = window.location.host;
  const wsUrl = `${protocol}//${host}/ws/progress/${jobId}`;

  // 1. HTTP Polling Fallback (runs every 1000ms alongside WebSocket)
  const executePoll = async () => {
    if (isCleanedUp) return;
    const update = await pollJobStatus(jobId);
    if (update && !isCleanedUp) {
      onUpdate(update);
      if (update.status === "COMPLETED" || update.status === "FAILED") {
        if (pollTimer) clearInterval(pollTimer);
      }
    }
  };

  // Immediate initial poll
  executePoll();
  pollTimer = setInterval(executePoll, 1000);

  // 2. Primary WebSocket Listener
  try {
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      // Heartbeat ping every 20 seconds
      heartbeatTimer = setInterval(() => {
        if (socket && socket.readyState === WebSocket.OPEN) {
          socket.send("ping");
        }
      }, 20000);
    };

    socket.onmessage = (event) => {
      if (isCleanedUp) return;
      try {
        const raw = JSON.parse(event.data);
        const update = normalizeProgressUpdate(raw, jobId);
        if (update) {
          onUpdate(update);
        }
      } catch (e) {
        console.warn("Invalid WebSocket payload", event.data);
      }
    };

    socket.onerror = (e) => {
      console.warn("WebSocket temporary error (HTTP polling active fallback):", e);
      onError?.(e);
    };

    socket.onclose = () => {
      if (heartbeatTimer) clearInterval(heartbeatTimer);
    };
  } catch (err) {
    console.warn("Failed to instantiate WebSocket, continuing with HTTP polling fallback:", err);
  }

  // Cleanup handler
  return () => {
    isCleanedUp = true;
    if (pollTimer) clearInterval(pollTimer);
    if (heartbeatTimer) clearInterval(heartbeatTimer);
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.close();
    }
  };
}
