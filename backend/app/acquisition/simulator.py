from __future__ import annotations

import math
import random
from datetime import datetime, timezone

from app.acquisition.normalize import to_telemetry

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


def simulate_decoded(device_code: str, capabilities: dict) -> dict[str, float] | None:
    spec = NOMINAL.get(device_code)
    if spec is None or spec.get("offline"):
        return None

    now = datetime.now(timezone.utc)
    jitter = 0.97 + random.random() * 0.06
    power = spec["power"] * _load_factor(now.hour) * jitter
    pf = spec["pf"]
    apparent = power / pf if pf else power
    reactive = power * math.tan(math.acos(min(max(pf, 0.01), 0.999))) if 0 < pf < 1 else 0.0
    voltage = 400 + (random.random() - 0.5) * 4
    current = apparent * 1000 / (math.sqrt(3) * voltage) if voltage else 0.0
    energy = spec["energy"] + power * (now.hour + now.minute / 60) / 24

    decoded = {
        "voltage_l1": voltage + 0.4,
        "voltage_l2": voltage - 0.2,
        "voltage_l3": voltage,
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
    return decoded


def simulate_telemetry(device_code: str, capabilities: dict) -> dict | None:
    decoded = simulate_decoded(device_code, capabilities)
    if decoded is None:
        return None
    return to_telemetry(device_code, decoded, capabilities)
