import React, { useState } from "react";
import { motion } from "framer-motion";
import {
  ChevronUp,
  ChevronDown,
  Sparkles,
  Download,
  Film,
  Layers,
} from "lucide-react";
import { IsochronicSegment } from "../types";
import { CurationTimeline } from "./CurationTimeline";

interface MobileBottomSheetProps {
  segments: IsochronicSegment[];
  currentTime: number;
  onSeekToSegment: (time: number) => void;
  onUpdateSegment: (id: number, target: string, phonetic: string) => void;
  onTriggerSynthesize: () => void;
  isSynthesizing: boolean;
  targetLanguageName: string;
  finalVideoUrl: string | null;
}

export const MobileBottomSheet: React.FC<MobileBottomSheetProps> = ({
  segments,
  currentTime,
  onSeekToSegment,
  onUpdateSegment,
  onTriggerSynthesize,
  isSynthesizing,
  targetLanguageName,
  finalVideoUrl,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="md:hidden fixed inset-x-0 bottom-0 z-40 select-none">
      {/* Draggable Drawer Header Pill */}
      <motion.div
        animate={{ height: isOpen ? "75dvh" : "120px" }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="w-full bg-surface-card hairline-border rounded-t-studio shadow-floating-bar flex flex-col overflow-hidden"
      >
        {/* Drag Handle Bar */}
        <div
          onClick={() => setIsOpen(!isOpen)}
          className="w-full py-2.5 flex flex-col items-center justify-center cursor-pointer border-b border-hairline/60 bg-alabaster/60 shrink-0"
        >
          <div className="w-10 h-1 rounded-full bg-stone-light/60 mb-1" />
          <div className="w-full px-4 flex items-center justify-between text-xs font-mono">
            <div className="flex items-center gap-1.5">
              <span className="font-semibold text-carbon">
                {segments.length} Timecoded Phrases
              </span>
              <span className="text-stone-light">({targetLanguageName})</span>
            </div>
            <div className="text-stone-muted flex items-center gap-1">
              <span>{isOpen ? "Collapse" : "Expand"}</span>
              {isOpen ? (
                <ChevronDown className="w-3.5 h-3.5" />
              ) : (
                <ChevronUp className="w-3.5 h-3.5" />
              )}
            </div>
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-hidden">
          <CurationTimeline
            segments={segments}
            currentTime={currentTime}
            onSeekToSegment={(time) => {
              onSeekToSegment(time);
              // Auto-collapse slightly on mobile so video is visible
              setIsOpen(false);
            }}
            onUpdateSegment={onUpdateSegment}
            onTriggerSynthesize={onTriggerSynthesize}
            isSynthesizing={isSynthesizing}
            targetLanguageName={targetLanguageName}
          />
        </div>

        {/* Mobile Bottom Navigation Bar */}
        <div className="h-14 border-t border-hairline bg-surface-card flex items-center justify-around px-4 shrink-0">
          <button
            onClick={() => setIsOpen(false)}
            className="flex flex-col items-center gap-0.5 text-stone-muted hover:text-carbon text-[10px] font-mono cursor-pointer"
          >
            <Film className="w-4 h-4" />
            <span>Video</span>
          </button>

          <button
            onClick={() => setIsOpen(true)}
            className="flex flex-col items-center gap-0.5 text-signal-orange text-[10px] font-mono font-bold cursor-pointer"
          >
            <Layers className="w-4 h-4" />
            <span>Inspector</span>
          </button>

          {finalVideoUrl ? (
            <a
              href={finalVideoUrl}
              download="transmark_dubbed.mp4"
              className="flex flex-col items-center gap-0.5 text-emerald-sync text-[10px] font-mono font-bold cursor-pointer"
            >
              <Download className="w-4 h-4" />
              <span>Download</span>
            </a>
          ) : (
            <button
              onClick={onTriggerSynthesize}
              disabled={isSynthesizing || segments.length === 0}
              className="flex flex-col items-center gap-0.5 text-signal-orange disabled:text-stone-light text-[10px] font-mono cursor-pointer"
            >
              <Sparkles className="w-4 h-4" />
              <span>Lip-Sync</span>
            </button>
          )}
        </div>
      </motion.div>
    </div>
  );
};
