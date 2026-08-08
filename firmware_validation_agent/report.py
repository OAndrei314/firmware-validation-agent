from __future__ import annotations

from pathlib import Path

from .requirements import HardwareSpec
from .runner import ValidationResult


def summarize_results(spec: HardwareSpec, results: list[ValidationResult]) -> dict[str, float | int]:
    total = len(results)
    passed = sum(1 for item in results if item.passed)
    covered = {item.requirement_id for item in results}
    detected = sum(1 for item in results if item.detected_fault)
    return {
        "total": total,
        "passed": passed,
        "pass_rate": passed / total if total else 0.0,
        "coverage": len(covered) / len(spec.requirements) if spec.requirements else 0.0,
        "detected_faults": detected,
    }


def release_gate(spec: HardwareSpec, results: list[ValidationResult], min_detected_faults: int = 3) -> dict[str, object]:
    summary = summarize_results(spec, results)
    blockers: list[str] = []
    if summary["coverage"] < 1.0:
        blockers.append("requirement_coverage_gap")
    if summary["pass_rate"] < 1.0:
        blockers.append("scenario_failures")
    if summary["detected_faults"] < min_detected_faults:
        blockers.append("fault_detection_unproven")
    coverage = float(summary["coverage"])
    pass_rate = float(summary["pass_rate"])
    fault_score = min(1.0, float(summary["detected_faults"]) / max(1, min_detected_faults))
    confidence = 0.50 * coverage + 0.35 * pass_rate + 0.15 * fault_score
    return {
        "decision": "release_candidate" if not blockers else "hold_for_debug",
        "validation_confidence": round(confidence, 3),
        "blockers": tuple(blockers),
        "minimum_detected_faults": min_detected_faults,
    }


def render_markdown(spec: HardwareSpec, results: list[ValidationResult]) -> str:
    summary = summarize_results(spec, results)
    gate = release_gate(spec, results)
    lines = [
        f"# Validation Report: {spec.module_name}",
        "",
        "## Summary",
        "",
        f"- Scenarios: {summary['total']}",
        f"- Passed: {summary['passed']}",
        f"- Pass rate: {summary['pass_rate']:.1%}",
        f"- Requirement coverage: {summary['coverage']:.1%}",
        f"- Faults detected: {summary['detected_faults']}",
        f"- Release gate: {gate['decision']} ({gate['validation_confidence']:.1%} confidence)",
        f"- Gate blockers: {', '.join(gate['blockers']) or 'none'}",
        "",
        "## Traceability",
        "",
        "| requirement | scenario | status | detected fault | details |",
        "| --- | --- | --- | --- | --- |",
    ]
    for result in results:
        status = "pass" if result.passed else "fail"
        fault = result.detected_fault or "-"
        lines.append(
            f"| {result.requirement_id} | {result.scenario_id} | {status} | {fault} | {result.details} |"
        )
    lines.extend(
        [
            "",
            "## Notes",
            "",
            "Synthetic simulator only. No proprietary hardware behavior or data is included.",
        ]
    )
    return "\n".join(lines) + "\n"


def write_report(path: str | Path, spec: HardwareSpec, results: list[ValidationResult]) -> None:
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_markdown(spec, results), encoding="utf-8")
