"""Validasi input manajemen device dan akun."""
import pytest
from pydantic import ValidationError

from app.acquisition.profiles import MODEL_CATALOG, PROFILES, default_capabilities
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
        {"model": "MERK LAIN"},
        {"role": "utama"},
        {"transport": "wifi"},
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
