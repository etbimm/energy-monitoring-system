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
        "Alamat mengikuti kolom Offset pada manual Siemens (offset awal 1); konvensi offset PDU dan urutan word perlu dikonfirmasi pada meter. "
        "Nilai float IEEE754. Energi double 64-bit ada di manual, tetapi belum dipetakan oleh decoder."
    ),
    available=("V", "I", "kW", "kVA", "kVAR", "THD-i", "THD-u", "unbalance", "PF", "Hz"),
    unavailable=("kWh", "kVAh", "kVARh", "demand"),
    registers=(
        RegisterDef(1, 2, "U L1-N", "voltage_l1", "V", "float32", 1),
        RegisterDef(3, 2, "U L2-N", "voltage_l2", "V", "float32", 1),
        RegisterDef(5, 2, "U L3-N", "voltage_l3", "V", "float32", 1),
        RegisterDef(7, 2, "U L1-L2", "voltage_l12", "V", "float32", 1),
        RegisterDef(9, 2, "U L2-L3", "voltage_l23", "V", "float32", 1),
        RegisterDef(11, 2, "U L3-L1", "voltage_l31", "V", "float32", 1),
        RegisterDef(13, 2, "I L1", "current_l1", "A", "float32", 1),
        RegisterDef(15, 2, "I L2", "current_l2", "A", "float32", 1),
        RegisterDef(17, 2, "I L3", "current_l3", "A", "float32", 1),
        RegisterDef(19, 2, "S L1", "apparent_power_l1", "VA", "float32", 1000),
        RegisterDef(21, 2, "S L2", "apparent_power_l2", "VA", "float32", 1000),
        RegisterDef(23, 2, "S L3", "apparent_power_l3", "VA", "float32", 1000),
        RegisterDef(25, 2, "P L1", "power_l1", "W", "float32", 1000),
        RegisterDef(27, 2, "P L2", "power_l2", "W", "float32", 1000),
        RegisterDef(29, 2, "P L3", "power_l3", "W", "float32", 1000),
        RegisterDef(31, 2, "Q L1", "reactive_power_l1", "var", "float32", 1000),
        RegisterDef(33, 2, "Q L2", "reactive_power_l2", "var", "float32", 1000),
        RegisterDef(35, 2, "Q L3", "reactive_power_l3", "var", "float32", 1000),
        RegisterDef(37, 2, "PF L1", "pf_l1", "-", "float32", 1, poll=False),
        RegisterDef(39, 2, "PF L2", "pf_l2", "-", "float32", 1, poll=False),
        RegisterDef(41, 2, "PF L3", "pf_l3", "-", "float32", 1, poll=False),
        RegisterDef(43, 2, "THD U L1", "thd_voltage_l1", "%", "float32", 1),
        RegisterDef(45, 2, "THD U L2", "thd_voltage_l2", "%", "float32", 1),
        RegisterDef(47, 2, "THD U L3", "thd_voltage_l3", "%", "float32", 1),
        RegisterDef(49, 2, "THD I L1", "thd_current_l1", "%", "float32", 1),
        RegisterDef(51, 2, "THD I L2", "thd_current_l2", "%", "float32", 1),
        RegisterDef(53, 2, "THD I L3", "thd_current_l3", "%", "float32", 1),
        RegisterDef(55, 2, "Frekuensi", "frequency", "Hz", "float32", 1),
        RegisterDef(63, 2, "S total", "apparent_power", "VA", "float32", 1000),
        RegisterDef(65, 2, "P total", "power", "W", "float32", 1000),
        RegisterDef(67, 2, "Q total", "reactive_power", "var", "float32", 1000),
        RegisterDef(69, 2, "PF total", "pf_register", "-", "float32", 1, poll=False),
        RegisterDef(71, 2, "Voltage unbalance", "unbalance_voltage", "%", "float32", 1),
        RegisterDef(73, 2, "Current unbalance", "unbalance_current", "%", "float32", 1),
    ),
    word_order="big",
)

