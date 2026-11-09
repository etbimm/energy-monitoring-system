from app.services.derive import apply_derived, derive_energy_apparent, derive_power_factor


def test_pf_from_kw_kva():
    assert derive_power_factor(94, 100) == 0.94


def test_kvah_from_kwh_pf():
    assert derive_energy_apparent(1000, 0.94) == 1063.83


def test_zero_kva_does_not_crash():
    assert derive_power_factor(0, 0) is None


def test_apply_derived_ignores_meter_pf():
    payload = apply_derived(
        {
            "power": 94,
            "apparent_power": 100,
            "energy_active": 1000,
            "power_factor": 0.5,
        }
    )
    assert payload["power_factor"] == 0.94
    assert payload["energy_apparent"] == 1063.83


from app.services.derive import PreviousReading, integrate_energy_apparent


def test_kvah_is_integrated_per_interval():
    prev = PreviousReading(energy_active=1000.0, energy_apparent=1063.83, power_factor=0.94)
    # +10 kWh dengan PF rata-rata (0.94 + 0.86) / 2 = 0.90 -> +11.111 kVAh
    assert integrate_energy_apparent(1010.0, 0.86, prev) == round(1063.83 + 10 / 0.90, 3)


def test_kvah_counter_never_decreases_when_pf_rises():
    # Rumus lama kWh/PF: 1000/0.80 = 1250 lalu 1001/0.99 = 1011 (turun!).
    first = integrate_energy_apparent(1000.0, 0.80, None)
    second = integrate_energy_apparent(1001.0, 0.99, PreviousReading(1000.0, first, 0.80))
    assert first == 1250.0
    assert second > first


def test_kvah_restarts_after_meter_reset():
    prev = PreviousReading(energy_active=5000.0, energy_apparent=5500.0, power_factor=0.9)
    assert integrate_energy_apparent(10.0, 0.9, prev) == derive_energy_apparent(10.0, 0.9)


def test_kvah_without_pf_assumes_unity():
    prev = PreviousReading(energy_active=100.0, energy_apparent=110.0, power_factor=None)
    assert integrate_energy_apparent(100.5, None, prev) == 110.5


def test_apply_derived_uses_previous_reading():
    prev = PreviousReading(energy_active=1000.0, energy_apparent=1100.0, power_factor=0.95)
    payload = apply_derived(
        {"power": 95, "apparent_power": 100, "energy_active": 1009.5}, prev
    )
    assert payload["energy_apparent"] == 1110.0
