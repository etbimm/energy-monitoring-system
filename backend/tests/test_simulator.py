from app.acquisition.profiles import DEVICE_MODEL
from app.acquisition.simulator import NOMINAL, simulate_telemetry


def test_simulated_online_meters_have_thd_readings():
    capabilities = {"thdCurrent": True, "thdVoltage": True}

    for device_code, model in DEVICE_MODEL.items():
        meter_capabilities = {
            **capabilities,
            "thdVoltage": model != "WEIDMULLER EM220",
        }
        reading = simulate_telemetry(device_code, meter_capabilities)
        if NOMINAL[device_code].get("offline"):
            assert reading is None
            continue

        assert reading is not None
        assert reading["energy_active"] > NOMINAL[device_code]["energy"]
        assert reading["thd_current"] is not None
        if model == "WEIDMULLER EM220":
            assert reading["thd_voltage"] is None
        else:
            assert reading["thd_voltage"] is not None


def test_simulator_sends_only_voltage_registers_of_the_model():
    caps = {"thdCurrent": True, "thdVoltage": True}
    pac = simulate_telemetry("PM-LVMDP-IN-01", caps, "SIEMENS PAC3220")
    assert pac["voltage_ln"] is None
    assert 395 < pac["voltage_ll"] < 405

    acrel = simulate_telemetry("PM-MCC1-01", caps, "ACREL AMC96")
    assert acrel["voltage_ll"] is None
    assert 225 < acrel["voltage_ln"] < 235
    assert 395 < acrel["voltage"] < 405


def test_simulated_energy_counter_is_monotonic(monkeypatch):
    from datetime import datetime, timezone

    import app.acquisition.simulator as simulator

    readings = []
    for day, hour in [(5, 23), (6, 1), (7, 12)]:
        fixed = datetime(2026, 11, day, hour, tzinfo=timezone.utc)

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed

        monkeypatch.setattr(simulator, "datetime", FixedDateTime)
        readings.append(simulator.simulate_decoded("PM-LVMDP-IN-01", {})["energy_active"])
    assert readings == sorted(readings)


def test_load_profile_follows_local_wib_hour(monkeypatch):
    from datetime import datetime, timezone

    import app.acquisition.simulator as simulator

    monkeypatch.setattr(simulator.random, "random", lambda: 0.5)

    def power_at(utc_hour: int) -> float:
        fixed = datetime(2026, 11, 9, utc_hour, tzinfo=timezone.utc)

        class FixedDateTime(datetime):
            @classmethod
            def now(cls, tz=None):
                return fixed if tz is None else fixed.astimezone(tz)

        monkeypatch.setattr(simulator, "datetime", FixedDateTime)
        return simulator.simulate_decoded("PM-LVMDP-IN-01", {})["power"]

    nominal = simulator.NOMINAL["PM-LVMDP-IN-01"]["power"]
    # 05:00 UTC = 12:00 WIB -> beban puncak (1.15)
    assert power_at(5) == round(nominal * 1.15, 3)
    # 13:00 UTC = 20:00 WIB -> beban malam (0.35)
    assert power_at(13) == round(nominal * 0.35, 3)
