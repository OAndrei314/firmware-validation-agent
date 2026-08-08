from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .requirements import HardwareSpec


class RegisterAccessError(ValueError):
    """Raised when a register access violates the synthetic map."""


@dataclass
class OpticalModuleSimulator:
    spec: HardwareSpec
    powered: bool = False
    calibration_age_s: int = 0
    control_error: float = 1.0
    command_budget: int = 8
    faults: set[str] = field(default_factory=set)

    def __post_init__(self) -> None:
        self.registers: dict[str, Any] = {
            name: reg.reset for name, reg in self.spec.registers.items()
        }
        self._sync_status()

    def inject_fault(self, name: str) -> None:
        self.faults.add(name)
        if name == "telemetry_dropout":
            self.registers["telemetry_valid"] = False
        if name == "calibration_drift":
            self.calibration_age_s = 999
            self.control_error = 0.42
        if name == "control_loop_unstable":
            self.control_error = 0.75
        self._sync_status()

    def clear_faults(self) -> None:
        self.faults.clear()
        self.registers["telemetry_valid"] = True
        self.control_error = 0.02
        self.calibration_age_s = 0
        self._sync_status()

    def power_on(self) -> None:
        self.powered = True
        self.registers["module_state"] = "ready"
        self.registers["tx_disable"] = False
        self.registers["optical_power_dbm"] = -2.5
        self.registers["laser_bias_ma"] = 41.0
        self.registers["module_temp_c"] = 47.5
        self.registers["telemetry_valid"] = True
        self.control_error = 0.08
        self.calibration_age_s = 0
        self._sync_status()

    def calibrate(self, steps: int = 4) -> list[float]:
        if not self.powered:
            raise RuntimeError("module must be powered before calibration")
        history: list[float] = []
        for _ in range(steps):
            if "control_loop_unstable" in self.faults:
                self.control_error = min(1.0, self.control_error + 0.11)
            else:
                self.control_error *= 0.45
            self.calibration_age_s = 0
            history.append(round(self.control_error, 4))
        self.registers["calibrated"] = self.control_error <= 0.05
        self._sync_status()
        return history

    def read(self, name: str) -> Any:
        if name not in self.registers:
            raise RegisterAccessError(f"unknown register: {name}")
        return self.registers[name]

    def write(self, name: str, value: Any) -> None:
        spec = self.spec.registers.get(name)
        if spec is None:
            raise RegisterAccessError(f"unknown register: {name}")
        if "w" not in spec.access:
            raise RegisterAccessError(f"register is read-only: {name}")
        if self.command_budget <= 0:
            self.inject_fault("rate_limit")
            raise RegisterAccessError("command rate limit exceeded")
        if spec.minimum is not None and value < spec.minimum:
            raise RegisterAccessError(f"{name} below minimum {spec.minimum}")
        if spec.maximum is not None and value > spec.maximum:
            raise RegisterAccessError(f"{name} above maximum {spec.maximum}")
        self.command_budget -= 1
        self.registers[name] = value
        self._sync_status()

    def telemetry(self) -> dict[str, Any]:
        if not self.powered:
            return {"valid": False, "reason": "module_off"}
        if "telemetry_dropout" in self.faults:
            return {"valid": False, "reason": "dropout"}
        return {
            "valid": bool(self.registers["telemetry_valid"]),
            "module_temp_c": float(self.registers["module_temp_c"]),
            "laser_bias_ma": float(self.registers["laser_bias_ma"]),
            "optical_power_dbm": float(self.registers["optical_power_dbm"]),
            "control_error": round(self.control_error, 4),
            "calibration_age_s": self.calibration_age_s,
            "alarm": self.registers["alarm"],
        }

    def tick(self, seconds: int = 1) -> None:
        if not self.powered:
            return
        self.calibration_age_s += seconds
        if "calibration_drift" in self.faults:
            self.control_error = min(1.0, self.control_error + seconds * 0.002)
            self.registers["optical_power_dbm"] -= seconds * 0.002
        self._sync_status()

    def _sync_status(self) -> None:
        alarms: list[str] = []
        temp = float(self.registers.get("module_temp_c", 0.0))
        power = float(self.registers.get("optical_power_dbm", -99.0))
        if temp > 75.0:
            alarms.append("over_temperature")
        if power < -8.0:
            alarms.append("low_optical_power")
        if self.control_error > 0.3:
            alarms.append("control_loop_error")
        if "rate_limit" in self.faults:
            alarms.append("rate_limit")
        self.registers["alarm"] = ",".join(alarms) if alarms else "none"
