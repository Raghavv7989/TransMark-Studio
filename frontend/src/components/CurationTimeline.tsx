import React, { useState, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Sparkles,
  CheckCircle2,
  AlertTriangle,
  Play,
  Languages,
} from "lucide-react";
import { IsochronicSegment } from "../types";
import { formatTimecode, formatDurationBudget } from "../utils/time";
import { countSyllables, evaluateFit } from "../utils/syllables";

interface CurationTimelineProps {
  segments: IsochronicSegment[];
  currentTime: number;
  onSeekToSegment: (startTime: number) => void;
  onUpdateSegment: (segmentId: number, targetText: string, phoneticText: string) => void;
  onTriggerSynthesize: () => void;
  isSynthesizing: boolean;
  targetLanguageName: string;
}

export const CurationTimeline: React.FC<CurationTimelineProps> = ({
  segments,
  currentTime,
  onSeekToSegment,
  onUpdateSegment,
  onTriggerSynthesize,
  isSynthesizing,
  targetLanguageName,
}) => {
  // Local state for fast typing without input cursor lag
  const [localTexts, setLocalTexts] = useState<Record<number, { target: string; phonetic: string }>>({});

  // Initialize or update local state when segments change
  useEffect(() => {
    const initial: Record<number, { target: string; phonetic: string }> = {};
    segments.forEach((s) => {
      initial[s.segment_id] = {
        target: s.target_text || "",
        phonetic: s.phonetic_text || "",
      };
    });
    setLocalTexts(initial);
  }, [segments]);

  const handleTargetChange = (segmentId: number, newTarget: string) => {
    setLocalTexts((prev) => ({
      ...prev,
      [segmentId]: {
        ...prev[segmentId],
        target: newTarget,
      },
    }));
  };

  const handlePhoneticChange = (segmentId: number, newPhonetic: string) => {
    setLocalTexts((prev) => ({
      ...prev,
      [segmentId]: {
        ...prev[segmentId],
        phonetic: newPhonetic,
      },
    }));
  };

  const handleBlur = (segmentId: number) => {
    const current = localTexts[segmentId];
    if (current) {
      onUpdateSegment(segmentId, current.target, current.phonetic);
    }
  };

  const allFit = segments.length > 0 && segments.every((s) => s.fit_status === "FITS");

  return (
    <div className="w-full h-full flex flex-col bg-surface-card hairline-border overflow-hidden select-none">
      {/* Inspector Header */}
      <div className="p-4 border-b border-hairline bg-alabaster/40 flex items-center justify-between shrink-0">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-sm font-semibold text-carbon tracking-tight">
              Isochronic Dialogue Inspector
            </h2>
            <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-signal-orange-tint text-signal-orange hairline-border">
              {segments.length} PHRASES
            </span>
          </div>
          <p className="text-xs text-stone-muted mt-0.5 font-mono text-[11px]">
            Target: <span className="text-carbon font-medium">{targetLanguageName}</span> — Time & Syllable Aligned
          </p>
        </div>

        {/* Global Sync Verification Badge */}
        {allFit ? (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-emerald-sync-tint text-emerald-sync text-xs font-mono font-semibold hairline-border">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>100% SYNC FIT</span>
          </div>
        ) : (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded bg-amber-sync-tint text-amber-sync text-xs font-mono font-medium hairline-border">
            <AlertTriangle className="w-3.5 h-3.5" />
            <span>PACING REVIEW</span>
          </div>
        )}
      </div>

      {/* Scrollable Segment Cards List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3.5">
        {segments.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 text-stone-muted">
            <Languages className="w-8 h-8 mb-2 text-stone-light" />
            <p className="text-sm font-medium text-carbon">Awaiting Transcribed Dialogue</p>
            <p className="text-xs text-stone-muted mt-1 max-w-xs font-mono text-[11px]">
              Upload a video to extract 16kHz vocal stems, Whisper word-alignments, and isochronic translations.
            </p>
          </div>
        ) : (
          segments.map((seg) => {
            const isActive =
              currentTime >= seg.start_time && currentTime <= seg.end_time;
            const targetVal =
              localTexts[seg.segment_id]?.target ?? seg.target_text;
            const phoneticVal =
              localTexts[seg.segment_id]?.phonetic ?? seg.phonetic_text;

            // Live Indian Vernacular Akshara & Latin Syllable Calculation
            const liveSyllables =
              countSyllables(targetVal) || countSyllables(phoneticVal) || seg.target_syllables;
            const {
              fitStatus: liveFitStatus,
              pacingRatio: livePacingRatio,
              tolerancePct: liveTolerancePct,
            } = evaluateFit(seg.original_syllables, liveSyllables);

            // Lip-sync pacing bar calculations
            const isFit = liveFitStatus === "FITS";
            const ratioPercent = Math.min(Math.max(livePacingRatio * 100, 30), 170);

            return (
              <motion.div
                key={seg.segment_id}
                layout
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ type: "spring", stiffness: 300, damping: 30 }}
                className={`relative rounded-studio p-3.5 transition-all bg-surface-card hairline-border shadow-tactile ${
                  isActive
                    ? "ring-2 ring-signal-orange border-signal-orange shadow-tactile-elevated"
                    : "hover:border-stone-light/60"
                }`}
              >
                {/* Active Playhead Left Strip */}
                {isActive && (
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-signal-orange rounded-l-studio" />
                )}

                {/* Card Header: Timecode and Syllable Metric */}
                <div className="flex items-center justify-between mb-2 text-xs font-mono">
                  <button
                    onClick={() => onSeekToSegment(seg.start_time)}
                    className="flex items-center gap-1.5 text-stone-muted hover:text-signal-orange transition-colors cursor-pointer group"
                  >
                    <Play
                      className={`w-3 h-3 ${
                        isActive ? "text-signal-orange fill-signal-orange" : ""
                      }`}
                    />
                    <span className="font-bold tabular-nums text-carbon group-hover:text-signal-orange">
                      [{formatTimecode(seg.start_time)} - {formatTimecode(seg.end_time)}]
                    </span>
                    <span className="text-[10px] text-stone-light">
                      ({formatDurationBudget(seg.duration_budget)})
                    </span>
                  </button>

                  {/* Syllable Counter */}
                  <div className="flex items-center gap-1.5 text-[11px]">
                    <span className="text-stone-muted">BUDGET:</span>
                    <span className="font-semibold tabular-nums text-carbon">
                      {liveSyllables} / {seg.original_syllables} syll
                    </span>
                  </div>
                </div>

                {/* Source English Original Text */}
                <div className="mb-2.5 px-2.5 py-1.5 rounded bg-alabaster hairline-border text-xs text-stone-muted font-sans italic">
                  <span className="text-[10px] font-mono text-stone-light uppercase mr-1.5 not-italic">
                    SOURCE:
                  </span>
                  "{seg.source_text}"
                </div>

                {/* Editable Target Text (Native Script: Telugu, Hindi, etc.) */}
                <div className="space-y-1.5 mb-2.5">
                  <div className="flex items-center justify-between text-[11px] font-mono text-stone-muted">
                    <span>NATIVE SCRIPT TRANSLATION:</span>
                    <span className="text-[10px] text-stone-light">Editable</span>
                  </div>
                  <input
                    type="text"
                    value={targetVal}
                    onChange={(e) =>
                      handleTargetChange(seg.segment_id, e.target.value)
                    }
                    onBlur={() => handleBlur(seg.segment_id)}
                    placeholder="Enter translated sentence..."
                    className="w-full px-3 py-1.5 bg-alabaster/60 hover:bg-alabaster focus:bg-surface-card hairline-border rounded-tactile text-xs font-medium text-carbon focus:outline-none focus:ring-1 focus:ring-carbon transition-colors"
                  />
                </div>

                {/* Editable Phonetic Pronunciation Script */}
                <div className="space-y-1 mb-3">
                  <div className="text-[10px] font-mono text-stone-light">
                    PHONETIC ROMANIZED (FOR VIS-EME ACCURACY):
                  </div>
                  <input
                    type="text"
                    value={phoneticVal}
                    onChange={(e) =>
                      handlePhoneticChange(seg.segment_id, e.target.value)
                    }
                    onBlur={() => handleBlur(seg.segment_id)}
                    placeholder="e.g. Namaskaram andhariki..."
                    className="w-full px-3 py-1 bg-alabaster/30 hover:bg-alabaster focus:bg-surface-card hairline-border rounded-tactile text-xs font-mono text-stone-muted focus:text-carbon focus:outline-none focus:ring-1 focus:ring-carbon transition-colors"
                  />
                </div>

                {/* Live "Lip-Sync Pacing Meter" */}
                <div className="pt-2 border-t border-hairline/80 flex flex-col gap-1.5">
                  <div className="flex items-center justify-between text-[10px] font-mono">
                    <span className="text-stone-muted flex items-center gap-1">
                      <span>LIP-SYNC PACING METER</span>
                    </span>

                    {/* Sync Status Badge */}
                    {isFit ? (
                      <span className="px-1.5 py-0.2 rounded bg-emerald-sync-tint text-emerald-sync font-bold flex items-center gap-1">
                        <CheckCircle2 className="w-2.5 h-2.5" />
                        <span>100% SYNC FIT (±{liveTolerancePct.toFixed(0)}%)</span>
                      </span>
                    ) : (
                      <span className="px-1.5 py-0.2 rounded bg-amber-sync-tint text-amber-sync font-bold flex items-center gap-1">
                        <AlertTriangle className="w-2.5 h-2.5" />
                        <span>
                          {liveFitStatus === "TOO_LONG"
                            ? `+${liveTolerancePct.toFixed(0)}% FAST / PACKED`
                            : `-${liveTolerancePct.toFixed(0)}% SLOW / SPARSE`}
                        </span>
                      </span>
                    )}
                  </div>

                  {/* Visual Duration Pacing Bar */}
                  <div className="relative w-full h-1.5 bg-hairline rounded-full overflow-hidden">
                    {/* Safe Target Zone Window (90% - 110%) */}
                    <div
                      className="absolute top-0 bottom-0 bg-stone-light/30 rounded-full"
                      style={{ left: "45%", width: "10%" }}
                    />
                    {/* Active Pacing Fill Indicator */}
                    <motion.div
                      animate={{
                        width: `${Math.min(ratioPercent, 100)}%`,
                        backgroundColor: isFit ? "#10B981" : "#F59E0B",
                      }}
                      transition={{ type: "spring", stiffness: 300, damping: 30 }}
                      className="h-full rounded-full"
                    />
                  </div>
                </div>
              </motion.div>
            );
          })
        )}
      </div>

      {/* Bottom Sticky Action Bar: Synthesize & Lip-Sync Button */}
      {segments.length > 0 && (
        <div className="p-4 border-t border-hairline bg-alabaster/60 shrink-0">
          <motion.button
            whileTap={{ scale: 0.98 }}
            disabled={isSynthesizing}
            onClick={onTriggerSynthesize}
            className="w-full py-3 px-4 rounded-tactile bg-signal-orange hover:bg-signal-orange-hover text-alabaster font-semibold text-xs tracking-wide uppercase flex items-center justify-center gap-2 shadow-tactile transition-all cursor-pointer disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <Sparkles className="w-4 h-4 fill-current" />
            <span>
              {isSynthesizing
                ? "Processing Voice & Lip-Sync..."
                : `Synthesize & Lip-Sync (${segments.length} Segments)`}
            </span>
          </motion.button>
        </div>
      )}
    </div>
  );
};
