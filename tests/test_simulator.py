import pytest

from firmware_validation_agent.requirements import load_hardware_spec
from firmware_validation_agent.simulator import OpticalModuleSimulator, RegisterAccessError


def make_sim():
    return OpticalModuleSimulator(load_hardware_spec("examples/optical_module_requirements.yaml"))


def test_power_on_sets_ready_state_and_valid_telemetry():
    sim = make_sim()
    sim.power_on()

    telemetry = sim.telemetry()

    assert sim.read("module_state") == "ready"
    assert telemetry["valid"] is True
    assert -4.0 <= telemetry["optical_power_dbm"] <= -1.0


def test_calibration_converges_without_fault():
    sim = make_sim()
    sim.power_on()

    history = sim.calibrate(steps=5)

    assert history[-1] <= 0.05
    assert sim.read("calibrated") is True


def test_invalid_register_access_raises():
    sim = make_sim()

    with pytest.raises(RegisterAccessError):
        sim.read("missing_register")
