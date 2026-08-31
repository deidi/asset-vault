import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.services.connection_manager import manager

logger = logging.getLogger("assetvault.ws_routes")

router = APIRouter(tags=["WebSocket"])

@router.websocket("/ws/events")
async def websocket_events_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time filesystem and system event notifications."""
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive and receive incoming client pings or query messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.debug(f"WebSocket client connection closed: {e}")
        manager.disconnect(websocket)
