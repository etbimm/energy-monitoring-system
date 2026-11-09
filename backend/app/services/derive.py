from __future__ import annotations

from dataclasses import dataclass


def _round(value: float, digits: int) -> float:
    factor = 10**digits
    return round(value * factor) / factor


def derive_power_factor(power: float | None, apparent_power: float | None) -> float | None:
    if power is None or apparent_power in (None, 0):
        return None
    return _round(abs(power / apparent_power), 3)


def derive_energy_apparent(energy_active: float | None, power_factor: float | None) -> float | None:
    """Nilai awal counter kVAh: kWh / PF (dipakai bila belum ada pembacaan sebelumnya)."""
    if energy_active is None or not power_factor:
        return None
    return _round(energy_active / power_factor, 2)


@dataclass(frozen=True)
class PreviousReading:
    """Pembacaan terakhir meter yang tersimpan (basis integrasi kVAh)."""

    energy_active: float | None
    energy_apparent: float | None
    power_factor: float | None


def integrate_energy_apparent(
    energy_active: float | None,
    power_factor: float | None,
    previous: PreviousReading | None,
) -> float | None:
    """Counter kVAh kumulatif, diintegrasikan per interval.

    `kVAh_n = kVAh_(n-1) + ΔkWh / PF_rata2`, dengan `ΔkWh = kWh_n - kWh_(n-1)`
    dan `PF_rata2` = rata-rata PF awal & akhir interval (yang tersedia).
    Berbeda dari `kWh / PF` sesaat, counter ini selalu naik walau PF berubah.

    - Tanpa pembacaan sebelumnya (atau kVAh sebelumnya kosong): nilai awal
      `kWh / PF`.
    - `ΔkWh < 0` (counter meter reset/diganti): mulai ulang dari `kWh / PF`.
    - PF tidak diketahui di kedua ujung interval (S = 0, tanpa beban):
      `ΔkVAh = ΔkWh` (PF dianggap 1).
    """
    if energy_active is None:
        return None
    if previous is None or previous.energy_active is None or previous.energy_apparent is None:
        return derive_energy_apparent(energy_active, power_factor)

    delta = energy_active - previous.energy_active
    if delta < 0:
        return derive_energy_apparent(energy_active, power_factor)

    factors = [pf for pf in (previous.power_factor, power_factor) if pf]
    pf_avg = sum(factors) / len(factors) if factors else 1.0
    return _round(previous.energy_apparent + delta / pf_avg, 3)


def apply_derived(payload: dict, previous: PreviousReading | None = None) -> dict:
    """PF dan kVAh selalu dihitung di backend, tidak diambil dari register meter."""
    result = dict(payload)
    pf = derive_power_factor(result.get("power"), result.get("apparent_power"))
    result["power_factor"] = pf
    result["energy_apparent"] = integrate_energy_apparent(result.get("energy_active"), pf, previous)

    phases = result.get("phases") or {}
    for phase_name, phase in phases.items():
        phase_pf = derive_power_factor(phase.get("power"), phase.get("apparent_power"))
        phase["power_factor"] = phase_pf
        phases[phase_name] = phase
    result["phases"] = phases
    return result
