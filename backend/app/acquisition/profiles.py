from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

RegisterType = Literal["uint16", "int16", "uint32", "int32", "float32"]
FunctionCode = Literal["FC03", "FC04"]


@dataclass(frozen=True)
class RegisterDef:
    addr: int
    count: int
    label: str
    key: str
    unit: str
    type: RegisterType
    scale: float
    poll: bool = True
    note: str = ""
    word_order: Literal["little", "big"] | None = None


@dataclass(frozen=True)
class MeterProfile:
    model: str
    brand: str
    default_slave_id: int
    default_baud: int
    function_code: FunctionCode
    registers: tuple[RegisterDef, ...]
    available: tuple[str, ...]
    unavailable: tuple[str, ...] = ()
    notes: str = ""
    word_order: Literal["little", "big"] = "little"


PAC3220 = MeterProfile(
    model="SIEMENS PAC3220",
    brand="Siemens SENTRON 7KM",
    default_slave_id=1,
    default_baud=19200,
    function_code="FC04",
    notes=(
        "Nilai float IEEE754 little-endian. Register kVAh native ada di model ini saja. "
        "Pakai expansion module bila butuh RS485; secara bawaan PAC3220 memakai Ethernet."
    ),
    available=("V", "I", "kW", "kVA", "kVAR", "kWh", "kVAh", "kVARh", "THD-i", "THD-u", "unbalance", "PF", "Hz", "demand"),
    unavailable=(),
    registers=(
        RegisterDef(800, 1, "U L1-L2", "voltage_l12", "V", "uint16", 10),
        RegisterDef(801, 1, "U L2-L3", "voltage_l23", "V", "uint16", 10),
        RegisterDef(802, 1, "U L3-L1", "voltage_l31", "V", "uint16", 10),
        RegisterDef(805, 1, "I L1", "current_l1", "A", "uint16", 100),
        RegisterDef(806, 1, "I L2", "current_l2", "A", "uint16", 100),
        RegisterDef(807, 1, "I L3", "current_l3", "A", "uint16", 100),
        RegisterDef(850, 2, "P total", "power", "kW", "float32", 1),
        RegisterDef(852, 2, "Q total", "reactive_power", "kVAR", "float32", 1),
        RegisterDef(854, 2, "S total", "apparent_power", "kVA", "float32", 1),
        RegisterDef(856, 2, "PF total", "pf_register", "-", "float32", 1, poll=False, note="dihitung backend"),
        RegisterDef(860, 2, "Frekuensi", "frequency", "Hz", "float32", 1),
        RegisterDef(870, 2, "THD I L1", "thd_current_l1", "%", "float32", 1),
        RegisterDef(872, 2, "THD I L2", "thd_current_l2", "%", "float32", 1),
        RegisterDef(874, 2, "THD I L3", "thd_current_l3", "%", "float32", 1),
        RegisterDef(876, 2, "THD U L1", "thd_voltage_l1", "%", "float32", 1),
        RegisterDef(878, 2, "THD U L2", "thd_voltage_l2", "%", "float32", 1),
        RegisterDef(880, 2, "THD U L3", "thd_voltage_l3", "%", "float32", 1),
        RegisterDef(884, 2, "Unbalance U", "unbalance_voltage", "%", "float32", 1),
        RegisterDef(886, 2, "Unbalance I", "unbalance_current", "%", "float32", 1),
        RegisterDef(900, 2, "Active energy import T1", "energy_active", "kWh", "uint32", 100),
        RegisterDef(902, 2, "Reactive energy import T1", "energy_reactive", "kVARh", "uint32", 100),
        RegisterDef(904, 2, "Apparent energy T1", "energy_apparent_register", "kVAh", "uint32", 100, poll=False),
    ),
)

DMG510 = MeterProfile(
    model="LOVATO DMG510",
    brand="Lovato Electric",
    default_slave_id=1,
    default_baud=9600,
    function_code="FC03",
    notes="THD hanya aktif bila P02.12 disetel ke THD+HAR. TIDAK punya register kVAh.",
    available=("V", "I", "kW", "kVA", "kVAR", "kWh", "kVARh", "THD-i", "THD-u", "PF", "Hz", "demand"),
    unavailable=("kVAh", "unbalance"),
    registers=(
        RegisterDef(3000, 1, "V L1", "voltage_l1", "V", "uint16", 10),
        RegisterDef(3001, 1, "V L2", "voltage_l2", "V", "uint16", 10),
        RegisterDef(3002, 1, "V L3", "voltage_l3", "V", "uint16", 10),
        RegisterDef(3003, 1, "I L1", "current_l1", "A", "uint16", 100),
        RegisterDef(3004, 1, "I L2", "current_l2", "A", "uint16", 100),
        RegisterDef(3005, 1, "I L3", "current_l3", "A", "uint16", 100),
        RegisterDef(3006, 2, "P aktif", "power", "kW", "int32", 100),
        RegisterDef(3008, 2, "Q reaktif", "reactive_power", "kVAR", "int32", 100),
        RegisterDef(3010, 2, "S semu", "apparent_power", "kVA", "int32", 100),
        RegisterDef(3012, 1, "PF", "pf_register", "-", "int16", 1000, poll=False),
        RegisterDef(3013, 1, "Frekuensi", "frequency", "Hz", "uint16", 10),
        RegisterDef(3100, 1, "THD I L1", "thd_current_l1", "%", "uint16", 10, note="butuh P02.12 = THD+HAR"),
        RegisterDef(3101, 1, "THD U L1", "thd_voltage_l1", "%", "uint16", 10),
        RegisterDef(3200, 2, "Active energy import", "energy_active", "kWh", "uint32", 100),
        RegisterDef(3202, 2, "Reactive energy import", "energy_reactive", "kVARh", "uint32", 100),
    ),
)

