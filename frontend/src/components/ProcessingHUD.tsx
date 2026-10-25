import React from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  CheckCircle2,
  Clock,
  Cpu,
  Sparkles,
  Volume2,
  Smile,
  Film,
} from "lucide-react";
import { JobProgressUpdate, JobStatus } from "../types";

interface ProcessingHUDProps {
  progressUpdate: JobProgressUpdate | null;
  jobId?: string | null;
  onDismiss?: () => void;
}

interface StepInfo {
  status: JobStatus;
  title: string;
  icon: React.ComponentType<{ className?: string }>;
}

const PIPELINE_STEPS: StepInfo[] = [
  { status: "SEPARATING_AUDIO", title: "Lossless Audio Demuxing & Stem Separation", icon: Volume2 },
  { status: "TRANSCRIBING", title: "Precision Whisper ASR & 300ms Pause Phrasing", icon: Clock },
  { status: "CURATING_TRANSLATION", title: "Isochronic Vernacular Syllable Matching", icon: Sparkles },
  { status: "CLONING_VOICE", title: "Zero-Shot Voice Cloning & Time-Alignment", icon: Cpu },
  { status: "LIP_SYNCING", title: "Zero-Damage Lower-Face Landmarks & MuseTalk", icon: Smile },
  { status: "REMUXING", title: "CodeFormer Restoration & CRF 18 Remuxing", icon: Film },
  { status: "COMPLETED", title: "Master Dubbed & Lip-Synced Video Ready", icon: CheckCircle2 },
];

export const ProcessingHUD: React.FC<ProcessingHUDProps> = ({
  progressUpdate,
  jobId,
  onDismiss,
}) => {
  // If neither progressUpdate nor jobId is present, do not render
  if (!progressUpdate && !jobId) return null;

  const effectiveJobId = progressUpdate?.job_id || jobId || "INITIALIZING...";
  const rawProgress = progressUpdate?.progress;
  const safeProgress = Number.isFinite(Number(rawProgress))
    ? Math.min(100, Math.max(0, Math.round(Number(rawProgress))))
    : 0;

  const currentStatus: JobStatus = (progressUpdate?.status as JobStatus) || "UPLOADING";
  const subtaskMessage = progressUpdate?.subtask || "Executing pipeline stage...";
  const isFinished = currentStatus === "COMPLETED" || safeProgress === 100;
  const isFailed = currentStatus === "FAILED";

  const getStepState = (stepStatus: JobStatus): "done" | "active" | "pending" => {
    const order: JobStatus[] = [
      "UPLOADING",
      "SEPARATING_AUDIO",
      "TRANSCRIBING",
      "CURATING_TRANSLATION",
      "CLONING_VOICE",
      "LIP_SYNCING",
      "REMUXING",
      "COMPLETED",
    ];
    const currentIndex = order.indexOf(currentStatus);
    const stepIndex = order.indexOf(stepStatus);

    if (isFinished) return "done";
    if (currentIndex === -1) {
      return stepIndex === 0 ? "active" : "pending";
    }
    if (stepIndex < currentIndex) return "done";
    if (stepIndex === currentIndex) return "active";
    return "pending";
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 bg-carbon/60 backdrop-blur-sm flex items-center justify-center p-4 select-none"
      >
        <motion.div
          initial={{ scale: 0.95, y: 12 }}
          animate={{ scale: 1, y: 0 }}
          exit={{ scale: 0.95, y: 12 }}
          transition={{ type: "spring", stiffness: 300, damping: 30 }}
          className="w-full max-w-lg bg-surface-card hairline-border rounded-studio shadow-floating-bar p-6 overflow-hidden relative"
        >
          {/* Header & Percentage */}
          <div className="flex items-start justify-between mb-4">
            <div>
              <div className="flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-signal-orange animate-ping" />
                <h3 className="text-sm font-bold text-carbon tracking-tight uppercase font-mono">
                  Telemetry Processing HUD
                </h3>
              </div>
              <p className="text-xs text-stone-muted mt-1 font-mono text-[11px] truncate max-w-sm">
                Job ID: {effectiveJobId}
              </p>
            </div>

            {/* Big Monospace Progress Counter */}
            <div className="text-right">
              <span className="text-2xl font-mono font-bold text-carbon tabular-nums">
                {safeProgress}%
              </span>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="w-full h-2 bg-alabaster hairline-border rounded-full overflow-hidden mb-5">
            <motion.div
              animate={{ width: `${safeProgress}%` }}
              transition={{ type: "spring", stiffness: 300, damping: 30 }}
              className={`h-full rounded-full ${
                isFailed ? "bg-red-500" : isFinished ? "bg-emerald-sync" : "bg-signal-orange"
              }`}
            />
          </div>

          {/* Active Subtask Log Readout */}
          <div className="p-2.5 bg-alabaster hairline-border rounded-tactile mb-5 font-mono text-xs text-carbon flex items-start gap-2">
            <span className="text-signal-orange shrink-0 mt-0.5">❯</span>
            <span className="leading-relaxed">{subtaskMessage}</span>
          </div>

          {/* Pipeline Stage Checklist */}
          <div className="space-y-2 mb-6">
            {PIPELINE_STEPS.map((step) => {
              const state = getStepState(step.status);
              const StepIcon = step.icon;

              return (
                <div
                  key={step.status}
                  className={`flex items-center justify-between px-3 py-2 rounded-tactile hairline-border text-xs font-mono transition-colors ${
                    state === "active"
                      ? "bg-signal-orange-tint border-signal-orange text-carbon font-semibold"
                      : state === "done"
                      ? "bg-alabaster/60 text-stone-muted border-hairline/60"
                      : "bg-surface-card text-stone-light border-transparent"
                  }`}
                >
                  <div className="flex items-center gap-2.5">
                    <StepIcon
                      className={`w-3.5 h-3.5 ${
                        state === "active"
                          ? "text-signal-orange"
                          : state === "done"
                          ? "text-emerald-sync"
                          : "text-stone-light"
                      }`}
                    />
                    <span>{step.title}</span>
                  </div>

                  {state === "done" && (
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-sync" />
                  )}
                  {state === "active" && (
                    <span className="w-1.5 h-1.5 rounded-full bg-signal-orange animate-ping" />
                  )}
                </div>
              );
            })}
          </div>

          {/* Dismiss or Completion Button */}
          {isFinished && (
            <motion.button
              whileTap={{ scale: 0.98 }}
              onClick={onDismiss}
              className="w-full py-2.5 rounded-tactile bg-emerald-sync hover:bg-emerald-600 text-alabaster font-semibold text-xs tracking-wide uppercase shadow-tactile transition-colors cursor-pointer"
            >
              View Dubbed Master Video
            </motion.button>
          )}

          {/* Active processing background dismiss */}
          {!isFinished && !isFailed && onDismiss && (
            <div className="mt-3 text-center">
              <button
                type="button"
                onClick={onDismiss}
                className="text-[11px] text-stone-muted hover:text-carbon font-mono underline transition-colors cursor-pointer"
              >
                Inspect segments in timeline while synthesis runs in background ❯
              </button>
            </div>
          )}

          {isFailed && (
            <div className="flex gap-2">
              <button
                onClick={onDismiss}
                className="w-full py-2.5 rounded-tactile bg-carbon text-alabaster font-semibold text-xs tracking-wide uppercase cursor-pointer"
              >
                Close & Retry
              </button>
            </div>
          )}
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
};
