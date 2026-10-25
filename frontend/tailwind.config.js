/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        alabaster: "#F8F7F4",
        "surface-card": "#FFFFFF",
        "hairline": "#E4E2DD",
        "hairline-dark": "#D6D3CC",
        carbon: "#111111",
        "carbon-soft": "#2A2927",
        "stone-muted": "#686662",
        "stone-light": "#96948F",
        "signal-orange": "#FF4F00",
        "signal-orange-hover": "#E04500",
        "signal-orange-tint": "rgba(255, 79, 0, 0.08)",
        "emerald-sync": "#10B981",
        "emerald-sync-tint": "rgba(16, 185, 129, 0.10)",
        "amber-sync": "#F59E0B",
        "amber-sync-tint": "rgba(245, 158, 11, 0.10)",
      },
      fontFamily: {
        sans: ["Inter", "-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
        mono: ["JetBrains Mono", "SF Mono", "ui-monospace", "monospace"],
      },
      boxShadow: {
        tactile: "0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02)",
        "tactile-elevated": "0 8px 24px -4px rgba(0,0,0,0.06), 0 2px 6px -1px rgba(0,0,0,0.03)",
        "floating-bar": "0 12px 32px -4px rgba(17,17,17,0.08), 0 4px 12px -2px rgba(17,17,17,0.04)",
      },
      borderRadius: {
        studio: "10px",
        tactile: "6px",
      },
    },
  },
  plugins: [],
};
