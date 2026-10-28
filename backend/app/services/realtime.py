from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

from app.config import get_settings


class Hub:
    def __init__(self) -> None:
        self.connections: set[WebSocket] = set()
        self.latest: dict[str, dict[str, Any]] = {}

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self.connections.add(ws)
        if self.latest:
            await ws.send_text(json.dumps({"type": "snapshot", "payload": list(self.latest.values())}, default=str))

    def disconnect(self, ws: WebSocket) -> None:
        self.connections.discard(ws)

    def remember(self, device_code: str, payload: dict[str, Any]) -> None:
        self.latest[device_code] = payload

    async def broadcast(self, message: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        data = json.dumps(message, default=str)
        for ws in self.connections:
            try:
                await ws.send_text(data)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.connections.discard(ws)


hub = Hub()


def device_status(last_seen_at: datetime | None, has_warning: bool = False) -> str:
    settings = get_settings()
    if last_seen_at is None:
        return "offline"
    if last_seen_at.tzinfo is None:
        last_seen_at = last_seen_at.replace(tzinfo=timezone.utc)
    age = (datetime.now(timezone.utc) - last_seen_at).total_seconds()
    if age > settings.offline_critical_seconds:
        return "offline"
    if age > settings.offline_warning_seconds or has_warning:
        return "warning"
    return "online"
