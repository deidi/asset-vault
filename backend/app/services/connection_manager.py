import asyncio
import logging
from typing import Set, Dict, Any
from fastapi import WebSocket

logger = logging.getLogger("assetvault.ws")

class ConnectionManager:
    """Manages active WebSocket client connections and event broadcasts."""
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"WebSocket client connected. Total active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Total active: {len(self.active_connections)}")

    async def broadcast(self, event_type: str, data: Dict[str, Any]) -> None:
        """Broadcasts a JSON message to all connected clients."""
        if not self.active_connections:
            return

        message = {
            "event": event_type,
            "data": data
        }
        
        dead_connections = set()
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Error sending WebSocket message: {e}")
                dead_connections.add(connection)

        for dead in dead_connections:
            self.disconnect(dead)

    def broadcast_sync(self, event_type: str, data: Dict[str, Any]) -> None:
        """Thread-safe synchronous wrapper for scheduling async broadcast from background threads."""
        if not self.active_connections:
            return

        try:
            loop = self._loop or asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self.broadcast(event_type, data), loop)
        except Exception as e:
            logger.debug(f"Could not broadcast event {event_type} synchronously: {e}")

# Global singleton connection manager instance
manager = ConnectionManager()
