from __future__ import annotations

import json
import os
import ssl
import urllib.request
from dataclasses import dataclass
from typing import Iterable, Protocol

from .requirements import HardwareSpec, Requirement


@dataclass(frozen=True)
class ValidationScenario:
    id: str
    requirement_id: str
    kind: str
    expected: dict[str, object]
    description: str


class Planner(Protocol):
    def plan(self, spec: HardwareSpec) -> list[ValidationScenario]:
        ...


class MockPlanner:
    """Deterministic planner used by tests and CI."""

    def plan(self, spec: HardwareSpec) -> list[ValidationScenario]:
        return [_scenario_from_requirement(req) for req in spec.requirements]


class OpenAICompatiblePlanner:
    def __init__(
        self,
        base_url: str,
        model: str,
        api_key_env: str = "OPENAI_API_KEY",
        timeout_s: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key_env = api_key_env
        self.timeout_s = timeout_s

    def plan(self, spec: HardwareSpec) -> list[ValidationScenario]:
        api_key = os.environ.get(self.api_key_env)
        if not api_key:
            raise RuntimeError(f"missing API key env var: {self.api_key_env}")
        prompt = _planner_prompt(spec.requirements)
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        context = ssl.create_default_context()
        with urllib.request.urlopen(req, timeout=self.timeout_s, context=context) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        content = body["choices"][0]["message"]["content"]
        raw_scenarios = json.loads(content)
        return [ValidationScenario(**item) for item in raw_scenarios]


def _scenario_from_requirement(req: Requirement) -> ValidationScenario:
    return ValidationScenario(
        id=f"scenario-{req.id.lower()}",
        requirement_id=req.id,
        kind=req.scenario,
        expected=req.expected,
        description=req.text,
    )


def _planner_prompt(requirements: Iterable[Requirement]) -> str:
    rows = [
        {
            "id": req.id,
            "text": req.text,
            "scenario": req.scenario,
            "expected": req.expected,
        }
        for req in requirements
    ]
    return (
        "Return JSON only: a list of validation scenarios with keys id, "
        "requirement_id, kind, expected, description. Requirements:\n"
        f"{json.dumps(rows, indent=2)}"
    )
