#!/usr/bin/env python3
"""Preflight planner for the cr-st-expert skill."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from planner import evaluate_request


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python scripts/main.py <input_json> [output_json]")
        return 1

    input_path = Path(sys.argv[1])
    output_path = Path(sys.argv[2]) if len(sys.argv) > 2 else input_path.with_suffix(".result.json")

    request = json.loads(input_path.read_text(encoding="utf-8"))
    result = evaluate_request(request)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[{result.status.upper()}] wrote result to {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
