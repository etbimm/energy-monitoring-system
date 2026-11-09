import asyncio
import time

import pytest

from app.services import realtime
from app.services.realtime import Hub


class FakeSocket:
    def __init__(self, delay: float = 0.0, fail: bool = False):
        self.delay = delay
        self.fail = fail
        self.sent: list[str] = []
        self.closed = False

    async def send_text(self, data: str) -> None:
        await asyncio.sleep(self.delay)
        if self.fail:
            raise RuntimeError("putus")
        self.sent.append(data)

    async def close(self, code: int = 1000) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_slow_client_does_not_block_broadcast(monkeypatch):
    monkeypatch.setattr(realtime, "SEND_TIMEOUT_SECONDS", 0.2)
    hub = Hub()
    fast, slow, broken = FakeSocket(), FakeSocket(delay=5), FakeSocket(fail=True)
    hub.connections = {fast, slow, broken}

    started = time.perf_counter()
    await hub.broadcast({"type": "telemetry"})
    elapsed = time.perf_counter() - started
    await asyncio.sleep(0.3)  # beri waktu task penutupan

    assert elapsed < 1.0  # tidak menunggu klien lambat 5 detik
    assert len(fast.sent) == 1
    assert hub.connections == {fast}  # klien lambat & rusak diputus
    assert slow.closed and broken.closed


@pytest.mark.asyncio
async def test_clients_receive_in_parallel():
    hub = Hub()
    clients = [FakeSocket(delay=0.2) for _ in range(5)]
    hub.connections = set(clients)
    started = time.perf_counter()
    await hub.broadcast({"type": "telemetry"})
    assert time.perf_counter() - started < 0.6  # berurutan butuh 1 detik
    assert all(len(c.sent) == 1 for c in clients)
