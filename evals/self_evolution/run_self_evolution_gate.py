"""Optional rule-maintenance check; does not use any memory service."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    required = ["SKILL.md", "test-prompts.json", "evals/self_evolution/criteria.json"]
    issues = [f"missing: {rel}" for rel in required if not (root / rel).is_file()]
    summary = {"gate_name": "rule_maintenance_v1", "passed": not issues, "issues": issues}
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