ELITE440 = MeterProfile(
    model="CEWE Elite440",
    brand="CEWE Instrument",
    default_slave_id=1,
    default_baud=9600,
    function_code="FC03",
    notes="Nilai float IEEE754. Meter multi-line: register dipetakan per baris via konfigurasi.",
    available=("V", "I", "kW", "kVA", "kVAR", "kWh", "kVARh", "THD-i", "THD-u", "PF", "Hz", "demand"),
    unavailable=("kVAh", "unbalance"),
    registers=(
        RegisterDef(0, 2, "U L1", "voltage_l1", "V", "float32", 1),
        RegisterDef(2, 2, "U L2", "voltage_l2", "V", "float32", 1),
        RegisterDef(4, 2, "U L3", "voltage_l3", "V", "float32", 1),
        RegisterDef(6, 2, "I L1", "current_l1", "A", "float32", 1),
        RegisterDef(8, 2, "I L2", "current_l2", "A", "float32", 1),
        RegisterDef(10, 2, "I L3", "current_l3", "A", "float32", 1),
        RegisterDef(12, 2, "P aktif", "power", "kW", "float32", 1),
        RegisterDef(14, 2, "Q reaktif", "reactive_power", "kVAR", "float32", 1),
        RegisterDef(16, 2, "S semu", "apparent_power", "kVA", "float32", 1),
        RegisterDef(18, 2, "PF", "pf_register", "-", "float32", 1, poll=False),
        RegisterDef(20, 2, "Frekuensi", "frequency", "Hz", "float32", 1),
        RegisterDef(22, 2, "THD I L1", "thd_current_l1", "%", "float32", 1),
        RegisterDef(24, 2, "THD U L1", "thd_voltage_l1", "%", "float32", 1),
        RegisterDef(26, 2, "THD P L1", "thd_power_l1", "%", "float32", 1, poll=False),
        RegisterDef(40, 2, "Active energy import", "energy_active", "kWh", "uint32", 1),
        RegisterDef(42, 2, "Reactive energy import", "energy_reactive", "kVARh", "uint32", 1),
    ),
)

AMC96 = MeterProfile(
    model="ACREL AMC96",
    brand="Acrel",
    default_slave_id=1,
    default_baud=9600,
    function_code="FC03",
    notes="THD arus dan tegangan tersedia pada unit meter.",
    available=("V", "I", "kW", "kVA", "kVAR", "kWh", "kVARh", "THD-i", "THD-u", "PF", "Hz"),
    unavailable=("kVAh", "unbalance", "demand"),
    registers=(
        RegisterDef(0, 1, "U L1", "voltage_l1", "V", "uint16", 10),
        RegisterDef(1, 1, "U L2", "voltage_l2", "V", "uint16", 10),
        RegisterDef(2, 1, "U L3", "voltage_l3", "V", "uint16", 10),
        RegisterDef(3, 1, "I L1", "current_l1", "A", "uint16", 100),
        RegisterDef(4, 1, "I L2", "current_l2", "A", "uint16", 100),
        RegisterDef(5, 1, "I L3", "current_l3", "A", "uint16", 100),
        RegisterDef(6, 1, "P aktif", "power", "kW", "uint16", 10),
        RegisterDef(7, 1, "Q reaktif", "reactive_power", "kVAR", "uint16", 10),
        RegisterDef(8, 1, "S semu", "apparent_power", "kVA", "uint16", 10),
        RegisterDef(9, 1, "PF", "pf_register", "-", "uint16", 100, poll=False),
        RegisterDef(10, 1, "Frekuensi", "frequency", "Hz", "uint16", 10),
        RegisterDef(11, 1, "THD I L1", "thd_current_l1", "%", "uint16", 10),
        RegisterDef(12, 1, "THD U L1", "thd_voltage_l1", "%", "uint16", 10),
        RegisterDef(30, 2, "Active energy import", "energy_active", "kWh", "uint32", 100),
        RegisterDef(32, 2, "Reactive energy import", "energy_reactive", "kVARh", "uint32", 100),
    ),
)

