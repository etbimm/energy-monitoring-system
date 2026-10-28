from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _mean(values: list[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    if not present:
        return None
    return round(sum(present) / len(present) * 1000) / 1000


def _get(decoded: dict[str, float], *keys: str) -> float | None:
    for key in keys:
        if key in decoded:
            return decoded[key]
    return None


def _optional(value: float | None, supported: bool) -> float | None:
    if not supported:
        return None
    return value


def to_telemetry(
    device_code: str,
    decoded: dict[str, float],
    capabilities: dict[str, Any] | None = None,
    timestamp: datetime | None = None,
) -> dict[str, Any]:
    """Ubah hasil decode per-register menjadi kontrak MQTT engineering."""
    caps = capabilities or {}
    ts = timestamp or datetime.now(timezone.utc)

    voltage = _mean(
        [
            _get(decoded, "voltage_l1", "voltage_l12"),
            _get(decoded, "voltage_l2", "voltage_l23"),
            _get(decoded, "voltage_l3", "voltage_l31"),
        ]
    )
    current = _mean(
        [
            decoded.get("current_l1"),
            decoded.get("current_l2"),
            decoded.get("current_l3"),
        ]
    )

    thd_current = _optional(
        _mean(
            [
                decoded.get("thd_current_l1"),
                decoded.get("thd_current_l2"),
                decoded.get("thd_current_l3"),
            ]
        ),
        bool(caps.get("thdCurrent", True)),
    )
    thd_voltage = _optional(
        _mean(
            [
                decoded.get("thd_voltage_l1"),
                decoded.get("thd_voltage_l2"),
                decoded.get("thd_voltage_l3"),
            ]
        ),
        bool(caps.get("thdVoltage", True)),
    )
    unbalance_voltage = _optional(
        decoded.get("unbalance_voltage"),
        bool(caps.get("unbalance", False)),
    )
    unbalance_current = _optional(
        decoded.get("unbalance_current"),
        bool(caps.get("unbalance", False)),
    )

    phases = {}
    for index, name in enumerate(("L1", "L2", "L3"), start=1):
        suffix = str(index)
        phase_voltage = _get(decoded, f"voltage_l{suffix}", f"voltage_l{suffix}{suffix % 3 + 1}")
        if name == "L1":
            phase_voltage = _get(decoded, "voltage_l1", "voltage_l12")
        elif name == "L2":
            phase_voltage = _get(decoded, "voltage_l2", "voltage_l23")
        else:
            phase_voltage = _get(decoded, "voltage_l3", "voltage_l31")

        phases[name] = {
            "voltage": phase_voltage,
            "current": decoded.get(f"current_l{suffix}"),
            "power": decoded.get(f"power_l{suffix}"),
            "apparent_power": decoded.get(f"apparent_power_l{suffix}"),
            "reactive_power": decoded.get(f"reactive_power_l{suffix}"),
            "thd_current": _optional(decoded.get(f"thd_current_l{suffix}"), bool(caps.get("thdCurrent", True))),
            "thd_voltage": _optional(decoded.get(f"thd_voltage_l{suffix}"), bool(caps.get("thdVoltage", True))),
        }

    return {
        "device_code": device_code,
        "timestamp": ts.replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "voltage": voltage,
        "current": current,
        "power": decoded.get("power"),
        "apparent_power": decoded.get("apparent_power"),
        "reactive_power": decoded.get("reactive_power"),
        "energy_active": decoded.get("energy_active"),
        "energy_reactive": decoded.get("energy_reactive"),
        "frequency": decoded.get("frequency"),
        "thd_current": thd_current,
        "thd_voltage": thd_voltage,
        "unbalance_voltage": unbalance_voltage,
        "unbalance_current": unbalance_current,
        "phases": phases,
    }
