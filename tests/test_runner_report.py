from firmware_validation_agent.planner import MockPlanner
from firmware_validation_agent.report import release_gate, render_markdown, summarize_results
from firmware_validation_agent.requirements import load_hardware_spec
from firmware_validation_agent.runner import ValidationRunner


def test_mock_planner_runner_covers_all_requirements():
    spec = load_hardware_spec("examples/optical_module_requirements.yaml")

    results = ValidationRunner(spec, MockPlanner()).run()
    summary = summarize_results(spec, results)

    assert all(item.passed for item in results)
    assert summary["coverage"] == 1.0
    assert summary["detected_faults"] >= 3
    assert release_gate(spec, results)["decision"] == "release_candidate"


def test_report_contains_traceability_table():
    spec = load_hardware_spec("examples/optical_module_requirements.yaml")
    results = ValidationRunner(spec, MockPlanner()).run()

    report = render_markdown(spec, results)

    assert "Requirement coverage: 100.0%" in report
    assert "Release gate: release_candidate" in report
    assert "REQ-001" in report
    assert "scenario-req-001" in report


def test_release_gate_blocks_failed_validation():
    spec = load_hardware_spec("examples/optical_module_requirements.yaml")
    results = ValidationRunner(spec, MockPlanner()).run()
    failed = [results[0].__class__(results[0].scenario_id, results[0].requirement_id, False, None, "forced failure", {})]

    gate = release_gate(spec, failed)

    assert gate["decision"] == "hold_for_debug"
    assert "requirement_coverage_gap" in gate["blockers"]
    assert "scenario_failures" in gate["blockers"]
