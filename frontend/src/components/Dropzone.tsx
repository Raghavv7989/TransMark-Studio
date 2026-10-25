import React, { useState, useRef } from "react";
import { motion } from "framer-motion";
import { Upload, Film, AlertCircle } from "lucide-react";

interface DropzoneProps {
  onVideoSelected: (file: File) => void;
  disabled?: boolean;
}

export const Dropzone: React.FC<DropzoneProps> = ({
  onVideoSelected,
  disabled = false,
}) => {
  const [isDragging, setIsDragging] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (disabled) return;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndProcessFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndProcessFile(e.target.files[0]);
    }
  };

  const validateAndProcessFile = (file: File) => {
    setErrorMessage(null);
    const validExtensions = [".mp4", ".mov", ".mkv", ".webm", ".avi"];
    const extension = "." + file.name.split(".").pop()?.toLowerCase();

    if (!validExtensions.includes(extension)) {
      setErrorMessage(`Please upload a valid video file (${validExtensions.join(", ")})`);
      return;
    }

    if (file.size > 500 * 1024 * 1024) {
      setErrorMessage("File exceeds maximum upload size of 500MB");
      return;
    }

    onVideoSelected(file);
  };

  const handleSampleSelect = async () => {
    try {
      await fetch("/api/v1/projects");
      // Create a lightweight sample blob if user wants instant demo
      const blob = new Blob(["sample video data"], { type: "video/mp4" });
      const sampleFile = new File([blob], "demo_reel_portrait.mp4", {
        type: "video/mp4",
      });
      onVideoSelected(sampleFile);
    } catch {
      // Fallback synthetic file
      const blob = new Blob(["demo"], { type: "video/mp4" });
      const sampleFile = new File([blob], "demo_reel.mp4", { type: "video/mp4" });
      onVideoSelected(sampleFile);
    }
  };

  return (
    <div className="w-full flex flex-col gap-4 select-none">
      <motion.div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
        animate={{
          scale: isDragging ? 1.015 : 1,
          borderColor: isDragging ? "#FF4F00" : "#E4E2DD",
          backgroundColor: isDragging ? "rgba(255, 79, 0, 0.03)" : "#FFFFFF",
        }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className={`relative border-2 border-dashed rounded-studio p-8 sm:p-12 flex flex-col items-center justify-center text-center cursor-pointer transition-shadow shadow-tactile hover:shadow-tactile-elevated ${
          disabled ? "opacity-60 cursor-not-allowed pointer-events-none" : ""
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="video/mp4,video/quicktime,video/x-matroska,video/webm"
          onChange={handleFileChange}
          className="hidden"
          disabled={disabled}
        />

        <div className="w-14 h-14 rounded-full bg-alabaster hairline-border flex items-center justify-center mb-4 text-carbon shadow-tactile">
          <Upload className="w-6 h-6 text-carbon" />
        </div>

        <h3 className="text-base font-semibold text-carbon tracking-tight mb-1">
          Drop Reel or Video Asset
        </h3>
        <p className="text-xs text-stone-muted max-w-sm mb-4 leading-relaxed">
          Optimized for vertical 9:16 reels, shorts, and 16:9 widescreen dialogue.
          Supports MP4, MOV, MKV up to 500MB.
        </p>

        <div className="flex items-center gap-2">
          <button
            type="button"
            className="px-4 py-2 bg-carbon hover:bg-carbon-soft text-alabaster text-xs font-medium rounded-tactile shadow-tactile transition-transform active:scale-95 cursor-pointer"
          >
            Browse Files
          </button>
        </div>

        {/* Tactile corner brackets */}
        <div className="absolute top-2.5 left-2.5 w-2.5 h-2.5 border-t border-l border-stone-light/60 pointer-events-none" />
        <div className="absolute top-2.5 right-2.5 w-2.5 h-2.5 border-t border-r border-stone-light/60 pointer-events-none" />
        <div className="absolute bottom-2.5 left-2.5 w-2.5 h-2.5 border-b border-l border-stone-light/60 pointer-events-none" />
        <div className="absolute bottom-2.5 right-2.5 w-2.5 h-2.5 border-b border-r border-stone-light/60 pointer-events-none" />
      </motion.div>

      {errorMessage && (
        <div className="p-3 bg-red-50 border border-red-200 rounded-tactile flex items-center gap-2 text-xs text-red-700 font-mono">
          <AlertCircle className="w-4 h-4 shrink-0 text-red-500" />
          <span>{errorMessage}</span>
        </div>
      )}

      {/* Quick sample reel starter */}
      <div className="flex items-center justify-between px-3 py-2 bg-alabaster hairline-border rounded-tactile text-xs text-stone-muted">
        <span className="font-mono text-[11px]">Need a test file?</span>
        <button
          type="button"
          onClick={handleSampleSelect}
          className="text-signal-orange hover:text-signal-orange-hover font-medium flex items-center gap-1 cursor-pointer transition-colors"
        >
          <Film className="w-3.5 h-3.5" />
          <span>Load Synthetic 9:16 Sample</span>
        </button>
      </div>
    </div>
  );
};
