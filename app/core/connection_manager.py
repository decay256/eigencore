"""WebSocket ConnectionManager for room-based real-time communication.

Replaces the bare dict[str, set[WebSocket]] with a proper class that
encapsulates connect/disconnect/broadcast logic and is easier to swap
for a Redis pub/sub backend later.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages per-room WebSocket connections."""

    def __init__(self) -> None:
        # room_code (upper) -> set of active websockets
        self._rooms: dict[str, set[WebSocket]] = defaultdict(set)

    # -- lifecycle ----------------------------------------------------------

    def connect(self, room_code: str, websocket: WebSocket) -> None:
        """Register *websocket* in *room_code*."""
        key = room_code.upper()
        self._rooms[key].add(websocket)
        logger.debug("ws connect room=%s total=%d", key, len(self._rooms[key]))

    def disconnect(self, room_code: str, websocket: WebSocket) -> None:
        """Remove *websocket* from *room_code*, cleaning up empty rooms."""
        key = room_code.upper()
        self._rooms[key].discard(websocket)
        if not self._rooms[key]:
            del self._rooms[key]
        logger.debug("ws disconnect room=%s", key)

    # -- messaging ----------------------------------------------------------

    async def broadcast(self, room_code: str, message: dict[str, Any]) -> None:
        """Send *message* to **all** connections in *room_code*."""
        key = room_code.upper()
        for ws in list(self._rooms.get(key, ())):
            try:
                await ws.send_json(message)
            except Exception:
                logger.warning("broadcast send failed, removing ws from %s", key)
                self.disconnect(key, ws)

    async def broadcast_except(
        self,
        room_code: str,
        message: dict[str, Any],
        exclude: WebSocket,
    ) -> None:
        """Send *message* to every connection in *room_code* except *exclude*."""
        key = room_code.upper()
        for ws in list(self._rooms.get(key, ())):
            if ws is exclude:
                continue
            try:
                await ws.send_json(message)
            except Exception:
                logger.warning("broadcast_except send failed, removing ws from %s", key)
                self.disconnect(key, ws)

    # -- introspection ------------------------------------------------------

    def count(self, room_code: str) -> int:
        """Return number of connections in *room_code*."""
        return len(self._rooms.get(room_code.upper(), ()))

    def rooms(self) -> list[str]:
        """Return list of room codes with active connections."""
        return list(self._rooms.keys())


# Module-level singleton — import this from routes.
manager = ConnectionManager()
