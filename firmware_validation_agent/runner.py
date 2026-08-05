from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .planner import Planner, ValidationScenario
from .requirements import HardwareSpec
from .simulator import OpticalModuleSimulator, RegisterAccessError


@dataclass(frozen=True)
class ValidationResult:
    scenario_id: str
    requirement_id: str
    passed: bool
    detected_fault: str | None
    details: str
    measurements: dict[str, object]


class ValidationRunner:
    def __init__(self, spec: HardwareSpec, planner: Planner) -> None:
        self.spec = spec
        self.planner = planner

    def run(self) -> list[ValidationResult]:
        return [run_scenario(self.spec, scenario) for scenario in self.planner.plan(self.spec)]


def run_scenario(spec: HardwareSpec, scenario: ValidationScenario) -> ValidationResult:
    handlers: dict[str, Callable[[OpticalModuleSimulator, dict[str, object]], tuple[bool, str, dict[str, object], str | None]]] = {
        "power_on_bringup": _power_on_bringup,
        "threshold_alarm": _threshold_alarm,
        "telemetry_dropout": _telemetry_dropout,
        "calibration_convergence": _calibration_convergence,
        "rate_limit": _rate_limit,
        "invalid_register_access": _invalid_register_access,
        "signal_verification": _signal_verification,
    }
    sim = OpticalModuleSimulator(spec)
    if scenario.kind not in handlers:
        return ValidationResult(
            scenario.id,
            scenario.requirement_id,
            False,
            None,
            f"unknown scenario kind: {scenario.kind}",
            {},
        )
    passed, details, measurements, detected_fault = handlers[scenario.kind](sim, scenario.expected)
    return ValidationResult(
        scenario.id,
        scenario.requirement_id,
        passed,
        detected_fault,
        details,
        measurements,
    )


def _power_on_bringup(sim: OpticalModuleSimulator, expected: dict[str, object]):
    sim.power_on()
    telemetry = sim.telemetry()
    target_state = expected.get("module_state", "ready")
    passed = sim.read("module_state") == target_state and telemetry["valid"] is True
    return passed, f"module_state={sim.read('module_state')}", telemetry, None


def _threshold_alarm(sim: OpticalModuleSimulator, expected: dict[str, object]):
    sim.power_on()
    sim.write("module_temp_c", float(expected.get("temp_c", 80.0)))
    alarm = sim.read("alarm")
    expected_alarm = str(expected.get("alarm", "over_temperature"))
    passed = expected_alarm in alarm
    return passed, f"alarm={alarm}", {"alarm": alarm}, expected_alarm if passed else None


def _telemetry_dropout(sim: OpticalModuleSimulator, expected: dict[str, object]):
    sim.power_on()
    sim.inject_fault("telemetry_dropout")
    telemetry = sim.telemetry()
    passed = telemetry["valid"] is bool(expected.get("valid", False))
    return passed, f"telemetry_valid={telemetry['valid']}", telemetry, "telemetry_dropout" if passed else None


def _calibration_convergence(sim: OpticalModuleSimulator, expected: dict[str, object]):
    sim.power_on()
    history = sim.calibrate(steps=int(expected.get("steps", 5)))
    limit = float(expected.get("control_error_lte", 0.05))
    passed = history[-1] <= limit and sim.read("calibrated") is True
    return passed, f"final_error={history[-1]:.4f}", {"history": history}, None


def _rate_limit(sim: OpticalModuleSimulator, expected: dict[str, object]):
    sim.power_on()
    attempts = int(expected.get("writes", 10))
    failures = 0
    for value in range(attempts):
        try:
            sim.write("laser_bias_ma", 40.0 + value)
        except RegisterAccessError:
            failures += 1
    passed = failures >= 1 and "rate_limit" in sim.read("alarm")
    return passed, f"failures={failures}", {"failures": failures, "alarm": sim.read("alarm")}, "rate_limit" if passed else None


def _invalid_register_access(sim: OpticalModuleSimulator, expected: dict[str, object]):
    sim.power_on()
    register = str(expected.get("register", "unknown_register"))
    try:
        sim.read(register)
    except RegisterAccessError as exc:
        return True, str(exc), {"register": register}, "invalid_register"
    return False, "invalid access did not raise", {"register": register}, None


def _signal_verification(sim: OpticalModuleSimulator, expected: dict[str, object]):
    sim.power_on()
    power_min = float(expected.get("optical_power_min_dbm", -4.0))
    power_max = float(expected.get("optical_power_max_dbm", 0.0))
    telemetry = sim.telemetry()
    power = float(telemetry["optical_power_dbm"])
    passed = power_min <= power <= power_max
    return passed, f"optical_power_dbm={power:.2f}", telemetry, None
