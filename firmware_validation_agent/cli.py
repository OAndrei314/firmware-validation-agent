from __future__ import annotations

import argparse

from .planner import MockPlanner
from .report import render_markdown, write_report
from .requirements import load_hardware_spec
from .runner import ValidationRunner


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run synthetic firmware validation scenarios.")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("run", help="run validation and write a markdown report")
    run.add_argument("--requirements", required=True)
    run.add_argument("--out", required=True)
    run.add_argument("--print", action="store_true", dest="print_report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "run":
        spec = load_hardware_spec(args.requirements)
        results = ValidationRunner(spec, MockPlanner()).run()
        write_report(args.out, spec, results)
        if args.print_report:
            print(render_markdown(spec, results))
        return 0 if all(item.passed for item in results) else 1
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
