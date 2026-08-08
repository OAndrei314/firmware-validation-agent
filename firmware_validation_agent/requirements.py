from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class RegisterSpec:
    name: str
    address: int
    access: str
    reset: float | int | bool
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True)
class Requirement:
    id: str
    text: str
    scenario: str
    expected: dict[str, Any]


@dataclass(frozen=True)
class HardwareSpec:
    module_name: str
    registers: dict[str, RegisterSpec]
    requirements: list[Requirement]


def _parse_address(value: Any) -> int:
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        return int(value, 0)
    raise TypeError(f"invalid register address: {value!r}")


def load_hardware_spec(path: str | Path) -> HardwareSpec:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    registers = {
        item["name"]: RegisterSpec(
            name=item["name"],
            address=_parse_address(item["address"]),
            access=item.get("access", "rw"),
            reset=item["reset"],
            minimum=item.get("min"),
            maximum=item.get("max"),
        )
        for item in raw["registers"]
    }
    requirements = [
        Requirement(
            id=item["id"],
            text=item["text"],
            scenario=item["scenario"],
            expected=dict(item.get("expected", {})),
        )
        for item in raw["requirements"]
    ]
    return HardwareSpec(
        module_name=raw["module"]["name"],
        registers=registers,
        requirements=requirements,
    )
