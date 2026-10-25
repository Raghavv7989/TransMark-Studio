from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.logging import get_logger
from app.core.ws_manager import ws_manager, ConnectionManager

logger = get_logger("websockets")
router = APIRouter(tags=["websockets"])


@router.websocket("/ws/progress/{job_id}")
async def websocket_progress_endpoint(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint streaming real-time job progress:
    - job_id: The unique project processing job ID
    - Yields JobProgressUpdate JSON objects
    """
    await ws_manager.connect(websocket, job_id)
    try:
        while True:
            # Keep connection open and listen for client heartbeats or cancel signals
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type": "pong"}')
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, job_id)
    except Exception as e:
        logger.error(f"WebSocket error for job {job_id}: {e}")
        await ws_manager.disconnect(websocket, job_id)