DMG510 = MeterProfile(
    model="LOVATO DMG510",
    brand="Lovato Electric",
    default_slave_id=1,
    default_baud=9600,
    function_code="FC03",
    notes=(
        "UNVERIFIED against supplied documents: the DMG series protocol PDF lists DMG210/300/700/800/900, "
        "not DMG510; the supplied DMG510 datasheet has no register table. Obtain the DMG500/510 Modbus map."
    ),
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
    notes="Alamat 40xxx dikurangi 40001 menjadi offset 0-based; Float32 high-word first.",
    available=("V", "I", "kW", "kVA", "kVAR", "kWh", "kVARh", "THD-i", "THD-u", "PF", "Hz", "demand"),
    unavailable=("kVAh", "unbalance"),
    registers=(
        RegisterDef(99, 2, "U L1", "voltage_l1", "V", "float32", 1),
        RegisterDef(101, 2, "U L2", "voltage_l2", "V", "float32", 1),
        RegisterDef(103, 2, "U L3", "voltage_l3", "V", "float32", 1),
        RegisterDef(107, 2, "U L1-L2", "voltage_l12", "V", "float32", 1),
        RegisterDef(109, 2, "U L2-L3", "voltage_l23", "V", "float32", 1),
        RegisterDef(111, 2, "U L3-L1", "voltage_l31", "V", "float32", 1),
        RegisterDef(113, 2, "I L1", "current_l1", "A", "float32", 1),
        RegisterDef(115, 2, "I L2", "current_l2", "A", "float32", 1),
        RegisterDef(117, 2, "I L3", "current_l3", "A", "float32", 1),
        RegisterDef(139, 2, "PF total", "pf_register", "-", "float32", 1, poll=False),
        RegisterDef(141, 2, "P L1", "power_l1", "kW", "float32", 1),
        RegisterDef(143, 2, "P L2", "power_l2", "kW", "float32", 1),
        RegisterDef(145, 2, "P L3", "power_l3", "kW", "float32", 1),
        RegisterDef(147, 2, "P total", "power", "kW", "float32", 1),
        RegisterDef(149, 2, "Q L1", "reactive_power_l1", "kVAR", "float32", 1),
        RegisterDef(151, 2, "Q L2", "reactive_power_l2", "kVAR", "float32", 1),
        RegisterDef(153, 2, "Q L3", "reactive_power_l3", "kVAR", "float32", 1),
        RegisterDef(155, 2, "Q total", "reactive_power", "kVAR", "float32", 1),
        RegisterDef(157, 2, "S L1", "apparent_power_l1", "kVA", "float32", 1),
        RegisterDef(159, 2, "S L2", "apparent_power_l2", "kVA", "float32", 1),
        RegisterDef(161, 2, "S L3", "apparent_power_l3", "kVA", "float32", 1),
        RegisterDef(163, 2, "S total", "apparent_power", "kVA", "float32", 1),
        RegisterDef(171, 2, "Frekuensi", "frequency", "Hz", "float32", 1),
        RegisterDef(177, 2, "THD U L1", "thd_voltage_l1", "%", "float32", 1),
        RegisterDef(179, 2, "THD U L2", "thd_voltage_l2", "%", "float32", 1),
        RegisterDef(181, 2, "THD U L3", "thd_voltage_l3", "%", "float32", 1),
        RegisterDef(183, 2, "THD I L1", "thd_current_l1", "%", "float32", 1),
        RegisterDef(185, 2, "THD I L2", "thd_current_l2", "%", "float32", 1),
        RegisterDef(187, 2, "THD I L3", "thd_current_l3", "%", "float32", 1),
        RegisterDef(199, 2, "Active energy import", "energy_active", "kWh", "float32", 1),
        RegisterDef(201, 2, "Active energy export", "energy_active_export", "kWh", "float32", 1, poll=False),
        RegisterDef(215, 2, "Apparent energy import", "energy_apparent_register", "kVAh", "float32", 1, poll=False),
        RegisterDef(219, 2, "Reactive energy import", "energy_reactive", "kVARh", "float32", 1),
    ),
    word_order="big",
)

