"""
WebSocket connection manager for real-time agent telemetry streaming.
Streams live agent thoughts, tool execution logs, and approval events to the UI.
"""

from typing import List, Dict, Any
from fastapi import WebSocket
from utils.logger import logger


class TelemetryConnectionManager:
    """Manages active WebSocket connections to frontend clients."""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Active connections: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Active connections: {len(self.active_connections)}")

    async def broadcast(self, event_type: str, data: Dict[str, Any]):
        """Broadcasts a structured JSON event to all connected UI clients."""
        payload = {
            "event": event_type,
            "data": data
        }
        for connection in list(self.active_connections):
            try:
                await connection.send_json(payload)
            except Exception as e:
                logger.warning(f"Failed to send event to WebSocket client: {e}")
                self.disconnect(connection)


telemetry_manager = TelemetryConnectionManager()

