#!/usr/bin/env bash
# ==============================================================================
# TransMark Studio: One-Command Startup Script
# Production-grade AI Video Dubbing & Lip-Sync Platform
# macOS & Linux Compatible
# ==============================================================================

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ANSI Terminal Styling
ORANGE='\033[38;2;255;79;0m'
EMERALD='\033[38;2;16;185;129m'
MUTED='\033[38;2;104;102;98m'
BOLD='\033[1m'
NC='\033[0m'

echo ""
echo -e "${BOLD}${ORANGE}TransMark Studio${NC} ${MUTED}v0.1.0${NC}"
echo -e "${MUTED}AI Video Dubbing, Isochronic Translation & Zero-Damage Lip-Sync${NC}"
echo "----------------------------------------------------------------------"

# ------------------------------------------------------------------------------
# 1. Pre-Flight Dependency Checks
# ------------------------------------------------------------------------------
echo -e "${BOLD}[1/4] Pre-flight system checks...${NC}"

check_cmd() {
  local cmd="$1"
  local install_hint="$2"
  if ! command -v "$cmd" &>/dev/null; then
    echo -e "  [!] Missing required tool: ${BOLD}$cmd${NC}"
    echo -e "      Install suggestion: $install_hint"
    exit 1
  fi
}

check_cmd "ffmpeg" "brew install ffmpeg (macOS) or sudo apt install ffmpeg (Linux)"
check_cmd "ffprobe" "Included with ffmpeg package"
check_cmd "node" "brew install node or visit https://nodejs.org"
check_cmd "npm" "Included with Node.js"

# Check Python 3 (prefer python3.12 or python3)
if command -v python3.12 &>/dev/null; then
  SYSTEM_PYTHON="python3.12"
elif command -v python3 &>/dev/null; then
  SYSTEM_PYTHON="python3"
else
  echo -e "  [!] Missing python3. Install Python 3.10+ via brew install python@3.12"
  exit 1
fi

FFMPEG_VER=$(ffmpeg -version 2>&1 | head -n 1 | awk '{print $3}')
NODE_VER=$(node -v)
PYTHON_VER=$($SYSTEM_PYTHON --version 2>&1)

echo -e "  ${EMERALD}✓${NC} FFmpeg detected:  ${MUTED}$FFMPEG_VER${NC}"
echo -e "  ${EMERALD}✓${NC} Node.js detected: ${MUTED}$NODE_VER${NC}"
echo -e "  ${EMERALD}✓${NC} Python detected:  ${MUTED}$PYTHON_VER${NC}"

# ------------------------------------------------------------------------------
# 2. Python Environment & Backend Preparation
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[2/4] Setting up Python virtual environment...${NC}"
VENV_DIR="$SCRIPT_DIR/backend/.venv"
VENV_PYTHON="$VENV_DIR/bin/python"

if [ ! -f "$VENV_PYTHON" ]; then
  echo -e "  [*] Creating Python virtual environment in backend/.venv..."
  $SYSTEM_PYTHON -m venv "$VENV_DIR"
  echo -e "  [*] Installing backend dependencies from requirements.txt..."
  "$VENV_DIR/bin/pip" install --upgrade pip
  "$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/backend/requirements.txt"
else
  echo -e "  ${EMERALD}✓${NC} Virtual environment found at ${MUTED}$VENV_DIR${NC}"
fi

