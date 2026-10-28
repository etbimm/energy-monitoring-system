from __future__ import annotations

import inspect
import logging

from pymodbus.client import AsyncModbusTcpClient
from pymodbus.exceptions import ModbusException

from app.acquisition.decoder import merge_decode
from app.acquisition.normalize import to_telemetry
from app.acquisition.profiles import MeterProfile, register_blocks

log = logging.getLogger("ems.modbus")


def _unit_kwargs(method, unit_id: int) -> dict:
    params = inspect.signature(method).parameters
    if "device_id" in params:
        return {"device_id": unit_id}
    return {"slave": unit_id}


async def read_block(client: AsyncModbusTcpClient, profile: MeterProfile, unit_id: int, address: int, count: int) -> list[int]:
    if profile.function_code == "FC04":
        method = client.read_input_registers
    else:
        method = client.read_holding_registers
    response = await method(address, count=count, **_unit_kwargs(method, unit_id))
    if response.isError():
        raise ModbusException(str(response))
    return list(response.registers)


async def poll_device(
    host: str,
    port: int,
    unit_id: int,
    profile: MeterProfile,
    device_code: str,
    capabilities: dict,
    timeout: float = 2.0,
) -> dict:
    client = AsyncModbusTcpClient(host=host, port=port, timeout=timeout)
    try:
        connected = await client.connect()
        if not connected:
            raise ConnectionError(f"Tidak bisa konek Modbus TCP {host}:{port}")

        blocks: list[tuple[int, list[int]]] = []
        for address, count in register_blocks(profile):
            words = await read_block(client, profile, unit_id, address, count)
            blocks.append((address, words))
        decoded = merge_decode(profile, blocks)
        return to_telemetry(device_code, decoded, capabilities)
    finally:
        client.close()
