import React, { useState, useEffect, useCallback } from "react";
import { Header } from "./components/Header";
import { Dropzone } from "./components/Dropzone";
import { LanguageSelector } from "./components/LanguageSelector";
import { VideoPlayerStage } from "./components/VideoPlayerStage";
import { CurationTimeline } from "./components/CurationTimeline";
import { ProcessingHUD } from "./components/ProcessingHUD";
import { MobileBottomSheet } from "./components/MobileBottomSheet";
import {
  IsochronicSegment,
  JobProgressUpdate,
  JobStatus,
  SUPPORTED_LANGUAGES,
} from "./types";
import {
  uploadVideo,
  getSegments,
  updateSegments,
  triggerSynthesize,
  getArtifactUrl,
  connectProgressWebSocket,
} from "./utils/api";

export const App: React.FC = () => {
  // Studio State
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [targetLanguage, setTargetLanguage] = useState<string>("te");
  const [segments, setSegments] = useState<IsochronicSegment[]>([]);

  // Video Stage State
  const [sourceVideoUrl, setSourceVideoUrl] = useState<string | null>(null);
  const [finalVideoUrl, setFinalVideoUrl] = useState<string | null>(null);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);

  // Telemetry HUD & Processing State
  const [progressUpdate, setProgressUpdate] = useState<JobProgressUpdate | null>(null);
  const [showHUD, setShowHUD] = useState<boolean>(false);
  const [isSynthesizing, setIsSynthesizing] = useState<boolean>(false);

  // Active language metadata
  const activeLang = SUPPORTED_LANGUAGES.find((l) => l.code === targetLanguage) || SUPPORTED_LANGUAGES[0];

  // 1. Video Selection & Upload
  const handleVideoSelected = async (file: File) => {
    // Generate instant local blob preview
    const localUrl = URL.createObjectURL(file);
    setSourceVideoUrl(localUrl);
    setFinalVideoUrl(null);
    setCurrentTime(0);

    try {
      const res = await uploadVideo(file, targetLanguage);
      setJobId(res.job_id);
      setStatus(res.status);
      setProgressUpdate({
        job_id: res.job_id,
        status: res.status,
        progress: 10,
        subtask: "Initiating lossless demuxing and stem separation pipeline",
        timestamp: new Date().toISOString(),
      });
      setShowHUD(true);
    } catch (err: any) {
      console.error("Video upload error:", err);
      alert(`Upload failed: ${err.message}`);
      setShowHUD(false);
    }
  };

  // 2. WebSocket Telemetry Stream
  useEffect(() => {
    if (!jobId) return;

    const cleanupWs = connectProgressWebSocket(jobId, (update) => {
      setProgressUpdate(update);
      setStatus(update.status);

      // When transcription/translation finishes, fetch segments
      if (
        update.status === "CURATING_TRANSLATION" ||
        update.status === "CLONING_VOICE" ||
        update.status === "LIP_SYNCING" ||
        update.status === "REMUXING" ||
        update.status === "COMPLETED"
      ) {
        getSegments(jobId)
          .then((segs) => {
            if (segs.length > 0) setSegments(segs);
          })
          .catch(console.error);
      }

      // When synthesis completes, expose final dubbed video artifact
      if (update.status === "COMPLETED") {
        setIsSynthesizing(false);
        const finalUrl = getArtifactUrl(jobId, "final_video");
        setFinalVideoUrl(finalUrl);
      }
    });

    return () => cleanupWs();
  }, [jobId]);

  // 3. Human-in-the-Loop Segment Editing
  const handleUpdateSegment = useCallback(
    async (segmentId: number, targetText: string, phoneticText: string) => {
      if (!jobId) return;

      try {
        const updated = await updateSegments(jobId, [
          {
            segment_id: segmentId,
            target_text: targetText,
            phonetic_text: phoneticText,
          },
        ]);
        if (updated && updated.length > 0) {
          setSegments(updated);
        }
      } catch (err) {
        console.error("Segment curation update error:", err);
      }
    },
    [jobId]
  );

  // 4. Trigger Synthesis & Zero-Damage Lip-Sync
  const handleTriggerSynthesize = async () => {
    if (!jobId) return;

    try {
      setIsSynthesizing(true);
      setProgressUpdate((prev) => ({
        job_id: jobId,
        status: "CLONING_VOICE",
        progress: 72,
        subtask: "Initiating voice cloning & dynamic duration alignment...",
        timestamp: new Date().toISOString(),
        details: prev?.details,
      }));
      setShowHUD(true);
      await triggerSynthesize(jobId);
    } catch (err: any) {
      setIsSynthesizing(false);
      alert(`Failed to trigger synthesis: ${err.message}`);
    }
  };

  // 5. Video Playhead Transport Handlers
  const handleTogglePlay = () => setIsPlaying((prev) => !prev);
  const handleSeek = (time: number) => {
    setCurrentTime(time);
  };
  const handleSeekToSegment = (startTime: number) => {
    setCurrentTime(startTime);
    setIsPlaying(true);
  };

  // 6. Reset Workspace
  const handleReset = () => {
    setJobId(null);
    setStatus(null);
    setSegments([]);
    setSourceVideoUrl(null);
    setFinalVideoUrl(null);
    setCurrentTime(0);
    setDuration(0);
    setIsPlaying(false);
    setProgressUpdate(null);
    setShowHUD(false);
    setIsSynthesizing(false);
  };

  return (
    <div className="flex flex-col h-[100dvh] w-screen bg-alabaster text-carbon overflow-hidden">
      {/* Studio Masthead */}
      <Header jobId={jobId} status={status} onReset={handleReset} />

      {/* Main Split-Screen Workspace (Desktop) */}
      <main className="flex-1 flex flex-col md:flex-row overflow-hidden">
        {/* Left Side: Adaptive Video Stage */}
        <section className="flex-1 h-full min-h-[300px] flex flex-col items-center justify-center relative overflow-hidden bg-alabaster border-r border-hairline">
          <VideoPlayerStage
            sourceVideoUrl={sourceVideoUrl}
            finalVideoUrl={finalVideoUrl}
            currentTime={currentTime}
            duration={duration}
            isPlaying={isPlaying}
            onTimeUpdate={setCurrentTime}
            onDurationChange={setDuration}
            onTogglePlay={handleTogglePlay}
            onSeek={handleSeek}
            isCompleted={status === "COMPLETED"}
          />
        </section>

        {/* Right Side: Dubbing Inspector & Word Curation Timeline */}
        <section className="hidden md:flex w-[480px] lg:w-[540px] xl:w-[580px] h-full flex-col bg-surface-card overflow-hidden">
          {!sourceVideoUrl ? (
            /* Upload & Configuration State */
            <div className="flex-1 flex flex-col justify-center p-8 space-y-6 overflow-y-auto">
              <div>
                <h1 className="text-xl font-bold tracking-tight text-carbon">
                  AI Video Dubbing Studio
                </h1>
                <p className="text-xs text-stone-muted mt-1 leading-relaxed">
                  Lossless FFmpeg demuxing, isochronic dialogue matching, zero-shot voice cloning,
                  and zero-damage lower-facial lip-syncing.
                </p>
              </div>

              {/* Target Language Selection */}
              <LanguageSelector
                selectedLanguage={targetLanguage}
                onSelectLanguage={setTargetLanguage}
                disabled={jobId !== null}
              />

              {/* Drag & Drop File Zone */}
              <Dropzone onVideoSelected={handleVideoSelected} />
            </div>
          ) : (
            /* Active Curation Timeline Inspector */
            <CurationTimeline
              segments={segments}
              currentTime={currentTime}
              onSeekToSegment={handleSeekToSegment}
              onUpdateSegment={handleUpdateSegment}
              onTriggerSynthesize={handleTriggerSynthesize}
              isSynthesizing={isSynthesizing}
              targetLanguageName={activeLang.name}
            />
          )}
        </section>
      </main>

      {/* Mobile Drawer & Bottom Navigation Bar (< 768px) */}
      {sourceVideoUrl && (
        <MobileBottomSheet
          segments={segments}
          currentTime={currentTime}
          onSeekToSegment={handleSeekToSegment}
          onUpdateSegment={handleUpdateSegment}
          onTriggerSynthesize={handleTriggerSynthesize}
          isSynthesizing={isSynthesizing}
          targetLanguageName={activeLang.name}
          finalVideoUrl={finalVideoUrl}
        />
      )}

      {/* Live WebSocket & Polling Processing Telemetry HUD */}
      {showHUD && (
        <ProcessingHUD
          jobId={jobId}
          progressUpdate={progressUpdate}
          onDismiss={() => setShowHUD(false)}
        />
      )}
    </div>
  );
};

export default App;
