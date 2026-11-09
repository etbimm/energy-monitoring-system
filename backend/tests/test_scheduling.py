import asyncio
import time

import pytest

import app.acquisition.__main__ as acquisition
from app.acquisition.scheduling import SIMULATOR_GATEWAY, group_by_gateway, next_deadline

DEVICES = [
    {"device_code": "A1", "modbus_host": "10.0.0.1", "modbus_port": 502},
    {"device_code": "B1", "modbus_host": "10.0.0.2", "modbus_port": None},
    {"device_code": "A2", "modbus_host": "10.0.0.1", "modbus_port": 502},
]


def test_group_by_gateway_keeps_order_per_gateway():
    groups = group_by_gateway(DEVICES)
    assert [d["device_code"] for d in groups[("10.0.0.1", 502)]] == ["A1", "A2"]
    assert [d["device_code"] for d in groups[("10.0.0.2", 502)]] == ["B1"]


def test_simulator_uses_single_group():
    assert list(group_by_gateway(DEVICES, simulator=True)) == [SIMULATOR_GATEWAY]


def test_fixed_interval_schedule():
    # Siklus selesai lebih cepat: deadline berikutnya tetap start + interval.
    assert next_deadline(100.0, 5.0, 101.2) == (105.0, 0)
    # Siklus molor 12 detik: lompat ke kelipatan berikutnya, 2 siklus dilewati.
    assert next_deadline(100.0, 5.0, 117.0) == (120.0, 3)


@pytest.mark.asyncio
async def test_gateways_are_polled_in_parallel(monkeypatch):
    order: list[str] = []

    async def fake_poll_one(_mqtt, device, _gateway):
        order.append(device["device_code"])
        await asyncio.sleep(0.2)

    monkeypatch.setattr(acquisition, "poll_one", fake_poll_one)
    poller = acquisition.Poller()
    poller.simulator = False
    poller.devices = DEVICES

    started = time.perf_counter()
    await poller.cycle(mqtt=None)
    elapsed = time.perf_counter() - started
    poller.close()

    # Berurutan total 0.6 s; paralel per gateway ~0.4 s (gateway .1 punya 2 meter).
    assert elapsed < 0.55
    assert order.index("A1") < order.index("A2")
    assert set(poller.gateways) == set()
