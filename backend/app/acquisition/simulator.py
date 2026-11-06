from __future__ import annotations

import math
import random
from datetime import datetime, timezone

from app.acquisition.normalize import to_telemetry
from app.acquisition.profiles import DEVICE_MODEL, PROFILES

VOLTAGE_KEYS = (
    "voltage_l1", "voltage_l2", "voltage_l3",
    "voltage_l12", "voltage_l23", "voltage_l31",
)
SQRT3 = math.sqrt(3)
ENERGY_EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _model_register_keys(model: str | None) -> set[str] | None:
    profile = PROFILES.get(model or "")
    if profile is None:
        return None
    return {register.key for register in profile.registers}

NOMINAL = {
    "PM-LVMDP-IN-01": {"power": 118.6, "pf": 0.94, "energy": 1421.3, "thd_i": 2.4, "thd_u": 1.3, "u_unb": 0.6, "i_unb": 1.8},
    "PM-LVMDP-IN-02": {"power": 74.2, "pf": 0.92, "energy": 889.4, "thd_i": 3.1, "thd_u": 1.6, "u_unb": 0.9, "i_unb": 2.4},
    "PM-LVMDP-IN-03": {"power": 52.8, "pf": 0.88, "energy": 633.6, "thd_i": 6.2, "thd_u": 2.4, "u_unb": 1.8, "i_unb": 5.1},
    "PM-LVMDP-IN-04": {"power": 33.1, "pf": 0.93, "energy": 397.2, "thd_i": 2.7, "thd_u": 1.4, "u_unb": 0.5, "i_unb": 1.2},
    "PM-LVMDP-IN-05": {"power": 21.3, "pf": 0.90, "energy": 255.6, "thd_i": 2.2, "thd_u": 1.2, "u_unb": 0.4, "i_unb": 1.5},
    "PM-LVMDP-OUT-01": {"power": 96.4, "pf": 0.91, "energy": 1156.8, "thd_i": 3.8, "thd_u": 1.9},
    "PM-LVMDP-OUT-02": {"power": 71.8, "pf": 0.90, "energy": 861.6, "thd_i": 4.2, "thd_u": 2.1},
    "PM-LVMDP-OUT-03": {"power": 55.2, "pf": 0.92, "energy": 662.4, "thd_i": 3.4, "thd_u": 1.7},
    "PM-MVMDP-01": {"power": 64.5, "pf": 0.95, "energy": 774.0, "thd_i": 5.8, "thd_u": 2.9},
    "PM-MCC1-01": {"power": 42.6, "pf": 0.90, "energy": 511.2, "thd_i": 3.6, "thd_u": 1.8},
    "PM-MCC1-02": {"power": 38.2, "pf": 0.89, "energy": 458.4, "thd_i": 5.4, "thd_u": 2.6},
    "PM-MCC2-01": {"power": 29.4, "pf": 0.88, "energy": 352.8, "thd_i": 4.1, "thd_u": 2.2},
    "PM-MCC3-01": {"power": 31.7, "pf": 0.91, "energy": 380.4, "thd_i": 3.2, "thd_u": 1.6},
    "PM-MCC3-02": {"power": 27.3, "pf": 0.90, "energy": 327.6, "thd_i": 2.9, "thd_u": 1.5},
    "PM-MCC4-01": {"power": 0.0, "pf": 0.90, "energy": 210.0, "thd_i": 3.4, "thd_u": 1.7, "offline": True},
    "PM-PEL1-01": {"power": 26.5, "pf": 0.93, "energy": 318.0, "thd_i": 3.7, "thd_u": 1.9},
    "PM-PEL2-01": {"power": 24.1, "pf": 0.92, "energy": 289.2, "thd_i": 4.3, "thd_u": 2.1},
    "PM-PEL3-01": {"power": 28.9, "pf": 0.94, "energy": 346.8, "thd_i": 3.5, "thd_u": 1.7},
}


def _load_factor(hour: int) -> float:
    if hour < 6:
        return 0.25
    if hour < 8:
        return 0.55
    if hour < 11:
        return 0.95
    if hour < 14:
        return 1.15
    if hour < 17:
        return 1.00
    if hour < 20:
        return 0.70
    return 0.35


def simulate_decoded(
    device_code: str,
    capabilities: dict,
    model: str | None = None,
) -> dict[str, float] | None:
    spec = NOMINAL.get(device_code)
    if spec is None or spec.get("offline"):
        return None

    now = datetime.now(timezone.utc)
    jitter = 0.97 + random.random() * 0.06
    power = spec["power"] * _load_factor(now.hour) * jitter
    pf = spec["pf"]
    apparent = power / pf if pf else power
    reactive = power * math.tan(math.acos(min(max(pf, 0.01), 0.999))) if 0 < pf < 1 else 0.0
    # Tegangan antar-fasa (L-L) ~400 V; fasa-netral (L-N) = L-L / sqrt(3) ~231 V.
    voltage = 400 + (random.random() - 0.5) * 4
    voltage_ln = voltage / SQRT3
    current = apparent * 1000 / (SQRT3 * voltage) if voltage else 0.0
    # Titik awal tetap agar counter kWh selalu naik (monoton) seperti meter asli.
    elapsed_days = (now - ENERGY_EPOCH).total_seconds() / 86400
    energy = spec["energy"] + spec["power"] * 0.59 * elapsed_days

    decoded = {
        "voltage_l1": round(voltage_ln + 0.2, 3),
        "voltage_l2": round(voltage_ln - 0.1, 3),
        "voltage_l3": round(voltage_ln, 3),
        "voltage_l12": voltage + 0.4,
        "voltage_l23": voltage - 0.2,
        "voltage_l31": voltage,
        "current_l1": current * 0.34,
        "current_l2": current * 0.33,
        "current_l3": current * 0.33,
        "power": round(power, 3),
        "apparent_power": round(apparent, 3),
        "reactive_power": round(reactive, 3),
        "frequency": round(50 + (random.random() - 0.5) * 0.06, 3),
        "energy_active": round(energy, 3),
        "energy_reactive": round(energy * 0.4, 3),
    }
    if capabilities.get("thdCurrent") and "thd_i" in spec:
        decoded["thd_current_l1"] = spec["thd_i"]
        decoded["thd_current_l2"] = spec["thd_i"] - 0.2
        decoded["thd_current_l3"] = spec["thd_i"] + 0.1
    if capabilities.get("thdVoltage") and "thd_u" in spec:
        decoded["thd_voltage_l1"] = spec["thd_u"]
        decoded["thd_voltage_l2"] = spec["thd_u"]
        decoded["thd_voltage_l3"] = spec["thd_u"]
    if capabilities.get("unbalance"):
        decoded["unbalance_voltage"] = spec.get("u_unb", 0.5)
        decoded["unbalance_current"] = spec.get("i_unb", 1.5)

    # Kirim hanya register tegangan yang memang dimiliki model meter
    # (PAC3220 hanya L-L, model lain hanya L-N) agar perilakunya sama dengan
    # meter fisik.
    register_keys = _model_register_keys(model or DEVICE_MODEL.get(device_code))
    if register_keys is not None:
        for key in VOLTAGE_KEYS:
            if key not in register_keys:
                decoded.pop(key, None)
    return decoded


def simulate_telemetry(
    device_code: str,
    capabilities: dict,
    model: str | None = None,
) -> dict | None:
    decoded = simulate_decoded(device_code, capabilities, model)
    if decoded is None:
        return None
    return to_telemetry(device_code, decoded, capabilities)
