from app.acquisition.decoder import decode, read_float32_le, read_int32_le, read_uint32_le
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
    words = [0] * 50
    words[12] = 0x0000
    words[13] = 0x42ED
    words[40] = 1234
    words[41] = 0
    decoded = decode(PROFILES["CEWE Elite440"], words)
    assert decoded["P aktif"]["value"] == 118.5
    assert decoded["P aktif"]["unit"] == "kW"
    assert decoded["Active energy import"]["value"] == 1234


def test_elite440_skips_unread_registers():
    words = [0] * 14
    decoded = decode(PROFILES["CEWE Elite440"], words)
    assert "P aktif" in decoded
    assert "Active energy import" not in decoded


def test_amc96_scaled_integers():
    words = [
        4000, 3990, 3980,
        1824, 1131, 804,
        1186, 430, 1262,
        94,
        500,
    ]
    decoded = decode(PROFILES["ACREL AMC96"], words)
    assert decoded["U L1"]["value"] == 400
    assert decoded["I L1"]["value"] == 18.24
    assert decoded["P aktif"]["value"] == 118.6
    assert decoded["PF"]["value"] == 0.94
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


def test_em220_uint32_scale():
    words = [0] * 30
    words[6] = 26500
    decoded = decode(PROFILES["WEIDMULLER EM220"], words)
    assert decoded["P aktif"]["value"] == 26.5


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
    assert len(with_kvah) == 1
    assert with_kvah[0].model == "SIEMENS PAC3220"
    with_thd = [p for p in PROFILES.values() if "THD-i" in p.available]
    assert len(with_thd) == len(PROFILES)
    assert "THD-u" not in PROFILES["WEIDMULLER EM220"].available
    assert PROFILES["WEIDMULLER EM220"].function_code == "FC04"
    assert PROFILES["WEIDMULLER EM220"].word_order == "little"
    assert {
        reg.word_order
        for reg in PROFILES["WEIDMULLER EM220"].registers
        if reg.key.startswith("thd_current_")
    } == {"big"}


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
                assert reg.type in {"uint32", "int32"}


def test_register_blocks_split_gaps():
    blocks = register_blocks(PROFILES["CEWE Elite440"], max_gap=4)
    addresses = [start for start, _ in blocks]
    assert 0 in addresses
    assert 40 in addresses
