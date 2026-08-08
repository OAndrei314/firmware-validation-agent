"""Firmware validation agent for synthetic optical-module bring-up."""

from .requirements import HardwareSpec, load_hardware_spec
from .report import release_gate
from .runner import ValidationResult, ValidationRunner

__all__ = [
    "HardwareSpec",
    "ValidationResult",
    "ValidationRunner",
    "load_hardware_spec",
    "release_gate",
]
