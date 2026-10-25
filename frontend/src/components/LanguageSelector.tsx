import React from "react";
import { motion } from "framer-motion";
import { Globe } from "lucide-react";
import { SUPPORTED_LANGUAGES } from "../types";

interface LanguageSelectorProps {
  selectedLanguage: string;
  onSelectLanguage: (code: string) => void;
  disabled?: boolean;
}

export const LanguageSelector: React.FC<LanguageSelectorProps> = ({
  selectedLanguage,
  onSelectLanguage,
  disabled = false,
}) => {
  return (
    <div className="flex flex-col gap-2 select-none">
      <div className="flex items-center justify-between">
        <label className="text-[11px] font-mono uppercase tracking-wider text-stone-muted flex items-center gap-1.5">
          <Globe className="w-3.5 h-3.5 text-stone-muted" />
          <span>Target Language & Script</span>
        </label>
        <span className="text-[11px] font-mono text-stone-light">
          Isochronic Syllable Matching
        </span>
      </div>

      <div className="flex flex-wrap gap-1.5 p-1 bg-alabaster hairline-border rounded-studio">
        {SUPPORTED_LANGUAGES.map((lang) => {
          const isSelected = selectedLanguage === lang.code;
          return (
            <button
              key={lang.code}
              type="button"
              disabled={disabled}
              onClick={() => onSelectLanguage(lang.code)}
              className={`relative px-3 py-1.5 rounded-tactile text-xs font-medium transition-colors cursor-pointer flex items-center gap-1.5 focus:outline-none ${
                isSelected
                  ? "text-carbon font-semibold"
                  : "text-stone-muted hover:text-carbon"
              } ${disabled ? "opacity-60 cursor-not-allowed" : ""}`}
            >
              {isSelected && (
                <motion.div
                  layoutId="active-language-pill"
                  transition={{ type: "spring", stiffness: 300, damping: 30 }}
                  className="absolute inset-0 bg-surface-card hairline-border rounded-tactile shadow-tactile z-0"
                />
              )}
              <span className="relative z-10">{lang.name}</span>
              <span
                className={`relative z-10 px-1 py-0.2 rounded text-[10px] font-mono transition-colors ${
                  isSelected
                    ? "bg-alabaster hairline-border text-signal-orange font-bold"
                    : "bg-surface-card/60 text-stone-light"
                }`}
              >
                {lang.nativeBadge}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
