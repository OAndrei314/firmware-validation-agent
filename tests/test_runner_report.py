from firmware_validation_agent.planner import MockPlanner
from firmware_validation_agent.report import render_markdown, summarize_results
from firmware_validation_agent.requirements import load_hardware_spec
from firmware_validation_agent.runner import ValidationRunner


def test_mock_planner_runner_covers_all_requirements():
    spec = load_hardware_spec("examples/optical_module_requirements.yaml")

    results = ValidationRunner(spec, MockPlanner()).run()
    summary = summarize_results(spec, results)

    assert all(item.passed for item in results)
    assert summary["coverage"] == 1.0
    assert summary["detected_faults"] >= 3


def test_report_contains_traceability_table():
    spec = load_hardware_spec("examples/optical_module_requirements.yaml")
    results = ValidationRunner(spec, MockPlanner()).run()

    report = render_markdown(spec, results)

    assert "Requirement coverage: 100.0%" in report
    assert "REQ-001" in report
    assert "scenario-req-001" in report
