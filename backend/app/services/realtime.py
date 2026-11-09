from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from typing import Any

from fastapi import WebSocket

from app.config import get_settings

# Batas waktu kirim per klien WebSocket (detik).
SEND_TIMEOUT_SECONDS = 2.0


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

    async def _send(self, ws: WebSocket, data: str) -> bool:
        try:
            await asyncio.wait_for(ws.send_text(data), SEND_TIMEOUT_SECONDS)
            return True
        except Exception:
            return False

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Kirim ke semua klien secara paralel, masing-masing dengan batas waktu.

        broadcast dipanggil dari jalur ingest telemetry, jadi satu klien yang
        lambat (mis. koneksi Wi-Fi buruk) tidak boleh menahan penyimpanan data.
        Klien yang gagal atau melewati batas waktu diputus.
        """
        if not self.connections:
            return
        data = json.dumps(message, default=str)
        clients = list(self.connections)
        results = await asyncio.gather(*(self._send(ws, data) for ws in clients))
        for ws, ok in zip(clients, results):
            if not ok:
                self.connections.discard(ws)
                asyncio.get_running_loop().create_task(self._close(ws))

    @staticmethod
    async def _close(ws: WebSocket) -> None:
        try:
            await asyncio.wait_for(ws.close(code=1011), SEND_TIMEOUT_SECONDS)
        except Exception:
            pass


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
