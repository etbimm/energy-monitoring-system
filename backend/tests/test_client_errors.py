import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


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
