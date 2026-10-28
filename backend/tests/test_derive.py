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
