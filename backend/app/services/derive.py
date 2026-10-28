from __future__ import annotations


def _round(value: float, digits: int) -> float:
    factor = 10**digits
    return round(value * factor) / factor


def derive_power_factor(power: float | None, apparent_power: float | None) -> float | None:
    if power is None or apparent_power in (None, 0):
        return None
    return _round(abs(power / apparent_power), 3)


def derive_energy_apparent(energy_active: float | None, power_factor: float | None) -> float | None:
    if energy_active is None or not power_factor:
        return None
    return _round(energy_active / power_factor, 2)


def apply_derived(payload: dict) -> dict:
    """PF dan kVAh selalu dihitung di backend, tidak diambil dari register meter."""
    result = dict(payload)
    pf = derive_power_factor(result.get("power"), result.get("apparent_power"))
    result["power_factor"] = pf
    result["energy_apparent"] = derive_energy_apparent(result.get("energy_active"), pf)

    phases = result.get("phases") or {}
    for phase_name, phase in phases.items():
        phase_pf = derive_power_factor(phase.get("power"), phase.get("apparent_power"))
        phase["power_factor"] = phase_pf
        phases[phase_name] = phase
    result["phases"] = phases
    return result
