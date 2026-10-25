import React, { useState, useEffect } from "react";
import { Layers, Activity, ChevronDown, Cpu, Sparkles, Volume2, Smile, ShieldCheck } from "lucide-react";

interface HeaderProps {
  jobId: string | null;
  status: string | null;
  onReset: () => void;
}

interface SystemHealth {
  status: string;
  overall_mode: string;
  hardware_accelerator: string;
  version: string;
  engines: {
    asr: { name: string; mode: string; device: string };
    translation: { name: string; mode: string; has_api_key: boolean };
    voice_cloning: { name: string; mode: string; has_api_key: boolean };
    lipsync: { name: string; mode: string; restoration: string; zero_damage_guaranteed: boolean };
    demux: { name: string; mode: string };
  };
}

export const Header: React.FC<HeaderProps> = ({ jobId, status, onReset }) => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [showEngineModal, setShowEngineModal] = useState(false);

  useEffect(() => {
    fetch("/api/v1/system/health")
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setHealth(data);
      })
      .catch(() => {});
  }, []);

  const isLive = health?.overall_mode === "LIVE_PRODUCTION";
  const isHybrid = health?.overall_mode === "HYBRID_LOCAL";

  return (
    <header className="h-14 border-b border-hairline bg-alabaster/80 backdrop-blur-md px-4 lg:px-6 flex items-center justify-between z-30 select-none relative">
      {/* Brand & Studio Title */}
      <div className="flex items-center gap-3">
        <button
          onClick={onReset}
          className="flex items-center gap-2 group cursor-pointer focus:outline-none"
        >
          <div className="w-7 h-7 rounded-tactile bg-carbon text-alabaster flex items-center justify-center font-mono font-bold text-xs tracking-tighter shadow-tactile transition-transform duration-200 group-hover:scale-105">
            TM
          </div>
          <span className="font-semibold text-sm tracking-tight text-carbon">
            TransMark
          </span>
          <span className="text-[10px] uppercase font-mono tracking-widest px-1.5 py-0.5 rounded bg-hairline text-stone-muted">
            Studio
          </span>
        </button>

        <div className="hidden sm:block h-4 w-[1px] bg-hairline" />

        <div className="hidden sm:flex items-center gap-1.5 text-xs text-stone-muted font-mono">
          <span>AI Dubbing & Zero-Damage Lip-Sync</span>
        </div>
      </div>

      {/* Right Telemetry: AI Live vs Fallback Badge & Job Pill */}
      <div className="flex items-center gap-2.5">
        {/* AI Engine Status Telemetry Pill */}
        <div className="relative">
          <button
            onClick={() => setShowEngineModal(!showEngineModal)}
            className="flex items-center gap-2 px-2.5 py-1 rounded-tactile bg-surface-card hairline-border shadow-tactile text-xs font-mono transition-colors hover:bg-hairline/40 cursor-pointer"
          >
            <span
              className={`w-2 h-2 rounded-full ${
                isLive
                  ? "bg-emerald-sync animate-pulse"
                  : isHybrid
                  ? "bg-signal-orange"
                  : "bg-stone-muted"
              }`}
            />
            <span className="text-stone-muted">AI ENGINE:</span>
            <span className="font-semibold text-carbon">
              {isLive
                ? "LIVE CLOUD"
                : isHybrid
                ? `ACCELERATED (${health?.hardware_accelerator?.toUpperCase() || "GPU"})`
                : "LOCAL ZERO-DAMAGE"}
            </span>
            <ChevronDown className="w-3 h-3 text-stone-muted" />
          </button>

          {/* Engine Health Dropdown Popover */}
          {showEngineModal && health && (
            <div className="absolute right-0 top-full mt-2 w-72 bg-surface-card hairline-border rounded-studio shadow-floating-bar p-3.5 z-50 text-xs font-mono">
              <div className="flex items-center justify-between pb-2 mb-2 border-b border-hairline">
                <span className="font-bold text-carbon">ENGINE TELEMETRY</span>
                <span className="text-[10px] text-stone-muted uppercase px-1.5 py-0.2 rounded bg-alabaster hairline-border">
                  {health.overall_mode}
                </span>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-stone-muted flex items-center gap-1.5">
                    <Volume2 className="w-3 h-3 text-carbon" />
                    <span>Demuxing</span>
                  </span>
                  <span className="text-carbon font-medium">{health.engines.demux.name}</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-stone-muted flex items-center gap-1.5">
                    <Cpu className="w-3 h-3 text-carbon" />
                    <span>Whisper ASR</span>
                  </span>
                  <span className="text-carbon font-medium">{health.engines.asr.name} ({health.hardware_accelerator})</span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-stone-muted flex items-center gap-1.5">
                    <Sparkles className="w-3 h-3 text-signal-orange" />
                    <span>Translation</span>
                  </span>
                  <span className={`font-medium ${health.engines.translation.mode === "LIVE_PRODUCTION" ? "text-emerald-sync" : "text-stone-muted"}`}>
                    {health.engines.translation.mode === "LIVE_PRODUCTION" ? "LIVE LLM" : "LOCAL HEURISTIC"}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-stone-muted flex items-center gap-1.5">
                    <Activity className="w-3 h-3 text-signal-orange" />
                    <span>Voice Cloning</span>
                  </span>
                  <span className={`font-medium ${health.engines.voice_cloning.mode === "LIVE_PRODUCTION" ? "text-emerald-sync" : "text-stone-muted"}`}>
                    {health.engines.voice_cloning.mode === "LIVE_PRODUCTION" ? "11LABS V2" : "LOCAL TIMBRE"}
                  </span>
                </div>

                <div className="flex items-center justify-between">
                  <span className="text-stone-muted flex items-center gap-1.5">
                    <Smile className="w-3 h-3 text-carbon" />
                    <span>Lip-Sync</span>
                  </span>
                  <span className="text-carbon font-medium">MuseTalk + {health.engines.lipsync.restoration}</span>
                </div>

                <div className="pt-2 border-t border-hairline flex items-center gap-1.5 text-[10px] text-emerald-sync font-bold">
                  <ShieldCheck className="w-3.5 h-3.5" />
                  <span>Zero-Damage Pixel Integrity Locked</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Active Job Status */}
        {jobId ? (
          <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-tactile bg-surface-card hairline-border shadow-tactile text-xs font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-signal-orange animate-pulse" />
            <span className="text-stone-muted">JOB:</span>
            <span className="text-carbon font-medium truncate max-w-[100px]">
              {jobId.slice(0, 8)}...
            </span>
            {status && (
              <span className="px-1.5 py-0.2 rounded bg-alabaster hairline-border text-[10px] uppercase text-carbon font-medium">
                {status.replace(/_/g, " ")}
              </span>
            )}
          </div>
        ) : (
          <div className="hidden sm:flex items-center gap-2 px-2.5 py-1 rounded-tactile bg-surface-card hairline-border shadow-tactile text-xs font-mono text-stone-muted">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-sync" />
            <span>READY</span>
          </div>
        )}

        <button
          onClick={onReset}
          className="hidden md:flex items-center gap-1.5 text-xs font-medium text-stone-muted hover:text-carbon px-2.5 py-1 rounded-tactile hover:bg-hairline/60 transition-colors cursor-pointer"
        >
          <Layers className="w-3.5 h-3.5" />
          <span>New Project</span>
        </button>
      </div>
    </header>
  );
};
