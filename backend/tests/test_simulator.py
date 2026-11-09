from app.acquisition.profiles import DEVICE_MODEL, register_capabilities
from app.acquisition.simulator import NOMINAL, simulate_telemetry


def test_simulated_online_meters_have_thd_readings():
    for device_code, model in DEVICE_MODEL.items():
        meter_capabilities = register_capabilities(model)
        reading = simulate_telemetry(device_code, meter_capabilities)
        if NOMINAL[device_code].get("offline"):
            assert reading is None
            continue

        assert reading is not None
        # Pembacaan pertama (tanpa state counter) dimulai dari energi awal spec.
        assert reading["energy_active"] >= NOMINAL[device_code]["energy"]
        assert reading["thd_current"] is not None
        if not meter_capabilities["thdVoltage"]:
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


def _fixed_now(monkeypatch, simulator, moment):
    from datetime import datetime

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return moment if tz is None else moment.astimezone(tz)

    monkeypatch.setattr(simulator, "datetime", FixedDateTime)


def test_energy_counter_integrates_power(monkeypatch):
    """kWh naik sebesar rata-rata kW x jam, bukan rumus tetap per hari."""
    from datetime import datetime, timedelta, timezone

    import app.acquisition.simulator as simulator

    monkeypatch.setattr(simulator.random, "random", lambda: 0.5)
    start = datetime(2026, 11, 9, 5, 0, tzinfo=timezone.utc)  # 12:00 WIB, beban puncak
    _fixed_now(monkeypatch, simulator, start)
    first = simulator.simulate_decoded("PM-LVMDP-IN-01", {})
    _fixed_now(monkeypatch, simulator, start + timedelta(minutes=30))
    second = simulator.simulate_decoded("PM-LVMDP-IN-01", {})

    expected = (first["power"] + second["power"]) / 2 * 0.5
    # Toleransi 0,002 karena counter dibulatkan 3 desimal.
    assert abs((second["energy_active"] - first["energy_active"]) - expected) <= 0.002
    expected_kvarh = (first["reactive_power"] + second["reactive_power"]) / 2 * 0.5
    assert abs((second["energy_reactive"] - first["energy_reactive"]) - expected_kvarh) <= 0.002


def test_counter_continues_from_database_after_restart(monkeypatch):
    from datetime import datetime, timedelta, timezone

    import app.acquisition.simulator as simulator

    last = datetime(2026, 11, 9, 5, 0, tzinfo=timezone.utc)
    simulator.prime_counter("PM-MCC1-01", last, 8000.0, 3200.0, 40.0, 20.0)
    _fixed_now(monkeypatch, simulator, last + timedelta(seconds=5))
    reading = simulator.simulate_decoded("PM-MCC1-01", {})
    # Lanjut dari 8000 kWh, bukan mulai ulang dari energi awal spec.
    assert 8000.0 < reading["energy_active"] < 8000.2
    assert 3200.0 < reading["energy_reactive"] < 3200.2
