#!/usr/bin/env python3

from __future__ import annotations

import argparse
from pathlib import Path

from suite_runner import SKILL_DIR, run_suite


def main() -> int:
    parser = argparse.ArgumentParser(description="Run cr-st-expert customer acceptance suite")
    parser.add_argument("--output-root", default="output/reports/customer_acceptance", help="Output directory")
    args = parser.parse_args()

    output_root = Path(args.output_root)
    if not output_root.is_absolute():
        output_root = SKILL_DIR / output_root

    summary = run_suite(
        SKILL_DIR / "evals" / "customer_acceptance.json",
        output_root,
        "customer_acceptance_summary.json",
    )
    print(f"Customer acceptance suite: {summary['passed_count']}/{summary['total_count']} passed")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
