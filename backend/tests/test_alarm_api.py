"""Acknowledge alarm membentuk respons dari objek yang sama (tanpa re-query)."""
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from app.api.alarms import acknowledge_alarm


class _Result:
    def __init__(self, row):
        self._row = row

    def first(self):
        return self._row


class _Session:
    def __init__(self, row):
        self.row = row
        self.flushed = False
        self.committed = False
        self.added = []

    async def execute(self, _stmt):
        return _Result(self.row)

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        self.flushed = True

    async def commit(self):
        self.committed = True


@pytest.mark.asyncio
async def test_acknowledge_returns_updated_alarm_without_relisting():
    alarm = SimpleNamespace(
        id=7,
        severity="warning",
        message="Power factor rendah",
        acknowledged=False,
        acknowledged_at=None,
        triggered_at=datetime.now(timezone.utc),
    )
    device = SimpleNamespace(device_code="PM-X", name="Meter X")
    session = _Session((alarm, device))
    admin = SimpleNamespace(id=1, username="admin")

    result = await acknowledge_alarm(7, admin, session)

    assert result.id == "7"
    assert result.acknowledged is True
    assert result.device_id == "PM-X"
    assert result.device_name == "Meter X"
    assert session.flushed and session.committed
    assert len(session.added) == 1
    assert session.added[0].action == "alarm.acknowledge"
    assert session.added[0].username == "admin"
    assert session.added[0].target == "PM-X"
    assert session.added[0].detail == {"alarm_id": 7, "severity": "warning"}
