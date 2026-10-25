import asyncio
from collections import defaultdict
from typing import Dict, Optional, Set
from fastapi import WebSocket
from app.core.logging import get_logger
from app.models.job import JobProgressUpdate

logger = get_logger("ws_manager")


class ConnectionManager:
    """Thread/async-safe WebSocket manager partitioned by job_id."""

    def __init__(self) -> None:
        self._active_connections: Dict[str, Set[WebSocket]] = defaultdict(set)
        self._last_status: Dict[str, JobProgressUpdate] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, job_id: str) -> None:
        """Accept connection, register under job_id, and immediately send latest state."""
        await websocket.accept()
        async with self._lock:
            self._active_connections[job_id].add(websocket)
            cached_update = self._last_status.get(job_id)

        logger.info(f"WebSocket client connected for job {job_id}. Total active: {len(self._active_connections[job_id])}")

        if cached_update:
            try:
                await websocket.send_text(cached_update.model_dump_json())
            except Exception as e:
                logger.warning(f"Failed sending initial cached status for job {job_id}: {e}")

    async def disconnect(self, websocket: WebSocket, job_id: str) -> None:
        """Remove a disconnected WebSocket."""
        async with self._lock:
            if job_id in self._active_connections:
                self._active_connections[job_id].discard(websocket)
                if not self._active_connections[job_id]:
                    del self._active_connections[job_id]
        logger.info(f"WebSocket client disconnected for job {job_id}.")

    async def broadcast(self, job_id: str, update: JobProgressUpdate) -> None:
        """Broadcast status update to all connected subscribers for a job."""
        async with self._lock:
            self._last_status[job_id] = update
            subscribers = list(self._active_connections.get(job_id, []))

        payload = update.model_dump_json()
        dead_sockets: Set[WebSocket] = set()

        for ws in subscribers:
            try:
                await ws.send_text(payload)
            except Exception as err:
                logger.warning(f"Error sending update to client for job {job_id}: {err}")
                dead_sockets.add(ws)

        if dead_sockets:
            async with self._lock:
                for dead_ws in dead_sockets:
                    self._active_connections[job_id].discard(dead_ws)
                if not self._active_connections[job_id]:
                    del self._active_connections[job_id]

    def get_last_status(self, job_id: str) -> Optional[JobProgressUpdate]:
        """Get the most recent cached status update for a job."""
        return self._last_status.get(job_id)

    def set_last_status(self, job_id: str, update: JobProgressUpdate) -> None:
        """Cache status update directly."""
        self._last_status[job_id] = update


# Global singleton instance
ws_manager = ConnectionManager()
