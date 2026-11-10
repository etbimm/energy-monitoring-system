"""Validasi input manajemen device dan akun."""
import pytest
from pydantic import ValidationError

from app.acquisition.profiles import (
    CUSTOM_MODEL_CAPABILITIES,
    MODEL_CATALOG,
    PROFILES,
    default_capabilities,
    is_supported_model,
)
from app.schemas import DeviceCreate, DeviceUpdate, UserCreate

BASE = {
    "deviceCode": "PM-MCC5-01",
    "name": "MCC 5 Meter 1",
    "model": "ACREL AMC96",
    "role": "distribution",
    "transport": "rs485",
    "modbusHost": "192.168.10.30",
    "modbusAddress": 1,
}


def make(**overrides):
    return DeviceCreate.model_validate({**BASE, **overrides})


def test_valid_device_is_normalized():
    device = make(deviceCode=" pm-mcc5-01 ", name="  MCC 5  ", location="   ")
    assert device.device_code == "PM-MCC5-01"
    assert device.name == "MCC 5"
    assert device.location is None
    assert device.modbus_port == 502


@pytest.mark.parametrize(
    "overrides",
    [
        {"deviceCode": "MCC5"},
        {"deviceCode": "PM-MCC 5"},
        {"name": "   "},
        {"model": "   "},
        {"model": "X" * 61},
        {"role": "   "},
        {"role": "R" * 41},
        {"transport": ""},
        {"modbusHost": "192.168.10.300"},
        {"modbusHost": "host dengan spasi"},
        {"modbusAddress": 0},
        {"modbusAddress": 248},
        {"modbusPort": 70000},
        {"ratedPowerKw": 0},
    ],
)
def test_invalid_device_rejected(overrides):
    with pytest.raises(ValidationError):
        make(**overrides)


def test_hostname_allowed():
    assert make(modbusHost="gateway-mcc5.local").modbus_host == "gateway-mcc5.local"


def test_update_is_partial_and_cannot_change_code():
    update = DeviceUpdate.model_validate({"name": "Baru", "isActive": False})
    assert update.model_dump(exclude_unset=True) == {"name": "Baru", "is_active": False}
    assert "device_code" not in DeviceUpdate.model_fields


def test_every_profile_has_catalog_entry_and_defaults():
    assert set(MODEL_CATALOG) == set(PROFILES)
    caps = default_capabilities("SIEMENS PAC3220")
    assert caps["perPhase"] and caps["maxHarmonicOrder"] == 40
    # Salinan baru setiap kali: mengubah hasil tidak mengubah katalog.
    caps["perPhase"] = False
    assert MODEL_CATALOG["SIEMENS PAC3220"]["capabilities"]["perPhase"] is True


@pytest.mark.parametrize("username", ["ab", "nama spasi", "a" * 33, "admin!"])
def test_invalid_username_rejected(username):
    with pytest.raises(ValidationError):
        UserCreate.model_validate({"username": username, "fullName": "X", "password": "abcd1234"})


def test_username_lowercased_and_default_viewer():
    user = UserCreate.model_validate({"username": " Budi.S ", "fullName": " Budi ", "password": "abcd1234"})
    assert user.username == "budi.s"
    assert user.full_name == "Budi"
    assert user.role == "viewer"


def test_custom_model_allowed_and_cleaned():
    device = make(model="  Schneider   PM5350 ", brand="  Schneider  Electric ")
    assert device.model == "Schneider PM5350"
    assert device.brand == "Schneider Electric"
    assert not is_supported_model(device.model)


def test_known_model_case_insensitive_is_normalized():
    # Salah ketik huruf besar/kecil tidak boleh membuat meter jadi "tak dikenal".
    assert make(model="acrel  amc96").model == "ACREL AMC96"
    assert is_supported_model("ACREL AMC96")


def test_custom_model_gets_conservative_capabilities():
    caps = default_capabilities("Schneider PM5350")
    assert caps == CUSTOM_MODEL_CAPABILITIES
    assert caps is not CUSTOM_MODEL_CAPABILITIES
    assert caps["thdCurrent"] is False and caps["maxHarmonicOrder"] == 0


@pytest.mark.parametrize(
    ("role", "expected"),
    [("Incoming", "incoming"), (" OUTCOMING ", "outcoming"), ("Distribution", "distribution"),
     ("  Genset   Cadangan ", "Genset Cadangan"), ("Solar PV", "Solar PV")],
)
def test_role_lainnya_and_known_normalized(role, expected):
    assert make(role=role).role == expected


@pytest.mark.parametrize(
    ("transport", "expected"),
    [("RS-485", "rs485"), ("rs 485", "rs485"), ("Ethernet", "ethernet"),
     ("Modbus RTU via USB", "Modbus RTU via USB"), ("Wi-Fi", "Wi-Fi")],
)
def test_transport_lainnya_and_known_normalized(transport, expected):
    assert make(transport=transport).transport == expected


def test_update_role_transport_cleaned():
    update = DeviceUpdate.model_validate({"role": "INCOMING", "transport": " Fiber  optik "})
    assert update.role == "incoming"
    assert update.transport == "Fiber optik"
