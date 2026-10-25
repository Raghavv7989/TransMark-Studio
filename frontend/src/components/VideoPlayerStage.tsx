import React, { useState, useRef, useEffect } from "react";
import { motion } from "framer-motion";
import {
  Play,
  Pause,
  Volume2,
  VolumeX,
  Download,
  Sliders,
  CheckCircle2,
  Smartphone,
  Tv,
} from "lucide-react";
import { formatTimecode } from "../utils/time";

interface VideoPlayerStageProps {
  sourceVideoUrl: string | null;
  finalVideoUrl: string | null;
  currentTime: number;
  duration: number;
  isPlaying: boolean;
  onTimeUpdate: (time: number) => void;
  onDurationChange: (duration: number) => void;
  onTogglePlay: () => void;
  onSeek: (time: number) => void;
  isCompleted?: boolean;
}

export const VideoPlayerStage: React.FC<VideoPlayerStageProps> = ({
  sourceVideoUrl,
  finalVideoUrl,
  currentTime,
  duration,
  isPlaying,
  onTimeUpdate,
  onDurationChange,
  onTogglePlay,
  onSeek,
  isCompleted = false,
}) => {
  const [aspectRatio, setAspectRatio] = useState<"9:16" | "16:9">("9:16");
  const [volume, setVolume] = useState(1);
  const [isMuted, setIsMuted] = useState(false);
  const [isSplitMode, setIsSplitMode] = useState(false);
  const [splitPos, setSplitPos] = useState(50); // percentage 0-100
  const [isDraggingSplit, setIsDraggingSplit] = useState(false);

  const videoRef = useRef<HTMLVideoElement>(null);
  const finalVideoRef = useRef<HTMLVideoElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  // Master-Slave Frame-Accurate Video Synchronization Loop (requestAnimationFrame)
  useEffect(() => {
    let animId: number;

    const syncFrameLoop = () => {
      const master = videoRef.current;
      const slave = finalVideoRef.current;

      if (master && slave && isSplitMode) {
        // 1. Sync Play/Pause State
        if (!master.paused && slave.paused) {
          slave.play().catch(() => {});
        } else if (master.paused && !slave.paused) {
          slave.pause();
        }

        // 2. Sub-Frame Drift Correction (< 25ms / 1 frame lock)
        const drift = Math.abs(master.currentTime - slave.currentTime);
        if (drift > 0.025) {
          slave.currentTime = master.currentTime;
        }

        // 3. Playback rate sync
        if (slave.playbackRate !== master.playbackRate) {
          slave.playbackRate = master.playbackRate;
        }
      }

      animId = requestAnimationFrame(syncFrameLoop);
    };

    animId = requestAnimationFrame(syncFrameLoop);
    return () => cancelAnimationFrame(animId);
  }, [isSplitMode]);

  // Sync seek across both players with zero-drift locking
  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newTime = parseFloat(e.target.value);
    onSeek(newTime);
    if (videoRef.current) {
      videoRef.current.currentTime = newTime;
    }
    if (finalVideoRef.current) {
      finalVideoRef.current.currentTime = newTime;
    }
  };

  const handleVolumeChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newVol = parseFloat(e.target.value);
    setVolume(newVol);
    setIsMuted(newVol === 0);
    if (videoRef.current) videoRef.current.volume = newVol;
    if (finalVideoRef.current) finalVideoRef.current.volume = newVol;
  };

  const toggleMute = () => {
    const nextMuted = !isMuted;
    setIsMuted(nextMuted);
    if (videoRef.current) videoRef.current.muted = nextMuted;
    if (finalVideoRef.current) finalVideoRef.current.muted = nextMuted;
  };

  // Split-slider drag handlers
  const handleSplitMouseDown = (e: React.MouseEvent) => {
    e.preventDefault();
    setIsDraggingSplit(true);
  };

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDraggingSplit || !containerRef.current) return;
      const rect = containerRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const pct = Math.min(Math.max((x / rect.width) * 100, 5), 95);
      setSplitPos(pct);
    };

    const handleMouseUp = () => {
      setIsDraggingSplit(false);
    };

    if (isDraggingSplit) {
      window.addEventListener("mousemove", handleMouseMove);
      window.addEventListener("mouseup", handleMouseUp);
    }
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [isDraggingSplit]);

  // Keyboard shortcut: Space to toggle play
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.code === "Space" && e.target === document.body) {
        e.preventDefault();
        onTogglePlay();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onTogglePlay]);

  const activeVideoSrc = finalVideoUrl && !isSplitMode ? finalVideoUrl : sourceVideoUrl;

  return (
    <div className="relative w-full h-full flex flex-col items-center justify-center p-4 lg:p-6 select-none bg-alabaster">
      {/* Top Controls Bar */}
      <div className="w-full max-w-xl flex items-center justify-between mb-3 text-xs font-mono">
        {/* Aspect Ratio Switch */}
        <div className="flex items-center gap-1 p-0.5 bg-surface-card hairline-border rounded-tactile shadow-tactile">
          <button
            onClick={() => setAspectRatio("9:16")}
            className={`px-2 py-1 rounded flex items-center gap-1 cursor-pointer transition-colors ${
              aspectRatio === "9:16"
                ? "bg-carbon text-alabaster font-semibold"
                : "text-stone-muted hover:text-carbon"
            }`}
          >
            <Smartphone className="w-3 h-3" />
            <span>9:16 Reel</span>
          </button>
          <button
            onClick={() => setAspectRatio("16:9")}
            className={`px-2 py-1 rounded flex items-center gap-1 cursor-pointer transition-colors ${
              aspectRatio === "16:9"
                ? "bg-carbon text-alabaster font-semibold"
                : "text-stone-muted hover:text-carbon"
            }`}
          >
            <Tv className="w-3 h-3" />
            <span>16:9 Wide</span>
          </button>
        </div>

        {/* Before / After Split Slider Toggle (when final video ready) */}
        {finalVideoUrl && (
          <div className="flex items-center gap-2">
            <button
              onClick={() => setIsSplitMode(!isSplitMode)}
              className={`px-2.5 py-1 rounded-tactile hairline-border shadow-tactile flex items-center gap-1.5 transition-colors cursor-pointer ${
                isSplitMode
                  ? "bg-signal-orange text-alabaster font-semibold"
                  : "bg-surface-card text-carbon hover:bg-hairline/60"
              }`}
            >
              <Sliders className="w-3 h-3" />
              <span>Before / After Split</span>
            </button>
          </div>
        )}
      </div>

      {/* Adaptive Video Frame Canvas */}
      <div
        ref={containerRef}
        className={`relative bg-carbon overflow-hidden rounded-studio shadow-tactile-elevated hairline-border flex items-center justify-center transition-all duration-300 ${
          aspectRatio === "9:16"
            ? "w-full max-w-[340px] sm:max-w-[380px] aspect-[9/16] max-h-[calc(100dvh-170px)]"
            : "w-full max-w-2xl aspect-video max-h-[calc(100dvh-170px)]"
        }`}
      >
        {/* Main Video Element */}
        {activeVideoSrc ? (
          <video
            ref={videoRef}
            src={activeVideoSrc}
            playsInline
            onTimeUpdate={(e) => onTimeUpdate(e.currentTarget.currentTime)}
            onLoadedMetadata={(e) => onDurationChange(e.currentTarget.duration)}
            onClick={onTogglePlay}
            className="w-full h-full object-cover cursor-pointer"
          />
        ) : (
          <div className="w-full h-full flex flex-col items-center justify-center text-stone-light text-xs font-mono p-6 text-center">
            <span>No video asset loaded</span>
          </div>
        )}

        {/* Split Comparison Mode: Dubbed video overlaid with clip-path */}
        {isSplitMode && finalVideoUrl && (
          <>
            <div
              className="absolute inset-0 pointer-events-none overflow-hidden"
              style={{ clipPath: `inset(0 0 0 ${splitPos}%)` }}
            >
              <video
                ref={finalVideoRef}
                src={finalVideoUrl}
                playsInline
                muted={isMuted}
                className="w-full h-full object-cover"
              />
            </div>

            {/* Draggable Divider Line */}
            <div
              onMouseDown={handleSplitMouseDown}
              style={{ left: `${splitPos}%` }}
              className="absolute top-0 bottom-0 w-1 bg-signal-orange shadow-lg cursor-ew-resize z-20 flex items-center justify-center -translate-x-1/2"
            >
              <div className="w-6 h-6 rounded-full bg-signal-orange text-alabaster flex items-center justify-center shadow-tactile text-[9px] font-mono font-bold">
                ⇄
              </div>
            </div>

            {/* Labels */}
            <div className="absolute top-3 left-3 px-2 py-0.5 rounded bg-carbon/80 text-alabaster text-[10px] font-mono tracking-wider z-10 backdrop-blur-sm">
              ORIGINAL
            </div>
            <div className="absolute top-3 right-3 px-2 py-0.5 rounded bg-signal-orange text-alabaster text-[10px] font-mono tracking-wider font-bold z-10 shadow-tactile">
              DUBBED / LIP-SYNC
            </div>
          </>
        )}

        {/* 100% Zero-Damage Verification Badge */}
        {isCompleted && (
          <div className="absolute bottom-16 left-3 px-2.5 py-1 rounded bg-surface-card/90 hairline-border backdrop-blur-md flex items-center gap-1.5 text-[11px] font-mono text-emerald-sync font-bold shadow-tactile z-10">
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-sync" />
            <span>ZERO VIDEO DAMAGE VERIFIED</span>
          </div>
        )}

        {/* Floating Glassmorphic Transport Control Bar */}
        <div className="absolute bottom-3 left-3 right-3 p-2 bg-surface-card/90 backdrop-blur-md hairline-border rounded-studio shadow-floating-bar flex flex-col gap-1.5 z-20 transition-opacity duration-200">
          {/* Seek Scrubber Slider */}
          <div className="relative w-full flex items-center group">
            <input
              type="range"
              min={0}
              max={duration || 100}
              step={0.01}
              value={currentTime}
              onChange={handleSeek}
              className="w-full h-1.5 bg-hairline rounded-lg appearance-none cursor-pointer accent-signal-orange focus:outline-none"
            />
          </div>

          {/* Transport Buttons & Counters */}
          <div className="flex items-center justify-between text-xs">
            {/* Play/Pause Button */}
            <div className="flex items-center gap-2">
              <motion.button
                whileTap={{ scale: 0.92 }}
                onClick={onTogglePlay}
                className="w-7 h-7 rounded-tactile bg-carbon hover:bg-carbon-soft text-alabaster flex items-center justify-center transition-colors cursor-pointer shadow-tactile"
              >
                {isPlaying ? (
                  <Pause className="w-3.5 h-3.5 fill-current" />
                ) : (
                  <Play className="w-3.5 h-3.5 fill-current ml-0.5" />
                )}
              </motion.button>

              {/* Precise Timecode (JetBrains Mono tabular-nums) */}
              <div className="font-mono text-[11px] tabular-nums text-carbon font-medium flex items-center gap-1">
                <span className="text-carbon font-semibold">
                  {formatTimecode(currentTime)}
                </span>
                <span className="text-stone-light">/</span>
                <span className="text-stone-muted">
                  {formatTimecode(duration)}
                </span>
              </div>
            </div>

            {/* Volume Control & Download */}
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1 text-stone-muted">
                <button
                  onClick={toggleMute}
                  className="p-1 hover:text-carbon transition-colors cursor-pointer"
                >
                  {isMuted || volume === 0 ? (
                    <VolumeX className="w-3.5 h-3.5 text-signal-orange" />
                  ) : (
                    <Volume2 className="w-3.5 h-3.5" />
                  )}
                </button>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.05}
                  value={isMuted ? 0 : volume}
                  onChange={handleVolumeChange}
                  className="w-12 h-1 bg-hairline rounded appearance-none accent-carbon cursor-pointer"
                />
              </div>

              {/* 1-Click High Bitrate MP4 Download Button */}
              {finalVideoUrl && (
                <a
                  href={finalVideoUrl}
                  download="transmark_dubbed_lipsync.mp4"
                  className="flex items-center gap-1 px-2.5 py-1 rounded bg-signal-orange hover:bg-signal-orange-hover text-alabaster text-[11px] font-mono font-bold tracking-tight shadow-tactile transition-transform active:scale-95 cursor-pointer"
                >
                  <Download className="w-3 h-3" />
                  <span>Download MP4</span>
                </a>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
