import pytest
from httpx import ASGITransport, AsyncClient

from app.api import client_errors
from app.main import app


@pytest.fixture(autouse=True)
def reset_rate_limiter():
    client_errors._report_times.clear()
    yield
    client_errors._report_times.clear()


async def _report_from(ip: str, count: int = 3) -> list[int]:
    transport = ASGITransport(app=app, client=(ip, 4000))
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return [
            (
                await client.post(
                    "/api/client-errors",
                    json={"key": "network-test-endpoint", "summary": "API tidak dapat diakses"},
                )
            ).status_code
            for _ in range(count)
        ]


@pytest.mark.asyncio
async def test_frontend_error_can_be_reported_and_resolved():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        reported = await client.post(
            "/api/client-errors",
            json={"key": "network-test-endpoint", "summary": "API tidak dapat diakses"},
        )
        resolved = await client.post(
            "/api/client-errors/network-test-endpoint/resolve"
        )

    assert reported.status_code == 200
    assert reported.json() == {"ok": True}
    assert resolved.status_code == 200
    assert resolved.json() == {"ok": True}


@pytest.mark.asyncio
async def test_rate_limit_is_per_client_ip(monkeypatch):
    monkeypatch.setattr(client_errors, "_REPORT_LIMIT", 2)

    # IP yang error berulang hanya menghabiskan kuotanya sendiri.
    assert await _report_from("10.0.0.1") == [200, 200, 429]
    assert await _report_from("10.0.0.2") == [200, 200, 429]
    assert await _report_from("10.0.0.1") == [429, 429, 429]
