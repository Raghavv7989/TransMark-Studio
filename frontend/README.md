# TransMark Studio — Frontend Application

A high-craft Swiss Minimalist / Tactile Editorial AI Video Dubbing & Zero-Damage Lip-Sync application built with React, TypeScript, Tailwind CSS, and Framer Motion.

---

## 🎨 Design Language & Philosophy

- **Surface Palette:**
  - Daylight Warm Alabaster (`#F8F7F4`)
  - Elevated Pure White Studio Cards (`#FFFFFF`)
  - Exposed Hairline Grid Borders (`1px solid #E4E2DD`)
  - Deep Carbon Ink Typography (`#111111`)
  - Muted Stone Secondary (`#686662`)
- **Accent Signals:**
  - International Signal Orange (`#FF4F00`) for primary actions and active timeline playheads
  - Emerald (`#10B981`) for 100% sync verification badges
  - Amber (`#F59E0B`) for slight pacing deviations
- **Typography:**
  - Geometric sans-serif (`Inter`) paired with `JetBrains Mono` (`tabular-nums`) for all timecodes, FPS counters, and syllable duration metrics.
- **Physics-Based Transitions:**
  - Framer Motion spring physics (`stiffness: 300, damping: 30`).

---

## 📱 Responsive & Mobile-First Architecture

- **Desktop Layout:** Full-viewport (`100dvh`) split-screen workspace:
  - Left: Adaptive 9:16 / 16:9 Video Stage with floating glassmorphic transport controls and an interactive Before / After split-slider.
  - Right: Isochronic Dialogue Inspector with live Lip-Sync Pacing Meters, syllable budget counters, and target language pill selectors.
- **Mobile Layout (`< 768px`):**
  - Sticky top video stage preview.
  - Draggable bottom sheet drawer with segment curation cards.
  - Mobile bottom navigation bar.
  - `manifest.json` and viewport lock (`user-scalable=no, viewport-fit=cover`).

---

## 🚀 Quickstart

```bash
cd frontend
npm install
npm run dev
```

App runs on `http://localhost:5173`. Proxies `/api` and `/ws` to FastAPI backend at `http://127.0.0.1:8008` / `8000`.
