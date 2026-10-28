from app.acquisition.profiles import DEVICE_MODEL
from app.acquisition.simulator import NOMINAL, simulate_telemetry


def test_simulated_online_meters_have_thd_readings():
    capabilities = {"thdCurrent": True, "thdVoltage": True}

    for device_code, model in DEVICE_MODEL.items():
        meter_capabilities = {
            **capabilities,
            "thdVoltage": model != "WEIDMULLER EM220",
        }
        reading = simulate_telemetry(device_code, meter_capabilities)
        if NOMINAL[device_code].get("offline"):
            assert reading is None
            continue

        assert reading is not None
        assert reading["thd_current"] is not None
        if model == "WEIDMULLER EM220":
            assert reading["thd_voltage"] is None
        else:
            assert reading["thd_voltage"] is not None
