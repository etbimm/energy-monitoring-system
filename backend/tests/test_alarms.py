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
