import json

import pytest
from sqlalchemy.exc import SQLAlchemyError

from app.api import health
from app.services.auth import login_throttle
from app.services import mqtt_state


class _Session:
    def __init__(self, healthy: bool = True):
        self.healthy = healthy

    async def execute(self, _stmt):
        if not self.healthy:
            raise SQLAlchemyError("database down")
        return None


@pytest.mark.asyncio
async def test_health_reports_database_and_mqtt_ok(monkeypatch):
    monkeypatch.setattr(mqtt_state, "_state", "ok")
    async def redis_ok():
        return True

    monkeypatch.setattr(login_throttle, "ping", redis_ok)
    response = await health.health(_Session())
    assert response.status_code == 200
    assert json.loads(response.body) == {
        "status": "ok",
        "database": "ok",
        "mqtt": "ok",
        "redis": "ok",
    }


@pytest.mark.asyncio
async def test_health_degraded_when_database_or_mqtt_down(monkeypatch):
    monkeypatch.setattr(mqtt_state, "_state", "disconnected")
    async def redis_ok():
        return True

    monkeypatch.setattr(login_throttle, "ping", redis_ok)
    response = await health.health(_Session(healthy=False))
    assert response.status_code == 503
    assert json.loads(response.body) == {
        "status": "degraded",
        "database": "error",
        "mqtt": "error",
        "redis": "ok",
    }


@pytest.mark.asyncio
async def test_health_degraded_when_mqtt_disconnected(monkeypatch):
    monkeypatch.setattr(mqtt_state, "_state", "disconnected")
    async def redis_ok():
        return True

    monkeypatch.setattr(login_throttle, "ping", redis_ok)
    response = await health.health(_Session())
    assert response.status_code == 503
    assert json.loads(response.body) == {
        "status": "degraded",
        "database": "ok",
        "mqtt": "error",
        "redis": "ok",
    }


@pytest.mark.asyncio
async def test_health_degraded_when_redis_unavailable(monkeypatch):
    monkeypatch.setattr(mqtt_state, "_state", "ok")

    async def redis_down():
        from redis.exceptions import ConnectionError

        raise ConnectionError("redis down")

    monkeypatch.setattr(login_throttle, "ping", redis_down)
    response = await health.health(_Session())
    assert response.status_code == 503
    assert json.loads(response.body) == {
        "status": "degraded",
        "database": "ok",
        "mqtt": "ok",
        "redis": "error",
    }
