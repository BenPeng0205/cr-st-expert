#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from suite_runner import SKILL_DIR, run_suite


def main() -> int:
    parser = argparse.ArgumentParser(description="Run cr-st-expert regression suite")
    parser.add_argument("--output-root", default="output/reports/regression", help="Output directory")
    args = parser.parse_args()

    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = SKILL_DIR / output_root

    summary = run_suite(SKILL_DIR / "evals" / "regression_suite.json", output_root, "regression_summary.json")
    print(f"Regression suite: {summary['passed_count']}/{summary['total_count']} passed")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