AMC96 = MeterProfile(
    model="ACREL AMC96",
    brand="Acrel",
    default_slave_id=1,
    default_baud=9600,
    function_code="FC03",
    notes=(
        "Menggunakan register sisi sekunder 0x0100-0x0119 pada manual AMC Series generik; kecocokan varian/firmware AMC96 perlu dikonfirmasi. "
        "register harmonik memakai skala 0.01%. Energy kWh bergantung rasio PT/CT."
    ),
    available=("V", "I", "kW", "kVA", "kVAR", "THD-i", "THD-u", "PF", "Hz"),
    unavailable=("kVAh", "unbalance", "demand"),
    registers=(
        RegisterDef(0x0100, 1, "U L1-N", "voltage_l1", "V", "uint16", 10),
        RegisterDef(0x0101, 1, "U L2-N", "voltage_l2", "V", "uint16", 10),
        RegisterDef(0x0102, 1, "U L3-N", "voltage_l3", "V", "uint16", 10),
        RegisterDef(0x0103, 1, "U L1-L2", "voltage_l12", "V", "uint16", 10),
        RegisterDef(0x0104, 1, "U L2-L3", "voltage_l23", "V", "uint16", 10),
        RegisterDef(0x0105, 1, "U L3-L1", "voltage_l31", "V", "uint16", 10),
        RegisterDef(0x0106, 1, "I L1", "current_l1", "A", "uint16", 1000),
        RegisterDef(0x0107, 1, "I L2", "current_l2", "A", "uint16", 1000),
        RegisterDef(0x0108, 1, "I L3", "current_l3", "A", "uint16", 1000),
        RegisterDef(0x0109, 1, "P L1", "power_l1", "kW", "int16", 1000),
        RegisterDef(0x010A, 1, "P L2", "power_l2", "kW", "int16", 1000),
        RegisterDef(0x010B, 1, "P L3", "power_l3", "kW", "int16", 1000),
        RegisterDef(0x010C, 1, "P total", "power", "kW", "int16", 1000),
        RegisterDef(0x010D, 1, "Q L1", "reactive_power_l1", "kVAR", "int16", 1000),
        RegisterDef(0x010E, 1, "Q L2", "reactive_power_l2", "kVAR", "int16", 1000),
        RegisterDef(0x010F, 1, "Q L3", "reactive_power_l3", "kVAR", "int16", 1000),
        RegisterDef(0x0110, 1, "Q total", "reactive_power", "kVAR", "int16", 1000),
        RegisterDef(0x0111, 1, "PF L1", "pf_l1", "-", "int16", 1000, poll=False),
        RegisterDef(0x0112, 1, "PF L2", "pf_l2", "-", "int16", 1000, poll=False),
        RegisterDef(0x0113, 1, "PF L3", "pf_l3", "-", "int16", 1000, poll=False),
        RegisterDef(0x0114, 1, "PF total", "pf_register", "-", "int16", 1000, poll=False),
        RegisterDef(0x0115, 1, "S L1", "apparent_power_l1", "kVA", "uint16", 1000),
        RegisterDef(0x0116, 1, "S L2", "apparent_power_l2", "kVA", "uint16", 1000),
        RegisterDef(0x0117, 1, "S L3", "apparent_power_l3", "kVA", "uint16", 1000),
        RegisterDef(0x0118, 1, "S total", "apparent_power", "kVA", "uint16", 1000),
        RegisterDef(0x0119, 1, "Frekuensi", "frequency", "Hz", "uint16", 100),
        RegisterDef(0x0400, 1, "THD U L1", "thd_voltage_l1", "%", "uint16", 100),
        RegisterDef(0x0401, 1, "THD U L2", "thd_voltage_l2", "%", "uint16", 100),
        RegisterDef(0x0402, 1, "THD U L3", "thd_voltage_l3", "%", "uint16", 100),
        RegisterDef(0x0403, 1, "THD I L1", "thd_current_l1", "%", "uint16", 100),
        RegisterDef(0x0404, 1, "THD I L2", "thd_current_l2", "%", "uint16", 100),
        RegisterDef(0x0405, 1, "THD I L3", "thd_current_l3", "%", "uint16", 100),
    ),
)

