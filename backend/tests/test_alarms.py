from types import SimpleNamespace

from app.acquisition.normalize import to_telemetry
from app.services.alarms import evaluate_conditions

DEVICE = SimpleNamespace(rated_power_kw=None)


def _voltage_alarms(payload: dict) -> list[tuple[str, str, str]]:
    return [item for item in evaluate_conditions(payload, DEVICE) if item[0] == "voltage"]


def test_normal_line_to_neutral_voltage_has_no_alarm():
    assert _voltage_alarms({"voltage_ln": 230.5, "voltage": 399.2}) == []


def test_low_line_to_neutral_voltage_is_critical():
    alarms = _voltage_alarms({"voltage_ln": 200.0})
    assert alarms and alarms[0][1] == "critical"
    assert "L-N" in alarms[0][2]


def test_slightly_high_line_to_neutral_voltage_is_warning():
    alarms = _voltage_alarms({"voltage_ln": 245.0})
    assert alarms and alarms[0][1] == "warning"


def test_line_to_line_limits_still_apply():
    assert _voltage_alarms({"voltage_ll": 400.0}) == []
    assert _voltage_alarms({"voltage_ll": 345.0})[0][1] == "critical"
    # Payload lama tanpa voltage_ln/voltage_ll: `voltage` dianggap L-L.
    assert _voltage_alarms({"voltage": 400.0}) == []


def test_normalize_derives_system_voltage_from_line_to_neutral():
    payload = to_telemetry(
        "X", {"voltage_l1": 230.0, "voltage_l2": 230.0, "voltage_l3": 230.0}
    )
    assert payload["voltage_ln"] == 230.0
    assert payload["voltage_ll"] is None
    assert round(payload["voltage"], 1) == 398.4
    assert payload["phases"]["L1"]["voltage"] == 230.0


def test_normalize_keeps_measured_line_to_line():
    payload = to_telemetry(
        "X", {"voltage_l12": 400.0, "voltage_l23": 401.0, "voltage_l31": 402.0}
    )
    assert payload["voltage_ln"] is None
    assert payload["voltage_ll"] == 401.0
    assert payload["voltage"] == 401.0


# ---------------------------------------------------------------------------
# Delay dan hysteresis (A15) + notifikasi alarm kritis (A17)
# ---------------------------------------------------------------------------
from datetime import datetime, timedelta, timezone

import pytest

from app.models import Alarm
from app.services.alarms import AlarmTracker, apply_alarms


class _Result:
    def __init__(self, items):
        self._items = items

    def scalars(self):
        return self

    def all(self):
        return list(self._items)


class FakeSession:
    """Session minimal: menyimpan alarm di list, tanpa database."""

    def __init__(self):
        self.alarms: list[Alarm] = []
        self._next_id = 1

    async def execute(self, _stmt):
        return _Result([a for a in self.alarms if a.cleared_at is None])

    def add(self, alarm):
        self.alarms.append(alarm)

    async def flush(self):
        for alarm in self.alarms:
            if alarm.id is None:
                alarm.id = self._next_id
                self._next_id += 1


T0 = datetime(2026, 11, 6, 8, 0, tzinfo=timezone.utc)
METER = SimpleNamespace(id=1, device_code="PM-X", name="Meter X", rated_power_kw=None)


async def _step(session, state, seconds, pf):
    return await apply_alarms(
        session, METER, {"power_factor": pf}, now=T0 + timedelta(seconds=seconds), state=state
    )


@pytest.mark.asyncio
async def test_alarm_waits_for_on_delay():
    session, state = FakeSession(), AlarmTracker()
    created, _ = await _step(session, state, 0, 0.88)
    assert created == []
    created, _ = await _step(session, state, 15, 0.88)
    assert created == []
    created, _ = await _step(session, state, 30, 0.88)
    assert [a.alarm_type for a in created] == ["power_factor"]


@pytest.mark.asyncio
async def test_short_spike_does_not_create_alarm():
    session, state = FakeSession(), AlarmTracker()
    await _step(session, state, 0, 0.88)
    await _step(session, state, 10, 0.95)  # kembali normal sebelum delay
    created, _ = await _step(session, state, 35, 0.88)
    assert created == []
    assert session.alarms == []


@pytest.mark.asyncio
async def test_hysteresis_keeps_alarm_inside_deadband_and_clears_after_off_delay():
    session, state = FakeSession(), AlarmTracker()
    await _step(session, state, 0, 0.88)
    await _step(session, state, 30, 0.88)
    alarm = session.alarms[0]

    # 0.905 sudah di atas ambang 0.90, tetapi masih di dalam deadband (+0.01).
    await _step(session, state, 60, 0.905)
    await _step(session, state, 120, 0.905)
    assert alarm.cleared_at is None

    # Benar-benar normal: baru clear setelah bertahan >= 30 detik.
    await _step(session, state, 130, 0.95)
    assert alarm.cleared_at is None
    await _step(session, state, 160, 0.95)
    assert alarm.cleared_at == T0 + timedelta(seconds=160)


@pytest.mark.asyncio
async def test_critical_alarm_produces_telegram_report_and_recovery():
    session, state = FakeSession(), AlarmTracker()
    await _step(session, state, 0, 0.80)
    _, notices = await _step(session, state, 30, 0.80)
    assert [(n.action, n.key) for n in notices] == [("report", "alarm:PM-X:power_factor")]
    assert "Meter X (PM-X)" in notices[0].text

    # Turun ke warning -> notifikasi pulih dari kondisi kritis.
    _, notices = await _step(session, state, 60, 0.88)
    assert [(n.action, n.key) for n in notices] == [("resolve", "alarm:PM-X:power_factor")]


@pytest.mark.asyncio
async def test_warning_alarm_is_not_reported_to_telegram():
    session, state = FakeSession(), AlarmTracker()
    await _step(session, state, 0, 0.88)
    _, notices = await _step(session, state, 30, 0.88)
    assert all(n.action == "resolve" for n in notices)