EM220 = MeterProfile(
    model="WEIDMULLER EM220",
    brand="Weidmuller",
    default_slave_id=1,
    default_baud=9600,
    function_code="FC04",
    notes="THD-I fase A/B/C float32 ABCD di register 0x00F0/0x00F2/0x00F4. THD-U tidak tersedia. Update internal tiap 1 detik.",
    available=("V", "I", "kW", "kVA", "kVAR", "kWh", "kVARh", "THD-i", "PF", "Hz", "demand"),
    unavailable=("kVAh", "THD-u", "unbalance"),
    registers=(
        RegisterDef(0, 1, "U L1", "voltage_l1", "V", "uint16", 10),
        RegisterDef(1, 1, "U L2", "voltage_l2", "V", "uint16", 10),
        RegisterDef(2, 1, "U L3", "voltage_l3", "V", "uint16", 10),
        RegisterDef(3, 1, "I L1", "current_l1", "A", "uint16", 100),
        RegisterDef(4, 1, "I L2", "current_l2", "A", "uint16", 100),
        RegisterDef(5, 1, "I L3", "current_l3", "A", "uint16", 100),
        RegisterDef(6, 2, "P aktif", "power", "kW", "uint32", 1000),
        RegisterDef(8, 2, "Q reaktif", "reactive_power", "kVAR", "int32", 1000),
        RegisterDef(10, 2, "S semu", "apparent_power", "kVA", "uint32", 1000),
        RegisterDef(12, 1, "PF", "pf_register", "-", "int16", 1000, poll=False),
        RegisterDef(13, 1, "Frekuensi", "frequency", "Hz", "uint16", 100),
        RegisterDef(20, 2, "Active energy import", "energy_active", "kWh", "uint32", 100),
        RegisterDef(22, 2, "Reactive energy import", "energy_reactive", "kVARh", "uint32", 100),
        RegisterDef(24, 2, "Active energy export", "energy_active_export", "kWh", "uint32", 100, poll=False),
        RegisterDef(26, 2, "Reactive energy export", "energy_reactive_export", "kVARh", "uint32", 100, poll=False),
        RegisterDef(0x00F0, 2, "THD I L1", "thd_current_l1", "%", "float32", 1, word_order="big"),
        RegisterDef(0x00F2, 2, "THD I L2", "thd_current_l2", "%", "float32", 1, word_order="big"),
        RegisterDef(0x00F4, 2, "THD I L3", "thd_current_l3", "%", "float32", 1, word_order="big"),
    ),
)

PROFILES: dict[str, MeterProfile] = {
    "SIEMENS PAC3220": PAC3220,
    "LOVATO DMG510": DMG510,
    "CEWE Elite440": ELITE440,
    "ACREL AMC96": AMC96,
    "WEIDMULLER EM220": EM220,
}

DEVICE_MODEL: dict[str, str] = {
    "PM-LVMDP-IN-01": "SIEMENS PAC3220",
    "PM-LVMDP-IN-02": "SIEMENS PAC3220",
    "PM-LVMDP-IN-03": "SIEMENS PAC3220",
    "PM-LVMDP-IN-04": "SIEMENS PAC3220",
    "PM-LVMDP-IN-05": "SIEMENS PAC3220",
    "PM-LVMDP-OUT-01": "LOVATO DMG510",
    "PM-LVMDP-OUT-02": "LOVATO DMG510",
    "PM-LVMDP-OUT-03": "LOVATO DMG510",
    "PM-MVMDP-01": "CEWE Elite440",
    "PM-MCC1-01": "ACREL AMC96",
    "PM-MCC1-02": "ACREL AMC96",
    "PM-MCC2-01": "ACREL AMC96",
    "PM-MCC3-01": "ACREL AMC96",
    "PM-MCC3-02": "ACREL AMC96",
    "PM-MCC4-01": "ACREL AMC96",
    "PM-PEL1-01": "WEIDMULLER EM220",
    "PM-PEL2-01": "WEIDMULLER EM220",
    "PM-PEL3-01": "WEIDMULLER EM220",
}


def get_profile(model: str) -> MeterProfile:
    try:
        return PROFILES[model]
    except KeyError as exc:
        raise KeyError(f"Profil meter tidak dikenal: {model}") from exc


def register_blocks(
    profile: MeterProfile,
    *,
    max_gap: int = 8,
    max_size: int = 120,
    polled_only: bool = True,
) -> list[tuple[int, int]]:
    """Gabungkan register berdekatan menjadi blok baca Modbus."""
    regs = [r for r in profile.registers if (r.poll if polled_only else True)]
    if not regs:
        return []
    regs = sorted(regs, key=lambda r: r.addr)
    blocks: list[tuple[int, int]] = []
    start = regs[0].addr
    end = regs[0].addr + regs[0].count
    for reg in regs[1:]:
        reg_end = reg.addr + reg.count
        if reg.addr <= end + max_gap and (reg_end - start) <= max_size:
            end = max(end, reg_end)
        else:
            blocks.append((start, end - start))
            start = reg.addr
            end = reg_end
    blocks.append((start, end - start))
    return blocks