EM220 = MeterProfile(
    model="WEIDMULLER EM220",
    brand="Weidmuller",
    default_slave_id=1,
    default_baud=9600,
    function_code="FC04",
    notes="Float32 FC04 ABCD big-endian sesuai contoh respons manual EM220; alamat dari Start Address Hex.",
    available=("V", "I", "kW", "kVA", "kVAR", "kWh", "kVAh", "kVARh", "THD-i", "THD-u", "PF", "Hz", "demand"),
    unavailable=("unbalance",),
    registers=(
        RegisterDef(0, 2, "U L1-N", "voltage_l1", "V", "float32", 1),
        RegisterDef(2, 2, "U L2-N", "voltage_l2", "V", "float32", 1),
        RegisterDef(4, 2, "U L3-N", "voltage_l3", "V", "float32", 1),
        RegisterDef(200, 2, "U L1-L2", "voltage_l12", "V", "float32", 1),
        RegisterDef(202, 2, "U L2-L3", "voltage_l23", "V", "float32", 1),
        RegisterDef(204, 2, "U L3-L1", "voltage_l31", "V", "float32", 1),
        RegisterDef(6, 2, "I L1", "current_l1", "A", "float32", 1),
        RegisterDef(8, 2, "I L2", "current_l2", "A", "float32", 1),
        RegisterDef(10, 2, "I L3", "current_l3", "A", "float32", 1),
        RegisterDef(12, 2, "P L1", "power_l1", "W", "float32", 1000),
        RegisterDef(14, 2, "P L2", "power_l2", "W", "float32", 1000),
        RegisterDef(16, 2, "P L3", "power_l3", "W", "float32", 1000),
        RegisterDef(18, 2, "S L1", "apparent_power_l1", "VA", "float32", 1000),
        RegisterDef(20, 2, "S L2", "apparent_power_l2", "VA", "float32", 1000),
        RegisterDef(22, 2, "S L3", "apparent_power_l3", "VA", "float32", 1000),
        RegisterDef(24, 2, "Q L1", "reactive_power_l1", "var", "float32", 1000),
        RegisterDef(26, 2, "Q L2", "reactive_power_l2", "var", "float32", 1000),
        RegisterDef(28, 2, "Q L3", "reactive_power_l3", "var", "float32", 1000),
        RegisterDef(30, 2, "PF L1", "pf_l1", "-", "float32", 1, poll=False),
        RegisterDef(32, 2, "PF L2", "pf_l2", "-", "float32", 1, poll=False),
        RegisterDef(34, 2, "PF L3", "pf_l3", "-", "float32", 1, poll=False),
        RegisterDef(42, 2, "Average voltage L-N", "voltage_l1", "V", "float32", 1, poll=False),
        RegisterDef(52, 2, "P total", "power", "W", "float32", 1000),
        RegisterDef(56, 2, "S total", "apparent_power", "VA", "float32", 1000),
        RegisterDef(60, 2, "Q total", "reactive_power", "var", "float32", 1000),
        RegisterDef(62, 2, "PF total", "pf_register", "-", "float32", 1, poll=False),
        RegisterDef(70, 2, "Frekuensi", "frequency", "Hz", "float32", 1),
        RegisterDef(72, 2, "Active energy import", "energy_active", "kWh", "float32", 1),
        RegisterDef(74, 2, "Active energy export", "energy_active_export", "kWh", "float32", 1, poll=False),
        RegisterDef(76, 2, "Reactive energy import", "energy_reactive", "kVARh", "float32", 1),
        RegisterDef(78, 2, "Reactive energy export", "energy_reactive_export", "kVARh", "float32", 1, poll=False),
        RegisterDef(80, 2, "Apparent energy", "energy_apparent_register", "kVAh", "float32", 1, poll=False),
        RegisterDef(234, 2, "THD U L1", "thd_voltage_l1", "%", "float32", 1),
        RegisterDef(236, 2, "THD U L2", "thd_voltage_l2", "%", "float32", 1),
        RegisterDef(238, 2, "THD U L3", "thd_voltage_l3", "%", "float32", 1),
        RegisterDef(240, 2, "THD I L1", "thd_current_l1", "%", "float32", 1),
        RegisterDef(242, 2, "THD I L2", "thd_current_l2", "%", "float32", 1),
        RegisterDef(244, 2, "THD I L3", "thd_current_l3", "%", "float32", 1),
    ),
    word_order="big",
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


# Katalog model untuk form "Tambah device": label merek (kolom devices.brand)
# dan kapabilitas default (kolom devices.capabilities). Nilai sama dengan
# seed database/init/02-seed-devices.sql. Kapabilitas THD tetap ditimpa oleh
# register_capabilities() saat ditampilkan.
MODEL_CATALOG: dict[str, dict] = {
    "SIEMENS PAC3220": {
        "label": "SIEMENS PAC3220",
        "capabilities": {
            "perPhase": True, "apparentEnergyRegister": False, "thdCurrent": True,
            "thdVoltage": True, "maxHarmonicOrder": 40, "unbalance": True,
            "reactiveEnergy": False, "demand": False,
        },
    },
    "LOVATO DMG510": {
        "label": "LOVATO DMG510",
        "capabilities": {
            "perPhase": True, "apparentEnergyRegister": False, "thdCurrent": True,
            "thdVoltage": True, "maxHarmonicOrder": 15, "unbalance": False,
            "reactiveEnergy": True, "demand": True,
        },
    },
    "CEWE Elite440": {
        "label": "CEWE Elite440",
        "capabilities": {
            "perPhase": True, "apparentEnergyRegister": False, "thdCurrent": True,
            "thdVoltage": True, "maxHarmonicOrder": 31, "unbalance": False,
            "reactiveEnergy": True, "demand": True,
        },
    },
    "ACREL AMC96": {
        "label": "Acrel AMC96",
        "capabilities": {
            "perPhase": True, "apparentEnergyRegister": False, "thdCurrent": True,
            "thdVoltage": True, "maxHarmonicOrder": 31, "unbalance": False,
            "reactiveEnergy": False, "demand": False,
        },
    },
    "WEIDMULLER EM220": {
        "label": "Weidmuller EM220",
        "capabilities": {
            "perPhase": True, "apparentEnergyRegister": False, "thdCurrent": True,
            "thdVoltage": True, "maxHarmonicOrder": 0, "unbalance": False,
            "reactiveEnergy": True, "demand": True,
        },
    },
}


# Kapabilitas konservatif untuk model "Lainnya" (belum ada profil register):
# hanya besaran dasar; THD/unbalance/harmonik dianggap tidak tersedia sampai
# profilnya ditambahkan di PROFILES.
CUSTOM_MODEL_CAPABILITIES: dict = {
    "perPhase": True, "apparentEnergyRegister": False, "thdCurrent": False,
    "thdVoltage": False, "maxHarmonicOrder": 0, "unbalance": False,
    "reactiveEnergy": True, "demand": False,
}


def is_supported_model(model: str | None) -> bool:
    """True bila model punya profil register (bisa dibaca akuisisi modbus)."""
    return bool(model) and model in PROFILES


def default_capabilities(model: str) -> dict:
    """Kapabilitas awal device baru berdasarkan model (salinan, aman diubah)."""
    entry = MODEL_CATALOG.get(model)
    caps = dict(entry["capabilities"]) if entry else dict(CUSTOM_MODEL_CAPABILITIES)
    return {**caps, **register_capabilities(model)}


def register_capabilities(model: str) -> dict[str, bool]:
    """Kapabilitas THD yang diturunkan dari register profil meter.

    Satu-satunya sumber aturan "model X punya/tidak punya THD": bila register
    THD dipoll di profil, kapabilitasnya True. Model tak dikenal -> {} (tidak
    menimpa kapabilitas dari database).
    """
    profile = PROFILES.get(model)
    if profile is None:
        return {}
    keys = {register.key for register in profile.registers if register.poll}
    return {
        "thdCurrent": any(key.startswith("thd_current") for key in keys),
        "thdVoltage": any(key.startswith("thd_voltage") for key in keys),
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
