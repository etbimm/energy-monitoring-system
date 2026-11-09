"""Penjadwalan polling: pengelompokan per gateway dan interval tetap."""

from __future__ import annotations

import math
from collections import defaultdict

SIMULATOR_GATEWAY = ("simulator", 0)


def gateway_key(device: dict, simulator: bool) -> tuple[str, int]:
    if simulator:
        return SIMULATOR_GATEWAY
    return (str(device.get("modbus_host") or ""), int(device.get("modbus_port") or 502))


def group_by_gateway(devices: list[dict], simulator: bool = False) -> dict[tuple[str, int], list[dict]]:
    """Kelompokkan meter per gateway (host, port), urutan meter dipertahankan.

    Gateway berbeda dibaca paralel; meter dalam satu gateway (satu jalur
    RS485) dibaca berurutan.
    """
    groups: dict[tuple[str, int], list[dict]] = defaultdict(list)
    for device in devices:
        groups[gateway_key(device, simulator)].append(device)
    return dict(groups)


def next_deadline(previous: float, interval: float, now: float) -> tuple[float, int]:
    """Jadwal interval tetap: deadline berikutnya dan jumlah siklus terlewat.

    Siklus berikutnya dimulai tepat `interval` detik setelah siklus sebelumnya
    dimulai (bukan setelah siklus selesai), sehingga data tidak "molor". Bila
    satu siklus lebih lama dari interval, jadwal melompat ke kelipatan
    berikutnya agar tidak terjadi polling beruntun tanpa jeda.
    """
    deadline = previous + interval
    if now <= deadline:
        return deadline, 0
    skipped = math.ceil((now - deadline) / interval)
    return deadline + skipped * interval, skipped
