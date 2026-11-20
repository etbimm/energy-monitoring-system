from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.schemas import AlarmThresholds
from app.services import thresholds
from app.services.alarms import evaluate_conditions

DEVICE = SimpleNamespace(rated_power_kw=100.0)


class _Result:
    def __init__(self, row):
        self.row = row

    def scalar_one_or_none(self):
        return self.row


class _Session:
    def __init__(self, row):
        self.row = row

    async def execute(self, _stmt):
        return _Result(self.row)


def test_default_thresholds_match_previous_hardcoded_values():
    t = AlarmThresholds()
    assert (t.voltage_ll_warning_low, t.voltage_ll_warning_high) == (385.0, 415.0)
    assert (t.voltage_ll_critical_low, t.voltage_ll_critical_high) == (350.0, 440.0)
    assert (t.power_factor_warning, t.power_factor_critical) == (0.90, 0.85)
    assert (t.frequency_warning, t.frequency_critical) == (0.5, 1.0)
    assert (t.thd_current_warning, t.thd_current_critical) == (5.0, 8.0)
    assert (t.unbalance_voltage_warning, t.unbalance_voltage_critical) == (2.0, 5.0)
    assert (t.load_warning, t.load_critical) == (0.80, 0.95)


def test_custom_power_factor_threshold_is_used():
    custom = AlarmThresholds(power_factor_warning=0.95, power_factor_critical=0.90)
    assert [item[1] for item in evaluate_conditions({"power_factor": 0.92}, DEVICE, thresholds=custom)] == [
        "warning"
    ]
    # Dengan ambang bawaan, 0.92 masih normal.
    assert evaluate_conditions({"power_factor": 0.92}, DEVICE) == []


def test_custom_thd_threshold_is_used():
    custom = AlarmThresholds(thd_current_warning=8.5, thd_current_critical=10.0)
    assert [item[1] for item in evaluate_conditions({"thd_current": 8.5}, DEVICE, thresholds=custom)] == [
        "warning"
    ]
    # Bawaan: 8.5 sudah kritis.
    assert [item[1] for item in evaluate_conditions({"thd_current": 8.5}, DEVICE)] == ["critical"]


def test_custom_voltage_threshold_is_used():
    custom = AlarmThresholds(
        voltage_ll_warning_low=390.0,
        voltage_ll_warning_high=400.0,
        voltage_ll_critical_low=360.0,
        voltage_ll_critical_high=405.0,
    )
    assert [item[1] for item in evaluate_conditions({"voltage": 418.0}, DEVICE, thresholds=custom)] == [
        "critical"
    ]
    # Bawaan: 418 masih warning.
    assert [item[1] for item in evaluate_conditions({"voltage": 418.0}, DEVICE)] == ["warning"]


def test_threshold_validation_rejects_inverted_ranges():
    with pytest.raises(ValidationError):
        AlarmThresholds(
            voltage_ll_warning_low=390.0,
            voltage_ll_warning_high=415.0,
            voltage_ll_critical_low=400.0,
            voltage_ll_critical_high=440.0,
        )
    with pytest.raises(ValidationError):
        AlarmThresholds(power_factor_warning=0.80, power_factor_critical=0.90)
    with pytest.raises(ValidationError):
        AlarmThresholds(load_warning=0.95, load_critical=0.80)


def test_cached_thresholds_start_from_defaults():
    assert thresholds.current_thresholds() == thresholds.DEFAULT_ALARM_THRESHOLDS


@pytest.mark.asyncio
async def test_invalid_stored_thresholds_are_not_silently_replaced():
    with pytest.raises(ValidationError):
        await thresholds.load_thresholds(
            _Session(SimpleNamespace(thresholds={"power_factor_warning": 0.2}))
        )
