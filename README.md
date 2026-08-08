# firmware-validation-agent

Maintained by: codex-daily-routine

An agentic validation harness for embedded optical-module firmware, built around
synthetic hardware requirements and a deterministic module simulator.

This repo is inspired by optical-module bring-up and validation work, but it uses no
proprietary data, hardware, registers, or product behavior. Everything here is synthetic.

## What It Does

- Parses a small YAML requirement/register-map file.
- Uses a pluggable planning provider to generate validation scenarios.
- Runs scenarios against a deterministic simulated optical module.
- Injects realistic validation faults: telemetry dropouts, calibration drift, invalid
  register access, and control-loop instability.
- Produces a traceable markdown report with pass/fail status, requirement coverage, and
  detected faults.

## Quickstart

```bash
pip install -r requirements.txt

python -m firmware_validation_agent.cli run \
  --requirements examples/optical_module_requirements.yaml \
  --out reports/mock_validation.md
```

Run tests:

```bash
pip install -r requirements-dev.txt
pytest -v
```

## Provider Model

The default `MockPlanner` is deterministic and requires no network or API keys. It maps
requirement IDs to known scenario templates and is what CI uses.

The `OpenAICompatiblePlanner` is intentionally small: it sends the requirement text to a
chat-completions-compatible endpoint and expects JSON scenario definitions. This makes the
repo ready for local vLLM/Ollama/OpenRouter-style experiments without making tests depend
on a model provider.

## Metrics

The CLI report includes:

- Requirement coverage.
- Scenario pass rate.
- Fault detection count.
- Release-gate decision and blockers.
- Failed assertions with measured values.
- Traceability from requirement ID to scenario ID.

## Status

The simulator is deliberately compact. It models register reads/writes, power-on bring-up,
calibration state, telemetry channels, alarms, control-loop stability, rate limiting, and
fault injection. It is not a model of any Nokia or Bell Labs system.

## License

MIT - see [LICENSE](LICENSE).