# ------------------------------------------------------------------------------
# 3. Node Modules & Frontend Preparation
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[3/4] Preparing Frontend Studio...${NC}"
if [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
  echo -e "  [*] Installing frontend dependencies via npm install..."
  (cd "$SCRIPT_DIR/frontend" && npm install)
else
  echo -e "  ${EMERALD}✓${NC} Frontend node_modules verified"
fi

# ------------------------------------------------------------------------------
# 4. Port Selection & Service Orchestration
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[4/4] Starting TransMark Services...${NC}"

is_port_free() {
  local p="$1"
  if lsof -Pi :"$p" -sTCP:LISTEN -t >/dev/null 2>&1; then
    return 1 # occupied
  else
    return 0 # free
  fi
}

# Standardize Backend Port to 8000
DESIRED_BACKEND_PORT="${BACKEND_PORT:-8000}"
if ! is_port_free "$DESIRED_BACKEND_PORT"; then
  echo -e "  [!] Port $DESIRED_BACKEND_PORT is occupied. Clearing stale process..."
  lsof -ti tcp:"$DESIRED_BACKEND_PORT" | xargs kill -9 2>/dev/null || true
  sleep 0.5
fi

# Standardize Frontend Port to 5173
DESIRED_FRONTEND_PORT="${FRONTEND_PORT:-5173}"
if ! is_port_free "$DESIRED_FRONTEND_PORT"; then
  echo -e "  [!] Port $DESIRED_FRONTEND_PORT is occupied. Clearing stale process..."
  lsof -ti tcp:"$DESIRED_FRONTEND_PORT" | xargs kill -9 2>/dev/null || true
  sleep 0.5
fi

export BACKEND_PORT="$DESIRED_BACKEND_PORT"
export PORT="$DESIRED_BACKEND_PORT"
export FRONTEND_PORT="$DESIRED_FRONTEND_PORT"

# Clean shutdown handler
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  echo -e "${ORANGE}Shutting down TransMark Studio...${NC}"
  if [ -n "$BACKEND_PID" ]; then
    pkill -P "$BACKEND_PID" 2>/dev/null || true
    kill -TERM "$BACKEND_PID" 2>/dev/null || true
  fi
  if [ -n "$FRONTEND_PID" ]; then
    pkill -P "$FRONTEND_PID" 2>/dev/null || true
    kill -TERM "$FRONTEND_PID" 2>/dev/null || true
  fi
  wait "$BACKEND_PID" 2>/dev/null || true
  wait "$FRONTEND_PID" 2>/dev/null || true
  echo -e "${EMERALD}TransMark Studio stopped cleanly.${NC}"
  exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# Start Backend
echo -e "  [*] Launching FastAPI Backend on port ${BOLD}$BACKEND_PORT${NC}..."
(
  cd "$SCRIPT_DIR/backend"
  PYTHONPATH="$SCRIPT_DIR/backend" "$VENV_PYTHON" -m uvicorn main:app \
    --host 0.0.0.0 \
    --port "$BACKEND_PORT" \
    --log-level info
) &
BACKEND_PID=$!

# Wait for Backend to become healthy
echo -e "  [*] Waiting for backend health probe..."
MAX_WAIT=20
WAIT_COUNT=0
HEALTHY=false

while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
  if curl -sf "http://127.0.0.1:$BACKEND_PORT/api/v1/system/health" >/dev/null 2>&1; then
    HEALTHY=true
    break
  fi
  sleep 0.5
  WAIT_COUNT=$((WAIT_COUNT + 1))
done

if [ "$HEALTHY" = true ]; then
  echo -e "  ${EMERALD}✓${NC} Backend healthy: ${MUTED}http://127.0.0.1:$BACKEND_PORT${NC}"
else
  echo -e "  [!] Warning: Backend health probe took longer than expected, continuing startup..."
fi

# Start Frontend
echo -e "  [*] Launching Vite Studio on port ${BOLD}$FRONTEND_PORT${NC}..."
(
  cd "$SCRIPT_DIR/frontend"
  BACKEND_PORT="$BACKEND_PORT" npm run dev -- --host 0.0.0.0 --port "$FRONTEND_PORT"
) &
FRONTEND_PID=$!

sleep 1

echo ""
echo "======================================================================"
echo -e "${BOLD}${ORANGE}  TRANSMARK STUDIO READY${NC}"
echo "======================================================================"
echo -e "  ${BOLD}Studio Web UI:${NC}    ${EMERALD}http://localhost:$FRONTEND_PORT${NC}"
echo -e "  ${BOLD}Backend API:${NC}      http://localhost:$BACKEND_PORT"
echo -e "  ${BOLD}System Health:${NC}    http://localhost:$BACKEND_PORT/api/v1/system/health"
echo -e "  ${BOLD}API Docs (Swagger):${NC} http://localhost:$BACKEND_PORT/docs"
echo -e "  ${BOLD}WebSocket Stream:${NC} ws://localhost:$BACKEND_PORT/ws/progress/{job_id}"
echo "======================================================================"
echo -e "${MUTED}Press Ctrl+C to stop all services.${NC}\n"

# Keep script running and waiting for background jobs
wait "$BACKEND_PID" "$FRONTEND_PID"
