from app.acquisition.decoder import decode, decode_by_key, read_float32_le, read_int32_le, read_uint32_le
from app.acquisition.normalize import to_telemetry
from app.acquisition.profiles import DEVICE_MODEL, PROFILES, register_blocks


def test_read_float32_le():
    assert read_float32_le([0x0000, 0x42ED]) == 118.5


def test_read_uint32_le():
    assert read_uint32_le([1234, 0]) == 1234
    assert read_uint32_le([0, 1]) == 65536


def test_read_int32_le():
    assert read_int32_le([0xFFFF, 0xFFFF]) == -1
    assert read_int32_le([100, 0]) == 100


def test_elite440_sparse_registers():
    words = [0] * 102
    words[147 - 99] = 0x42ED
    words[147 - 99 + 1] = 0x0000
    words[199 - 99] = 0x449A
    words[199 - 99 + 1] = 0x4000
    decoded = decode(PROFILES["CEWE Elite440"], words)
    assert decoded["P total"]["value"] == 118.5
    assert decoded["P total"]["unit"] == "kW"
    assert decoded["Active energy import"]["value"] == 1234


def test_elite440_skips_unread_registers():
    words = [0] * 50
    decoded = decode(PROFILES["CEWE Elite440"], words)
    assert "P total" in decoded
    assert "Active energy import" not in decoded


def test_amc96_scaled_integers():
    expanded = [0] * 26
    expanded[:3] = [4000, 3990, 3980]
    expanded[6:9] = [1824, 1131, 804]
    expanded[12] = 1186
    expanded[20] = 940
    expanded[25] = 5000
    decoded = decode(PROFILES["ACREL AMC96"], expanded, base_addr=0x0100)
    assert decoded["U L1-N"]["value"] == 400
    assert decoded["I L1"]["value"] == 1.824
    assert decoded["P total"]["value"] == 1.186
    assert decoded["PF total"]["value"] == 0.94
    assert decoded["Frekuensi"]["value"] == 50


def test_dmg510_int32_and_pf():
    profile = PROFILES["LOVATO DMG510"]
    base = 3000
    words = [0] * 200
    words[3006 - base] = 1186
    words[3012 - base] = 940
    decoded = decode(profile, words, base)
    assert decoded["P aktif"]["value"] == 11.86
    assert decoded["PF"]["value"] == 0.94


def test_em220_float32_scale_and_word_order():
    words = [0] * 54
    words[52] = 0x46CF
    words[53] = 0x0800
    decoded = decode(PROFILES["WEIDMULLER EM220"], words)
    assert decoded["P total"]["value"] == 26.5


def test_em220_thd_i_big_endian_registers():
    words = [0x3F80, 0x0000, 0x4000, 0x0000, 0x4040, 0x0000]
    decoded = decode(PROFILES["WEIDMULLER EM220"], words, base_addr=0x00F0)
    assert decoded["THD I L1"]["value"] == 1
    assert decoded["THD I L2"]["value"] == 2
    assert decoded["THD I L3"]["value"] == 3


def test_registry_integrity():
    assert len(PROFILES) == 5
    assert len(DEVICE_MODEL) == 18
    for model in DEVICE_MODEL.values():
        assert model in PROFILES
    with_kvah = [p for p in PROFILES.values() if "kVAh" in p.available]
    assert {profile.model for profile in with_kvah} == {
        "SIEMENS PAC3220",
        "LOVATO DMG510",
        "WEIDMULLER EM220",
    }
    with_thd = [p for p in PROFILES.values() if "THD-i" in p.available]
    assert len(with_thd) == len(PROFILES)
    assert "THD-u" in PROFILES["WEIDMULLER EM220"].available
    assert PROFILES["WEIDMULLER EM220"].function_code == "FC04"
    assert PROFILES["WEIDMULLER EM220"].word_order == "big"
    assert {
        reg.word_order or PROFILES["WEIDMULLER EM220"].word_order
        for reg in PROFILES["WEIDMULLER EM220"].registers
        if reg.key.startswith("thd_current_")
    } == {"big"}


def test_pac3220_native_kvah_and_demand_registers_are_documented_but_not_polled():
    profile = PROFILES["SIEMENS PAC3220"]
    registers = {register.key: register for register in profile.registers}

    assert {"kVAh", "demand"} <= set(profile.available)
    assert not {"kVAh", "demand"} & set(profile.unavailable)
    assert registers["energy_apparent_t1"].addr == 2817
    assert registers["energy_apparent_t1"].unit == "VAh"
    assert registers["energy_apparent_t2"].addr == 2819
    assert registers["demand_active_import"].addr == 501
    assert registers["demand_active_max"].addr == 509
    assert all(
        not registers[key].poll
        for key in (
            "energy_apparent_t1",
            "energy_apparent_t2",
            "demand_active_import",
            "demand_active_max",
        )
    )


def test_dmg510_native_kvah_and_unbalance_capabilities():
    profile = PROFILES["LOVATO DMG510"]
    registers = {register.key: register for register in profile.registers}
    apparent_energy = registers["energy_apparent_register"]

    assert {"kVAh", "unbalance"} <= set(profile.available)
    assert not {"kVAh", "unbalance"} & set(profile.unavailable)
    assert (apparent_energy.addr, apparent_energy.count) == (0x1A28, 2)
    assert (apparent_energy.type, apparent_energy.scale, apparent_energy.poll) == (
        "uint32",
        100,
        False,
    )
    assert not any(register.key.startswith("unbalance_") for register in profile.registers)


def test_amc96_unbalance_registers_are_scaled_and_normalized():
    profile = PROFILES["ACREL AMC96"]
    decoded = decode_by_key(profile, [20, 37], base_addr=0x0700)

    assert decoded["unbalance_voltage"] == 2
    assert decoded["unbalance_current"] == 3.7
    assert {"unbalance", "demand"} <= set(profile.available)
    assert not {"unbalance", "demand"} & set(profile.unavailable)
    assert not any(register.key == "demand" for register in profile.registers)

    telemetry = to_telemetry("AMC96", decoded, {"unbalance": True})
    assert telemetry["unbalance_voltage"] == 2
    assert telemetry["unbalance_current"] == 3.7


def test_register_layout():
    wide = {"uint32", "int32", "float32"}
    for profile in PROFILES.values():
        addrs = [reg.addr for reg in profile.registers]
        assert len(set(addrs)) == len(addrs)
        sorted_regs = sorted(profile.registers, key=lambda item: item.addr)
        for prev, current in zip(sorted_regs, sorted_regs[1:]):
            assert prev.addr + prev.count <= current.addr
        for reg in profile.registers:
            assert reg.scale > 0
            need = 2 if reg.type in wide else 1
            assert reg.count == need
            if "energy" in reg.label.lower():
                assert reg.count == 2
                assert reg.type in {"uint32", "int32", "float32"}


def test_register_blocks_split_gaps():
    blocks = register_blocks(PROFILES["CEWE Elite440"], max_gap=4)
    addresses = [start for start, _ in blocks]
    assert 99 in addresses
    assert 199 in addresses


def test_capabilities_follow_profile_registers():
    from app.acquisition.profiles import register_capabilities

    assert register_capabilities("WEIDMULLER EM220") == {"thdCurrent": True, "thdVoltage": True}
    assert register_capabilities("SIEMENS PAC3220") == {"thdCurrent": True, "thdVoltage": True}
    assert register_capabilities("MODEL TIDAK DIKENAL") == {}
